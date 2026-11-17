"""No-Limit Hold'em for two to six players: one hand, with blinds, side pots and showdown.

Amounts are chips: the small blind is 1 and the big blind 2, so 1bb = 2 chips. Seats are numbered
clockwise. The seat after the button posts the small blind (heads-up, the button does), the next
one the big blind, and the action starts to the big blind's left. An all-in raise smaller than a
full raise does not reopen the betting: players who already acted may only call it or fold.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from holdem.core.cards import Card, cards_str
from holdem.core.evaluator import category_of_rank, evaluate
from holdem.engine.headsup import BIG_BLIND, SMALL_BLIND, STREETS, Action, IllegalActionError, Legal

MAX_SEATS = 6
_EARLY = ("UTG", "HJ", "CO")


def position_names(seats: int) -> tuple[str, ...]:
    """Position names in seat order starting at the button."""
    if seats == 2:
        return ("BTN", "BB")
    return ("BTN", "SB", "BB", *_EARLY[len(_EARLY) - (seats - 3) :])


@dataclass
class TableHand:
    stacks: list[int]  # chips behind at the start of the hand, one per seat
    button: int
    rng: random.Random
    hole: list[tuple[Card, Card]] = field(init=False)
    board: list[Card] = field(init=False, default_factory=list)
    behind: list[int] = field(init=False)
    bets: list[int] = field(init=False)  # chips bet on the current street
    committed: list[int] = field(init=False)  # chips put in over the whole hand
    folded: list[bool] = field(init=False)
    acted: list[bool] = field(init=False)
    pot: int = field(init=False, default=0)  # collected from finished streets
    street: int = field(init=False, default=0)
    current: int = field(init=False)
    last_raise: int = field(init=False, default=BIG_BLIND)
    log: list[Action] = field(init=False, default_factory=list)
    raisable: list[bool] = field(init=False, default_factory=list)  # per log entry: could raise
    finished: bool = field(init=False, default=False)
    winnings: list[int] = field(init=False)  # chips each seat takes from the pot
    showdown: bool = field(init=False, default=False)
    _deck: list[Card] = field(init=False)

    def __post_init__(self) -> None:
        n = len(self.stacks)
        if not 2 <= n <= MAX_SEATS or min(self.stacks) <= BIG_BLIND:
            raise ValueError("need two to six stacks larger than the big blind")
        deck = list(range(52))
        self.rng.shuffle(deck)
        self._deck = deck
        self.hole = [(deck.pop(), deck.pop()) for _ in range(n)]
        self.behind = list(self.stacks)
        self.bets = [0] * n
        self.committed = [0] * n
        self.folded = [False] * n
        self.acted = [False] * n
        self.winnings = [0] * n
        small = self.button if n == 2 else (self.button + 1) % n
        big = (small + 1) % n
        self._post(small, SMALL_BLIND)
        self._post(big, BIG_BLIND)
        self.current = (big + 1) % n

    # ----------------------------------------------------------------- queries

    @property
    def seats(self) -> int:
        return len(self.stacks)

    @property
    def street_name(self) -> str:
        return STREETS[self.street]

    @property
    def total_pot(self) -> int:
        return self.pot + sum(self.bets)

    @property
    def positions(self) -> list[str]:
        """Position name of every seat ("BTN", "SB", "BB", "UTG", "HJ", "CO")."""
        names = position_names(self.seats)
        return [names[(seat - self.button) % self.seats] for seat in range(self.seats)]

    def live(self) -> list[int]:
        """Seats that have not folded."""
        return [seat for seat in range(self.seats) if not self.folded[seat]]

    def legal(self) -> Legal:
        player = self.current
        top = max(self.bets)
        to_call = min(top - self.bets[player], self.behind[player])
        all_in_total = self.bets[player] + self.behind[player]
        opponents_with_chips = any(self.behind[s] > 0 for s in self.live() if s != player)
        return Legal(
            to_call=to_call,
            can_check=to_call == 0,
            # Acting again after already acting means a short all-in came in between.
            can_raise=opponents_with_chips and all_in_total > top and not self.acted[player],
            min_raise_to=min(top + max(self.last_raise, BIG_BLIND), all_in_total),
            max_raise_to=all_in_total,
        )

    def net(self) -> list[int]:
        """Chips won or lost by each seat in this hand (only once it is finished)."""
        return [self.behind[s] + self.winnings[s] - self.stacks[s] for s in range(self.seats)]

    # ----------------------------------------------------------------- actions

    def act(self, kind: str, to: int | None = None) -> None:
        if self.finished:
            raise IllegalActionError("the hand is over")
        legal = self.legal()
        player = self.current
        before = self.total_pot
        match kind:
            case "fold":
                if legal.can_check:
                    raise IllegalActionError("nothing to call: check instead of folding")
                self._record(player, "fold", 0, before, legal.to_call)
                self.folded[player] = True
            case "check":
                if not legal.can_check:
                    raise IllegalActionError("cannot check facing a bet")
                self._record(player, "check", 0, before, 0)
            case "call":
                if legal.can_check:
                    raise IllegalActionError("nothing to call")
                self._put(player, legal.to_call)
                self._record(player, "call", legal.to_call, before, legal.to_call)
            case "bet" | "raise":
                if to is None or not legal.can_raise:
                    raise IllegalActionError("raising is not allowed here")
                if not legal.min_raise_to <= to <= legal.max_raise_to:
                    raise IllegalActionError(
                        f"raise to between {legal.min_raise_to} and {legal.max_raise_to}"
                    )
                facing = max(self.bets)
                full = to - facing >= self.last_raise
                amount = to - self.bets[player]
                self._put(player, amount)
                self._record(
                    player, "bet" if facing == 0 else "raise", amount, before, legal.to_call
                )
                if full:  # a short all-in leaves earlier actors closed
                    self.last_raise = to - facing
                    self.acted = [False] * self.seats
            case _:
                raise IllegalActionError(f"unknown action {kind!r}")
        self.raisable.append(legal.can_raise)
        self.acted[player] = True
        self._advance()

    # ----------------------------------------------------------------- internals

    def _post(self, player: int, amount: int) -> None:
        pot = self.total_pot
        self._put(player, amount)
        self.log.append(Action("preflop", player, "post", amount, self.bets[player], pot, 0))
        self.raisable.append(False)

    def _put(self, player: int, amount: int) -> None:
        self.behind[player] -= amount
        self.bets[player] += amount
        self.committed[player] += amount

    def _record(self, player: int, kind: str, amount: int, pot: int, to_call: int) -> None:
        self.log.append(
            Action(self.street_name, player, kind, amount, self.bets[player], pot, to_call)
        )

    def _next_to_act(self, after: int) -> int | None:
        """The next seat clockwise that still owes a decision on this street."""
        top = max(self.bets)
        for step in range(1, self.seats + 1):
            seat = (after + step) % self.seats
            owes = not self.acted[seat] or self.bets[seat] < top
            if not self.folded[seat] and self.behind[seat] > 0 and owes:
                return seat
        return None

    def _advance(self) -> None:
        """Pass the action on, or close the street when nobody needs to act any more."""
        live = self.live()
        if len(live) == 1:
            self._collect()
            self.winnings[live[0]] = self.pot
            self.finished = True
            return
        seat = self._next_to_act(self.current)
        if seat is not None:
            self.current = seat
            return
        self._end_street()

    def _collect(self) -> None:
        """Return the uncalled part of the biggest bet and sweep the bets into the pot."""
        ranked = sorted(range(self.seats), key=lambda s: self.bets[s], reverse=True)
        high = ranked[0]
        excess = self.bets[high] - self.bets[ranked[1]]
        self.bets[high] -= excess
        self.committed[high] -= excess
        self.behind[high] += excess
        self.pot += sum(self.bets)
        self.bets = [0] * self.seats

    def _end_street(self) -> None:
        self._collect()
        can_bet = [s for s in self.live() if self.behind[s] > 0]
        if self.street == 3 or len(can_bet) < 2:
            self._show_down()
            return
        self.street += 1
        self.board.extend(self._deck.pop() for _ in range(3 if self.street == 1 else 1))
        self.acted = [False] * self.seats
        self.last_raise = BIG_BLIND
        first = self._next_to_act(self.button)
        assert first is not None
        self.current = first

    def _show_down(self) -> None:
        while len(self.board) < 5:
            self.board.append(self._deck.pop())
        self.street = 3
        self.showdown = True
        live = self.live()
        ranks = {s: evaluate([*self.hole[s], *self.board]) for s in live}
        paid = 0
        # One pot per all-in level: the main pot first, then each side pot.
        for level in sorted({self.committed[s] for s in live}):
            amount = sum(min(c, level) - min(c, paid) for c in self.committed)
            eligible = [s for s in live if self.committed[s] >= level]
            best = min(ranks[s] for s in eligible)
            self._pay(amount, [s for s in eligible if ranks[s] == best])
            paid = level
        self.finished = True

    def _pay(self, amount: int, winners: list[int]) -> None:
        share, odd = divmod(amount, len(winners))
        # Odd chips go to the winners closest to the button's left.
        winners.sort(key=lambda s: (s - self.button - 1) % self.seats)
        for place, seat in enumerate(winners):
            self.winnings[seat] += share + (place < odd)

    def made_hand(self, seat: int) -> str | None:
        """What a seat holds in words ("Two Pair"), once there is a flop."""
        if len(self.board) < 3:
            return None
        return category_of_rank(evaluate([*self.hole[seat], *self.board])).label

    def public(self, viewer: int, reveal: bool = False) -> dict[str, Any]:
        """The hand as ``viewer`` sees it; other hands only at showdown or with ``reveal``."""
        shown = [
            s == viewer or reveal or (self.showdown and not self.folded[s])
            for s in range(self.seats)
        ]
        return {
            "street": self.street_name,
            "button": self.button,
            "positions": self.positions,
            "board": [cards_str([c]) for c in self.board],
            "hole": [
                [cards_str([c]) for c in self.hole[s]] if shown[s] else None
                for s in range(self.seats)
            ],
            "made": [self.made_hand(s) if shown[s] else None for s in range(self.seats)],
            "behind": list(self.behind),
            "bets": list(self.bets),
            "folded": list(self.folded),
            "pot": self.total_pot,
            "current": None if self.finished else self.current,
            "finished": self.finished,
            "showdown": self.showdown,
            "net": self.net() if self.finished else None,
            "winners": [s for s, won in enumerate(self.winnings) if won],
            "last": self.log[-1].public(),
            "log": [a.public() for a in self.log],
        }
