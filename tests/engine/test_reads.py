import random

import pytest

from holdem.core.cards import parse_cards
from holdem.core.ranges import Range
from holdem.engine import reads
from holdem.engine.bots import STYLES, hand_class
from holdem.engine.reads import _share, equity_against, likely_ranges, push_value
from holdem.engine.table import TableHand

TAG, NIT, STATION = STYLES["tag"], STYLES["nit"], STYLES["station"]


def two(text):
    a, b = parse_cards(text)
    return (a, b)


def flop_hand(hero, board="Kh7d2c9s3h", stacks=(200, 200, 200)):
    """Hero opens the button, the big blind calls, and the flop comes down."""
    hand = TableHand(list(stacks), 0, random.Random(7))
    hand.hole[0] = two(hero)
    hand.hole[1] = two("4c4d")
    hand.hole[2] = two("KsQs")
    hand._deck = parse_cards(board)[::-1]
    hand.act("raise", 6)
    hand.act("fold")
    hand.act("call")
    return hand


def test_a_bet_narrows_the_range_towards_hands_that_bet():
    hand = flop_hand("AsAd")
    styles = [TAG, NIT]  # seat 2 is the nit
    before = dict(likely_ranges(styles, hand, len(hand.log), "flop")[2])
    assert set(before.values()) == {1.0}
    assert not any(set(c) & set(hand.hole[0]) for c in before)
    hand.act("bet", 8)
    after = dict(likely_ranges(styles, hand, len(hand.log), "flop")[2])
    board = hand.board
    monster = next(c for c in after if hand_class(c, board) == "monster")
    air = next(c for c in after if hand_class(c, board) == "air")
    assert after[monster] / after[air] == pytest.approx(0.9 / 0.05)
    wide, _ = equity_against(styles, hand, len(hand.log) - 1, "flop")
    narrow, opponents = equity_against(styles, hand, len(hand.log), "flop")
    assert opponents == 1
    assert narrow < wide  # the nit's betting range is stronger than its calling range


def test_impossible_actions_and_blocked_ranges_fall_back(monkeypatch):
    hand = flop_hand("AsAd")
    hand.act("bet", 8)
    styles = [TAG, NIT]
    monkeypatch.setattr(reads, "postflop_odds", lambda *a: {})
    unchanged = dict(likely_ranges(styles, hand, len(hand.log), "flop")[2])
    assert set(unchanged.values()) == {1.0}
    monkeypatch.setattr(reads, "seat_range", lambda *a: Range.of(["AA"]))
    blocked = flop_hand("AsAd", board="AhAc2c9s3h")
    everything = likely_ranges(styles, blocked, len(blocked.log), "flop")[2]
    assert len(everything) > 500  # no aces left for AA, so any two cards


def test_share_of_a_showdown():
    assert _share(5, [3, 9]) == 0.0
    assert _share(2, [3, 9]) == 1.0
    assert _share(3, [3, 3, 9]) == pytest.approx(1 / 3)


def test_a_value_bet_against_a_station_beats_checking():
    hand = flop_hand("KdKc")  # top set
    hand.act("check")
    hand.act("bet", 8)
    push = push_value([TAG, STATION], hand, len(hand.log) - 1, samples=300)
    assert push is not None
    assert push.alternative == "checking"
    assert push.aggressive > push.passive > 0
    assert 0 < push.fold_all < 0.8
    assert push.called_equity > 0.8


def test_a_raise_is_compared_with_calling_or_folding():
    strong = flop_hand("KdKc")
    strong.act("bet", 8)
    strong.act("raise", 24)
    push = push_value([TAG, NIT], strong, len(strong.log) - 1, samples=300)
    assert push is not None and push.alternative == "calling"
    weak = flop_hand("5s6c", stacks=(200, 200, 200))
    weak.act("bet", 8)
    weak.act("raise", 24)
    bluff = push_value([TAG, NIT], weak, len(weak.log) - 1, samples=300)
    assert bluff is not None and bluff.alternative == "folding"
    assert bluff.passive == 0.0


def test_push_value_edge_cases(monkeypatch):
    hand = flop_hand("KdKc")
    hand.act("check")
    hand.act("bet", 8)
    index = len(hand.log) - 1
    monkeypatch.setattr(reads, "postflop_odds", lambda *a: {"fold": 1.0})
    scared = push_value([TAG, NIT], hand, index, samples=50)
    assert scared is not None
    assert scared.fold_all == pytest.approx(1.0)
    assert scared.called_equity == 0.0
    assert scared.aggressive == pytest.approx(hand.log[index].pot)
    clash = {1: [((0, 1), 1.0)], 2: [((1, 2), 1.0)]}  # both would hold the same card
    monkeypatch.setattr(reads, "likely_ranges", lambda *a: clash)
    assert push_value([TAG, NIT], hand, index, samples=10) is None
