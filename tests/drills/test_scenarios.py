import random

import pytest

from holdem.core import odds
from holdem.core.cards import parse_cards
from holdem.core.ranges import ALL_CLASSES
from holdem.drills.base import AnswerKind, grade
from holdem.drills.scenarios import (
    SCENARIO_DRILLS,
    BluffCatchDrill,
    BluffEvDrill,
    HandStoryDrill,
    IcmDrill,
    ImpliedOddsDrill,
    PushFoldDrill,
    RangeHitsDrill,
    chart_range,
    hand_strength,
    pair_class,
    range_grid,
    top_range,
)


def combo(text):
    a, b = parse_cards(text)
    return (a, b)


def steps(question):
    while question is not None:
        yield question
        question = question.follow_up


@pytest.mark.parametrize("drill", SCENARIO_DRILLS, ids=lambda d: d.key)
@pytest.mark.parametrize("seed", range(12))
def test_questions_are_well_formed(drill, seed):
    for question in steps(drill.make_question(random.Random(seed))):
        assert question.drill == drill.key
        assert question.explanation
        public = question.public()
        assert "answer" not in public
        for fact in question.payload.get("facts", []):
            assert fact["label"]
            assert fact["value"]
        if question.kind is AnswerKind.CHOICE:
            assert question.answer in question.choices
            assert grade(question, question.answer).correct
        else:
            assert grade(question, float(question.answer)).correct
            assert not grade(question, float(question.answer) + question.tolerance + 1).correct


def test_hand_story_is_three_linked_steps():
    for seed in range(40):
        chain = list(steps(HandStoryDrill().make_question(random.Random(seed))))
        assert len(chain) == 3
        preflop, turn, river = chain
        assert preflop.answer == "Raise"
        assert len(turn.payload["board"]) == 4
        assert len(river.payload["board"]) == 5
        assert turn.payload["board"] == river.payload["board"][:4]
        assert preflop.payload["hole"] == turn.payload["hole"] == river.payload["hole"]
        assert grade(turn, turn.answer).follow_up is river
        assert river.highlight  # villain's actual hand is revealed


def test_hand_story_skips_ranges_too_narrow_to_teach():
    hero = combo("Ah9h")
    board = parse_cards("QhJh2s5d7c")
    story = HandStoryDrill()._story(random.Random(0), hero, board[:3], board[3], board[4], [])
    assert story is None


def test_pair_class():
    board = parse_cards("Kh7d2c")
    assert pair_class(combo("AsKd"), board) == "top pair+"
    assert pair_class(combo("AsAd"), board) == "top pair+"
    assert pair_class(combo("7s6s"), board) == "weaker pair"
    assert pair_class(combo("QsQd"), board) == "weaker pair"
    assert pair_class(combo("Ks7s"), board) == "two pair+"
    assert pair_class(combo("AsQd"), board) == "no pair"


def test_hand_strength_table_matches_known_values():
    table = hand_strength()
    assert len(table) == 169
    assert set(table) == set(ALL_CLASSES)
    assert table["AA"] == pytest.approx(0.852, abs=0.01)
    assert table["72o"] == pytest.approx(0.346, abs=0.01)
    assert max(table, key=lambda c: table[c]) == "AA"


def test_top_range():
    top15 = top_range(0.15)
    assert "AA" in top15
    assert "72o" not in top_range(0.5)
    assert 0.15 <= top15.fraction() < 0.17
    assert len(top_range(1.0)) == 169


def test_range_grid_marks_members():
    grid = range_grid(chart_range("utg-open", "Raise"))
    assert grid[0][0] == "In range"  # AA
    assert grid[12][0] == "Fold"  # A2o


def test_bluff_ev_matches_the_formula():
    for seed in range(20):
        q = BluffEvDrill().make_question(random.Random(seed))
        pot, bet = q.payload["pot"], q.payload["bet"]
        fold = int(q.payload["facts"][1]["value"].rstrip("%")) / 100
        if "nothing" in q.prompt:
            assert float(q.answer) == pytest.approx(fold * pot - (1 - fold) * bet, abs=0.06)


def test_implied_odds_make_the_call_break_even():
    for seed in range(20):
        q = ImpliedOddsDrill().make_question(random.Random(seed))
        pot, bet, extra = q.payload["pot"], q.payload["bet"], float(q.answer)
        outs = int(q.payload["facts"][0]["value"])
        hit = outs / 46
        ev = hit * (pot + bet + extra) - (1 - hit) * bet
        assert ev == pytest.approx(0, abs=0.1)


def test_bluff_catch_answer_follows_the_counts():
    for seed in range(30):
        q = BluffCatchDrill().make_question(random.Random(seed))
        value = int(q.payload["facts"][0]["value"])
        bluffs = int(q.payload["facts"][1]["value"])
        need = odds.required_equity(q.payload["pot"], q.payload["bet"])
        assert (q.answer == "Call") == (bluffs / (value + bluffs) > need)


def test_push_fold_premium_hands_always_shove():
    calls_wide = PushFoldDrill()
    for seed in range(15):
        q = calls_wide.make_question(random.Random(seed))
        if q.reveal["hand"] in ("AA", "KK", "QQ"):
            assert q.answer == "Shove"


def test_icm_questions_cover_both_kinds():
    prompts = {IcmDrill().make_question(random.Random(s)).prompt for s in range(20)}
    assert any("ICM equity" in p for p in prompts)
    assert any("shoves" in p for p in prompts)


def test_range_hits_reveals_the_range():
    q = RangeHitsDrill().make_question(random.Random(1))
    assert q.reveal["choices"] == ["In range"]
    assert q.reveal["label"].endswith("range")
    assert 0 < float(q.answer) < 100
