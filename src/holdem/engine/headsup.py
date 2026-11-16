"""Heads-up No-Limit Hold'em: one hand, with blinds, betting rounds, all-ins and showdown.

Amounts are chips: the small blind is 1 and the big blind 2, so 1bb = 2 chips. The button posts the
small blind, acts first preflop and last on every later street. With only two players a raise
against an all-in player is meaningless, so the player facing an all-in may only call or fold.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from holdem.core.cards import Card, cards_str
from holdem.core.evaluator import compare

SMALL_BLIND = 1
BIG_BLIND = 2
STREETS = ("preflop", "flop", "turn", "river")


@dataclass(frozen=True)
class Action:
    street: str
    player: int
    kind: str  # post, fold, check, call, bet, raise
    amount: int  # chips put in by this action
    to: int  # the player's total bet on this street afterwards
    pot: int  # chips in the middle before the action, including both players' street bets
    to_call: int  # what the player had to call before acting

    def public(self) -> dict[str, Any]:
        return {
            "street": self.street,
            "player": self.player,
            "kind": self.kind,
            "amount": self.amount,
            "to": self.to,
            "pot": self.pot,
            "to_call": self.to_call,
        }


@dataclass(frozen=True)
class Legal:
    to_call: int
    can_check: bool
    can_raise: bool
    min_raise_to: int  # smallest legal total bet when betting or raising
    max_raise_to: int  # all-in total


class IllegalActionError(ValueError):
    pass


@dataclass
class HeadsUpHand:
    stacks: list[int]  # chips behind at the start of the hand
    button: int
    rng: random.Random
    hole: list[tuple[Card, Card]] = field(init=False)
    board: list[Card] = field(init=False, default_factory=list)
    behind: list[int] = field(init=False)
    bets: list[int] = field(init=False)
    pot: int = field(init=False, default=0)  # collected from finished streets
    street: int = field(init=False, default=0)
    current: int = field(init=False)
    acted: list[bool] = field(init=False)
    last_raise: int = field(init=False, default=BIG_BLIND)
    log: list[Action] = field(init=False, default_factory=list)
    finished: bool = field(init=False, default=False)
    winnings: list[int] = field(init=False)  # chips each player takes from the pot
    showdown: bool = field(init=False, default=False)
    _deck: list[Card] = field(init=False)

    def __post_init__(self) -> None:
        if len(self.stacks) != 2 or min(self.stacks) <= BIG_BLIND:
            raise ValueError("need two stacks larger than the big blind")
        deck = list(range(52))
        self.rng.shuffle(deck)
        self._deck = deck
        self.hole = [(deck.pop(), deck.pop()), (deck.pop(), deck.pop())]
        self.behind = list(self.stacks)
        self.bets = [0, 0]
        self.acted = [False, False]
        self.winnings = [0, 0]
        small, big = self.button, 1 - self.button
        self._post(small, SMALL_BLIND)
        self._post(big, BIG_BLIND)
        self.current = small

    # ----------------------------------------------------------------- queries

    @property
    def street_name(self) -> str:
        return STREETS[self.street]

    @property
    def total_pot(self) -> int:
        return self.pot + sum(self.bets)

    def legal(self) -> Legal:
        player = self.current
        other = 1 - player
        to_call = min(max(self.bets) - self.bets[player], self.behind[player])
        all_in_total = self.bets[player] + self.behind[player]
        can_raise = self.behind[other] > 0 and self.behind[player] > to_call
        min_to = max(self.bets) + max(self.last_raise, BIG_BLIND)
        return Legal(
            to_call=to_call,
            can_check=to_call == 0,
            can_raise=can_raise,
            min_raise_to=min(min_to, all_in_total),
            max_raise_to=all_in_total,
        )

    def net(self) -> list[int]:
        """Chips won or lost by each player in this hand (only once it is finished)."""
        final = [self.behind[i] + self.winnings[i] for i in (0, 1)]
        return [final[i] - self.stacks[i] for i in (0, 1)]

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
                self._award([1 - player])
                return
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
                self.last_raise = max(self.last_raise, to - facing)
                amount = to - self.bets[player]
                self._put(player, amount)
                name = "bet" if facing == 0 else "raise"
                self._record(player, name, amount, before, legal.to_call)
                self.acted[1 - player] = False
            case _:
                raise IllegalActionError(f"unknown action {kind!r}")
        self.acted[player] = True
        self._advance()

    # ----------------------------------------------------------------- internals

    def _post(self, player: int, amount: int) -> None:
        self._put(player, amount)
        self.log.append(Action("preflop", player, "post", amount, self.bets[player], 0, 0))

    def _put(self, player: int, amount: int) -> None:
        self.behind[player] -= amount
        self.bets[player] += amount

    def _record(self, player: int, kind: str, amount: int, pot: int, to_call: int) -> None:
        self.log.append(
            Action(self.street_name, player, kind, amount, self.bets[player], pot, to_call)
        )

    def _advance(self) -> None:
        """Pass the action on, or close the street when nobody needs to act any more."""
        other = 1 - self.current
        must_act = not self.acted[other] or self.bets[other] < max(self.bets)
        if self.behind[other] > 0 and must_act:
            self.current = other
            return
        self._end_street()

    def _end_street(self) -> None:
        # Return an uncalled part of a bet.
        high = 0 if self.bets[0] > self.bets[1] else 1
        excess = self.bets[high] - self.bets[1 - high]
        if excess:
            self.bets[high] -= excess
            self.behind[high] += excess
        self.pot += sum(self.bets)
        self.bets = [0, 0]
        if 0 in self.behind or self.street == 3:
            self._run_out()
            return
        self.street += 1
        self._deal_board()
        self.acted = [False, False]
        self.last_raise = BIG_BLIND
        self.current = 1 - self.button

    def _deal_board(self) -> None:
        count = 3 if self.street == 1 else 1
        self.board.extend(self._deck.pop() for _ in range(count))

    def _run_out(self) -> None:
        while len(self.board) < 5:
            self.street = min(self.street + 1, 3)
            self.board.append(self._deck.pop())
        self.showdown = True
        result = compare(self.hole[0], self.hole[1], self.board)
        winners = [0] if result > 0 else [1] if result < 0 else [0, 1]
        self._award(winners)

    def _award(self, winners: list[int]) -> None:
        self.pot += sum(self.bets)
        self.bets = [0, 0]
        share, odd = divmod(self.pot, len(winners))
        for w in winners:
            self.winnings[w] += share
        if odd:  # an odd chip goes to the player out of position (the big blind)
            self.winnings[1 - self.button] += odd
        self.finished = True

    def public(self, viewer: int, reveal: bool = False) -> dict[str, Any]:
        """The hand as ``viewer`` sees it; the opponent's cards only at showdown or ``reveal``."""
        show = reveal or self.showdown
        return {
            "street": self.street_name,
            "button": self.button,
            "board": [cards_str([c]) for c in self.board],
            "hole": [
                [cards_str([c]) for c in self.hole[p]] if p == viewer or show else None
                for p in (0, 1)
            ],
            "behind": list(self.behind),
            "bets": list(self.bets),
            "pot": self.total_pot,
            "current": None if self.finished else self.current,
            "finished": self.finished,
            "showdown": self.showdown,
            "net": self.net() if self.finished else None,
            "log": [a.public() for a in self.log],
        }
