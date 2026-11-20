"""Toy betting games: the AKQ game and the 1-to-10 card game from the MIT problem set.

Both are the same half-street game with a different deck. Two players ante 1 chip and get one card
each. The caller checks dark. The bettor either checks (showdown for the antes) or bets 1 chip;
facing a bet the caller calls or folds. The higher card wins.

A strategy is just one number per card: how often the bettor bets it, and how often the caller
calls with it. That makes everything exact: the value of each action against any opponent, the best
response, and the optimal (Nash) strategy, which is solved numerically here rather than typed in.
"""

from __future__ import annotations

import random
import secrets
import uuid
from dataclasses import dataclass, field
from functools import cache
from typing import Any

ANTE = 1
BET = 1
SOLVER_ROUNDS = 4000
EPSILON = 0.01  # chips: values closer than this count as equal


@dataclass(frozen=True)
class Game:
    key: str
    name: str
    blurb: str
    cards: tuple[str, ...]  # weakest first

    @property
    def size(self) -> int:
        return len(self.cards)

    def public(self) -> dict[str, Any]:
        return {"key": self.key, "name": self.name, "blurb": self.blurb, "cards": list(self.cards)}


GAMES: dict[str, Game] = {
    g.key: g
    for g in (
        Game(
            "akq",
            "The AKQ game",
            "Three cards. The ace always wins, the queen can only bluff, and the king has to "
            "guess. The smallest game with a real bluffing decision.",
            ("Q", "K", "A"),
        ),
        Game(
            "ten",
            "The 1 to 10 game",
            "Ten cards, from the MIT problem set. Which cards are worth a value bet, which "
            "should bluff, and which can call?",
            tuple(str(n) for n in range(1, 11)),
        ),
    )
}


@dataclass(frozen=True)
class Strategy:
    bet: tuple[float, ...]  # how often the bettor bets each card
    call: tuple[float, ...]  # how often the caller calls with each card


# ----------------------------------------------------------------- exact values


def _others(game: Game, card: int) -> list[int]:
    return [c for c in range(game.size) if c != card]


def bettor_values(game: Game, card: int, call: tuple[float, ...]) -> dict[str, float]:
    """Average chips won by checking and by betting ``card`` against a calling strategy."""
    others = _others(game, card)
    check = sum(ANTE if card > o else -ANTE for o in others) / len(others)
    bet = 0.0
    for o in others:
        showdown = ANTE + BET if card > o else -(ANTE + BET)
        bet += call[o] * showdown + (1 - call[o]) * ANTE
    return {"bet": bet / len(others), "check": check}


def caller_values(game: Game, card: int, bet: tuple[float, ...]) -> dict[str, float]:
    """Average chips won by calling and by folding ``card`` against a betting strategy."""
    others = _others(game, card)
    total = sum(bet[o] for o in others)
    # If the opponent never bets any of these cards the spot cannot happen: weigh them equally.
    weights = [bet[o] / total if total else 1 / len(others) for o in others]
    call = sum(
        w * (ANTE + BET if card > o else -(ANTE + BET))
        for w, o in zip(weights, others, strict=True)
    )
    return {"call": call, "fold": -float(ANTE)}


@cache
def nash(game: Game) -> Strategy:
    """The optimal strategy, found by regret matching (CFR+) with weighted averaging."""
    n = game.size
    # Regrets for the aggressive action (bet, call) and the passive one (check, fold).
    regret_bet = [[0.0, 0.0] for _ in range(n)]
    regret_call = [[0.0, 0.0] for _ in range(n)]
    sum_bet = [0.0] * n
    sum_call = [0.0] * n

    def current(regrets: list[list[float]]) -> tuple[float, ...]:
        return tuple(r[0] / (r[0] + r[1]) if r[0] + r[1] > 0 else 0.5 for r in regrets)

    for round_ in range(1, SOLVER_ROUNDS + 1):
        call = current(regret_call)
        for card in range(n):
            values = bettor_values(game, card, call)
            p = current(regret_bet)[card]
            node = p * values["bet"] + (1 - p) * values["check"]
            regret_bet[card][0] = max(0.0, regret_bet[card][0] + values["bet"] - node)
            regret_bet[card][1] = max(0.0, regret_bet[card][1] + values["check"] - node)
        bet = current(regret_bet)
        for card in range(n):
            # Counterfactual values: weighted by how often the bettor actually bets.
            reach = sum(bet[o] for o in _others(game, card)) / (n - 1)
            values = caller_values(game, card, bet)
            p = call[card]
            node = p * values["call"] + (1 - p) * values["fold"]
            regret_call[card][0] = max(0.0, regret_call[card][0] + reach * (values["call"] - node))
            regret_call[card][1] = max(0.0, regret_call[card][1] + reach * (values["fold"] - node))
        for card in range(n):
            sum_bet[card] += round_ * bet[card]
            sum_call[card] += round_ * current(regret_call)[card]
    weight = SOLVER_ROUNDS * (SOLVER_ROUNDS + 1) / 2
    call = tuple(s / weight for s in sum_call)
    return Strategy(tuple(s / weight for s in sum_bet), _threshold(game, call))


