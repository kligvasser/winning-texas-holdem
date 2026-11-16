import random
import tomllib

import pytest

from holdem.core.cards import parse_cards
from holdem.drills.base import grade
from holdem.stories import (
    PREDICATES,
    STORY_DRILLS,
    Story,
    StoryDrill,
    _board_ok,
    _Context,
    _deal,
    _decide,
    _step,
    build_story,
    hero_ok,
    load_stories,
    villain_keeps,
)


def combo(text):
    a, b = parse_cards(text)
    return (a, b)


def chain(question):
    while question is not None:
        yield question
        question = question.follow_up


@pytest.mark.parametrize("drill", STORY_DRILLS, ids=lambda d: d.key)
@pytest.mark.parametrize("seed", range(6))
def test_every_story_deals_a_consistent_graded_hand(drill, seed):
    steps = list(chain(drill.make_question(random.Random(seed))))
    assert len(steps) == len(drill.story.steps)
    hole = steps[0].payload["hole"]
    previous_board: list[str] = []
    for question in steps:
        assert question.drill == drill.key
        assert question.payload["hole"] == hole
        board = question.payload.get("board", [])
        assert board[: len(previous_board)] == previous_board  # the board only grows
        previous_board = board
        assert question.answer in question.choices
        assert grade(question, question.answer).correct
        assert "{" not in question.prompt  # every placeholder was filled
    assert steps[-1].highlight  # the villain's hand is revealed at the end
    assert "actually had" in steps[-1].explanation[-1]


def test_stories_load_with_unique_keys_and_keep_the_old_key():
    stories = load_stories()
    keys = [s.key for s in stories]
    assert len(set(keys)) == len(keys) >= 4
    assert "hand-story" in keys
    for story in stories:
        assert story.playable_classes()
        assert len(story.villain_range()) > 0


BOARD = parse_cards("Kh7d2c")


@pytest.mark.parametrize(
    ("name", "hand", "expected"),
    [
        ("set", "7s7c", True),
        ("set", "QsQc", False),
        ("overpair", "AsAc", True),
        ("overpair", "QsQc", False),
        ("underpair_to_top", "QsQc", True),
        ("underpair_to_top", "AsAc", False),
        ("top_pair", "AsKd", True),
        ("top_pair", "KsKc", False),
        ("top_pair_plus", "AsAc", True),
        ("top_pair_plus", "7s6s", False),
        ("two_pair_plus", "Ks7s", True),
        ("two_pair_plus", "AsKd", False),
        ("pair_plus", "3s3c", True),
        ("pair_plus", "AsQd", False),
        ("one_pair", "7s6s", True),
        ("one_pair", "Ks7s", False),
        ("weak_pair", "7s6s", True),
        ("weak_pair", "AsKd", False),
        ("nothing", "AsQd", True),
        ("nothing", "7s6s", False),  # a pair
    ],
)
def test_predicates(name, hand, expected):
    assert PREDICATES[name](combo(hand), BOARD) is expected


def test_draw_predicates():
    board = parse_cards("Kh7h2c")
    assert PREDICATES["flush_draw"](combo("Ah5h"), board)
    assert PREDICATES["oesd"](combo("9c8c"), parse_cards("Th7d2c"))
    assert PREDICATES["draw"](combo("Ah5h"), board)
    river = parse_cards("Kh7h2c3s4d")
    assert not PREDICATES["flush_draw"](combo("Ah5h"), river)
    assert not PREDICATES["oesd"](combo("9c8c"), river)
    assert not PREDICATES["draw"](combo("Ah5h"), river)
    assert PREDICATES["two_pair_plus"](combo("5s6s"), river)  # a made straight


def test_condition_lists():
    assert hero_ok(["top_pair", "not_set"], combo("AsKd"), BOARD)
    assert not hero_ok(["set"], combo("AsKd"), BOARD)
    assert villain_keeps([], combo("2s3s"), BOARD)  # no filter keeps everything
    assert villain_keeps(["set", "top_pair"], combo("AsKd"), BOARD)
    assert not villain_keeps(["set"], combo("AsKd"), BOARD)


