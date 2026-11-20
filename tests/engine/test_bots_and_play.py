import random
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from holdem.core.cards import parse_cards
from holdem.db import hand_summary, play_stats, save_hand
from holdem.engine.bots import (
    STYLES,
    Bot,
    SeatBot,
    band_range,
    call_share,
    estimated_range,
    hand_class,
    limp_share,
    open_share,
    percentile,
    seat_range,
    three_bet_share,
    top_share_range,
)
from holdem.engine.headsup import Action, HeadsUpHand
from holdem.engine.play import HERO, STACK, PlaySession, bb, new_session, review
from holdem.engine.reads import Push, equity_against, opponents_in_pot
from holdem.engine.table import TableHand


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
        ("Ks2d", "Ah2c2s", "monster"),  # trips with one hole card
        ("As7d", "7h7c2s", "monster"),
        ("Ks5d", "Kh2c2s", "strong"),  # top pair on a paired board, not trips
        ("2c3d", "5h6d7s8c9h", "medium"),  # the straight is on the board
        ("Tc3d", "5h6d7s8c9h", "monster"),  # a higher straight than the board's
        ("2c3d", "KhKd7s7c4h", "air"),  # two pair on the board is nobody's hand
    ],
)
def test_hand_classes(hole, board, expected):
    assert hand_class(combo(hole), parse_cards(board)) == expected


def test_every_style_is_described():
    for style in STYLES.values():
        public = style.public()
        assert public["name"] and public["blurb"] and public["character"]
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


def raise_log(*entries):
    return [Action("preflop", p, k, 0, 0, 0, 0) for p, k in entries]


def test_seat_ranges_follow_position_and_preflop_actions():
    tag = STYLES["tag"]
    station = STYLES["station"]
    opened = raise_log((3, "post"), (1, "raise"))
    assert seat_range(tag, opened, 1, "UTG") == top_share_range(open_share(tag, "UTG"))
    assert len(seat_range(tag, opened, 1, "UTG")) < len(seat_range(tag, opened, 1, "BTN"))
    three_bet = raise_log((1, "raise"), (2, "raise"))
    assert seat_range(tag, three_bet, 2, "CO") == top_share_range(three_bet_share(tag))
    cold_four = raise_log((1, "raise"), (2, "raise"), (3, "raise"))
    assert seat_range(tag, cold_four, 3, "BTN") == top_share_range(tag.four_bet)
    five_bet = raise_log((1, "raise"), (2, "raise"), (1, "raise"))
    assert seat_range(tag, five_bet, 1, "CO") == top_share_range(tag.four_bet)
    called_3bet = raise_log((1, "raise"), (2, "raise"), (1, "call"))
    assert seat_range(tag, called_3bet, 1, "BTN") == top_share_range(tag.call_3bet)
    limp = raise_log((1, "call"))
    limped = seat_range(station, limp, 1, "HJ")
    assert limped == band_range(open_share(station, "HJ"), limp_share(station))
    assert "AA" not in limped  # it would have raised its best hands
    called = raise_log((1, "raise"), (2, "call"))
    flat = seat_range(tag, called, 2, "BB")
    assert flat == band_range(three_bet_share(tag), call_share(tag, "BB"))
    assert "AA" not in flat and "AA" in top_share_range(call_share(tag, "BB"))
    # A maniac re-raises everything it would call with, so a call says nothing more.
    maniac = STYLES["maniac"]
    assert seat_range(maniac, called, 2, "CO") == top_share_range(call_share(maniac, "CO"))
    # The big blind raises limpers only with its re-raising hands.
    iso = raise_log((1, "call"), (2, "raise"))
    assert seat_range(tag, iso, 2, "BB") == top_share_range(three_bet_share(tag))
    assert seat_range(tag, iso, 2, "BTN") == top_share_range(open_share(tag, "BTN"))
    assert len(seat_range(tag, called, 2, "CO")) < len(seat_range(tag, called, 2, "BB"))
    cold_call = raise_log((1, "raise"), (2, "raise"), (3, "call"))
    assert seat_range(tag, cold_call, 3, "BTN") == top_share_range(tag.call_3bet)
    limp_call = raise_log((1, "call"), (2, "raise"), (1, "call"))
    assert seat_range(station, limp_call, 1, "HJ") == limped
    waiting = raise_log((1, "raise"), (2, "check"))
    assert len(seat_range(tag, waiting, 4, "BB")) == 169
    assert len(seat_range(tag, waiting, 2, "BB")) == 169


