import pytest
from hypothesis import given
from hypothesis import strategies as st

from holdem.core.cards import parse_cards
from holdem.core.ranges import (
    ALL_CLASSES,
    Range,
    class_combo_count,
    class_grid_position,
    class_of_combo,
    combos_of_class,
    grid_class,
    live_combos,
    normalize_class,
    parse_class,
)


def test_169_classes_and_1326_combos():
    assert len(ALL_CLASSES) == len(set(ALL_CLASSES)) == 169
    combos = [c for cls in ALL_CLASSES for c in combos_of_class(cls)]
    assert len(combos) == 1326
    assert len({frozenset(c) for c in combos}) == 1326


def test_grid_layout():
    assert grid_class(0, 0) == "AA"
    assert grid_class(0, 1) == "AKs"
    assert grid_class(1, 0) == "AKo"
    assert grid_class(12, 12) == "22"
    assert grid_class(11, 12) == "32s"
    with pytest.raises(ValueError):
        grid_class(13, 0)


@pytest.mark.parametrize("hand_class", ALL_CLASSES)
def test_grid_position_round_trip(hand_class):
    assert grid_class(*class_grid_position(hand_class)) == hand_class


@pytest.mark.parametrize(("cls", "count"), [("AA", 6), ("AKs", 4), ("AKo", 12)])
def test_combo_counts(cls, count):
    assert class_combo_count(cls) == count
    assert len(combos_of_class(cls)) == count


def test_parse_and_normalize_class():
    assert parse_class("AKs") == (12, 11, "s")
    assert parse_class("tt") == (8, 8, "p")
    assert normalize_class("KAo") == "AKo"
    for bad in ["AAs", "AKx", "A", "AKQs", "XYs"]:
        with pytest.raises(ValueError):
            parse_class(bad)


def test_class_of_combo():
    assert class_of_combo(*parse_cards("AsKs")) == "AKs"
    assert class_of_combo(*parse_cards("Kd As")) == "AKo"
    assert class_of_combo(*parse_cards("7c7d")) == "77"
    with pytest.raises(ValueError):
        class_of_combo(5, 5)


def test_blockers_remove_combos():
    assert len(live_combos("AA", parse_cards("Ah"))) == 3
    assert len(live_combos("AKo", parse_cards("Ah"))) == 9
    assert len(live_combos("AKs", parse_cards("Ah Kh"))) == 3


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("TT+", {"TT", "JJ", "QQ", "KK", "AA"}),
        ("A9s+", {"A9s", "ATs", "AJs", "AQs", "AKs"}),
        ("KTo+", {"KTo", "KJo", "KQo"}),
        ("22-44", {"22", "33", "44"}),
        ("44-22", {"22", "33", "44"}),
        ("A5s-A2s", {"A2s", "A3s", "A4s", "A5s"}),
        ("AK", {"AKs", "AKo"}),
        ("QJ+", {"QJs", "QJo"}),
        ("AKs, ; 72o", {"AKs", "72o"}),
    ],
)
def test_range_notation(text, expected):
    assert set(Range.parse(text)) == expected


def test_range_weights_and_counts():
    hand_range = Range.parse("AA, AKs:0.5")
    assert hand_range.weight("AA") == 1
    assert hand_range.weight("AKs") == 0.5
    assert hand_range.weight("72o") == 0
    assert hand_range.combo_count() == 8
    assert hand_range.fraction() == pytest.approx(8 / 1326)
    assert "AKs" in hand_range
    assert 3 not in hand_range
    assert len(hand_range) == 2
    assert hand_range.to_text() == "AA, AKs:0.5"


def test_range_combos_with_dead_cards():
    hand_range = Range.parse("AA, KK")
    combos = hand_range.combos(parse_cards("As"))
    assert len(combos) == 9
    assert all(w == 1 for _, w in combos)


def test_range_rejects_bad_input():
    with pytest.raises(ValueError):
        Range({"AA": 1.5})
    with pytest.raises(ValueError):
        Range.parse("22-AKs")
    with pytest.raises(ValueError):
        Range.parse("AKs-QJs")


def test_zero_weights_are_dropped_and_of_builds_ranges():
    assert len(Range({"AA": 0})) == 0
    assert Range.of(["AA", "KK"], 0.25).combo_count() == 3


@given(st.sets(st.sampled_from(ALL_CLASSES), max_size=40))
def test_to_text_round_trips(classes):
    hand_range = Range.of(classes)
    assert Range.parse(hand_range.to_text()) == hand_range
