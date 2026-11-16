import random
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from holdem.core.cards import parse_cards
from holdem.db import hand_summary, play_stats, save_hand
from holdem.engine.bots import STYLES, Bot, estimated_range, hand_class, percentile, top_share_range
from holdem.engine.headsup import Action, HeadsUpHand
from holdem.engine.play import BOT, HERO, PlaySession, bb, equity_against, new_session, review


def combo(text):
    a, b = parse_cards(text)
    return (a, b)


def test_percentile_ranks_hands():
    ranks = percentile()
    assert ranks["AA"] < ranks["KK"] < ranks["72o"]
    assert ranks["AA"] == pytest.approx(6 / 1326)
    assert max(ranks.values()) == pytest.approx(1.0)
    assert "AA" in top_share_range(0.01)
    assert len(top_share_range(1.0)) == 169


@pytest.mark.parametrize(
    ("hole", "board", "expected"),
    [
        ("7s7c", "Kh7d2c", "monster"),
        ("AsKd", "Kh7d2c", "strong"),
        ("QsQd", "Kh7d2c", "medium"),  # an underpair to the king
        ("AsAd", "Kh7d2c", "strong"),  # an overpair
        ("QsQd", "Jh7d2c", "strong"),  # an overpair
        ("8s6s", "Kh7d5c", "draw"),
        ("AsQd", "Kh7d2c", "air"),
    ],
)
def test_hand_classes(hole, board, expected):
    assert hand_class(combo(hole), parse_cards(board)) == expected


def test_every_style_is_described():
    for style in STYLES.values():
        public = style.public()
        assert public["name"] and public["blurb"]
        assert style.open + style.limp > 0


def play_out(hand, bots):
    for _ in range(100):
        if hand.finished:
            return
        kind, to = bots[hand.current].decide(hand)
        hand.act(kind, to)
    raise AssertionError("hand did not finish")


@pytest.mark.parametrize("a", list(STYLES))
@pytest.mark.parametrize("b", list(STYLES))
def test_bots_only_make_legal_moves(a, b):
    for seed in range(15):
        hand = HeadsUpHand([200, 200], seed % 2, random.Random(seed))
        bots = [Bot(STYLES[a], random.Random(seed)), Bot(STYLES[b], random.Random(seed + 7))]
        play_out(hand, bots)
        assert sum(hand.net()) == 0


def test_short_stacks_and_tiny_bets(monkeypatch):
    """Bots must cope when stacks are smaller than their usual sizes."""
    for seed in range(30):
        hand = HeadsUpHand([7, 9], seed % 2, random.Random(seed))
        bots = [
            Bot(STYLES["maniac"], random.Random(seed)),
            Bot(STYLES["station"], random.Random(1)),
        ]
        play_out(hand, bots)


def log_of(*entries):
    return [Action("preflop", p, k, 0, 0, 0, 0) for p, k in entries]


def test_estimated_ranges_follow_preflop_actions():
    tag = STYLES["tag"]
    button, bot = 1, 1
    opened = log_of((1, "post"), (0, "post"), (1, "raise"))
    assert estimated_range(tag, opened, bot, button) == top_share_range(tag.open)
    three_bet = log_of((0, "raise"), (1, "raise"))
    assert estimated_range(tag, three_bet, bot, 0) == top_share_range(tag.three_bet)
    called_3bet = log_of((1, "raise"), (0, "raise"), (1, "call"))
    assert estimated_range(tag, called_3bet, bot, button) == top_share_range(tag.call_3bet)
    four_bet = log_of((1, "raise"), (0, "raise"), (1, "raise"))
    assert estimated_range(tag, four_bet, bot, button) == top_share_range(tag.four_bet)
    limp = log_of((1, "call"))
    station = STYLES["station"]
    assert estimated_range(station, limp, bot, button) == top_share_range(station.limp)
    called_open = log_of((0, "raise"), (1, "call"))
    assert estimated_range(tag, called_open, bot, 0) == top_share_range(tag.call)
    checked = log_of((0, "call"), (1, "check"))
    assert len(estimated_range(tag, checked, bot, 0)) == 169


def test_session_plays_reviews_and_alternates_the_button():
    play = new_session("station", seed=3)
    assert play.hand.button == 0
    rng = random.Random(0)
    for _ in range(6):
        while not play.hand.finished:
            legal = play.hand.legal()
            play.act("check" if legal.can_check else rng.choice(["call", "fold"]))
        state = play.state()
        assert state["legal"] is None
        assert state["hand"]["finished"]
        record = play.record()
        assert record["style"] == "station"
        assert record["hand"]["hole"][1] is not None  # the record always shows the bot's cards
        for d in state["decisions"]:
            assert d["verdict"] in ("good", "leak", "mistake", "info")
        button = play.hand.button
        play.new_hand()
        assert play.hand.button == 1 - button
    assert play.hands_played == 6


