"""Board texture, outs against a known hand, and draw detection."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from holdem.core.cards import Card, rank_of, remaining_deck, suit_of
from holdem.core.evaluator import Category, category, compare

# Rank sets for each straight, as rank indices (0 = deuce .. 12 = ace). The wheel uses the ace low.
STRAIGHTS: tuple[frozenset[int], ...] = (
    frozenset({12, 0, 1, 2, 3}),
    *(frozenset(range(low, low + 5)) for low in range(0, 9)),
)


class SuitTexture(StrEnum):
    RAINBOW = "rainbow"
    TWO_TONE = "two-tone"
    MONOTONE = "monotone"


class PairTexture(StrEnum):
    UNPAIRED = "unpaired"
    PAIRED = "paired"
    TRIPS = "trips"


@dataclass(frozen=True)
class Texture:
    suits: SuitTexture
    pairing: PairTexture
    high_rank: int
    connected: bool  # three distinct ranks fit inside one five-rank straight window
    straight_possible: bool  # some two hole cards make a straight

    @property
    def wet(self) -> bool:
        return self.suits is not SuitTexture.RAINBOW or self.connected


def flop_texture(flop: Sequence[Card]) -> Texture:
    if len(flop) != 3 or len(set(flop)) != 3:
        raise ValueError("a flop is three distinct cards")
    suit_count = len({suit_of(c) for c in flop})
    suits = {3: SuitTexture.RAINBOW, 2: SuitTexture.TWO_TONE, 1: SuitTexture.MONOTONE}[suit_count]
    ranks = {rank_of(c) for c in flop}
    pairing = {3: PairTexture.UNPAIRED, 2: PairTexture.PAIRED, 1: PairTexture.TRIPS}[len(ranks)]
    covering = [s for s in STRAIGHTS if ranks <= s]
    return Texture(
        suits=suits,
        pairing=pairing,
        high_rank=max(ranks),
        connected=len(ranks) == 3 and bool(covering),
        straight_possible=any(len(s & ranks) >= 3 for s in STRAIGHTS),
    )


def straight_completing_ranks(cards: Sequence[Card]) -> set[int]:
    """Ranks that would give these cards a straight they do not already have."""
    ranks = {rank_of(c) for c in cards}
    if any(s <= ranks for s in STRAIGHTS):
        return set()
    return {next(iter(s - ranks)) for s in STRAIGHTS if len(s - ranks) == 1}


@dataclass(frozen=True)
class Draws:
    flush_draw: bool
    straight_outs_ranks: int  # 2 = open-ended (or double gutshot), 1 = gutshot, 0 = none

    @property
    def open_ended(self) -> bool:
        return self.straight_outs_ranks >= 2

    @property
    def gutshot(self) -> bool:
        return self.straight_outs_ranks == 1


def draws(hole: Sequence[Card], board: Sequence[Card]) -> Draws:
    """Flush and straight draws that use at least one hole card."""
    cards = [*hole, *board]
    made = category(cards)
    suit_counts = Counter(suit_of(c) for c in cards)
    hole_suits = {suit_of(c) for c in hole}
    flush_draw = made < Category.FLUSH and any(
        n == 4 and s in hole_suits for s, n in suit_counts.items()
    )
    straight_ranks = 0
    if made < Category.STRAIGHT:
        board_ranks = straight_completing_ranks(board) if len(board) >= 4 else set()
        straight_ranks = len(straight_completing_ranks(cards) - board_ranks)
    return Draws(flush_draw=flush_draw, straight_outs_ranks=straight_ranks)


@dataclass(frozen=True)
class OutsResult:
    status: int  # 1 hero ahead now, 0 tied, -1 behind (on the current board)
    winning: tuple[Card, ...]  # next cards that leave hero winning outright
    tying: tuple[Card, ...]  # next cards that leave a split pot
    tainted: tuple[Card, ...]  # next cards that improve hero's category but still lose
    unseen: int

    @property
    def count(self) -> int:
        return len(self.winning)


def outs_against(
    hero: Sequence[Card], villain: Sequence[Card], board: Sequence[Card]
) -> OutsResult:
    """Outs for ``hero`` against a known ``villain`` hand with one card to come."""
    if len(board) not in (3, 4):
        raise ValueError("outs need a flop or turn board")
    used = [*hero, *villain, *board]
    if len(set(used)) != len(used):
        raise ValueError("duplicate cards")
    current = compare(hero, villain, board)
    hero_category = category([*hero, *board])
    deck = remaining_deck(used)
    winning, tying, tainted = [], [], []
    for card in deck:
        next_board = [*board, card]
        result = compare(hero, villain, next_board)
        if result > 0:
            winning.append(card)
        elif result == 0:
            tying.append(card)
        elif category([*hero, *next_board]) > hero_category:
            tainted.append(card)
    return OutsResult(
        status=current,
        winning=tuple(winning),
        tying=tuple(tying),
        tainted=tuple(tainted),
        unseen=len(deck),
    )
