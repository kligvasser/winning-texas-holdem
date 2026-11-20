import random

import pytest

from holdem.core.cards import parse_cards
from holdem.core.range_score import best_match, grade_range, range_match
from holdem.core.ranges import class_of_combo, combos_of_class
from holdem.drills.base import AnswerKind, Question, grade
from holdem.engine.bots import STYLES, Bot
from holdem.engine.headsup import HeadsUpHand
from holdem.reading import HandReadingDrill, _checkpoints, _play, deal_read, describe

W = {"AA": 6.0, "KK": 6.0, "72o": 0.0}
C = {"AA": 6, "KK": 6, "72o": 12}


def test_range_match_rewards_the_right_shape():
    assert range_match(["AA", "KK"], W, C) == pytest.approx(1.0)
    assert range_match(["AA"], W, C) == pytest.approx(0.5)  # too narrow
    assert range_match(["AA", "KK", "72o"], W, C) == pytest.approx(0.5)  # too wide
    assert range_match([], W, C) == 0
    assert range_match(["QQ"], W, C) == 0  # no live combos
    assert range_match(["AA"], {"AA": 0.0}, {"AA": 6}) == 0


def test_best_match_finds_the_ideal_range():
    score, chosen = best_match(W, C)
    assert score == pytest.approx(1.0)
    assert sorted(chosen) == ["AA", "KK"]
    assert best_match({}, {}) == (0.0, [])


def test_grade_range_feedback():
    reveal = {"class_weights": W, "class_combos": C, "best": 1.0, "villain": "Nit"}
    score, best, lines = grade_range(["AA", "72o"], reveal)
    assert score == pytest.approx(1 / 3 + 0)  # AA share 6/18 of painted vs 0.5 true
    assert best == 1.0
    assert "matched 33%" in lines[0]
    assert any("removed: KK" in line for line in lines)
    assert any("almost never" in line and "72o" in line for line in lines)
    _, _, empty = grade_range([], reveal)
    assert any("removed every hand" in line for line in empty)


def test_range_answers_are_graded_by_match():
    reveal = {"class_weights": W, "class_combos": C, "best": 1.0, "villain": "Nit"}
    q = Question(
        "hand-reading", "c", "p", AnswerKind.RANGE, 100.0, reveal=reveal, explanation=("x",)
    )
    good = grade(q, ["AA", "KK"])
    assert good.correct
    assert good.response == 100.0
    assert good.expected == 100.0
    assert good.error is None
    assert good.explanation[-1] == "x"
    assert grade(q, "AA, KK").correct  # a comma-separated string works too
    assert not grade(q, ["AA"]).correct
    assert not grade(q, []).correct
    with pytest.raises(ValueError):
        grade(q, 3)


def test_describe_conjugates_for_you_and_the_bot():
    hand = HeadsUpHand([200, 200], 0, random.Random(1))
    hand.act("raise", 5)
    hand.act("call")
    raise_, call = hand.log[2], hand.log[3]
    assert describe(raise_, ("You", "Nit"), hero=0) == "You raise to 2.5bb"
    assert describe(call, ("You", "Nit"), hero=0) == "Nit calls 1.5bb"
    assert describe(raise_, ("Nit", "You"), hero=1) == "Nit raises to 2.5bb"


def preflop_probability(read, combo):
    """P(villain's preflop actions | villain holds combo), replayed independently."""
    villain = read.villain
    replay = HeadsUpHand(list(read.hand.stacks), read.hand.button, random.Random(read.seed))
    model = Bot(read.style, random.Random(0))
    probability = 1.0
    for action in read.hand.log:
        if action.kind == "post" or action.street != "preflop":
            continue
        if action.player == villain:
            actual = replay.hole[villain]
            replay.hole[villain] = combo
            probability *= sum(p for kind, _, p in model.options(replay) if kind == action.kind)
            replay.hole[villain] = actual
        replay.act(action.kind, action.to if action.kind in ("bet", "raise") else None)
    return probability


@pytest.mark.parametrize("seed", range(4))
def test_preflop_weights_match_an_independent_replay(seed):
    read = deal_read(random.Random(seed))
    point = read.checkpoints[0]
    assert point.street == "preflop"
    hero_cards = set(read.hand.hole[1 - read.villain])
    for hand_class in ("AA", "KQs", "T9o", "72o", "54s"):
        live = [c for c in combos_of_class(hand_class) if not set(c) & hero_cards]
        expected = sum(preflop_probability(read, c) for c in live)
        assert point.weights.get(hand_class, 0.0) == pytest.approx(expected)
        assert point.combos.get(hand_class, 0) in (0, len(live))


@pytest.mark.parametrize("seed", range(8))
def test_reading_questions_chain_through_the_hand(seed):
    question = HandReadingDrill().make_question(random.Random(seed))
    steps = []
    while question is not None:
        steps.append(question)
        question = question.follow_up
    assert len(steps) >= 3
    streets = [q.prompt.split(":")[0].removeprefix("After the ") for q in steps]
    assert streets[0] == "preflop"
    assert len(set(streets)) == len(streets)
    for q in steps:
        assert q.kind is AnswerKind.RANGE
        assert 0 < q.reveal["best"] <= 1
        assert len(q.reveal["weights"]) == 13
        assert q.payload["lines"]
        best_range = best_match(q.reveal["class_weights"], q.reveal["class_combos"])[1]
        assert grade(q, best_range).correct
    last = steps[-1]
    assert last.reveal["hand"] == class_of_combo(*parse_cards("".join(last.highlight)))
    assert "actually had" in last.explanation[-1]


def test_play_and_checkpoints_cover_both_seats():
    rng = random.Random(0)
    for villain in (0, 1):
        hand = _play(STYLES["station"], villain, 0, 5, rng)
        assert hand.finished
        points = _checkpoints(STYLES["station"], villain, hand, 5)
        assert all(p.weights for p in points)
        assert all(0 <= v <= 1 for p in points for v in p.density().values())


def test_missed_hands_of_equal_weight_are_listed_strongest_first():
    weights = {"72o": 1.0, "AA": 1.0, "KQs": 1.0}
    reveal = {"class_weights": weights, "class_combos": {"72o": 12, "AA": 6, "KQs": 4}}
    reveal |= {"best": 1.0, "villain": "Nit"}
    _, _, lines = grade_range([], reveal)
    assert any("AA, KQs, 72o" in line for line in lines)
