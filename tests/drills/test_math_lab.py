import random

import pytest

from holdem.core.cards import parse_card, parse_cards
from holdem.core.equity import calculate_equity
from holdem.core.evaluator import Category
from holdem.drills import math_lab
from holdem.drills.base import AnswerKind, Question, grade
from holdem.drills.math_lab import (
    ALL_DRILLS,
    DRILLS,
    FLOP_EVENTS,
    MATCHUPS,
    PreflopEquityDrill,
    flop_event_probability,
    nut_hand,
)

SEEDS = range(12)


def all_cards_valid(cards):
    return all(parse_card(c) is not None for c in cards)


@pytest.fixture(autouse=True)
def fast_preflop(monkeypatch):
    monkeypatch.setattr(PreflopEquityDrill, "samples", 2000)


def test_registry_is_consistent():
    assert len(DRILLS) == len(ALL_DRILLS)
    for drill in ALL_DRILLS:
        meta = drill.meta()
        assert meta["key"] == drill.key
        assert meta["title"]
        assert meta["description"]
        assert 0 <= meta["tier"] <= 7


@pytest.mark.parametrize("drill", ALL_DRILLS, ids=lambda d: d.key)
@pytest.mark.parametrize("seed", SEEDS)
def test_questions_are_well_formed_and_self_consistent(drill, seed):
    question = drill.make_question(random.Random(seed))
    assert question.drill == drill.key
    assert question.concept == drill.concept
    assert question.prompt
    assert question.explanation
    public = question.public()
    assert "answer" not in public
    assert "explanation" not in public
    for key in ("hole", "villain", "board"):
        if key in question.payload:
            assert all_cards_valid(question.payload[key])
    if question.kind is AnswerKind.CHOICE:
        assert question.answer in question.choices
        assert grade(question, question.answer).correct
        wrong = next(c for c in question.choices if c != question.answer)
        assert not grade(question, wrong).correct
    else:
        answer = float(question.answer)
        assert grade(question, answer).correct
        assert grade(question, answer + question.tolerance).correct
        assert not grade(question, answer + question.tolerance + 1).correct


@pytest.mark.parametrize("drill", ALL_DRILLS, ids=lambda d: d.key)
def test_questions_are_reproducible(drill):
    a = drill.make_question(random.Random(99))
    b = drill.make_question(random.Random(99))
    assert (a.prompt, a.answer, a.payload) == (b.prompt, b.answer, b.payload)


def test_hand_ranking_covers_rare_categories():
    seen = {DRILLS["hand-ranking"].make_question(random.Random(s)).answer for s in range(60)}
    assert Category.STRAIGHT_FLUSH.label in seen
    assert Category.FOUR_OF_A_KIND.label in seen


def test_hand_ranking_falls_back_when_target_not_found(monkeypatch):
    monkeypatch.setattr(math_lab, "category", lambda cards: Category.HIGH_CARD)
    rng = random.Random(0)
    monkeypatch.setattr(rng, "choice", lambda seq: Category.FLUSH)
    question = DRILLS["hand-ranking"].make_question(rng)
    assert question.answer == Category.HIGH_CARD.label


def test_nut_hand():
    board = parse_cards("AhKhQh7c2d")
    _, combo = nut_hand(board)
    assert set(combo) == set(parse_cards("JhTh"))


@pytest.mark.parametrize(
    ("event", "hole", "expected"),
    [
        ("set", "7c7d", 0.1176),
        ("pair", "Ac9d", 0.324),
        ("flush-draw", "Ah9h", 0.109 + 0.0084),
        ("overcard", "KcKd", 0.226),
        ("overcard", "TcTd", 0.695),
    ],
)
def test_flop_event_probabilities(event, hole, expected):
    _, func = FLOP_EVENTS[event]
    assert flop_event_probability(parse_cards(hole), func) == pytest.approx(expected, abs=0.001)


def test_open_ended_flop_odds_are_plausible():
    _, func = FLOP_EVENTS["straight-draw"]
    prob = flop_event_probability(parse_cards("9c8d"), func)
    assert 0.09 < prob < 0.13


@pytest.mark.parametrize(
    ("response", "value"),
    [
        (25, 25.0),
        ("25", 25.0),
        ("25%", 25.0),
        (" 25 % ", 25.0),
        ("0,5", 0.5),
        ("1,326", 1326.0),
        ("12,5", 12.5),
    ],
)
def test_grade_accepts_friendly_numbers(response, value):
    question = Question("d", "c", "p", AnswerKind.NUMBER, value, tolerance=0)
    assert grade(question, response).correct


@pytest.mark.parametrize("response", ["nan", "inf", "-inf", "", "1/3"])
def test_grade_rejects_non_finite_or_unparseable(response):
    question = Question("d", "c", "p", AnswerKind.NUMBER, 1.0)
    with pytest.raises(ValueError):
        grade(question, response)


def test_grade_rejects_bad_responses():
    number = Question("d", "c", "p", AnswerKind.NUMBER, 10.0, tolerance=1)
    with pytest.raises(ValueError, match="number"):
        grade(number, "ten")
    choice = Question("d", "c", "p", AnswerKind.CHOICE, "A", choices=("A", "B"))
    with pytest.raises(ValueError, match="choices"):
        grade(choice, "C")
    result = grade(number, "11.5")
    assert not result.correct
    assert result.error == 1.5
    assert result.public()["expected"] == 10.0


@pytest.mark.parametrize("drill", ALL_DRILLS, ids=lambda d: d.key)
def test_many_seeds_hit_every_branch(drill):
    """Wider seed sweep so random branches (blockers, tainted outs, splits) are exercised."""
    for seed in range(100, 130):
        drill.make_question(random.Random(seed))


ANCHOR_BANDS = {
    "pair vs two overcards": (0.46, 0.62),
    "overpair vs underpair": (0.77, 0.86),
    "dominated hand": (0.60, 0.79),
    "two overcards vs two undercards": (0.55, 0.73),
    "pair vs one overcard": (0.62, 0.76),
}


@pytest.mark.parametrize("name", ANCHOR_BANDS)
def test_matchup_generators_stay_near_their_anchor(name):
    """The explanation quotes an anchor; generated hands must not contradict it."""
    builder, _ = MATCHUPS[name]
    low, high = ANCHOR_BANDS[name]
    rng = random.Random(5)
    for _ in range(40):
        hero, villain = builder(rng)
        equity = calculate_equity(
            [(hero[0], hero[1]), (villain[0], villain[1])], samples=2500, seed=1, exact_limit=0
        )[0].equity
        assert low <= equity <= high, (name, hero, villain, equity)


def test_numeric_grades_report_their_tolerance():
    question = Question("d", "c", "p", AnswerKind.NUMBER, 25.0, tolerance=1.5)
    assert grade(question, 26).public()["tolerance"] == 1.5
