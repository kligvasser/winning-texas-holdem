import random

import pytest

from holdem.core.cards import (
    FULL_DECK,
    card_str,
    cards_str,
    deal,
    make_card,
    parse_card,
    parse_cards,
    rank_of,
    remaining_deck,
    suit_of,
)


def test_encoding_matches_rank_times_four_plus_suit():
    assert parse_card("2c") == 0
    assert parse_card("2s") == 3
    assert parse_card("As") == 51
    assert make_card(12, 0) == 48
    assert rank_of(parse_card("Td")) == 8
    assert suit_of(parse_card("Td")) == 1


@pytest.mark.parametrize("card", FULL_DECK)
def test_round_trip_every_card(card):
    assert parse_card(card_str(card)) == card


def test_parse_is_case_insensitive():
    assert parse_card("ah") == parse_card("AH") == parse_card("Ah")


@pytest.mark.parametrize("bad", ["A", "Asd", "1s", "Ax", ""])
def test_parse_card_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        parse_card(bad)


def test_parse_cards_accepts_separators():
    expected = [parse_card("As"), parse_card("Kd"), parse_card("2c")]
    assert parse_cards("AsKd2c") == expected
    assert parse_cards("As Kd, 2c") == expected


def test_parse_cards_rejects_duplicates_and_odd_length():
    with pytest.raises(ValueError, match="duplicate"):
        parse_cards("AsAs")
    with pytest.raises(ValueError, match="odd"):
        parse_cards("AsK")


def test_make_card_and_card_str_validate():
    with pytest.raises(ValueError):
        make_card(13, 0)
    with pytest.raises(ValueError):
        make_card(0, 4)
    with pytest.raises(ValueError):
        card_str(52)


def test_cards_str():
    assert cards_str(parse_cards("AsKd")) == "AsKd"


def test_remaining_deck_and_deal():
    dead = parse_cards("AsKs")
    deck = remaining_deck(dead)
    assert len(deck) == 50
    assert not set(dead) & set(deck)
    dealt = deal(random.Random(1), 5, dead)
    assert len(set(dealt)) == 5
    assert not set(dealt) & set(dead)
    assert deal(random.Random(1), 5, dead) == dealt
