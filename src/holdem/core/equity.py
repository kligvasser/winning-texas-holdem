"""Equity calculation for two or more players, each holding a known hand or a range.

Small problems are enumerated exactly; larger ones fall back to seeded Monte Carlo sampling. A tie
splits the pot evenly among the tied players, so equity = win + share of ties.
"""

from __future__ import annotations

import itertools
import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

from phevaluator import evaluate_cards

from holdem.core.cards import Card, remaining_deck
from holdem.core.ranges import Combo, Range

type WeightedCombos = list[tuple[Combo, float]]
type PlayerHolding = Combo | Range | WeightedCombos

DEFAULT_EXACT_LIMIT = 6_000_000
DEFAULT_SAMPLES = 40_000


@dataclass(frozen=True)
class PlayerEquity:
    equity: float
    win: float
    tie: float


@dataclass(frozen=True)
class EquityResult:
    players: tuple[PlayerEquity, ...]
    exact: bool
    trials: int

    def __getitem__(self, index: int) -> PlayerEquity:
        return self.players[index]


def _is_combo(holding: object) -> bool:
    return (
        isinstance(holding, tuple)
        and len(holding) == 2
        and all(isinstance(c, int) for c in holding)
    )


def _normalize(holding: PlayerHolding, dead: set[Card]) -> WeightedCombos:
    if isinstance(holding, Range):
        combos = holding.combos(dead)
    elif _is_combo(holding):
        combo: Combo = holding  # type: ignore[assignment]
        if combo[0] == combo[1]:
            raise ValueError("a hand needs two different cards")
        combos = [(combo, 1.0)] if not (set(combo) & dead) else []
    else:
        combos = [(c, w) for c, w in holding if w > 0 and not (set(c) & dead)]  # type: ignore[union-attr]
    if not combos:
        raise ValueError("a player has no possible hands given the dead cards")
    return combos


def _known_cards(players: list[WeightedCombos]) -> set[Card]:
    return {card for combos in players if len(combos) == 1 for card in combos[0][0]}


def calculate_equity(
    players: Sequence[PlayerHolding],
    board: Sequence[Card] = (),
    dead: Sequence[Card] = (),
    *,
    samples: int = DEFAULT_SAMPLES,
    seed: int = 0,
    exact_limit: int = DEFAULT_EXACT_LIMIT,
) -> EquityResult:
    """Equity of each player at showdown, exact when the work fits under ``exact_limit``."""
    if len(players) < 2:
        raise ValueError("need at least two players")
    if len(board) > 5 or len(set(board)) != len(board):
        raise ValueError("board must be up to five distinct cards")
    blocked = set(board) | set(dead)
    if len(blocked) != len(board) + len(dead):
        raise ValueError("board and dead cards overlap")

    normalized = [_normalize(p, blocked) for p in players]
    # Known single hands block each other's ranges too.
    known = _known_cards(normalized)
    normalized = [
        combos if len(combos) == 1 else _normalize(combos, blocked | known) for combos in normalized
    ]
    if len(known) != 2 * sum(1 for c in normalized if len(c) == 1):
        raise ValueError("two players hold the same card")

    to_come = 5 - len(board)
    deck_size = 52 - len(blocked) - 2 * len(players)
    runouts = math.comb(deck_size, to_come)
    work = math.prod(len(c) for c in normalized) * runouts * len(players)
    if work <= exact_limit:
        return _exact(normalized, list(board), blocked)
    return _monte_carlo(normalized, list(board), blocked, samples, seed)


def _settle(
    ranks: list[int], weight: float, wins: list[float], ties: list[float], eq: list[float]
) -> None:
    best = min(ranks)
    winners = [i for i, r in enumerate(ranks) if r == best]
    if len(winners) == 1:
        wins[winners[0]] += weight
        eq[winners[0]] += weight
        return
    share = weight / len(winners)
    for i in winners:
        ties[i] += weight
        eq[i] += share


def _result(
    wins: list[float], ties: list[float], eq: list[float], total: float, exact: bool, trials: int
) -> EquityResult:
    if total == 0:
        raise ValueError("no valid deal: every combination of hands conflicts")
    return EquityResult(
        players=tuple(
            PlayerEquity(equity=e / total, win=w / total, tie=t / total)
            for w, t, e in zip(wins, ties, eq, strict=True)
        ),
        exact=exact,
        trials=trials,
    )


def _exact(players: list[WeightedCombos], board: list[Card], blocked: set[Card]) -> EquityResult:
    n = len(players)
    wins, ties, eq = [0.0] * n, [0.0] * n, [0.0] * n
    total = 0.0
    trials = 0
    to_come = 5 - len(board)
    for assignment in itertools.product(*players):
        used = [card for combo, _ in assignment for card in combo]
        if len(set(used)) != len(used):
            continue
        weight = math.prod(w for _, w in assignment)
        deck = remaining_deck(blocked | set(used))
        hands = [combo for combo, _ in assignment]
        for runout in itertools.combinations(deck, to_come):
            full = (*board, *runout)
            ranks = [evaluate_cards(*hand, *full) for hand in hands]
            _settle(ranks, weight, wins, ties, eq)
            total += weight
            trials += 1
    return _result(wins, ties, eq, total, exact=True, trials=trials)


def _monte_carlo(
    players: list[WeightedCombos], board: list[Card], blocked: set[Card], samples: int, seed: int
) -> EquityResult:
    rng = random.Random(seed)
    n = len(players)
    wins, ties, eq = [0.0] * n, [0.0] * n, [0.0] * n
    combos = [[c for c, _ in p] for p in players]
    weights = [[w for _, w in p] for p in players]
    base_deck = remaining_deck(blocked)
    to_come = 5 - len(board)
    accepted = 0
    attempts = 0
    max_attempts = samples * 50
    while accepted < samples:
        attempts += 1
        if attempts > max_attempts:
            raise ValueError("ranges conflict too often to sample")
        hands = [rng.choices(combos[i], weights[i])[0] for i in range(n)]
        used = {card for hand in hands for card in hand}
        if len(used) != 2 * n:
            continue
        runout = rng.sample([c for c in base_deck if c not in used], to_come)
        full = (*board, *runout)
        ranks = [evaluate_cards(*hand, *full) for hand in hands]
        _settle(ranks, 1.0, wins, ties, eq)
        accepted += 1
    return _result(wins, ties, eq, float(samples), exact=False, trials=samples)
