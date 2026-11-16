import itertools
import random

import pytest

from holdem.core.ranges import ALL_CLASSES
from holdem.drills.base import grade
from holdem.drills.preflop import PREFLOP_DRILLS, sample_class
from holdem.preflop import FOLD, SPOTS, SPOTS_BY_ID, grade_paint


@pytest.mark.parametrize("spot", SPOTS, ids=lambda s: s.id)
def test_every_spot_is_well_formed(spot):
    assert spot.choices[-1] == FOLD
    assert set(spot.chart.values()) <= set(spot.choices)
    assert sum(spot.frequency(a) for a in spot.choices) == pytest.approx(1)
    assert "AA" not in {c for c, a in spot.chart.items() if a == FOLD}
    assert spot.chart["72o"] == FOLD
    grid = spot.grid()
    assert len(grid) == 13
    assert all(len(row) == 13 for row in grid)
    public = spot.public()
    assert public["source"].startswith("Baseline")
    assert public["grid"] == grid


def test_open_ranges_widen_towards_the_button():
    opens = [SPOTS_BY_ID[f"{p}-open"].frequency("Raise") for p in ("utg", "hj", "co", "btn")]
    assert opens == sorted(opens)
    assert 0.17 < opens[0] < 0.21
    assert 0.40 < opens[-1] < 0.48


def test_open_ranges_are_nested():
    """Anything opened from an earlier seat is also opened from every later seat."""
    order = ["utg-open", "hj-open", "co-open", "btn-open"]
    for early, late in itertools.pairwise(order):
        early_range = {c for c, a in SPOTS_BY_ID[early].chart.items() if a == "Raise"}
        late_range = {c for c, a in SPOTS_BY_ID[late].chart.items() if a == "Raise"}
        assert early_range <= late_range, early_range - late_range


def test_big_blind_defends_widest_against_the_button():
    defend = {s: 1 - SPOTS_BY_ID[s].frequency(FOLD) for s in ("bb-vs-utg", "bb-vs-co", "bb-vs-btn")}
    assert defend["bb-vs-utg"] < defend["bb-vs-co"] < defend["bb-vs-btn"]


def test_priority_order_decides_overlaps():
    spot = SPOTS_BY_ID["bb-vs-btn"]
    assert spot.action_for("AA") == "3-bet"  # in both 3-bet and call text
    assert spot.action_for("K5s") == "Call"
    assert spot.action_for("72o") == FOLD


def test_boundaries():
    spot = SPOTS_BY_ID["utg-open"]
    assert not spot.is_boundary("AA")  # surrounded by raises
    assert not spot.is_boundary("72o")  # surrounded by folds
    assert spot.is_boundary("ATo")  # A9o next door folds


def test_grade_paint():
    spot = SPOTS_BY_ID["utg-open"]
    target = [c for c, a in spot.chart.items() if a == "Raise"]
    perfect = grade_paint(spot, "Raise", target)
    assert perfect.combos_wrong == 0
    assert perfect.accuracy == 1
    assert not perfect.missed
    painted = [c for c in target if c != "22"] + ["72o"]
    result = grade_paint(spot, "Raise", painted)
    assert result.missed == ("22",)
    assert result.extra == ("72o",)
    assert result.combos_wrong == 6 + 12
    assert result.public()["accuracy"] == round(1 - 18 / 1326, 4)
    for action in ("Fold", "Call"):
        with pytest.raises(ValueError):
            grade_paint(spot, action, [])


def test_sample_class_prefers_boundaries():
    spot = SPOTS_BY_ID["co-open"]
    rng = random.Random(0)
    samples = [sample_class(spot, rng) for _ in range(400)]
    share = sum(spot.is_boundary(c) for c in samples) / len(samples)
    assert share > 0.75
    assert set(samples) <= set(ALL_CLASSES)


@pytest.mark.parametrize("drill", PREFLOP_DRILLS, ids=lambda d: d.key)
@pytest.mark.parametrize("seed", range(20))
def test_preflop_questions(drill, seed):
    question = drill.make_question(random.Random(seed))
    spot = SPOTS_BY_ID[question.payload["spot"]]
    assert spot.kind == drill.kind
    assert question.choices == spot.choices
    hand = question.reveal["hand"]
    assert question.answer == spot.chart[hand]
    assert len(question.payload["hole"]) == 2
    result = grade(question, question.answer)
    assert result.correct
    assert result.public()["reveal"]["grid"] == spot.grid()
    assert drill.meta()["tier"] == 2