def _threshold(game: Game, call: tuple[float, ...]) -> tuple[float, ...]:
    """The same amount of calling, done with the highest cards first.

    Cards that only beat a bluff are interchangeable, so the solver may spread its calls over
    them in any way. Calling from the top down is the form people learn; it is kept only if the
    bettor cannot gain anything against it.
    """
    mixed = [card for card in range(game.size) if 0.02 < call[card] < 0.98]
    mass = sum(call[card] for card in mixed)
    tidy = list(call)
    for card in reversed(mixed):
        tidy[card] = min(1.0, mass)
        mass -= tidy[card]

    def bettor_gain(strategy: tuple[float, ...]) -> float:
        return sum(max(bettor_values(game, c, strategy).values()) for c in range(game.size))

    return tuple(tidy) if bettor_gain(tuple(tidy)) <= bettor_gain(call) + 1e-3 else call


def _pick(values: dict[str, float], active: str, passive: str, tie: float) -> float:
    gap = values[active] - values[passive]
    if abs(gap) < EPSILON:
        return tie
    return 1.0 if gap > 0 else 0.0


def best_response(game: Game, opponent: Strategy) -> Strategy:
    """The most profitable strategy against ``opponent`` (the optimal mix where it is a tie)."""
    optimal = nash(game)
    return Strategy(
        tuple(
            _pick(bettor_values(game, c, opponent.call), "bet", "check", optimal.bet[c])
            for c in range(game.size)
        ),
        tuple(
            _pick(caller_values(game, c, opponent.bet), "call", "fold", optimal.call[c])
            for c in range(game.size)
        ),
    )


# ----------------------------------------------------------------- opponents


def _top(game: Game, share: float) -> set[int]:
    """The best ``share`` of the deck, at least one card."""
    count = max(1, round(game.size * share))
    return set(range(game.size - count, game.size))


def _only(game: Game, cards: set[int]) -> tuple[float, ...]:
    return tuple(1.0 if c in cards else 0.0 for c in range(game.size))


@dataclass(frozen=True)
class Opponent:
    key: str  # the avatar, shared with the six-max bots
    character: str
    name: str
    blurb: str

    def strategy(self, game: Game) -> Strategy:
        everything = set(range(game.size))
        match self.key:
            case "station":
                return Strategy(_only(game, _top(game, 0.2)), _only(game, everything - {0}))
            case "nit":
                return Strategy(_only(game, _top(game, 1 / 3)), _only(game, _top(game, 0.2)))
            case "maniac":
                return Strategy(_only(game, everything), _only(game, _top(game, 2 / 3)))
            case _:
                return nash(game)

    def public(self) -> dict[str, str]:
        return {
            "key": self.key,
            "character": self.character,
            "name": self.name,
            "blurb": self.blurb,
        }


OPPONENTS: dict[str, Opponent] = {
    o.key: o
    for o in (
        Opponent(
            "tag",
            "Finn",
            "Optimal",
            "Plays the unexploitable mix. You cannot beat it, only lose less: try to copy it.",
        ),
        Opponent(
            "station",
            "Moby",
            "Calling station",
            "Calls with almost anything and only bets its best cards. Never bluff; "
            "bet more of your good cards for value and fold when it bets.",
        ),
        Opponent(
            "nit",
            "Rocky",
            "Nit",
            "Never bluffs and folds far too often. Bluff your worst cards every time, "
            "and fold everything but the top when it bets.",
        ),
        Opponent(
            "maniac",
            "Blaze",
            "Maniac",
            "Bets every card and calls a lot. Call it down with anything decent, and bluff less.",
        ),
    )
}


# ----------------------------------------------------------------- session

ROLES = ("bettor", "caller")
ACTIONS = {"bettor": ("bet", "check"), "caller": ("call", "fold")}


@dataclass
class Tally:
    """How often you took the aggressive action with one card."""

    seen: int = 0
    taken: int = 0

    def public(self, optimal: float, best: float) -> dict[str, Any]:
        return {
            "n": self.seen,
            "yours": round(self.taken / self.seen, 3) if self.seen else None,
            "optimal": round(optimal, 3),
            "best": round(best, 3),
        }


