import random

import pytest

from holdem.core.cards import parse_cards
from holdem.engine.headsup import IllegalActionError
from holdem.engine.table import TableHand, position_names


def table(stacks, button=0, seed=1):
    return TableHand(list(stacks), button, random.Random(seed))


def rig(hand, holes, board):
    """Fix the hole cards and the five board cards of a hand."""
    hand.hole = [tuple(parse_cards(h)) for h in holes]
    hand._deck = parse_cards(board)


def test_position_names():
    assert position_names(2) == ("BTN", "BB")
    assert position_names(3) == ("BTN", "SB", "BB")
    assert position_names(4) == ("BTN", "SB", "BB", "CO")
    assert position_names(6) == ("BTN", "SB", "BB", "UTG", "HJ", "CO")


@pytest.mark.parametrize("stacks", [[200], [200] * 7, [200, 2, 200]])
def test_rejects_bad_tables(stacks):
    with pytest.raises(ValueError):
        table(stacks)


def test_blinds_and_first_to_act():
    hand = table([200] * 6, button=4)
    assert hand.positions == ["BB", "UTG", "HJ", "CO", "BTN", "SB"]
    assert hand.bets == [2, 0, 0, 0, 0, 1]
    assert hand.current == 1
    assert hand.total_pot == 3
    assert hand.made_hand(0) is None
    heads_up = table([200, 200], button=1)
    assert heads_up.bets == [2, 1]  # the button posts the small blind and acts first
    assert heads_up.current == 1


def test_everyone_folds_to_the_big_blind():
    hand = table([200] * 6)
    for _ in range(5):
        hand.act("fold")
    assert hand.finished and not hand.showdown
    assert hand.net() == [0, -1, 1, 0, 0, 0]
    view = hand.public(viewer=0)
    assert view["winners"] == [2]
    assert view["current"] is None
    assert view["hole"][2] is None  # no showdown, no cards shown
    with pytest.raises(IllegalActionError):
        hand.act("check")


def test_illegal_actions():
    hand = table([200] * 3)
    with pytest.raises(IllegalActionError):
        hand.act("check")  # facing the big blind
    with pytest.raises(IllegalActionError):
        hand.act("raise", 3)  # below the minimum
    with pytest.raises(IllegalActionError):
        hand.act("raise")
    with pytest.raises(IllegalActionError):
        hand.act("dance")
    hand.act("call")
    hand.act("call")
    with pytest.raises(IllegalActionError):
        hand.act("fold")  # the big blind can check
    with pytest.raises(IllegalActionError):
        hand.act("call")
    hand.act("check")
    assert hand.street_name == "flop"
    assert hand.current == 1  # the small blind acts first after the flop
    assert len(hand.board) == 3


def test_side_pots_go_to_the_best_eligible_hands():
    hand = table([20, 60, 200])  # button 0, small blind 1, big blind 2
    rig(hand, ["AsAh", "KsKh", "QsQh"], "2c7d9hJc3s")
    hand.act("raise", 20)  # all in
    hand.act("raise", 60)  # all in
    legal = hand.legal()
    assert not legal.can_raise  # nobody left to raise against
    with pytest.raises(IllegalActionError):
        hand.act("raise", 200)
    hand.act("call")
    assert hand.finished and hand.showdown
    assert hand.winnings == [60, 80, 0]  # main pot to the aces, side pot to the kings
    assert hand.net() == [40, 20, -60]
    view = hand.public(viewer=0)
    assert view["winners"] == [0, 1]
    assert view["made"] == ["One Pair", "One Pair", "One Pair"]
    assert view["hole"][2] == ["Qs", "Qh"]
    assert view["last"]["kind"] == "call"


def test_uncalled_bets_come_back_and_short_calls_are_capped():
    hand = table([200, 30, 200])
    rig(hand, ["AsAh", "KsKh", "7c2d"], "2c7d9hJc3s")
    hand.act("raise", 200)
    assert hand.legal().to_call == 29  # all the small blind has left
    hand.act("call")
    hand.act("fold")
    assert hand.net() == [32, -30, -2]
    assert sum(hand.committed) == 62


def test_split_pot_and_the_odd_chip():
    hand = table([200] * 3)
    rig(hand, ["AsKh", "7c2d", "AdKc"], "2s8dTh4cQs")
    hand.act("call")
    hand.act("fold")
    hand.act("check")
    for _ in range(3):  # flop, turn, river: the big blind acts first
        assert hand.current == 2
        hand.act("check")
        hand.act("check")
    assert hand.showdown
    assert hand.winnings == [2, 0, 3]  # the odd chip goes to the first winner left of the button
    view = hand.public(viewer=1)
    assert view["hole"][1] == ["7c", "2d"]
    assert view["hole"][0] is not None
    hidden = hand.public(viewer=0)
    assert hidden["hole"][1] is None and hidden["made"][1] is None  # folded hands stay hidden
    assert hand.public(viewer=0, reveal=True)["hole"][1] is not None


