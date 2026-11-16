import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from holdem.engine.headsup import BIG_BLIND, HeadsUpHand, IllegalActionError


def new_hand(seed=0, stacks=(200, 200), button=0):
    return HeadsUpHand(list(stacks), button, random.Random(seed))


def test_blinds_and_first_action():
    hand = new_hand(button=1)
    assert hand.bets == [2, 1]  # player 1 is the button and posts the small blind
    assert hand.current == 1
    assert hand.total_pot == 3
    legal = hand.legal()
    assert legal.to_call == 1
    assert legal.min_raise_to == 4
    assert legal.max_raise_to == 200


def test_limp_and_big_blind_option_then_postflop_order():
    hand = new_hand(button=0)
    hand.act("call")
    assert hand.current == 1
    assert hand.street_name == "preflop"  # the big blind's option
    hand.act("check")
    assert hand.street_name == "flop"
    assert len(hand.board) == 3
    assert hand.current == 1  # big blind acts first after the flop
    hand.act("check")
    hand.act("check")
    assert hand.street_name == "turn"
    assert len(hand.board) == 4


def test_fold_awards_the_pot():
    hand = new_hand(button=0)
    hand.act("raise", 6)
    hand.act("fold")
    assert hand.finished
    assert hand.net() == [2, -2]
    assert not hand.showdown


def test_min_raise_tracks_the_last_raise():
    hand = new_hand(button=0)
    hand.act("raise", 6)  # a raise of 4
    assert hand.legal().min_raise_to == 10
    hand.act("raise", 16)  # a raise of 10
    assert hand.legal().min_raise_to == 26


def test_short_all_in_call_returns_the_uncalled_part():
    hand = new_hand(stacks=(200, 50), button=0)
    hand.act("raise", 120)
    assert hand.legal().to_call == 48  # player 1 has 48 behind
    hand.act("call")
    assert hand.finished
    assert hand.showdown
    assert len(hand.board) == 5
    assert sum(hand.net()) == 0
    assert abs(hand.net()[0]) in (0, 50)


def test_all_in_must_be_answered_before_the_street_ends():
    hand = new_hand(button=0)
    hand.act("call")
    hand.act("check")
    hand.act("bet", 198)  # the big blind shoves on the flop
    assert not hand.finished
    assert hand.current == 0
    assert not hand.legal().can_raise  # no re-raising an all-in
    hand.act("call")
    assert hand.finished
    assert hand.showdown


def test_illegal_actions():
    hand = new_hand(button=0)
    with pytest.raises(IllegalActionError, match="cannot check"):
        hand.act("check")
    with pytest.raises(IllegalActionError, match="raise to between"):
        hand.act("raise", 3)
    with pytest.raises(IllegalActionError, match="not allowed"):
        hand.act("raise")
    with pytest.raises(IllegalActionError, match="unknown"):
        hand.act("dance")
    hand.act("call")
    with pytest.raises(IllegalActionError, match="check instead"):
        hand.act("fold")
    hand.act("check")
    with pytest.raises(IllegalActionError, match="nothing to call"):
        hand.act("call")
    hand.act("bet", 200 - BIG_BLIND)
    hand.act("fold")
    with pytest.raises(IllegalActionError, match="over"):
        hand.act("check")


def test_stacks_must_cover_the_blinds():
    with pytest.raises(ValueError):
        new_hand(stacks=(200, 2))


def test_split_pot_odd_chip_goes_to_the_big_blind(monkeypatch):
    hand = new_hand(button=0)
    monkeypatch.setattr("holdem.engine.headsup.compare", lambda a, b, board: 0)
    hand.pot = 1  # force an odd pot at showdown
    hand.act("raise", 200)
    hand.act("call")
    assert hand.showdown
    assert hand.winnings[1] == hand.winnings[0] + 1


def test_showdown_winner_takes_the_pot(monkeypatch):
    monkeypatch.setattr("holdem.engine.headsup.compare", lambda a, b, board: 1)
    hand = new_hand(button=0)
    hand.act("raise", 200)
    hand.act("call")
    assert hand.net() == [200, -200]
    monkeypatch.setattr("holdem.engine.headsup.compare", lambda a, b, board: -1)
    hand = new_hand(button=0)
    hand.act("raise", 200)
    hand.act("call")
    assert hand.net() == [-200, 200]


def test_public_view_hides_the_opponent_until_showdown():
    hand = new_hand(button=0)
    view = hand.public(viewer=0)
    assert view["hole"][0] is not None
    assert view["hole"][1] is None
    assert view["net"] is None
    assert hand.public(viewer=0, reveal=True)["hole"][1] is not None
    hand.act("raise", 200)
    hand.act("call")
    view = hand.public(viewer=0)
    assert view["hole"][1] is not None
    assert view["finished"]
    assert view["current"] is None
    assert view["log"][0]["kind"] == "post"


def random_action(hand, rng):
    legal = hand.legal()
    options = ["check"] if legal.can_check else ["fold", "call"]
    if legal.can_raise:
        options.append("raise")
    kind = rng.choice(options)
    if kind == "raise":
        to = rng.randint(legal.min_raise_to, legal.max_raise_to)
        hand.act("bet" if legal.can_check else "raise", to)
    else:
        hand.act(kind)


@settings(max_examples=300, deadline=None)
@given(
    seed=st.integers(0, 10_000),
    stacks=st.tuples(st.integers(3, 400), st.integers(3, 400)),
    button=st.integers(0, 1),
)
def test_random_play_conserves_chips_and_terminates(seed, stacks, button):
    hand = HeadsUpHand(list(stacks), button, random.Random(seed))
    rng = random.Random(seed + 1)
    for _ in range(200):
        if hand.finished:
            break
        assert min(hand.behind) >= 0
        assert sum(hand.behind) + hand.total_pot == sum(stacks)
        random_action(hand, rng)
    assert hand.finished
    assert sum(hand.net()) == 0
    assert all(n >= -s for n, s in zip(hand.net(), stacks, strict=True))
    if hand.showdown:
        assert len(hand.board) == 5
