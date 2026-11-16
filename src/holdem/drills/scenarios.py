"""Range, fold-equity, short-stack and tournament drills, plus a multi-street hand story.

Every answer is computed from the stated assumptions (a named range, a stated fold rule, a stated
calling range). The assumptions are simplifications for teaching and are always shown.
"""

from __future__ import annotations

import json
import math
import random
from functools import cache
from importlib import resources
from typing import Any

from holdem.core import odds
from holdem.core.cards import Card, deal, pretty_cards, rank_of, remaining_deck, suit_of
from holdem.core.equity import calculate_equity
from holdem.core.evaluator import Category, category, compare
from holdem.core.icm import icm_equities, risk_premium_call
from holdem.core.ranges import (
    ALL_CLASSES,
    Combo,
    HandClass,
    Range,
    class_combo_count,
    class_of_combo,
    combos_of_class,
    grid_class,
)
from holdem.drills.base import AnswerKind, Drill, Question, card_list, pct
from holdem.preflop import SPOTS_BY_ID

# Villain ranges taken from the baseline charts: (spot, action, label).
VILLAIN_RANGES: dict[str, tuple[str, str, str]] = {
    "utg": ("utg-open", "Raise", "UTG opening range"),
    "co": ("co-open", "Raise", "CO opening range"),
    "btn": ("btn-open", "Raise", "BTN opening range"),
    "bb": ("bb-vs-btn", "Call", "BB calling range vs a BTN open"),
}


def chart_range(spot_id: str, action: str) -> Range:
    spot = SPOTS_BY_ID[spot_id]
    return Range.of(c for c, a in spot.chart.items() if a == action)


def range_grid(hand_range: Range) -> list[list[str]]:
    """A 13x13 grid marking the classes in a range (for the chart reveal)."""
    return [
        ["In range" if grid_class(r, c) in hand_range else "Fold" for c in range(13)]
        for r in range(13)
    ]


def facts(**items: str) -> list[dict[str, str]]:
    return [{"label": k.replace("_", " ").capitalize(), "value": v} for k, v in items.items()]


def unpaired_flop(rng: random.Random, dead: list[Card]) -> list[Card]:
    while True:
        flop = deal(rng, 3, dead)
        if len({rank_of(c) for c in flop}) == 3:
            return flop


def pair_class(hole: Combo, board: list[Card]) -> str:
    """Made-hand class on an unpaired board: "two pair+", "top pair+", "weaker pair", "no pair"."""
    made = category([*hole, *board])
    if made >= Category.TWO_PAIR:
        return "two pair+"
    if made == Category.ONE_PAIR:
        board_ranks = {rank_of(c) for c in board}
        hole_ranks = [rank_of(c) for c in hole]
        pair_rank = (
            hole_ranks[0]
            if hole_ranks[0] == hole_ranks[1]
            else next(r for r in hole_ranks if r in board_ranks)
        )
        return "top pair+" if pair_rank >= max(board_ranks) else "weaker pair"
    return "no pair"


class RangeHitsDrill(Drill):
    key = "range-hits"
    title = "How often does the range hit?"
    concept = "range-equity"
    tier = 3
    description = "Estimate how often a preflop range flops a pair, or top pair or better."

    def make_question(self, rng: random.Random) -> Question:
        spot_id, action, label = VILLAIN_RANGES[rng.choice(list(VILLAIN_RANGES))]
        hand_range = chart_range(spot_id, action)
        flop = unpaired_flop(rng, [])
        combos = [c for c, _ in hand_range.combos(flop)]
        classes = [pair_class(c, flop) for c in combos]
        top = sum(c in ("two pair+", "top pair+") for c in classes)
        pair = top + classes.count("weaker pair")
        which = rng.choice(("top", "pair"))
        hits, wording = (
            (top, "top pair or better") if which == "top" else (pair, "a pair or better")
        )
        share = hits / len(combos)
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"How often does the {label} have {wording} on this flop?",
            kind=AnswerKind.NUMBER,
            answer=pct(share),
            unit="%",
            tolerance=6.0,
            payload={"board": card_list(flop), "facts": facts(range=label)},
            explanation=(
                f"{hits} of the {len(combos)} combos still possible ({pct(share)}%).",
                f"Two pair or better: {classes.count('two pair+')} · top pair or overpair: "
                f"{classes.count('top pair+')} · weaker pair: {classes.count('weaker pair')} · "
                f"no pair: {classes.count('no pair')}.",
                "Ranges miss most flops: even wide ranges make a pair only about a third of "
                "the time. That is why small c-bets work so often.",
            ),
            reveal={"grid": range_grid(hand_range), "choices": ["In range"], "label": label},
        )


