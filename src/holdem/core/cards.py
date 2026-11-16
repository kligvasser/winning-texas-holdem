"""Card representation.

A card is an int in 0..51 with ``card = rank * 4 + suit``, where rank 0 is a deuce and 12 an ace,
and suit 0..3 is clubs, diamonds, hearts, spades. This matches phevaluator's integer encoding, so
cards go to the evaluator without conversion.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence

RANKS = "23456789TJQKA"
SUITS = "cdhs"
SUIT_SYMBOLS = {"c": "♣", "d": "♦", "h": "♥", "s": "♠"}
RANK_NAMES = {
    "2": "deuce",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
    "T": "ten",
    "J": "jack",
    "Q": "queen",
    "K": "king",
    "A": "ace",
}

FULL_DECK: tuple[int, ...] = tuple(range(52))

type Card = int


def make_card(rank: int, suit: int) -> Card:
    if not 0 <= rank < 13 or not 0 <= suit < 4:
        raise ValueError(f"invalid rank/suit: {rank}/{suit}")
    return rank * 4 + suit


def rank_of(card: Card) -> int:
    return card // 4


def suit_of(card: Card) -> int:
    return card % 4


def parse_card(text: str) -> Card:
    """Parse ``"As"`` or ``"td"`` into a card."""
    if len(text) != 2:
        raise ValueError(f"card must be two characters, got {text!r}")
    rank_char, suit_char = text[0].upper(), text[1].lower()
    if rank_char not in RANKS or suit_char not in SUITS:
        raise ValueError(f"invalid card {text!r}")
    return make_card(RANKS.index(rank_char), SUITS.index(suit_char))


def parse_cards(text: str) -> list[Card]:
    """Parse ``"AsKd"``, ``"As Kd"`` or ``"As,Kd"`` into a list of distinct cards."""
    compact = "".join(ch for ch in text if not ch.isspace() and ch != ",")
    if len(compact) % 2:
        raise ValueError(f"odd number of characters in {text!r}")
    cards = [parse_card(compact[i : i + 2]) for i in range(0, len(compact), 2)]
    if len(set(cards)) != len(cards):
        raise ValueError(f"duplicate card in {text!r}")
    return cards


def card_str(card: Card) -> str:
    if not 0 <= card < 52:
        raise ValueError(f"invalid card {card}")
    return RANKS[rank_of(card)] + SUITS[suit_of(card)]


def cards_str(cards: Iterable[Card]) -> str:
    return "".join(card_str(c) for c in cards)


def remaining_deck(dead: Iterable[Card]) -> list[Card]:
    dead_set = set(dead)
    return [c for c in FULL_DECK if c not in dead_set]


def deal(rng: random.Random, count: int, dead: Sequence[Card] = ()) -> list[Card]:
    """Deal ``count`` distinct random cards that are not in ``dead``."""
    return rng.sample(remaining_deck(dead), count)