@pytest.mark.parametrize("seats", [3, 6])
def test_seat_bots_only_make_legal_moves(seats):
    styles = list(STYLES.values())
    rng = random.Random(seats)
    for seed in range(150):
        short = seed % 3 == 0
        stacks = [rng.randint(3, 40) if short else 200 for _ in range(seats)]
        hand = TableHand(stacks, seed % seats, random.Random(seed))
        bots = [SeatBot(styles[(seed + s) % 5], random.Random(seed + s)) for s in range(seats)]
        play_out(hand, bots)
        assert sum(hand.net()) == 0


def play_hand(play, rng):
    while not play.hand.finished:
        legal = play.hand.legal()
        roll = rng.random()
        if legal.can_raise and roll < 0.15:
            play.act("bet" if max(play.hand.bets) == 0 else "raise", legal.min_raise_to)
        elif legal.can_check:
            play.act("check")
        else:
            play.act("call" if roll < 0.8 else "fold")


def test_session_plays_reviews_and_moves_the_button():
    play = new_session(seed=3)
    assert play.hand.button == 0
    assert play.seats()[0]["key"] == "hero"
    assert {s["key"] for s in play.seats()[1:]} == set(STYLES)
    rng = random.Random(0)
    for played in range(7):
        assert play.hand.button == played % 6
        first = play.state()
        assert first["frames"][-1]["last"] == first["hand"]["last"]
        assert "log" not in first["frames"][0]
        play_hand(play, rng)
        state = play.state()
        assert state["legal"] is None
        assert state["hand"]["finished"]
        assert state["frames"]
        record = play.record()
        assert record["style"] == "6-max"
        assert record["frames"][-1]["finished"] and "log" not in record["frames"][0]
        assert len(record["frames"]) >= len(state["frames"])
        assert play.stacks != [STACK] * 6 or state["hand"]["net"] == [0] * 6
        assert not state["carry"]
        assert all(cards is not None for cards in record["hand"]["hole"])
        assert len(record["seats"]) == 6
        for d in state["decisions"]:
            assert d["verdict"] in ("good", "leak", "mistake", "info")
        play.new_hand()
        assert play.hand.stacks == [STACK] * 6
    assert play.hands_played >= 7


def test_carried_stacks_persist_and_short_stacks_rebuy():
    play = new_session(seed=3, carry=True)
    assert play.state()["carry"]
    rng = random.Random(1)
    for _ in range(4):
        play_hand(play, rng)
        after = list(play.stacks)
        assert sum(after) == sum(play.hand.stacks)
        play.new_hand()
        assert play.hand.stacks == [s if s >= 20 else STACK for s in after]
    play_hand(play, rng)
    play.stacks = [19, 400, 200, 200, 200, 181]
    play.new_hand()
    assert play.hand.stacks == [STACK, 400, 200, 200, 200, 181]


def test_not_your_turn_and_coach():
    play = new_session(seed=5)
    while play.hand.finished:
        play.new_hand()
    coach = play.coach()
    assert 0 <= coach["equity"] <= 1
    assert coach["opponents"] >= 1
    assert play.state()["legal"]["max_raise_to"] > 0
    while not play.hand.finished:
        play.act("check" if play.hand.legal().can_check else "fold")
    with pytest.raises(ValueError):
        play.act("check")
    with pytest.raises(ValueError):
        play.coach()
    assert new_session().seed >= 0


