"""Rule-based opponents with recognisable styles.

``Bot`` plays heads-up; ``SeatBot`` plays the six-max table with the same postflop logic and
position-aware preflop thresholds.

Preflop, a bot ranks its hand by equity against a random hand and compares the rank with
thresholds ("plays the top 55% from the button"). Postflop it sorts its hand into a class (monster,
strong, medium, draw, air) and bets, calls or raises with per-class frequencies. Styles differ only
in their numbers, so each is easy to describe and to exploit.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache

from holdem.core.ranges import ALL_CLASSES, Range, class_combo_count, class_of_combo
from holdem.drills.scenarios import hand_strength
from holdem.engine.headsup import BIG_BLIND, Action, HeadsUpHand
from holdem.engine.table import TableHand
from holdem.stories import PREDICATES

CLASSES = ("monster", "strong", "medium", "draw", "air")


@cache
def percentile() -> dict[str, float]:
    """Share of all combos at least as strong as each hand class (AA is about 0.5%)."""
    ordered = sorted(ALL_CLASSES, key=lambda c: -hand_strength()[c])
    result: dict[str, float] = {}
    total = 0
    for hand_class in ordered:
        total += class_combo_count(hand_class)
        result[hand_class] = total / 1326
    return result


def top_share_range(share: float) -> Range:
    return Range.of(c for c, p in percentile().items() if p <= share)


@dataclass(frozen=True)
class Style:
    key: str
    name: str
    character: str  # the bot's name at the six-max table
    blurb: str
    open: float  # raise this share of hands first in from the button
    limp: float  # otherwise limp this share (calling stations love to limp)
    three_bet: float  # re-raise this share facing a raise
    call: float  # call a raise with this share
    four_bet: float  # shove this share facing a re-raise
    call_3bet: float  # call a re-raise with this share
    bet: dict[str, float]  # bet frequency per hand class when checked to
    stay: dict[str, float]  # continue frequency per hand class facing a bet
    raise_: dict[str, float]  # raise frequency per hand class facing a bet
    size: float  # bet size as a share of the pot

    def public(self) -> dict[str, str]:
        return {
            "key": self.key,
            "name": self.name,
            "character": self.character,
            "blurb": self.blurb,
        }


def _f(*values: float) -> dict[str, float]:
    return dict(zip(CLASSES, values, strict=True))


STYLES: dict[str, Style] = {
    s.key: s
    for s in (
        Style(
            "nit",
            "Nit",
            "Rocky",
            "Plays few hands and bets only when strong. "
            "Steal its blinds; fold when it fights back.",
            open=0.3,
            limp=0.0,
            three_bet=0.04,
            call=0.15,
            four_bet=0.02,
            call_3bet=0.05,
            bet=_f(0.9, 0.7, 0.2, 0.15, 0.05),
            stay=_f(1, 0.8, 0.3, 0.3, 0),
            raise_=_f(0.5, 0.1, 0, 0.05, 0),
            size=0.66,
        ),
        Style(
            "tag",
            "TAG",
            "Finn",
            "Tight and aggressive: a solid regular. Few easy spots, so play fundamentally sound.",
            open=0.55,
            limp=0.0,
            three_bet=0.12,
            call=0.35,
            four_bet=0.05,
            call_3bet=0.12,
            bet=_f(0.95, 0.8, 0.4, 0.5, 0.25),
            stay=_f(1, 0.9, 0.55, 0.6, 0.05),
            raise_=_f(0.6, 0.15, 0, 0.15, 0.03),
            size=0.66,
        ),
        Style(
            "lag",
            "LAG",
            "Roxy",
            "Loose and aggressive: opens most hands and keeps betting. Call down lighter.",
            open=0.8,
            limp=0.0,
            three_bet=0.2,
            call=0.45,
            four_bet=0.08,
            call_3bet=0.2,
            bet=_f(1, 0.85, 0.55, 0.7, 0.45),
            stay=_f(1, 0.95, 0.65, 0.7, 0.15),
            raise_=_f(0.7, 0.25, 0.05, 0.3, 0.1),
            size=0.75,
        ),
        Style(
            "station",
            "Calling station",
            "Moby",
            "Calls far too much and rarely raises. Never bluff it; value bet relentlessly.",
            open=0.25,
            limp=0.95,
            three_bet=0.04,
            call=0.8,
            four_bet=0.02,
            call_3bet=0.5,
            bet=_f(0.6, 0.4, 0.2, 0.1, 0.05),
            stay=_f(1, 1, 0.95, 0.85, 0.35),
            raise_=_f(0.2, 0, 0, 0, 0),
            size=0.5,
        ),
        Style(
            "maniac",
            "Maniac",
            "Blaze",
            "Raises and bluffs constantly. Let it hang itself: call wider and trap.",
            open=0.95,
            limp=0.0,
            three_bet=0.4,
            call=0.4,
            four_bet=0.2,
            call_3bet=0.4,
            bet=_f(1, 0.9, 0.8, 0.8, 0.7),
            stay=_f(1, 0.95, 0.7, 0.7, 0.35),
            raise_=_f(0.8, 0.4, 0.2, 0.4, 0.3),
            size=1.0,
        ),
    )
}


def hand_class(hole: tuple[int, int], board: list[int]) -> str:
    if PREDICATES["two_pair_plus"](hole, board):
        return "monster"
    if PREDICATES["top_pair"](hole, board) or PREDICATES["overpair"](hole, board):
        return "strong"
    if PREDICATES["pair_plus"](hole, board):
        return "medium"
    if PREDICATES["draw"](hole, board):
        return "draw"
    return "air"


def preflop_raises(hand: HeadsUpHand | TableHand) -> int:
    """How many raises (not counting blinds) happened preflop so far."""
    return sum(1 for a in hand.log if a.street == "preflop" and a.kind == "raise")


@dataclass
class Bot:
    style: Style
    rng: random.Random

    def options(self, hand: HeadsUpHand | TableHand) -> list[tuple[str, int | None, float]]:
        """Every action this bot could take now, with its size and probability.

        ``decide`` samples from exactly these numbers, so they also tell us how likely the bot was
        to take an observed line with any given hand (used to read its range).
        """
        if hand.street == 0:
            kind, to = self._preflop(hand)
            return [(kind, to, 1.0)]
        legal = hand.legal()
        me = hand.current
        group = hand_class(hand.hole[me], hand.board)
        pot = hand.total_pot
        if legal.can_check:
            bet = self.style.bet[group] if legal.can_raise else 0.0
            size = self._size(legal.min_raise_to, legal.max_raise_to, pot)
            return [("bet", size, bet), ("check", None, 1 - bet)]
        stay = self.style.stay[group]
        before_bet = pot - legal.to_call  # the pot the bet was made into
        if legal.to_call >= before_bet * 0.6 and group in ("medium", "draw", "air"):
            stay *= 0.7  # bets of 60% pot or more push weaker hands out
        raise_ = self.style.raise_[group] if legal.can_raise else 0.0
        to = min(max(legal.min_raise_to, max(hand.bets) * 3), legal.max_raise_to)
        stays = 1.0 if legal.to_call <= BIG_BLIND // 2 else max(stay, raise_)
        return [("raise", to, raise_), ("call", None, stays - raise_), ("fold", None, 1 - stays)]

    def decide(self, hand: HeadsUpHand | TableHand) -> tuple[str, int | None]:
        """Choose an action for the player to act (assumed to be this bot)."""
        choices = [(k, to, p) for k, to, p in self.options(hand) if p > 0]
        if len(choices) == 1:
            return choices[0][0], choices[0][1]
        roll = self.rng.random()
        for kind, to, p in choices:
            if roll < p:
                return kind, to
            roll -= p
        return choices[-1][0], choices[-1][1]  # floating-point leftovers

    def _size(self, low: int, high: int, pot: int) -> int:
        return min(high, max(low, round(pot * self.style.size)))

    def _preflop(self, hand: HeadsUpHand | TableHand) -> tuple[str, int | None]:
        legal = hand.legal()
        me = hand.current
        strength = percentile()[class_of_combo(*hand.hole[me])]
        raises = preflop_raises(hand)
        s = self.style
        if raises == 0 and me == hand.button and hand.bets[me] < BIG_BLIND:
            # First in from the button.
            if strength <= s.open:
                return "raise", min(legal.max_raise_to, 5)  # 2.5bb
            if strength <= s.limp:
                return "call", None
            return "fold", None
        if raises == 0:
            # Big blind after a limp.
            if legal.can_raise and strength <= s.three_bet:
                return "raise", min(legal.max_raise_to, 8)
            return "check", None
        if raises == 1:
            if legal.can_raise and strength <= s.three_bet:
                return "raise", min(
                    legal.max_raise_to, max(legal.min_raise_to, hand.bets[1 - me] * 3)
                )
            if strength <= s.call:
                return "call", None
            return "fold", None
        if legal.can_raise and strength <= s.four_bet:
            return "raise", legal.max_raise_to  # four-bets go all in
        if strength <= s.call_3bet or legal.to_call <= BIG_BLIND:
            return "call", None
        return "fold", None


def estimated_range(style: Style, log: Sequence[Action], bot: int, button: int) -> Range:
    """The bot's likely range from its style and its preflop actions in ``log``."""
    preflop = [a for a in log if a.street == "preflop" and a.kind != "post"]
    mine = [a.kind for a in preflop if a.player == bot]
    raises = mine.count("raise")
    if raises >= 2:
        return top_share_range(style.four_bet)
    if raises == 1:
        raised_at = next(i for i, a in enumerate(preflop) if a.player == bot and a.kind == "raise")
        reraised = any(a.kind == "raise" and a.player != bot for a in preflop[raised_at + 1 :])
        if reraised and "call" in mine[mine.index("raise") :]:
            return top_share_range(style.call_3bet)
        return top_share_range(style.open if bot == button else style.three_bet)
    if mine and mine[0] == "call":
        return top_share_range(max(style.limp, style.open) if bot == button else style.call)
    return top_share_range(1.0)  # checked the big blind option: anything


