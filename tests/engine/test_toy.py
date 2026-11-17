import pytest

from holdem.engine.bots import STYLES
from holdem.engine.toy import (
    GAMES,
    OPPONENTS,
    Strategy,
    best_response,
    bettor_values,
    caller_values,
    nash,
    new_toy_session,
)

AKQ = GAMES["akq"]
TEN = GAMES["ten"]
Q, K, A = 0, 1, 2


def test_akq_values_are_exact():
    always_call = (1.0, 1.0, 1.0)
    assert bettor_values(AKQ, A, always_call) == {"bet": 2.0, "check": 1.0}
    assert bettor_values(AKQ, Q, always_call) == {"bet": -2.0, "check": -1.0}
    assert bettor_values(AKQ, Q, (0.0, 0.0, 0.0)) == {"bet": 1.0, "check": -1.0}
    # A king facing a bettor who bets aces and queens equally wins half the time.
    assert caller_values(AKQ, K, (1.0, 0.0, 1.0)) == {"call": 0.0, "fold": -1.0}
    assert caller_values(AKQ, K, (0.0, 0.0, 1.0)) == {"call": -2.0, "fold": -1.0}
    # A spot the opponent never creates still has a value.
    assert caller_values(AKQ, A, (0.0, 0.0, 1.0)) == {"call": 2.0, "fold": -1.0}


def test_nash_for_akq_bluffs_and_calls_a_third():
    optimal = nash(AKQ)
    assert optimal.bet[A] == pytest.approx(1, abs=0.01)
    assert optimal.bet[K] == pytest.approx(0, abs=0.01)
    assert optimal.bet[Q] == pytest.approx(1 / 3, abs=0.02)
    assert optimal.call[A] == pytest.approx(1, abs=0.01)
    assert optimal.call[K] == pytest.approx(1 / 3, abs=0.02)
    assert optimal.call[Q] == pytest.approx(0, abs=0.01)
    assert nash(AKQ) is optimal  # cached


@pytest.mark.parametrize("game", [AKQ, TEN])
def test_nash_cannot_be_exploited(game):
    optimal = nash(game)
    reply = best_response(game, optimal)
    n = game.size

    def bettor_total(bet):
        return sum(
            bet[c] * bettor_values(game, c, optimal.call)["bet"]
            + (1 - bet[c]) * bettor_values(game, c, optimal.call)["check"]
            for c in range(n)
        )

    assert bettor_total(reply.bet) - bettor_total(optimal.bet) < 0.02 * n


def test_ten_card_game_bets_the_top_and_bluffs_the_bottom():
    optimal = nash(TEN)
    assert optimal.bet[9] > 0.95
    assert optimal.bet[0] > optimal.bet[4]
    assert optimal.call[9] > 0.95
    assert optimal.call[0] < 0.05
    value = sum(optimal.bet[7:])
    bluffs = sum(optimal.bet[:5])
    assert bluffs == pytest.approx(value / 3, abs=0.15)  # one bluff per three value bets


def test_opponents_and_how_to_beat_them():
    assert {o.key: o.character for o in OPPONENTS.values()} == {
        key: STYLES[key].character for key in OPPONENTS
    }
    assert OPPONENTS["tag"].strategy(AKQ) == nash(AKQ)
    station = OPPONENTS["station"].strategy(AKQ)
    assert station == Strategy((0.0, 0.0, 1.0), (0.0, 1.0, 1.0))
    assert best_response(AKQ, station).bet[Q] == 0  # never bluff a calling station
    nit = OPPONENTS["nit"].strategy(TEN)
    assert sum(nit.bet) == 3 and sum(nit.call) == 2
    assert best_response(TEN, nit).bet[0] == 1  # always bluff a nit
    maniac = OPPONENTS["maniac"].strategy(AKQ)
    assert maniac.bet == (1.0, 1.0, 1.0)
    assert best_response(AKQ, maniac).call[K] == 1  # call a maniac down
    # Against optimal play the king is indifferent, so the best response keeps the optimal mix.
    assert best_response(AKQ, nash(AKQ)).call[K] == nash(AKQ).call[K]
    assert OPPONENTS["nit"].public()["character"] == "Rocky"
    assert AKQ.public()["cards"] == ["Q", "K", "A"]