class RangeEquityDrill(Drill):
    key = "range-equity"
    title = "Equity vs a range"
    concept = "range-equity"
    tier = 3
    description = "All in on the flop against a whole range, not one hand. What is your equity?"

    def make_question(self, rng: random.Random) -> Question:
        spot_id, action, label = VILLAIN_RANGES[rng.choice(list(VILLAIN_RANGES))]
        hand_range = chart_range(spot_id, action)
        hero_cards = deal(rng, 2)
        hero = (hero_cards[0], hero_cards[1])
        flop = deal(rng, 3, hero_cards)
        result = calculate_equity([hero, hand_range], flop)
        combos = [c for c, _ in hand_range.combos([*hero_cards, *flop])]
        ahead = sum(compare(hero, c, flop) > 0 for c in combos)
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"All in on the flop against the {label}. What is your equity?",
            kind=AnswerKind.NUMBER,
            answer=pct(result[0].equity),
            unit="%",
            tolerance=7.0,
            payload={
                "hole": card_list(hero),
                "board": card_list(flop),
                "facts": facts(villain=label),
            },
            explanation=(
                f"Exact equity against all {len(combos)} live combos: {pct(result[0].equity)}%.",
                f"Right now you are ahead of {ahead} combos ({pct(ahead / len(combos))}%).",
                "Against a range, ask what share of it you beat now and how often you improve "
                "against the rest.",
            ),
            reveal={"grid": range_grid(hand_range), "choices": ["In range"], "label": label},
        )


DRAWS = {
    4: "a gutshot",
    8: "an open-ended straight draw",
    9: "a flush draw",
    12: "a flush draw plus a gutshot",
    15: "a flush draw plus an open-ender",
}


def _pot(rng: random.Random) -> float:
    return float(rng.randrange(4, 21) * 5)


class ImpliedOddsDrill(Drill):
    key = "implied-odds"
    title = "Implied odds"
    concept = "implied-odds"
    tier = 3
    description = "The price is wrong for your draw. How much more must you win when you hit?"

    def make_question(self, rng: random.Random) -> Question:
        while True:
            outs = rng.choice(list(DRAWS))
            pot = _pot(rng)
            bet = pot * rng.choice((0.5, 0.75, 1.0))
            hit = outs / 46
            need = odds.required_equity(pot, bet)
            if hit < need - 0.02:
                break
        extra = bet / hit - pot - 2 * bet
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"Turn. Pot {pot:g}, villain bets {bet:g}. "
            f"You have {DRAWS[outs]} ({outs} outs). How much more must you win on the river "
            "when you hit, to break even on a call?",
            kind=AnswerKind.NUMBER,
            answer=round(extra, 1),
            unit="chips",
            tolerance=round(max(2.0, extra * 0.12), 1),
            payload={"pot": pot, "bet": bet, "facts": facts(outs=str(outs), street="Turn")},
            explanation=(
                f"You hit {outs}/46 = {pct(hit)}% of the time but need {pct(need)}%.",
                f"Break even when {pct(hit)}% x (pot + bet + extra) = miss chance x your call: "
                f"extra = bet / hit chance - pot - 2 x bet = {extra:.1f}.",
                "If villain will rarely pay that much when the draw comes in, fold.",
            ),
        )