def test_review_grades_calls_and_folds(monkeypatch):
    styles = list(STYLES.values())
    hand = TableHand([200] * 3, 0, random.Random(4))
    hand.act("call")  # hero limps the button
    hand.act("raise", 8)
    hand.act("fold")
    hand.act("call")  # hero calls the raise
    hand.act("bet", 10)
    hand.act("fold")
    monkeypatch.setattr("holdem.engine.play.equity_against", lambda *a: (0.9, 1))
    decisions = review(styles, hand)
    assert [d.action for d in decisions] == ["call", "call", "fold"]
    fold = decisions[-1]
    assert fold.verdict == "mistake"  # 90% equity and folded
    assert fold.loss_bb > 1
    assert "the bot's likely range" in fold.note
    monkeypatch.setattr("holdem.engine.play.equity_against", lambda *a: (0.02, 2))
    call = review(styles, hand)[1]
    assert call.verdict in ("leak", "mistake")
    assert "2 bots' likely ranges" in call.note
    monkeypatch.setattr("holdem.engine.play.equity_against", lambda *a: (0.5, 1))
    assert review(styles, hand)[1].verdict == "good"


def test_preflop_raises_and_checks_are_shown_but_not_graded(monkeypatch):
    hand = TableHand([200] * 3, 2, random.Random(4))  # hero is the small blind
    hand.act("raise", 6)
    hand.act("raise", 20)  # hero re-raises
    hand.act("fold")
    hand.act("call")
    hand.act("check")  # hero checks the flop
    monkeypatch.setattr("holdem.engine.play.equity_against", lambda *a: (0.5, 1))
    raised, checked = review(list(STYLES.values()), hand)
    assert raised.verdict == "info"
    assert "This raise is not graded" in raised.note
    assert raised.public()["need"] is not None
    assert checked.verdict == "info"
    assert "Checks are not graded" in checked.note
    assert checked.public()["need"] is None

    option = TableHand([200] * 3, 1, random.Random(4))  # hero is the big blind
    option.act("call")
    option.act("call")
    option.act("raise", 10)  # hero raises the limpers with nothing to call
    (raised,) = review(list(STYLES.values()), option)
    assert raised.verdict == "info"
    assert raised.note.startswith("You raise") and "not graded" in raised.note


def test_a_short_stack_is_priced_on_what_it_can_win(monkeypatch):
    hand = TableHand([30, 400, 400], 0, random.Random(4))
    hand.act("call")  # hero limps the button
    hand.act("fold")
    hand.act("raise", 200)  # the big blind shoves far more than hero has
    hand.act("call")  # hero calls all in for 28 more
    monkeypatch.setattr("holdem.engine.play.equity_against", lambda *a: (0.32, 1))
    call = review(list(STYLES.values()), hand)[1]
    assert call.to_call == 28
    assert call.pot == 33  # 30 from the big blind, 2 from hero, 1 dead small blind
    assert call.need == pytest.approx(28 / 61)
    assert call.verdict == "mistake"
    assert "into 16.5bb you needed 46%" in call.note


def test_review_grades_bets_and_raises_after_the_flop(monkeypatch):
    styles = list(STYLES.values())
    hand = TableHand([200] * 3, 0, random.Random(4))
    hand.act("raise", 6)  # hero opens the button
    hand.act("call")
    hand.act("call")
    hand.act("check")
    hand.act("bet", 10)
    hand.act("raise", 30)  # hero raises the flop bet
    hand.act("fold")
    hand.act("call")
    hand.act("check")
    hand.act("bet", 40)  # hero bets the turn
    monkeypatch.setattr("holdem.engine.play.equity_against", lambda *a: (0.5, 2))
    values = iter([Push(-20.0, 4.0, "calling", 0.2, 0.3), Push(30.0, 22.0, "checking", 0.4, 0.7)])
    monkeypatch.setattr("holdem.engine.play.push_value", lambda *a: next(values))
    opened, raised, bet = review(styles, hand)
    assert opened.verdict in ("good", "leak")  # first in: graded against the button chart
    assert "First in from BTN, the chart" in opened.note
    assert opened.loss_bb == 0
    assert raised.verdict == "mistake"
    assert raised.loss_bb == 12
    assert "Raising 30bb" not in raised.note and "Raising 15bb into" in raised.note
    assert "everyone folds about 20%" in raised.note
    assert "-12.0bb compared with calling" in raised.note
    assert bet.verdict == "good"
    assert bet.loss_bb == 0
    assert "Betting 20bb" in bet.note and "+4.0bb compared with checking" in bet.note
    # Without an estimate the raise is described but not graded.
    monkeypatch.setattr("holdem.engine.play.push_value", lambda *a: None)
    assert review(styles, hand)[1].verdict == "info"


