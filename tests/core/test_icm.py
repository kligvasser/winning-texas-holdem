import itertools

import pytest
from pokerkit import calculate_icm

from holdem.core.icm import icm_equities, risk_premium_call


def test_wikipedia_example():
    """Stacks 50/30/20, payouts 70/30 (Wikipedia, Independent Chip Model)."""
    equities = icm_equities([50, 30, 20], [70, 30])
    assert equities == pytest.approx((45.18, 32.25, 22.57), abs=0.01)


@pytest.mark.parametrize(
    ("stacks", "payouts"),
    [([5000, 3000, 2000], [50, 30, 20]), ([1, 1, 1, 1], [60, 40]), ([7, 2, 9, 4], [45, 30, 25])],
)
def test_matches_pokerkit(stacks, payouts):
    assert icm_equities(stacks, payouts) == pytest.approx(calculate_icm(payouts, stacks))


def test_equities_sum_to_paid_prizes_and_respect_order():
    for stacks in itertools.permutations([1000, 2500, 4000]):
        equities = icm_equities(stacks, [50, 30, 20])
        assert sum(equities) == pytest.approx(100)
        ranked = sorted(range(3), key=lambda i: stacks[i])
        assert [equities[i] for i in ranked] == sorted(equities)


def test_more_players_than_prizes_and_validation():
    assert sum(icm_equities([1, 1, 1], [100])) == pytest.approx(100)
    with pytest.raises(ValueError):
        icm_equities([0, 10], [100])
    with pytest.raises(ValueError):
        icm_equities([], [100])


def test_risk_premium_example():
    """GTO Wizard: stacks 500/300/200, payouts 50/30/20; the 200 stack calls a shove."""
    chip, icm = risk_premium_call([500, 300, 200], [50, 30, 20], hero=2, villain=0)
    assert chip == pytest.approx(0.5)
    assert icm > chip  # ICM always demands more than chip EV here


def test_risk_premium_when_hero_covers_villain():
    chip, icm = risk_premium_call([500, 300, 200], [50, 30, 20], hero=0, villain=2)
    assert chip == pytest.approx(0.5)
    assert icm > chip


def test_bust_outside_the_money():
    chip, icm = risk_premium_call([500, 300, 200, 100], [70, 30], hero=3, villain=0)
    assert 0 < chip < icm < 1


def test_flat_payouts_leave_only_the_chip_price():
    chip, icm = risk_premium_call([500, 300, 200], [10, 10, 10], hero=1, villain=0)
    assert icm == chip == 0.5