# Six-max: how much of a style's heads-up numbers it plays from each position.
OPEN_FACTOR = {"UTG": 0.3, "HJ": 0.4, "CO": 0.55, "BTN": 0.8, "SB": 0.6, "BB": 0.6}
MULTIWAY = 0.6  # limps and re-raises tighten up with more players behind


def open_share(style: Style, position: str) -> float:
    return style.open * OPEN_FACTOR[position]


def limp_share(style: Style) -> float:
    return style.limp * MULTIWAY


def three_bet_share(style: Style) -> float:
    return style.three_bet * MULTIWAY


def call_share(style: Style, position: str) -> float:
    return style.call * (0.9 if position == "BB" else 0.5)


def _clamp(low: int, value: int, high: int) -> int:
    return min(high, max(low, value))


@dataclass
class SeatBot(Bot):
    """A bot for the six-max table: the same postflop play, preflop by position."""

    def _preflop(self, hand: HeadsUpHand | TableHand) -> tuple[str, int | None]:
        assert isinstance(hand, TableHand)
        legal = hand.legal()
        me = hand.current
        position = hand.positions[me]
        strength = percentile()[class_of_combo(*hand.hole[me])]
        raises = preflop_raises(hand)
        s = self.style
        low, high = legal.min_raise_to, legal.max_raise_to
        if raises == 0:
            limpers = sum(1 for a in hand.log if a.kind == "call")
            if legal.can_check:  # the big blind's option after limps
                if strength <= three_bet_share(s):
                    return "raise", _clamp(low, 8 + 2 * limpers, high)
                return "check", None
            if strength <= open_share(s, position):
                return "raise", _clamp(low, 5 + 2 * limpers, high)  # 2.5bb plus 1bb per limper
            if strength <= limp_share(s):
                return "call", None
            return "fold", None
        if raises == 1:
            if legal.can_raise and strength <= three_bet_share(s):
                return "raise", _clamp(low, max(hand.bets) * 3, high)
            if strength <= call_share(s, position):
                return "call", None
            return "fold", None
        if legal.can_raise and strength <= s.four_bet:
            return "raise", high  # four-bets go all in
        if strength <= s.call_3bet or legal.to_call <= BIG_BLIND:
            return "call", None
        return "fold", None