def test_not_your_turn_and_coach():
    play = new_session("tag", seed=5)
    while play.hand.current != HERO and not play.hand.finished:
        play.new_hand()
    coach = play.coach()
    assert 0 <= coach["equity"] <= 1
    assert play.state()["legal"]["max_raise_to"] > 0
    play.act("fold") if not play.hand.legal().can_check else play.act("check")
    while not play.hand.finished:
        legal = play.hand.legal()
        play.act("check" if legal.can_check else "fold")
    with pytest.raises(ValueError):
        play.act("check")
    with pytest.raises(ValueError):
        play.coach()
    with pytest.raises(KeyError):
        new_session("shark")
    assert new_session("nit").seed >= 0


def test_review_grades_calls_and_folds(monkeypatch):
    style = STYLES["tag"]
    hand = HeadsUpHand([200, 200], 1, random.Random(4))
    hand.act("raise", 6)  # the bot (button) opens
    hand.act("call")  # hero calls
    hand.act("check")
    hand.act("bet", 10)
    hand.act("fold")
    monkeypatch.setattr("holdem.engine.play.equity_against", lambda *a: (0.9, 0.5))
    decisions = review(style, hand)
    kinds = [d.action for d in decisions]
    assert kinds == ["call", "check", "fold"]
    fold = decisions[-1]
    assert fold.verdict == "mistake"  # 90% equity and folded
    assert fold.loss_bb > 1
    monkeypatch.setattr("holdem.engine.play.equity_against", lambda *a: (0.02, 0.5))
    call = review(style, hand)[0]
    assert call.verdict in ("leak", "mistake")
    monkeypatch.setattr("holdem.engine.play.equity_against", lambda *a: (0.3, 0.5))
    assert review(style, hand)[0].verdict == "good"


def test_raises_are_shown_but_not_graded(monkeypatch):
    hand = HeadsUpHand([200, 200], 1, random.Random(4))
    hand.act("raise", 6)
    hand.act("raise", 20)
    hand.act("fold")
    monkeypatch.setattr("holdem.engine.play.equity_against", lambda *a: (0.5, 0.5))
    [decision] = review(STYLES["tag"], hand)
    assert decision.verdict == "info"
    assert "not graded" in decision.note
    assert decision.public()["need"] is not None


def test_equity_against_uses_the_estimated_range():
    hand = HeadsUpHand([200, 200], 0, random.Random(1))
    hand.act("raise", 6)
    equity, share = equity_against(STYLES["nit"], hand, hand.log, "preflop")
    assert 0 < equity < 1
    assert share == pytest.approx(1.0)  # the bot has not acted yet


def test_storage_summary_and_stats(engine):
    play = new_session("maniac", seed=9)
    with Session(engine) as session:
        assert play_stats(session)["hands"] == 0
        rows = []
        for _ in range(3):
            while not play.hand.finished:
                legal = play.hand.legal()
                if legal.can_raise and play.hand.street == 0:
                    play.act("raise", legal.min_raise_to)
                else:
                    play.act("check" if legal.can_check else "call")
            rows.append(save_hand(session, play.record(), datetime(2026, 11, 16, tzinfo=UTC)))
            play.new_hand()
        summary = hand_summary(rows[-1])
        assert summary["style"] == "maniac"
        assert len(summary["hole"]) == 2
        stats = play_stats(session)
    assert stats["hands"] == 3
    assert 0 < stats["vpip"] <= 1
    assert 0 < stats["pfr"] <= 1
    assert stats["bb_per_100"] == pytest.approx(stats["net_bb"] / 3 * 100, abs=0.1)


def test_bb_helper_and_constants():
    assert bb(5) == 2.5
    assert (HERO, BOT) == (0, 1)
    assert isinstance(new_session("lag", seed=1), PlaySession)


def test_decide_samples_from_options_with_a_safe_fallback():
    hand = HeadsUpHand([200, 200], 0, random.Random(2))
    hand.act("call")
    hand.act("check")  # flop, the big blind (player 1) to act
    bot = Bot(STYLES["tag"], random.Random(0))
    options = bot.options(hand)
    assert sum(p for _, _, p in options) == pytest.approx(1)

    class Edge:
        def random(self):
            return 1.0  # beyond every bucket, as rounding could leave

    bot.rng = Edge()  # type: ignore[assignment]
    kind, _ = bot.decide(hand)
    assert kind == [k for k, _, p in options if p > 0][-1]