@dataclass
class ToySession:
    game: Game
    opponent: Opponent
    seed: int
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    hands_played: int = 0
    chips: int = 0
    expected: float = 0.0  # what your choices earn on average against this opponent
    best: float = 0.0  # what the best choices would have earned
    role: str = field(init=False, default="bettor")
    card: int = field(init=False)
    their_card: int = field(init=False)
    before: list[dict[str, Any]] = field(init=False, default_factory=list)
    last: dict[str, Any] | None = field(init=False, default=None)
    _rng: random.Random = field(init=False)
    _theirs: Strategy = field(init=False)
    _bets: list[Tally] = field(init=False)
    _calls: list[Tally] = field(init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self._theirs = self.opponent.strategy(self.game)
        self._bets = [Tally() for _ in self.game.cards]
        self._calls = [Tally() for _ in self.game.cards]
        self._deal()

    def _deal(self) -> None:
        """Deal hands until one needs a decision from you; roles alternate every hand."""
        self.before = []
        while True:
            self.role = ROLES[self.hands_played % 2]
            self.card, self.their_card = self._rng.sample(range(self.game.size), 2)
            if self.role == "bettor" or self._rng.random() < self._theirs.bet[self.their_card]:
                return
            # The opponent checked behind: a showdown with nothing for you to decide.
            chips = ANTE if self.card > self.their_card else -ANTE
            self._settle(chips, float(chips), float(chips))
            self.before.append(self._outcome("check", chips))

    def _settle(self, chips: int, expected: float, best: float) -> None:
        self.hands_played += 1
        self.chips += chips
        self.expected += expected
        self.best += best

    def _outcome(self, their_action: str, chips: int) -> dict[str, Any]:
        return {
            "role": self.role,
            "card": self.game.cards[self.card],
            "their_card": self.game.cards[self.their_card],
            "their_action": their_action,
            "chips": chips,
        }

    def act(self, action: str) -> None:
        if action not in ACTIONS[self.role]:
            raise ValueError(f"you can {' or '.join(ACTIONS[self.role])} here")
        game, card, them = self.game, self.card, self.their_card
        wins = card > them
        if self.role == "bettor":
            values = bettor_values(game, card, self._theirs.call)
            optimal = nash(game).bet[card]
            tally = self._bets[card]
            if action == "check":
                their_action, chips = "check", ANTE if wins else -ANTE
            elif self._rng.random() < self._theirs.call[them]:
                their_action, chips = "call", ANTE + BET if wins else -(ANTE + BET)
            else:
                their_action, chips = "fold", ANTE
        else:
            values = caller_values(game, card, self._theirs.bet)
            optimal = nash(game).call[card]
            tally = self._calls[card]
            their_action = "bet"
            chips = -ANTE if action == "fold" else ANTE + BET if wins else -(ANTE + BET)
        active = ACTIONS[self.role][0]
        tally.seen += 1
        tally.taken += action == active
        best = max(values, key=lambda k: values[k])
        self.last = {
            **self._outcome(their_action, chips),
            "action": action,
            "values": {k: round(v, 3) for k, v in values.items()},
            "best": best,
            "active": active,
            "optimal": round(optimal, 3),
            "lesson": self._lesson(action, values, best, optimal),
        }
        self._settle(chips, values[action], values[best])
        self._deal()

    def _lesson(self, action: str, values: dict[str, float], best: str, optimal: float) -> str:
        card = self.game.cards[self.card]
        who = self.opponent.character
        active, passive = ACTIONS[self.role]
        if abs(values[active] - values[passive]) < EPSILON:
            return (
                f"Against {who}, {active} and {passive} earn the same with the {card} "
                f"({values[active]:+.2f} chips): the optimal mix is to {active} {optimal:.0%} "
                "of the time."
            )
        other = passive if best == active else active
        opening = "Right" if action == best else "Not this time"
        return (
            f"{opening}: against {who}, to {best} the {card} earns {values[best]:+.2f} chips on "
            f"average and to {other} earns {values[other]:+.2f}."
        )

    def summary(self) -> dict[str, Any]:
        optimal = nash(self.game)
        best = best_response(self.game, self._theirs)
        return {
            "chips": self.chips,
            "expected": round(self.expected, 2),
            "best": round(self.best, 2),
            "cards": [
                {
                    "card": label,
                    "bet": self._bets[c].public(optimal.bet[c], best.bet[c]),
                    "call": self._calls[c].public(optimal.call[c], best.call[c]),
                }
                for c, label in enumerate(self.game.cards)
            ],
        }

    def state(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "game": self.game.public(),
            "opponent": self.opponent.public(),
            "hand": {
                "number": self.hands_played + 1,
                "role": self.role,
                "card": self.game.cards[self.card],
                "actions": list(ACTIONS[self.role]),
                "before": self.before,
            },
            "last": self.last,
            "hands_played": self.hands_played,
            "summary": self.summary(),
        }


def new_toy_session(game: str, opponent: str, seed: int | None = None) -> ToySession:
    """Start a session; raises ``KeyError`` for an unknown game or opponent."""
    return ToySession(
        GAMES[game], OPPONENTS[opponent], secrets.randbits(63) if seed is None else seed
    )