def test_board_conditions():
    flop = parse_cards("Kh7d2c")
    assert _board_ok(["unpaired"], [], flop)
    assert not _board_ok(["unpaired"], [], parse_cards("Kh7dKc"))
    assert _board_ok(["blank"], flop, parse_cards("3s"))
    assert not _board_ok(["blank"], flop, parse_cards("7s"))  # pairs the board
    assert not _board_ok(["blank"], parse_cards("Kh7h2c"), parse_cards("3h"))  # third heart
    assert not _board_ok(["blank"], parse_cards("Jh9d8c"), parse_cards("Ts"))  # straight window
    assert _board_ok([], flop, parse_cards("Ks"))


def base(**over):
    data = {
        "key": "t",
        "title": "T",
        "description": "d",
        "pot": 5.5,
        "hero": {"classes": "AA"},
        "villain": {"name": "BB", "spot": "bb-vs-btn", "action": "Call"},
        "steps": [
            {
                "street": "preflop",
                "decision": "chart",
                "spot": "btn-open",
                "expect": "Raise",
                "prompt": "p",
            }
        ],
    }
    data.update(over)
    return data


@pytest.mark.parametrize(
    ("steps", "message"),
    [
        ([], "first step"),
        ([{"street": "flop", "decision": "call", "prompt": "p"}], "first step"),
        (
            [base()["steps"][0], {"street": "fifth", "decision": "call", "prompt": "p"}],
            "unknown street",
        ),
        (
            [base()["steps"][0], {"street": "flop", "decision": "shove", "prompt": "p"}],
            "unknown decision",
        ),
        (
            [
                base()["steps"][0],
                {"street": "flop", "decision": "call", "prompt": "p", "hero": ["x"]},
            ],
            "unknown condition",
        ),
    ],
)
def test_story_validation(steps, message):
    with pytest.raises(ValueError, match=message):
        Story.from_toml(base(steps=steps))


def test_story_needs_a_hero_hand_the_chart_plays():
    with pytest.raises(ValueError, match="no hero hand"):
        Story.from_toml(base(hero={"classes": "72o"}))


def test_toml_round_trip_and_villain_class_filter():
    text = """
key = "x"
title = "X"
description = "d"
pot = 17.5
[hero]
classes = "QQ"
[villain]
name = "CO"
spot = "co-open"
action = "Raise"
classes = "AA, KK"
[[steps]]
street = "preflop"
decision = "chart"
spot = "btn-vs-co"
expect = "3-bet"
prompt = "p"
"""
    story = Story.from_toml(tomllib.loads(text))
    assert set(story.villain_range()) == {"AA", "KK"}
    assert _step({"street": "flop", "decision": "call", "prompt": "p", "size": [0.5, 1]}).size == (
        0.5,
        1,
    )


def test_impossible_boards_give_up(monkeypatch):
    story = Story.from_toml(
        base(
            steps=[
                base()["steps"][0],
                {"street": "flop", "decision": "call", "prompt": "p", "hero": ["set"]},
            ]
        )
    )
    monkeypatch.setattr("holdem.stories.MAX_DEALS", 3)
    assert _deal(story, random.Random(0), combo("AsKd")) is None
    assert build_story(story, random.Random(0), "k", "c") is None


def ctx_for(story, hero, board, pot=10.0):
    return _Context(story, combo(hero), parse_cards(board), pot, random.Random(0))


def test_decisions_decline_spots_that_teach_nothing():
    story = Story.from_toml(base())
    tiny = _step(
        {"street": "flop", "decision": "call", "prompt": "p", "size": 0.5, "bets": ["set"]}
    )
    ctx = ctx_for(story, "7s2s", "Kh7d2c3s4d")  # hero blocks most sets
    ctx.filters.append((("set",), "flop"))
    assert _decide(tiny, ctx) is None  # fewer than four villain combos
    value = _step(
        {"street": "flop", "decision": "value", "prompt": "p", "size": 0.5, "calls": ["set"]}
    )
    assert _decide(value, ctx) is None


