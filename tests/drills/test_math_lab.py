import random

import pytest

from holdem.core.cards import parse_card, parse_cards
from holdem.core.evaluator import Category
from holdem.drills import math_lab
from holdem.drills.base import AnswerKind, Question, grade
from holdem.drills.math_lab import (
    ALL_DRILLS,
    DRILLS,
    FLOP_EVENTS,
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