def test_bets_raises_and_reopened_action():
    hand = table([200] * 4)
    for kind in ("call", "call", "call", "check"):
        hand.act(kind)
    assert hand.street_name == "flop"
    hand.act("bet", 4)
    hand.act("call")
    hand.act("raise", 12)
    assert hand.log[-1].kind == "raise"
    assert hand.legal().min_raise_to == 20
    hand.act("fold")
    hand.act("call")  # the bettor must act again
    hand.act("fold")
    assert hand.street_name == "turn"
    assert hand.pot == 8 + 4 + 12 + 12


@pytest.mark.parametrize("seats", [2, 3, 4, 5, 6])
def test_chips_are_conserved_under_random_play(seats):
    rng = random.Random(seats)
    for seed in range(120):
        stacks = [rng.randint(3, 300) for _ in range(seats)]
        hand = table(stacks, button=seed % seats, seed=seed)
        for _ in range(200):
            if hand.finished:
                break
            legal = hand.legal()
            roll = rng.random()
            if legal.can_raise and roll < 0.3:
                kind = "bet" if max(hand.bets) == 0 else "raise"
                hand.act(kind, rng.randint(legal.min_raise_to, legal.max_raise_to))
            elif legal.can_check:
                hand.act("check")
            else:
                hand.act("call" if roll < 0.8 else "fold")
        assert hand.finished
        assert sum(hand.net()) == 0
        assert sum(hand.winnings) == hand.pot
        assert all(b >= 0 for b in hand.behind)


def test_a_short_all_in_does_not_reopen_the_betting():
    hand = table([200, 200, 21])
    hand.act("raise", 6)
    hand.act("call")
    hand.act("call")
    hand.act("bet", 10)  # seat 1
    assert hand.legal().min_raise_to == 15  # seat 2 has only 15 left
    hand.act("raise", 15)  # all in for 5 more: less than a full raise
    legal = hand.legal()  # seat 0 has not acted on this street, so it may still raise
    assert legal.can_raise
    assert legal.min_raise_to == 25
    hand.act("call")
    legal = hand.legal()  # seat 1 already bet: it may only call or fold
    assert hand.current == 1
    assert not legal.can_raise
    assert legal.to_call == 5
    with pytest.raises(IllegalActionError):
        hand.act("raise", 40)
    hand.act("call")
    assert hand.street_name == "turn"
    assert len(hand.raisable) == len(hand.log)
    assert hand.raisable[:2] == [False, False]  # the blinds


def test_a_full_raise_over_a_short_all_in_reopens_the_betting():
    hand = table([200, 200, 21])
    hand.act("raise", 6)
    hand.act("call")
    hand.act("call")
    hand.act("bet", 10)
    hand.act("raise", 15)
    hand.act("raise", 40)  # seat 0 makes a full raise
    assert hand.current == 1
    assert hand.legal().can_raise


def test_short_all_ins_that_add_up_to_a_full_raise_reopen_the_betting():
    hand = table([30, 40, 200, 200])  # blinds on seats 1 and 2, seat 3 acts first
    hand.act("raise", 20)  # seat 3 opens: a raise of 18
    hand.act("raise", 30)  # seat 0 is all in for 10 more: short
    hand.act("raise", 40)  # seat 1 is all in for 10 more: short again
    hand.act("call")  # the big blind
    assert hand.current == 3
    legal = hand.legal()  # 20 more than seat 3 last faced: a full raise in total
    assert legal.can_raise
    assert legal.min_raise_to == 58

    single = table([30, 40, 200, 200])
    single.act("raise", 20)
    single.act("raise", 30)  # one short all-in only
    single.act("fold")
    single.act("call")  # the big blind
    assert single.current == 3
    assert not single.legal().can_raise


def test_a_short_all_in_bet_still_opens_the_betting():
    hand = table([200, 200, 7])
    hand.act("raise", 6)
    hand.act("call")
    hand.act("call")  # seat 2 has one chip left
    hand.act("check")  # seat 1
    hand.act("bet", 1)  # seat 2 is all in for less than a big blind
    hand.act("call")  # seat 0
    legal = hand.legal()  # seat 1 only checked, so the bet is new to it
    assert hand.current == 1
    assert legal.can_raise
    assert legal.min_raise_to == 3
