import itertools
from collections import Counter

import pytest

from holdem.core.cards import parse_cards
from holdem.core.evaluator import (
    ROYAL_FLUSH_RANK,
    Category,
    category,
    category_of_rank,
    compare,
    evaluate,
)


@pytest.mark.parametrize(
    ("cards", "expected"),
    [
        ("AsKsQsJsTs", Category.STRAIGHT_FLUSH),
        ("5h4h3h2hAh", Category.STRAIGHT_FLUSH),
        ("9c9d9h9s2c", Category.FOUR_OF_A_KIND),
        ("KcKdKh2s2c", Category.FULL_HOUSE),
        ("Ah9h7h4h2h", Category.FLUSH),
        ("5c4d3h2sAc", Category.STRAIGHT),
        ("7c7d7h3s2c", Category.THREE_OF_A_KIND),
        ("7c7d3h3s2c", Category.TWO_PAIR),
        ("7c7d9h3s2c", Category.ONE_PAIR),
        ("Ac9d7h4s2c", Category.HIGH_CARD),
    ],
)
def test_categories(cards, expected):
    assert category(parse_cards(cards)) is expected


def test_royal_flush_is_rank_one_and_seven_cards_supported():
    assert evaluate(parse_cards("AsKsQsJsTs")) == ROYAL_FLUSH_RANK
    assert category(parse_cards("AsKsQsJsTs2c3d")) is Category.STRAIGHT_FLUSH


def test_evaluate_rejects_wrong_card_counts():
    with pytest.raises(ValueError):
        evaluate(parse_cards("AsKs"))
    with pytest.raises(ValueError):
        evaluate(parse_cards("AsKsQsJsTs9s8s7s"))


def test_category_of_rank_bounds():
    assert category_of_rank(7462) is Category.HIGH_CARD
    with pytest.raises(ValueError):
        category_of_rank(7463)


def test_category_labels():
    assert Category.FULL_HOUSE.label == "Full House"


def test_compare():
    board = parse_cards("Kh7d2c3s9h")
    assert compare(parse_cards("AsAd"), parse_cards("KsKd"), board) == -1
    assert compare(parse_cards("KsKd"), parse_cards("AsAd"), board) == 1
    assert compare(parse_cards("4c5c"), parse_cards("4d5d"), parse_cards("6h7h8s2d2h")) == 0


@pytest.mark.slow
def test_five_card_frequencies_match_published_counts():
    """All 2,598,960 five-card hands (Wikipedia, "Poker probability")."""
    counts = Counter(category_of_rank(evaluate(h)) for h in itertools.combinations(range(52), 5))
    assert counts == {
        Category.STRAIGHT_FLUSH: 40,
        Category.FOUR_OF_A_KIND: 624,
        Category.FULL_HOUSE: 3744,
        Category.FLUSH: 5108,
        Category.STRAIGHT: 10200,
        Category.THREE_OF_A_KIND: 54912,
        Category.TWO_PAIR: 123552,
        Category.ONE_PAIR: 1098240,
        Category.HIGH_CARD: 1302540,
    }
