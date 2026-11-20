import pytest

from holdem.core.cards import parse_cards
from holdem.core.equity import calculate_equity
from holdem.core.ranges import Range


def hand(text):
    a, b = parse_cards(text)
    return (a, b)


# Exact all-in equities from full enumeration (research notes, cross-checked with The Poker Bank).
PREFLOP_MATCHUPS = [
    ("QhQd", "AsKc", 0.572),
    ("QhQd", "AsKs", 0.538),
    ("2h2d", "AsKc", 0.530),
    ("2h2d", "JsTs", 0.460),
    ("AhAd", "KsKc", 0.813),
    ("KhKd", "AsKc", 0.700),
    ("8h8d", "As5c", 0.692),
    ("AhAd", "AsKc", 0.926),
    ("AhAd", "AsKs", 0.879),
    ("AhKd", "AsQc", 0.740),
    ("AhKd", "KsQc", 0.742),
    ("AhKd", "8s7s", 0.581),
    ("AhKd", "7s2c", 0.670),
    ("AhKd", "JsTs", 0.588),
    ("AhAd", "7s6s", 0.770),
    ("AhAd", "7s2c", 0.874),
]


@pytest.mark.slow
@pytest.mark.parametrize(("hero", "villain", "expected"), PREFLOP_MATCHUPS)
def test_preflop_matchups_exact(hero, villain, expected):
    result = calculate_equity([hand(hero), hand(villain)])
    assert result.exact
    assert result.trials == 1_712_304
    assert result[0].equity == pytest.approx(expected, abs=0.0015)
    assert result[0].equity + result[1].equity == pytest.approx(1)


def test_river_showdown_and_ties():
    board = parse_cards("6h7h8s2d2h")
    result = calculate_equity([hand("4c5c"), hand("4d5d")], board)
    assert result[0].equity == pytest.approx(0.5)
    assert result[0].tie == 1
    assert result[0].win == 0
    result = calculate_equity([hand("AsAd"), hand("KsKd")], parse_cards("Kh7d2c3s9c"))
    assert result[1].equity == 1


def test_flop_hand_vs_hand_exact():
    # Flush draw vs top pair: 9 outs twice -> about 35%, minus a little for the board pairing.
    result = calculate_equity([hand("AhQh"), hand("KsKd")], parse_cards("Kh7h2c"))
    assert result.exact
    assert result.trials == 990
    assert 0.25 < result[0].equity < 0.40


def test_hand_vs_range_on_flop_is_exact_and_blocks_cards():
    board = parse_cards("Kh7d2c")
    result = calculate_equity([hand("AsAd"), Range.parse("KK, AK")], board)
    assert result.exact
    # Kh, As and Ad are blocked: 3 KK combos (sets) and 6 AK combos remain.
    vs_set = calculate_equity([hand("AsAd"), hand("KsKd")], board)[0].equity
    vs_ak = calculate_equity([hand("AsAd"), hand("AhKs")], board)[0].equity
    assert result[0].equity == pytest.approx((3 * vs_set + 6 * vs_ak) / 9, abs=0.01)
    assert result[0].equity + result[1].equity == pytest.approx(1)


def test_preflop_hand_vs_range_uses_seeded_monte_carlo():
    a = calculate_equity([hand("AsAd"), Range.parse("TT+, AK")], samples=4000, seed=3)
    b = calculate_equity([hand("AsAd"), Range.parse("TT+, AK")], samples=4000, seed=3)
    assert not a.exact
    assert a == b
    assert 0.8 < a[0].equity < 0.9


def test_multiway_monte_carlo():
    result = calculate_equity(
        [hand("AsAd"), hand("KsKd"), hand("7c6c")], samples=5000, seed=1, exact_limit=0
    )
    assert not result.exact
    assert sum(p.equity for p in result.players) == pytest.approx(1)
    assert result[0].equity > result[1].equity > 0.1


def test_weighted_combo_lists():
    villain = [(hand("KsKd"), 1.0), (hand("QsQd"), 0.0)]
    result = calculate_equity([hand("AsAd"), villain], parse_cards("2c3d4h"))
    single = calculate_equity([hand("AsAd"), hand("KsKd")], parse_cards("2c3d4h"))
    assert result[0].equity == pytest.approx(single[0].equity)


def test_validation():
    aa, kk = hand("AsAd"), hand("KsKd")
    two, three = parse_cards("2c"), parse_cards("3c")
    with pytest.raises(ValueError, match="two players"):
        calculate_equity([aa])
    with pytest.raises(ValueError, match="same card"):
        calculate_equity([aa, hand("AsKd")])
    with pytest.raises(ValueError, match="distinct"):
        calculate_equity([aa, kk], two + two)
    with pytest.raises(ValueError, match="overlap"):
        calculate_equity([aa, kk], two + three, two)
    with pytest.raises(ValueError, match="no possible hands"):
        calculate_equity([aa, kk], two + three, parse_cards("As"))


def test_invalid_hand_rejected():
    with pytest.raises(ValueError, match="two different"):
        calculate_equity([(5, 5), hand("KsKd")])


def test_range_fully_blocked_by_known_hands():
    with pytest.raises(ValueError, match="no possible hands"):
        calculate_equity([hand("AsAd"), hand("AhAc"), Range.parse("AA")])


def test_conflicting_ranges():
    first = [(hand("AsAd"), 1.0), (hand("AsAh"), 1.0)]
    second = [(hand("AsKd"), 1.0), (hand("AsKh"), 1.0)]
    with pytest.raises(ValueError, match="conflict"):
        calculate_equity([first, second], samples=10, exact_limit=0)
    with pytest.raises(ValueError, match="no valid deal"):
        calculate_equity([first, second], parse_cards("2c3c4c5d7d"))


def two(text):
    a, b = parse_cards(text)
    return (a, b)


def test_a_range_cut_to_one_combo_by_known_hands_is_still_dealt():
    aces = two("AsAh")
    result = calculate_equity([aces, Range.parse("AA")])
    assert result[0].equity == pytest.approx(0.5, abs=0.01)
    deuces = two("2c2d")
    kings = two("KsKh")
    other = two("KdKc")
    board = parse_cards("7h8h9s")
    result = calculate_equity([deuces, [(kings, 1.0)], [(kings, 1.0), (other, 1.0)]], board)
    assert sum(p.equity for p in result.players) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="same card"):
        calculate_equity([aces, aces])
