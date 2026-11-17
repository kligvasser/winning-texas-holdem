"""Reading the bots at the six-max table: their likely hands, your equity, and what a bet earns.

A bot's range starts from its style, position and preflop actions. Every action it takes after
the flop then reweights each hand by how often that style plays it that way, the same numbers the
bot itself rolls against. A bot that bets twice is therefore weighted towards the hands it bets.

``push_value`` estimates a bet or raise: each opponent folds as often as its style says for the
hand it holds, and whoever continues is assumed to call and see a showdown with no further
betting. That last part is a simplification, so the result is an estimate.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from functools import lru_cache

from holdem.core.cards import Card
from holdem.core.equity import WeightedCombos, calculate_equity
from holdem.core.evaluator import evaluate
from holdem.core.ranges import Combo
from holdem.engine.bots import (
    CLASSES,
    Style,
    hand_class,
    postflop_odds,
    seat_range,
    top_share_range,
)
from holdem.engine.headsup import Action
from holdem.engine.table import TableHand

HERO = 0
BOARD_CARDS = {"preflop": 0, "flop": 3, "turn": 4, "river": 5}
PUSH_SAMPLES = 1000


def opponents_in_pot(hand: TableHand, log: list[Action], street: str) -> list[int]:
    """The seats whose ranges you are up against at a point in the hand.

    After the flop that is everyone who has not folded. Before it, players still to act mostly
    fold, so only those who called or raised count (or the big blind when nobody has yet).
    """
    folded = {a.player for a in log if a.kind == "fold"}
    live = [s for s in range(1, hand.seats) if s not in folded]
    if street != "preflop":
        return live
    entered = {a.player for a in log if a.kind in ("call", "raise")}
    return [s for s in live if s in entered] or [hand.positions.index("BB")]


@lru_cache(maxsize=200_000)
def _group(combo: Combo, board: tuple[Card, ...]) -> str:
    return hand_class(combo, list(board))


def likely_ranges(
    styles: list[Style], hand: TableHand, upto: int, street: str
) -> dict[int, WeightedCombos]:
    """Each opponent's weighted hands just before log entry ``upto``, on ``street``."""
    log = hand.log[:upto]
    dead = set(hand.hole[HERO]) | set(hand.board[: BOARD_CARDS[street]])
    result: dict[int, WeightedCombos] = {}
    for seat in opponents_in_pot(hand, log, street):
        style = styles[seat - 1]
        start = seat_range(style, log, seat, hand.positions[seat]).combos(dead)
        weights = dict(start or top_share_range(1.0).combos(dead))
        for index, action in enumerate(log):
            if action.player != seat or action.street == "preflop":
                continue
            board = tuple(hand.board[: BOARD_CARDS[action.street]])
            odds = {
                group: postflop_odds(
                    style, group, action.to_call, action.pot, hand.raisable[index]
                ).get(action.kind, 0.0)
                for group in CLASSES
            }
            narrowed = {c: w * odds[_group(c, board)] for c, w in weights.items()}
            narrowed = {c: w for c, w in narrowed.items() if w > 0}
            weights = narrowed or weights  # an action the model calls impossible teaches nothing
        result[seat] = list(weights.items())
    return result


def equity_against(
    styles: list[Style], hand: TableHand, upto: int, street: str
) -> tuple[float, int]:
    """Hero's equity against the likely hands of the opponents in the pot, and their number."""
    ranges = likely_ranges(styles, hand, upto, street)
    result = calculate_equity(
        [hand.hole[HERO], *ranges.values()],
        hand.board[: BOARD_CARDS[street]],
        samples=1500,
        seed=upto,
        exact_limit=300_000,
    )
    return result[0].equity, len(ranges)


@dataclass(frozen=True)
class Push:
    """What a bet or raise is worth, in chips, next to the passive play."""

    aggressive: float  # EV of the bet or raise
    passive: float  # EV of checking, or of the better of calling and folding
    alternative: str  # "checking", "calling" or "folding"
    fold_all: float  # how often everybody folds
    called_equity: float  # your share of the pot when somebody continues


def _share(mine: int, others: list[int]) -> float:
    """Hero's share of a showdown against these ranks (lower is better)."""
    best = min(others)
    if mine > best:
        return 0.0
    return 1.0 if mine < best else 1 / (1 + others.count(best))


def push_value(
    styles: list[Style], hand: TableHand, index: int, samples: int = PUSH_SAMPLES
) -> Push | None:
    """Estimate hero's bet or raise at log entry ``index`` (after the flop)."""
    action = hand.log[index]
    board = hand.board[: BOARD_CARDS[action.street]]
    ranges = likely_ranges(styles, hand, index, action.street)
    seats = list(ranges)
    extra = action.amount - action.to_call  # what each opponent has to add to continue
    faced = action.pot + action.amount
    stay = {
        seat: {
            group: 1 - postflop_odds(styles[seat - 1], group, extra, faced, True)["fold"]
            for group in CLASSES
        }
        for seat in seats
    }
    combos = {s: [c for c, _ in ranges[s]] for s in seats}
    weights = {s: [w for _, w in ranges[s]] for s in seats}
    deck = [c for c in range(52) if c not in board and c not in hand.hole[HERO]]
    rng = random.Random(index)
    accepted = 0
    call_ev = check_ev = aggressive = fold_all = called = called_share = 0.0
    for _ in range(samples * 4):
        if accepted == samples:
            break
        holes = [rng.choices(combos[s], weights[s])[0] for s in seats]
        used = {card for hole in holes for card in hole}
        if len(used) != 2 * len(seats):
            continue
        accepted += 1
        runout = rng.sample([c for c in deck if c not in used], 5 - len(board))
        full = [*board, *runout]
        mine = evaluate([*hand.hole[HERO], *full])
        ranks = [evaluate([*hole, *full]) for hole in holes]
        everyone = _share(mine, ranks)
        check_ev += everyone * action.pot
        call_ev += everyone * (action.pot + action.to_call) - action.to_call
        stays = [stay[s][_group(hole, tuple(board))] for s, hole in zip(seats, holes, strict=True)]
        for subset in itertools.product((False, True), repeat=len(seats)):
            chance = 1.0
            for stays_in, p in zip(subset, stays, strict=True):
                chance *= p if stays_in else 1 - p
            callers = [r for r, stays_in in zip(ranks, subset, strict=True) if stays_in]
            if not callers:
                fold_all += chance
                aggressive += chance * action.pot
                continue
            share = _share(mine, callers)
            aggressive += chance * (share * (faced + extra * len(callers)) - action.amount)
            called += chance
            called_share += chance * share
    if not accepted:
        return None
    if action.to_call == 0:
        passive, alternative = check_ev / accepted, "checking"
    elif call_ev > 0:
        passive, alternative = call_ev / accepted, "calling"
    else:
        passive, alternative = 0.0, "folding"
    return Push(
        aggressive=aggressive / accepted,
        passive=passive,
        alternative=alternative,
        fold_all=fold_all / accepted,
        called_equity=called_share / called if called else 0.0,
    )