def test_equity_is_measured_against_the_players_in_the_pot():
    styles = list(STYLES.values())
    hand = TableHand([200] * 6, 0, random.Random(1))
    assert opponents_in_pot(hand, hand.log, "preflop") == [2]  # nobody in yet: the big blind
    hand.act("raise", 6)  # seat 3
    hand.act("fold")
    hand.act("call")  # seat 5
    assert opponents_in_pot(hand, hand.log, "preflop") == [3, 5]
    equity, opponents = equity_against(styles, hand, len(hand.log), "preflop")
    assert 0 < equity < 1
    assert opponents == 2
    hand.act("call")  # hero
    hand.act("fold")
    hand.act("call")  # the big blind
    assert opponents_in_pot(hand, hand.log, "flop") == [2, 3, 5]


def test_storage_summary_and_stats(engine):
    play = new_session(seed=9)
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
        assert summary["style"] == "6-max"
        assert len(summary["hole"]) == 2
        stats = play_stats(session)
    assert stats["hands"] == 3
    assert 0 < stats["vpip"] <= 1
    assert 0 < stats["pfr"] <= 1
    assert stats["bb_per_100"] == pytest.approx(stats["net_bb"] / 3 * 100, abs=0.1)
    assert sum(p["hands"] for p in stats["positions"]) == 3
    assert isinstance(stats["leaks"], list)


def test_bb_helper_and_constants():
    assert bb(5) == 2.5
    assert HERO == 0
    assert isinstance(new_session(seed=1), PlaySession)


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


def first_in(hole, kind, to=None, seats=6):
    """Hero under the gun (or on the button three-handed), first to act, holding ``hole``."""
    hand = TableHand([200] * seats, 3 if seats == 6 else 0, random.Random(1))
    assert hand.current == HERO
    hand.hole[HERO] = combo(hole)
    hand.act(kind, to)
    [decision] = [d for d in review(list(STYLES.values()), hand) if d.street == "preflop"]
    return hand.positions[HERO], decision


def test_first_in_decisions_follow_the_opening_chart():
    position, fold = first_in("Ah5d", "fold")
    assert position == "UTG"
    assert (fold.verdict, fold.loss_bb) == ("good", 0)
    assert fold.note == "First in from UTG, the chart folds A5o."
    _, opened = first_in("AhKd", "raise", 6)
    assert opened.verdict == "good"
    assert opened.note == "First in from UTG, the chart raises AKo."
    _, limp = first_in("AhKd", "call")
    assert limp.verdict == "leak"
    assert "raise or fold" in limp.note
    _, passed = first_in("AhAd", "fold")
    assert passed.verdict == "leak"
    assert passed.note.endswith("You chose to fold.")
    _, loose = first_in("7h2d", "raise", 6)
    assert loose.verdict == "leak"
    _, edge = first_in("AhTd", "fold")  # ATo is the weakest offsuit ace the chart opens
    assert edge.verdict == "good"
    assert "edge of the chart" in edge.note


def test_the_chart_stops_applying_once_somebody_enters():
    hand = TableHand([200] * 6, 2, random.Random(1))  # hero is in the hijack
    assert hand.positions[HERO] == "HJ"
    hand.act("raise", 6)  # under the gun opens
    hand.act("fold")
    [decision] = review(list(STYLES.values()), hand)
    assert "First in" not in decision.note
    assert decision.need is not None


def test_coach_points_at_the_chart_when_first_in():
    play = PlaySession(seed=1)
    for seed in range(200):
        play = PlaySession(seed=seed)
        if not play.hand.finished and play.hand.street_name == "preflop":
            entered = any(a.kind in ("call", "raise") for a in play.hand.log)
            expected = entered or play.hand.positions[HERO] == "BB"
            assert (play.coach()["chart"] is None) == expected
    assert play.coach()["chart"] in (None, "Raise", "Fold")
