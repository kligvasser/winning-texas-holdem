"""Hand evaluation on top of phevaluator.

Ranks follow phevaluator: 1 is a royal flush and 7462 the worst high card, so lower is better.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import IntEnum

from phevaluator import evaluate_cards

from holdem.core.cards import Card


class Category(IntEnum):
    """Hand categories, ordered from worst to best."""

    HIGH_CARD = 0
    ONE_PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()


# Upper rank bound (inclusive) for each category, best category first.
_CATEGORY_BOUNDS: tuple[tuple[int, Category], ...] = (
    (10, Category.STRAIGHT_FLUSH),
    (166, Category.FOUR_OF_A_KIND),
    (322, Category.FULL_HOUSE),
    (1599, Category.FLUSH),
    (1609, Category.STRAIGHT),
    (2467, Category.THREE_OF_A_KIND),
    (3325, Category.TWO_PAIR),
    (6185, Category.ONE_PAIR),
    (7462, Category.HIGH_CARD),
)

ROYAL_FLUSH_RANK = 1


def evaluate(cards: Sequence[Card]) -> int:
    """Rank of the best 5-card hand among 5 to 7 cards (lower is better)."""
    if not 5 <= len(cards) <= 7:
        raise ValueError(f"need 5 to 7 cards, got {len(cards)}")
    return evaluate_cards(*cards)


def category_of_rank(rank: int) -> Category:
    for bound, category in _CATEGORY_BOUNDS:
        if rank <= bound:
            return category
    raise ValueError(f"rank out of range: {rank}")


def category(cards: Sequence[Card]) -> Category:
    return category_of_rank(evaluate(cards))


def compare(hand_a: Sequence[Card], hand_b: Sequence[Card], board: Sequence[Card]) -> int:
    """1 if hand A wins at showdown on ``board``, -1 if hand B wins, 0 on a tie."""
    rank_a = evaluate([*hand_a, *board])
    rank_b = evaluate([*hand_b, *board])
    return (rank_a < rank_b) - (rank_a > rank_b)