def test_close_decisions_are_rejected(monkeypatch):
    story = Story.from_toml(base())
    ctx = ctx_for(story, "AsKd", "Kh7d2c3s4d")
    monkeypatch.setattr("holdem.stories._equity", lambda *a: 0.25)
    call = _step({"street": "flop", "decision": "call", "prompt": "p", "size": 0.5})
    assert _decide(call, ctx) is None  # 25% equity against a 25% price
    monkeypatch.setattr("holdem.stories._equity", lambda *a: 0.5)
    value = _step(
        {"street": "flop", "decision": "value", "prompt": "p", "size": 0.5, "calls": ["pair_plus"]}
    )
    assert _decide(value, ctx) is None
    bluff = _step(
        {
            "street": "river",
            "decision": "bluff",
            "prompt": "p",
            "size": 1.0,
            "folds": ["nothing", "weak_pair", "one_pair", "draw"],
        }
    )
    monkeypatch.setattr("holdem.stories.villain_keeps", lambda names, c, b: hash(c) % 2 == 0)
    decided = _decide(bluff, ctx)
    assert decided is None or decided["answer"] in ("Bet", "Check")


def test_value_check_and_bluff_outcomes():
    story = Story.from_toml(base())
    ctx = ctx_for(story, "7s2s", "Kh7d2c3s4d")
    value = _step(
        {
            "street": "river",
            "decision": "value",
            "prompt": "p",
            "size": 1.0,
            "calls": ["two_pair_plus"],
        }
    )
    decided = _decide(value, ctx)
    assert decided is not None
    assert decided["answer"] == "Check"  # bottom two pair loses to most hands that call
    thin = _step(
        {
            "street": "river",
            "decision": "value",
            "prompt": "p",
            "size": 1.0,
            "calls": ["top_pair_plus"],
        }
    )
    beats_top_pair = _decide(thin, ctx)
    assert beats_top_pair is not None
    assert beats_top_pair["answer"] == "Bet"
    bluff = _step(
        {"street": "river", "decision": "bluff", "prompt": "p", "size": 1.0, "folds": ["nothing"]}
    )
    decided = _decide(bluff, ctx)
    assert decided is not None
    assert decided["outcome"](combo("QsJs")) == "your bluff wins the pot"
    assert decided["outcome"](combo("AsKs")) == "they call"


def test_story_drill_retries_until_a_deal_works(monkeypatch):
    drill = StoryDrill(load_stories()[0])
    calls = []
    real = build_story

    def flaky(*args):
        calls.append(1)
        return None if len(calls) == 1 else real(*args)

    monkeypatch.setattr("holdem.stories.build_story", flaky)
    assert drill.make_question(random.Random(1)) is not None
    assert len(calls) == 2


def test_empty_final_range_rejects_the_deal(monkeypatch):
    story = next(s for s in load_stories() if s.steps[-1].street == "turn")
    real = _Context.villain_combos

    def no_river_hands(self, street, extra=()):
        return [] if street == "river" else real(self, street, extra)

    monkeypatch.setattr(_Context, "villain_combos", no_river_hands)
    assert build_story(story, random.Random(2), "k", "c") is None


def test_bluffs_need_a_real_range_and_a_clear_answer(monkeypatch):
    story = Story.from_toml(base())
    ctx = ctx_for(story, "AsKd", "Kh7d2c3s4d")
    bluff = _step(
        {"street": "river", "decision": "bluff", "prompt": "p", "size": 1.0, "folds": ["nothing"]}
    )
    monkeypatch.setattr(_Context, "villain_combos", lambda self, street, extra=(): [])
    assert _decide(bluff, ctx) is None
    monkeypatch.undo()
    monkeypatch.setattr("holdem.stories.villain_keeps", lambda names, c, b: True)
    monkeypatch.setattr("holdem.stories.odds.alpha", lambda pot, bet: 1.0)
    assert _decide(bluff, ctx) is None  # everyone folds and the bluff needs exactly that


def test_story_steps_can_narrow_the_villain_range():
    story = Story.from_toml(
        base(
            steps=[
                base()["steps"][0],
                {
                    "street": "flop",
                    "decision": "value",
                    "prompt": "Flop {flop}, pot {pot}, bet {bet}?",
                    "size": 0.5,
                    "villain": ["pair_plus", "draw"],
                    "calls": ["pair_plus"],
                    "hero": ["overpair"],
                },
            ]
        )
    )
    question = None
    rng = random.Random(4)
    while question is None:
        question = build_story(story, rng, "k", "c")
    flop = question.follow_up
    assert flop is not None
    assert flop.payload["bet"] > 0
    assert "Flop" in flop.prompt