def seat_range(style: Style, log: Sequence[Action], seat: int, position: str) -> Range:
    """A six-max bot's likely range from its style, position and preflop actions in ``log``."""
    preflop = [a for a in log if a.street == "preflop" and a.kind != "post"]
    mine = [i for i, a in enumerate(preflop) if a.player == seat]
    my_raises = [i for i in mine if preflop[i].kind == "raise"]
    my_calls = [i for i in mine if preflop[i].kind == "call"]

    def raises_before(index: int) -> int:
        return sum(1 for a in preflop[:index] if a.kind == "raise")

    if len(my_raises) >= 2:
        return top_share_range(style.four_bet)
    if my_raises:
        earlier = raises_before(my_raises[0])
        share = (
            open_share(style, position)
            if earlier == 0
            else three_bet_share(style)
            if earlier == 1
            else style.four_bet
        )
        if my_calls and my_calls[-1] > my_raises[0]:  # raised, was re-raised, and called
            share = min(share, style.call_3bet)
        return top_share_range(share)
    if my_calls:
        earlier = raises_before(my_calls[0])
        if earlier == 0:
            return top_share_range(max(limp_share(style), open_share(style, position)))
        return top_share_range(call_share(style, position) if earlier == 1 else style.call_3bet)
    return top_share_range(1.0)  # checked the big blind, or has not acted yet