class BluffEvDrill(Drill):
    key = "bluff-ev"
    title = "Bluff EV"
    concept = "fold-equity"
    tier = 4
    description = "What is a bluff or semi-bluff worth, given how often villain folds?"

    def make_question(self, rng: random.Random) -> Question:
        pot = _pot(rng)
        bet = pot * rng.choice((0.5, 0.75, 1.0))
        fold = rng.randrange(6, 15) * 5 / 100
        semi = rng.random() < 0.5
        outs = rng.choice((8, 9, 12)) if semi else 0
        equity = outs / 46
        ev = odds.bet_ev(pot, bet, fold, equity)
        street = "Turn" if semi else "River"
        hand = f"You have {DRAWS[outs]} ({outs} outs). " if semi else "You have nothing. "
        when_called = (
            f"When called you still win {outs}/46 of the time: "
            f"{pct(equity)}% x {pot + 2 * bet:g} - {bet:g}."
            if semi
            else f"When called you lose your {bet:g}."
        )
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"{street}. Pot {pot:g}. {hand}You bet {bet:g} and villain folds "
            f"{fold:.0%} of the time. What is the bet worth (EV in chips)?",
            kind=AnswerKind.NUMBER,
            answer=round(ev, 1),
            unit="chips",
            tolerance=round(max(1.0, pot * 0.04), 1),
            payload={"pot": pot, "bet": bet, "facts": facts(street=street, folds=f"{fold:.0%}")},
            explanation=(
                f"EV = folds x pot + calls x (result when called) = {fold:.2f} x {pot:g} + "
                f"{1 - fold:.2f} x (result when called) = {ev:+.1f}.",
                when_called,
                f"A pure bluff of this size breaks even at {pct(odds.alpha(pot, bet))}% folds.",
            ),
        )


class BluffCatchDrill(Drill):
    key = "bluff-catch"
    title = "Bluff-catching"
    concept = "bluff-catching"
    tier = 5
    description = "River bet into your bluff-catcher: do they have enough bluffs to call?"

    def make_question(self, rng: random.Random) -> Question:
        while True:
            pot = _pot(rng)
            size = rng.choice((0.5, 0.75, 1.0, 1.5))
            bet = pot * size
            value = rng.randrange(6, 31)
            bluffs = rng.randrange(1, 19)
            share = bluffs / (value + bluffs)
            need = odds.required_equity(pot, bet)
            if abs(share - need) >= 0.03:
                break
        answer = "Call" if share > need else "Fold"
        b, v = odds.bluff_to_value(pot, bet)
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"River. Pot {pot:g}, villain bets {bet:g}. Their betting range is {value} "
            f"value combos and {bluffs} bluffs; you beat every bluff and lose to every value hand. "
            "Call or fold?",
            kind=AnswerKind.CHOICE,
            answer=answer,
            choices=("Call", "Fold"),
            payload={"pot": pot, "bet": bet, "facts": facts(value=str(value), bluffs=str(bluffs))},
            explanation=(
                f"You win when they bluff: {bluffs}/{value + bluffs} = {pct(share)}%.",
                f"Calling {bet:g} to win {pot + bet:g} needs {pct(need)}%, so {answer.lower()}.",
                f"A balanced range at this size has {b} bluff for every {v} value hands "
                f"({pct(need)}% bluffs); more bluffs than that and calling prints money.",
            ),
        )


@cache
def hand_strength() -> dict[HandClass, float]:
    """All-in equity of each starting hand against a random hand (precomputed)."""
    text = resources.files("holdem.data").joinpath("hand_strength.json").read_text()
    return json.loads(text)


def top_range(share: float) -> Range:
    """The strongest hands (by equity against a random hand) covering ``share`` of combos."""
    picked: list[HandClass] = []
    combos = 0
    for hand_class in sorted(ALL_CLASSES, key=lambda c: -hand_strength()[c]):
        if combos >= share * 1326:
            break
        picked.append(hand_class)
        combos += class_combo_count(hand_class)
    return Range.of(picked)


