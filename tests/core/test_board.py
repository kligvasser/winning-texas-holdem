import itertools
from collections import Counter

import pytest

from holdem.core.board import (
    PairTexture,
    SuitTexture,
    draws,
    flop_texture,
    outs_against,
    straight_completing_ranks,
)
from holdem.core.cards import parse_cards


def test_flop_texture_examples():
    dry = flop_texture(parse_cards("Kh7d2c"))
    assert dry.suits is SuitTexture.RAINBOW
    assert dry.pairing is PairTexture.UNPAIRED
    assert not dry.connected
    assert not dry.wet
    assert dry.high_rank == 11
    wet = flop_texture(parse_cards("9h8h7c"))
    assert wet.suits is SuitTexture.TWO_TONE
    assert wet.connected
    assert wet.straight_possible
    assert wet.wet
    mono = flop_texture(parse_cards("Ah5h2h"))
    assert mono.suits is SuitTexture.MONOTONE
    assert mono.connected  # A-5-2 fits the wheel
    assert flop_texture(parse_cards("7h7d2c")).pairing is PairTexture.PAIRED
    assert flop_texture(parse_cards("7h7d7c")).pairing is PairTexture.TRIPS
    with pytest.raises(ValueError):
        flop_texture(parse_cards("7h7d"))


def test_flop_texture_frequencies():
    """Rainbow 39.8%, two-tone 55.1%, monotone 5.2%; paired 16.9% (research notes)."""
    flops = list(itertools.combinations(range(52), 3))
    textures = [flop_texture(f) for f in flops]
    suits = Counter(t.suits for t in textures)
    pairs = Counter(t.pairing for t in textures)
    total = len(flops)
    assert suits[SuitTexture.RAINBOW] / total == pytest.approx(0.398, abs=0.001)
    assert suits[SuitTexture.TWO_TONE] / total == pytest.approx(0.551, abs=0.001)
    assert suits[SuitTexture.MONOTONE] / total == pytest.approx(0.052, abs=0.001)
    assert pairs[PairTexture.PAIRED] / total == pytest.approx(0.169, abs=0.001)


def test_straight_completing_ranks():
    assert straight_completing_ranks(parse_cards("9h8d7c6s")) == {3, 8}  # 5 or T
    assert straight_completing_ranks(parse_cards("9h8d6c5s")) == {5}  # 7 only
    assert straight_completing_ranks(parse_cards("9h8d7c6s5c")) == set()


def test_draws():
    flush_draw = draws(parse_cards("AhKh"), parse_cards("7h2h9c"))
    assert flush_draw.flush_draw
    assert not flush_draw.open_ended
    oesd = draws(parse_cards("9h8d"), parse_cards("7c6s2h"))
    assert oesd.open_ended
    assert not oesd.flush_draw
    gutshot = draws(parse_cards("9h8d"), parse_cards("6c5s2h"))
    assert gutshot.gutshot
    made_flush = draws(parse_cards("AhKh"), parse_cards("7h2h9h"))
    assert not made_flush.flush_draw
    made_straight = draws(parse_cards("9h8d"), parse_cards("7c6s5h"))
    assert made_straight.straight_outs_ranks == 0
    board_only = draws(parse_cards("AcKd"), parse_cards("9h8s7c6d"))
    assert board_only.straight_outs_ranks == 0  # the straight draw is on the board
    four_flush_board = draws(parse_cards("Ac2d"), parse_cards("Kh9h5h3h"))
    assert not four_flush_board.flush_draw


def test_outs_flush_draw_vs_top_pair():
    result = outs_against(parse_cards("AhQh"), parse_cards("KsKd"), parse_cards("Kh7h2c"))
    assert result.status == -1
    assert result.unseen == 45
    # Villain has a set of kings. Nine hearts are unseen, but 2h pairs the board and gives
    # villain a full house, so only eight hearts win.
    assert result.count == 8
    assert all(c % 4 == 2 for c in result.winning)


def test_outs_tainted_and_ties():
    result = outs_against(parse_cards("8c9c"), parse_cards("AsAd"), parse_cards("6h7h2s"))
    # Straight cards: four 5s and four Ts. 5h and Th make a hearts-free straight, both still win.
    assert result.count == 8
    assert result.tainted  # pairing an 8 or 9 improves hero but still loses to aces
    tie = outs_against(parse_cards("Ac2d"), parse_cards("Ad3c"), parse_cards("KhQhJs"))
    assert tie.tying  # any ten gives both players broadway


def test_outs_validation():
    with pytest.raises(ValueError):
        outs_against(parse_cards("AhQh"), parse_cards("KsKd"), parse_cards("Kh7h"))
    with pytest.raises(ValueError):
        outs_against(parse_cards("AhQh"), parse_cards("AhKd"), parse_cards("Kc7h2c"))