def test_session_plays_hands_and_keeps_score():
    toy = new_toy_session("akq", "maniac", seed=3)
    assert new_toy_session("akq", "maniac", seed=3).state()["hand"] == toy.state()["hand"]
    assert new_toy_session("ten", "tag").seed >= 0
    with pytest.raises(KeyError):
        new_toy_session("akq", "nobody")
    seen = set()
    chips = 0
    for _ in range(60):
        state = toy.state()
        hand = state["hand"]
        assert hand["number"] == state["hands_played"] + 1
        role = hand["role"]
        assert hand["actions"] == (["bet", "check"] if role == "bettor" else ["call", "fold"])
        with pytest.raises(ValueError, match="you can"):
            toy.act("call" if role == "bettor" else "bet")
        # Bet aces and queens, check kings; call with kings and aces.
        action = (
            ("bet" if hand["card"] != "K" else "check")
            if role == "bettor"
            else ("call" if hand["card"] != "Q" else "fold")
        )
        toy.act(action)
        last = toy.last
        assert last is not None
        assert last["action"] == action and last["role"] == role
        assert last["active"] == ("bet" if role == "bettor" else "call")
        assert set(last["values"]) == set(hand["actions"])
        assert last["best"] in hand["actions"]
        assert last["lesson"].startswith(("Right", "Not this time", "Against"))
        seen.add((role, last["their_action"], action))
        chips += last["chips"] + sum(b["chips"] for b in toy.before)
        for before in toy.before:
            assert before["their_action"] == "check" and before["role"] == "caller"
    assert toy.chips == chips
    assert ("bettor", "call", "bet") in seen
    assert ("bettor", "fold", "bet") in seen
    assert ("bettor", "check", "check") in seen
    assert ("caller", "bet", "call") in seen
    assert ("caller", "bet", "fold") in seen
    summary = toy.summary()
    assert summary["chips"] == toy.chips
    assert summary["best"] >= summary["expected"]
    ace = summary["cards"][2]
    assert ace["card"] == "A" and ace["bet"]["yours"] == 1 and ace["bet"]["best"] == 1
    king = summary["cards"][1]
    assert king["bet"]["yours"] == 0 and king["call"]["yours"] == 1
    assert king["call"]["optimal"] == pytest.approx(1 / 3, abs=0.02)


def test_lessons_cover_right_wrong_and_indifferent():
    def play(opponent, card, role, action, seed=0):
        for s in range(seed, seed + 400):
            toy = new_toy_session("akq", opponent, seed=s)
            if role == "caller":
                toy.act("check")  # the first hand is always yours to bet
            hand = toy.state()["hand"]
            if hand["card"] == card and hand["role"] == role:
                toy.act(action)
                assert toy.last is not None
                return toy.last
        raise AssertionError("spot not found")

    assert play("nit", "Q", "bettor", "bet")["lesson"].startswith("Right: against Rocky, to bet")
    wrong = play("station", "Q", "bettor", "bet")
    assert wrong["lesson"].startswith("Not this time: against Moby, to check the Q")
    assert wrong["best"] == "check" and wrong["chips"] == -2
    assert "earn the same" in play("tag", "Q", "bettor", "check")["lesson"]
    assert play("maniac", "Q", "caller", "call")["lesson"].startswith("Not this time")


def test_opponent_can_check_behind_before_your_turn():
    for seed in range(50):
        toy = new_toy_session("akq", "station", seed=seed)
        toy.act("check")  # hand 1: you are the bettor
        if toy.before:
            assert toy.state()["hand"]["before"][0]["their_action"] == "check"
            assert toy.summary()["cards"][0]["call"]["yours"] is None
            return
    raise AssertionError("the station never checked behind")


def test_optimal_calling_is_a_threshold():
    from holdem.engine.toy import GAMES, nash  # noqa: PLC0415

    call = nash(GAMES["ten"]).call
    assert list(call) == sorted(call)  # higher cards never call less often
    assert sum(0.02 < c < 0.98 for c in call) <= 1  # at most one card mixes