class PushFoldDrill(Drill):
    key = "push-fold"
    title = "Shove or fold"
    concept = "icm"
    tier = 6
    description = "Short-stacked in the small blind against a stated calling range."

    def make_question(self, rng: random.Random) -> Question:
        while True:
            stack = rng.randrange(3, 16)
            call_share = rng.choice((0.15, 0.2, 0.25, 0.3, 0.4, 0.5))
            calling = top_range(call_share)
            hero_cards = deal(rng, 2)
            hero = (hero_cards[0], hero_cards[1])
            live = calling.combos(hero_cards)
            p_call = len(live) / math.comb(50, 2)
            equity = calculate_equity(
                [hero, calling], samples=3000, seed=rng.randrange(1 << 30), exact_limit=0
            )[0].equity
            shove = (1 - p_call) * 1 + p_call * (equity * 2 * stack - stack)
            if abs(shove - -0.5) >= 0.1:
                break
        answer = "Shove" if shove > -0.5 else "Fold"
        hand = class_of_combo(*hero)
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"Heads-up, blinds 0.5/1, no antes. You have {stack}bb in the small blind. "
            f"The big blind calls a shove with the top {call_share:.0%} of hands. Shove or fold?",
            kind=AnswerKind.CHOICE,
            answer=answer,
            choices=("Shove", "Fold"),
            payload={
                "hole": card_list(hero),
                "facts": facts(stack=f"{stack}bb", calls=f"top {call_share:.0%}"),
            },
            explanation=(
                "Folding loses your 0.5bb small blind: EV -0.5bb.",
                f"Shoving: BB folds {pct(1 - p_call)}% (you win 1bb) and calls {pct(p_call)}% "
                f"(your {hand} has {pct(equity)}% equity for a {2 * stack}bb pot).",
                f"EV(shove) = {1 - p_call:.2f} x 1 + {p_call:.2f} x ({equity:.2f} x {2 * stack} - "
                f"{stack}) = {shove:+.2f}bb, so {answer.lower()}.",
            ),
            reveal={
                "grid": range_grid(calling),
                "hand": hand,
                "choices": ["In range"],
                "label": f"Big blind's calling range (top {call_share:.0%})",
            },
        )


PAYOUT_TABLES = ((50, 30, 20), (65, 35), (60, 40), (45, 30, 25))


class IcmDrill(Drill):
    key = "icm-equity"
    title = "ICM: what are your chips worth?"
    concept = "icm"
    tier = 6
    description = "Turn chip stacks into prize money, and see why calling gets tighter."

    def make_question(self, rng: random.Random) -> Question:
        players = 3
        stacks = [rng.randrange(2, 13) * 500 for _ in range(players)]
        payouts = rng.choice(PAYOUT_TABLES)
        names = ["You", "Player B", "Player C"]
        stack_text = " · ".join(f"{n} {s:,}" for n, s in zip(names, stacks, strict=True))
        payout_text = "/".join(str(p) for p in payouts)
        shared: dict[str, Any] = {
            "facts": facts(stacks=stack_text, payouts=f"{payout_text} (of a 100 prize pool)")
        }
        equities = icm_equities(stacks, payouts)
        chip_share = stacks[0] / sum(stacks)
        if rng.random() < 0.5:
            return Question(
                drill=self.key,
                concept=self.concept,
                prompt="Three left in a tournament. What is your ICM equity, in prize-pool units?",
                kind=AnswerKind.NUMBER,
                answer=round(equities[0], 1),
                tolerance=2.0,
                payload=shared,
                explanation=(
                    f"Your chips are {pct(chip_share)}% of the total, but your ICM equity is "
                    f"{equities[0]:.1f} of 100.",
                    "Each player wins first place with probability stack / total; later places "
                    "follow the same rule among the rest (Malmuth-Harville).",
                    "Short stacks are worth more than their chip share and big stacks less: "
                    "chips you lose cost more than chips you win.",
                ),
            )
        villain = max((1, 2), key=lambda i: stacks[i])
        chip_need, icm_need = risk_premium_call(stacks, payouts, 0, villain)
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"{names[villain]} shoves and you are the only one left to act. Chip EV says "
            f"you need {pct(chip_need)}% equity to call. How much do you need under ICM?",
            kind=AnswerKind.NUMBER,
            answer=pct(icm_need),
            unit="%",
            tolerance=3.0,
            payload=shared,
            explanation=(
                f"Fold and keep {equities[0]:.1f} of the prize pool; call and win or lose your "
                "stack. The break-even equity makes both choices worth the same.",
                f"ICM needs {pct(icm_need)}% versus {pct(chip_need)}% by chips: a risk premium of "
                f"{pct(icm_need - chip_need)} points.",
                "Blinds are ignored to keep the arithmetic clear.",
            ),
        )


