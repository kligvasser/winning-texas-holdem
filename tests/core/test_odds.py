import pytest

from holdem.core import odds
from holdem.core.ranges import Range

# Outs table from the research notes (exact combinatorics).
OUTS_TABLE = {
    2: (0.043, 0.043, 0.084),
    4: (0.085, 0.087, 0.165),
    5: (0.106, 0.109, 0.204),
    6: (0.128, 0.130, 0.241),
    8: (0.170, 0.174, 0.315),
    9: (0.191, 0.196, 0.350),
    12: (0.255, 0.261, 0.450),
    15: (0.319, 0.326, 0.541),
}


@pytest.mark.parametrize(("outs", "expected"), OUTS_TABLE.items())
def test_draw_probabilities(outs, expected):
    flop_turn, turn_river, flop_river = expected
    assert odds.draw_probability(outs, "flop_turn") == pytest.approx(flop_turn, abs=0.0006)
    assert odds.draw_probability(outs, "turn_river") == pytest.approx(turn_river, abs=0.0006)
    assert odds.draw_probability(outs, "flop_river") == pytest.approx(flop_river, abs=0.0006)


def test_draw_probability_validation():
    with pytest.raises(ValueError):
        odds.draw_probability(9, "preflop")
    with pytest.raises(ValueError):
        odds.hit_probability(50, 47, 1)
    with pytest.raises(ValueError):
        odds.hit_probability(1, 47, 48)


def test_rule_of_2_and_4():
    assert odds.rule_of_2_and_4(9, 1) == 0.18
    assert odds.rule_of_2_and_4(15, 2) == 0.60
    assert odds.rule_of_2_and_4(30, 2) == 1.0
    with pytest.raises(ValueError):
        odds.rule_of_2_and_4(9, 3)


# Bet as a share of pot -> (required equity, MDF, alpha, bluff:value)
BET_TABLE = [
    (0.25, 0.167, 0.800, 0.200, (1, 5)),
    (1 / 3, 0.200, 0.750, 0.250, (1, 4)),
    (0.50, 0.250, 0.667, 0.333, (1, 3)),
    (2 / 3, 0.286, 0.600, 0.400, (2, 5)),
    (0.75, 0.300, 0.571, 0.429, (3, 7)),
    (1.00, 0.333, 0.500, 0.500, (1, 2)),
    (1.50, 0.375, 0.400, 0.600, (3, 5)),
    (2.00, 0.400, 0.333, 0.667, (2, 3)),
]


@pytest.mark.parametrize(("size", "req", "mdf", "alpha", "ratio"), BET_TABLE)
def test_bet_size_table(size, req, mdf, alpha, ratio):
    pot, bet = 100, 100 * size
    assert odds.required_equity(pot, bet) == pytest.approx(req, abs=0.0006)
    assert odds.bluff_share(pot, bet) == pytest.approx(req, abs=0.0006)
    assert odds.minimum_defense_frequency(pot, bet) == pytest.approx(mdf, abs=0.0006)
    assert odds.alpha(pot, bet) == pytest.approx(alpha, abs=0.0006)
    assert odds.bluff_to_value(pot, bet) == ratio


def test_pot_odds_ratio():
    assert odds.pot_odds_ratio(100, 50) == 3
    with pytest.raises(ValueError):
        odds.pot_odds_ratio(0, 50)
    with pytest.raises(ValueError):
        odds.required_equity(100, 0)


def test_spr():
    assert odds.stack_to_pot_ratio(97.5, 5.5) == pytest.approx(17.7, abs=0.05)
    with pytest.raises(ValueError):
        odds.stack_to_pot_ratio(100, 0)
    with pytest.raises(ValueError):
        odds.stack_to_pot_ratio(-1, 10)


def test_ev_formulas():
    # Pure bluff at alpha breaks even.
    assert odds.bet_ev(100, 100, 0.5) == pytest.approx(0)
    assert odds.bet_ev(100, 50, 0.5, 0.5) == pytest.approx(50 + 0.5 * (0.5 * 200 - 50))
    assert odds.call_ev(100, 50, 0.25) == pytest.approx(0)
    assert odds.call_ev(100, 50, 0.5) > 0
    with pytest.raises(ValueError):
        odds.bet_ev(100, 50, 1.5)
    with pytest.raises(ValueError):
        odds.bet_ev(100, 50, 0.5, -0.1)
    with pytest.raises(ValueError):
        odds.call_ev(100, 50, 2)


def test_dealt_probabilities():
    assert odds.dealt_probability(["AA"]) == pytest.approx(1 / 221)
    assert odds.dealt_probability(Range.parse("22+")) == pytest.approx(0.0588, abs=0.0001)
    assert odds.dealt_probability(Range.parse("JJ+, AK")) == pytest.approx(0.0302, abs=0.0001)


def test_odds_against():
    assert odds.odds_against(1 / 221) == pytest.approx(220)
    with pytest.raises(ValueError):
        odds.odds_against(0)