class HandStoryDrill(Drill):
    """Play one hand from the button: open, face a turn lead with a flush draw, then the river."""

    key = "hand-story"
    title = "Hand story: the flush draw"
    concept = "street-by-street"
    tier = 4
    description = "One hand, three decisions: open, call a turn bet with a draw, bluff the river."

    def make_question(self, rng: random.Random) -> Question:
        opening = [
            c
            for c in chart_range("btn-open", "Raise")
            if len(c) == 3 and c.endswith("s") and c[0] != c[1]
        ]
        villain_calls = chart_range("bb-vs-btn", "Call")
        while True:
            hero = rng.choice(combos_of_class(rng.choice(opening)))
            suit = suit_of(hero[0])
            board = self._board(rng, hero, suit)
            if board is None:
                continue
            flop, turn, river = board[:3], board[3], board[4]
            turn_board = [*flop, turn]
            leads = [
                c
                for c, _ in villain_calls.combos([*hero, *turn_board])
                if pair_class(c, turn_board) in ("top pair+", "two pair+") and river not in c
            ]
            story = self._story(rng, hero, flop, turn, river, leads)
            if story is not None:
                return story

    @staticmethod
    def _board(rng: random.Random, hero: Combo, suit: int) -> list[Card] | None:
        """Flop with two of hero's suit and no pair for hero; blank turn and river."""
        hero_ranks = {rank_of(c) for c in hero}
        deck = [c for c in remaining_deck(hero)]
        suited = [c for c in deck if suit_of(c) == suit and rank_of(c) not in hero_ranks]
        offsuit = [c for c in deck if suit_of(c) != suit and rank_of(c) not in hero_ranks]
        flop = [*rng.sample(suited, 2), rng.choice(offsuit)]
        used = {rank_of(c) for c in flop}
        blanks = [c for c in offsuit if c not in flop and rank_of(c) not in used]
        if len(used) < 3 or len(blanks) < 2:
            return None
        turn, river = rng.sample(blanks, 2)
        if (
            rank_of(turn) == rank_of(river)
            or category([*hero, *flop, turn, river]) > Category.HIGH_CARD
        ):
            return None
        return [*flop, turn, river]

    def _story(
        self,
        rng: random.Random,
        hero: Combo,
        flop: list[Card],
        turn: Card,
        river: Card,
        leads: list[Combo],
    ) -> Question | None:
        if len(leads) < 6:  # too few leading hands to make a meaningful range
            return None
        hand = class_of_combo(*hero)
        pot_flop = 5.5  # 2.5bb open, BB calls, 0.5bb dead small blind
        cbet = 2.0
        pot_turn = pot_flop + 2 * cbet
        lead_size = rng.choice((0.33, 0.5, 0.66, 0.75))
        lead = round(pot_turn * lead_size * 2) / 2
        turn_board = [*flop, turn]
        equity = calculate_equity([hero, [(c, 1.0) for c in leads]], turn_board)[0].equity
        need = odds.required_equity(pot_turn, lead)
        if abs(equity - need) < 0.02:
            return None
        pot_river = pot_turn + 2 * lead
        river_board = [*turn_board, river]
        river_range = [c for c in leads if river not in c]
        one_pair = [c for c in river_range if category([*c, *river_board]) == Category.ONE_PAIR]
        fold = len(one_pair) / len(river_range)
        bluff = pot_river * rng.choice((0.66, 1.0))
        bluff = round(bluff * 2) / 2
        alpha = odds.alpha(pot_river, bluff)
        if abs(fold - alpha) < 0.03:
            return None
        villain_hand = rng.choice(river_range)

        bluff_answer = "Bet" if fold > alpha else "Check"
        ev = fold * pot_river - (1 - fold) * bluff
        river_q = Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"River {pretty_cards([river])} misses your draw. BB checks. Pot {pot_river:g}. "
            f"BB folds one-pair hands to a bet and calls with two pair or better. Bet {bluff:g} "
            "as a bluff, or check and give up?",
            kind=AnswerKind.CHOICE,
            answer=bluff_answer,
            choices=("Bet", "Check"),
            payload={
                "hole": card_list(hero),
                "board": card_list(river_board),
                "pot": pot_river,
                "bet": bluff,
                "facts": facts(street="River · step 3 of 3", villain="BB"),
            },
            explanation=(
                f"BB's range here: {len(river_range)} combos, {len(one_pair)} of them one pair "
                f"that fold ({pct(fold)}%).",
                f"A {bluff:g} bluff needs {pct(alpha)}% folds; EV = {fold:.2f} x {pot_river:g} - "
                f"{1 - fold:.2f} x {bluff:g} = {ev:+.1f}, so {bluff_answer.lower()}.",
                f"BB actually had {pretty_cards(villain_hand)}"
                + (
                    ": one pair, so a bluff takes it down."
                    if villain_hand in one_pair
                    else ": two pair or better, so this time the bluff gets called."
                ),
            ),
            highlight=tuple(card_list(villain_hand)),
        )
        turn_answer = "Call" if equity > need else "Fold"
        extra = max(0.0, lead / max(equity, 1e-9) - pot_turn - 2 * lead)
        turn_q = Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"Flop {pretty_cards(flop)}: you c-bet {cbet:g}, BB calls. Turn "
            f"{pretty_cards([turn])}: BB leads {lead:g} into {pot_turn:g}, and only leads with "
            "top pair or better. On pot odds alone, call or fold?",
            kind=AnswerKind.CHOICE,
            answer=turn_answer,
            choices=("Call", "Fold"),
            payload={
                "hole": card_list(hero),
                "board": card_list(turn_board),
                "pot": pot_turn,
                "bet": lead,
                "facts": facts(street="Turn · step 2 of 3", villain="BB, top pair or better"),
            },
            explanation=(
                f"Against BB's {len(leads)} leading combos your flush draw has {pct(equity)}% "
                f"equity with one card to come.",
                f"Calling {lead:g} to win {pot_turn + lead:g} needs {pct(need)}%, so "
                f"{turn_answer.lower()} on pot odds.",
                (
                    f"Implied odds: you would need about {extra:.1f} more on the river "
                    "when you hit."
                    if turn_answer == "Fold"
                    else "The price is good enough without counting on implied odds."
                ),
                "Either way, let's see the river.",
            ),
            follow_up=river_q,
        )
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"6-max, 100bb. Folded to you on the button with {hand}. Open or fold?",
            kind=AnswerKind.CHOICE,
            answer="Raise",
            choices=("Raise", "Fold"),
            payload={
                "hole": card_list(hero),
                "position": "BTN",
                "facts": facts(street="Preflop · step 1 of 3"),
            },
            explanation=(
                f"{hand} is in the button's opening range: suited hands make flushes and play "
                "well in position.",
                "You open to 2.5bb and the big blind calls.",
            ),
            follow_up=turn_q,
        )


SCENARIO_DRILLS: tuple[Drill, ...] = (
    RangeHitsDrill(),
    RangeEquityDrill(),
    ImpliedOddsDrill(),
    BluffEvDrill(),
    HandStoryDrill(),
    BluffCatchDrill(),
    PushFoldDrill(),
    IcmDrill(),
)
