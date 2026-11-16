"""Math Lab drills (curriculum tiers 0, 1, 3 and 5). Every answer is computed by the engine."""

from __future__ import annotations

import itertools
import random
from collections.abc import Callable
from typing import ClassVar

from holdem.core import odds
from holdem.core.board import draws, outs_against
from holdem.core.cards import RANKS, Card, cards_str, deal, make_card, remaining_deck
from holdem.core.equity import calculate_equity
from holdem.core.evaluator import Category, category, evaluate
from holdem.core.ranges import Combo, Range, class_of_combo, live_combos, normalize_class
from holdem.drills.base import AnswerKind, Drill, Question, card_list, pct

CATEGORY_CHOICES = tuple(c.label for c in sorted(Category, reverse=True))
BET_SIZES = (0.25, 1 / 3, 0.5, 2 / 3, 0.75, 1.0, 1.5, 2.0)
BET_SIZE_LABELS = {
    0.25: "1/4",
    1 / 3: "1/3",
    0.5: "1/2",
    2 / 3: "2/3",
    0.75: "3/4",
    1.0: "pot",
    1.5: "1.5x pot",
    2.0: "2x pot",
}


def _fmt(value: float) -> str:
    return f"{value:g}"


class HandRankingDrill(Drill):
    key = "hand-ranking"
    title = "Name the hand"
    concept = "hand-rankings"
    tier = 0
    description = "Seven cards: name the best five-card hand."

    def make_question(self, rng: random.Random) -> Question:
        target = rng.choice(list(Category))
        # Rejection-sample so rare categories show up as often as common ones.
        attempts = (deal(rng, 7) for _ in range(50_000))
        cards = next((c for c in attempts if category(c) is target), None) or deal(rng, 7)
        hole, board = cards[:2], cards[2:]
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt="What is the best five-card hand?",
            kind=AnswerKind.CHOICE,
            answer=category(cards).label,
            choices=CATEGORY_CHOICES,
            payload={"hole": card_list(hole), "board": card_list(board)},
            explanation=(f"Your best hand is {category(cards).label.lower()}.",),
        )


class ShowdownDrill(Drill):
    key = "showdown"
    title = "Who wins?"
    concept = "board-reading"
    tier = 0
    description = "Read the river board and pick the winner, or a split pot."

    def make_question(self, rng: random.Random) -> Question:
        cards = deal(rng, 11)
        board = cards[:5]
        hands = [cards[5:7], cards[7:9], cards[9:11]]
        ranks = [evaluate([*h, *board]) for h in hands]
        best = min(ranks)
        winners = [i for i, r in enumerate(ranks) if r == best]
        answer = f"Player {winners[0] + 1}" if len(winners) == 1 else "Split pot"
        lines = [
            f"Player {i + 1}: {category([*h, *board]).label.lower()}" for i, h in enumerate(hands)
        ]
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt="Which player wins at showdown?",
            kind=AnswerKind.CHOICE,
            answer=answer,
            choices=("Player 1", "Player 2", "Player 3", "Split pot"),
            payload={"board": card_list(board), "players": [card_list(h) for h in hands]},
            explanation=(*lines, f"Result: {answer}."),
        )


def nut_hand(board: list[Card]) -> tuple[int, Combo]:
    """Best possible rank on a river board and one hand that makes it."""
    best: tuple[int, Combo] | None = None
    for a, b in itertools.combinations(remaining_deck(board), 2):
        rank = evaluate([a, b, *board])
        if best is None or rank < best[0]:
            best = (rank, (a, b))
    assert best is not None
    return best


class NutsDrill(Drill):
    key = "nuts"
    title = "Find the nuts"
    concept = "board-reading"
    tier = 0
    description = "What is the best possible hand on this river board?"

    def make_question(self, rng: random.Random) -> Question:
        board = deal(rng, 5)
        _, combo = nut_hand(board)
        answer = category([*combo, *board]).label
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt="What kind of hand is the nuts on this board?",
            kind=AnswerKind.CHOICE,
            answer=answer,
            choices=CATEGORY_CHOICES,
            payload={"board": card_list(board)},
            explanation=(f"The nuts is {answer.lower()}, for example {cards_str(combo)}.",),
            highlight=tuple(card_list(combo)),
        )


class OutsDrill(Drill):
    key = "outs"
    title = "Count your outs"
    concept = "outs"
    tier = 1
    description = "You are behind a known hand. How many cards win for you on the next street?"

    def make_question(self, rng: random.Random) -> Question:
        while True:
            board_size = rng.choice((3, 4))
            cards = deal(rng, 4 + board_size)
            hero, villain, board = cards[:2], cards[2:4], cards[4:]
            result = outs_against(hero, villain, board)
            if result.status < 0 and 3 <= result.count <= 16:
                break
        lines = [f"Winning cards ({result.count}): {cards_str(result.winning)}."]
        if result.tainted:
            lines.append(f"Tainted: {cards_str(result.tainted)} improve your hand but still lose.")
        if result.tying:
            lines.append(f"Split pot: {cards_str(result.tying)}.")
        street = "turn" if board_size == 3 else "river"
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"Villain shows their hand. How many {street} cards give you the lead?",
            kind=AnswerKind.NUMBER,
            answer=result.count,
            unit="outs",
            payload={
                "hole": card_list(hero),
                "villain": card_list(villain),
                "board": card_list(board),
            },
            explanation=tuple(lines),
            highlight=tuple(card_list(result.winning)),
        )


DRAW_LABELS = {
    2: "a pocket pair to a set",
    4: "a gutshot",
    5: "a pair to two pair or trips",
    6: "two overcards",
    8: "an open-ended straight draw",
    9: "a flush draw",
    12: "a flush draw plus a gutshot",
    15: "a flush draw plus an open-ended draw",
}
STREETS = {
    "flop_turn": ("on the turn", 1),
    "turn_river": ("on the river", 1),
    "flop_river": ("by the river (seeing both cards)", 2),
}


class DrawOddsDrill(Drill):
    key = "draw-odds"
    title = "Outs to percent"
    concept = "outs-to-odds"
    tier = 1
    description = "Convert outs into the chance of hitting, then compare with the rule of 2 and 4."

    def make_question(self, rng: random.Random) -> Question:
        outs = rng.choice(list(DRAW_LABELS))
        street = rng.choice(list(STREETS))
        label, cards = STREETS[street]
        exact = odds.draw_probability(outs, street)
        shortcut = odds.rule_of_2_and_4(outs, cards)
        unseen = 46 if street == "turn_river" else 47
        formula = f"{outs}/{unseen}" if cards == 1 else f"1 - C({47 - outs},2)/C(47,2)"
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"You have {DRAW_LABELS[outs]} ({outs} outs). Chance to hit {label}?",
            kind=AnswerKind.NUMBER,
            answer=pct(exact),
            unit="%",
            tolerance=2.0,
            payload={"outs": outs, "street": street},
            explanation=(
                f"Exact: {formula} = {pct(exact)}%.",
                f"Rule of {2 * cards}: {outs} x {2 * cards} = {pct(shortcut):g}%.",
            ),
        )


def _pot_and_bet(rng: random.Random) -> tuple[float, float, float]:
    pot = rng.randrange(4, 41) * 5
    size = rng.choice(BET_SIZES)
    return pot, round(pot * size, 1), size


class PotOddsDrill(Drill):
    key = "pot-odds"
    title = "Pot odds"
    concept = "pot-odds"
    tier = 1
    description = "Villain bets. What equity do you need to call?"

    def make_question(self, rng: random.Random) -> Question:
        pot, bet, _ = _pot_and_bet(rng)
        need = odds.required_equity(pot, bet)
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"The pot is {_fmt(pot)} and villain bets {_fmt(bet)}. "
            "What equity do you need to call?",
            kind=AnswerKind.NUMBER,
            answer=pct(need),
            unit="%",
            tolerance=1.5,
            payload={"pot": pot, "bet": bet},
            explanation=(
                f"You call {_fmt(bet)} to win a final pot of "
                f"{_fmt(pot + 2 * bet)}: {_fmt(bet)}/{_fmt(pot + 2 * bet)} = {pct(need)}%.",
                f"Pot odds {odds.pot_odds_ratio(pot, bet):.2g} to 1.",
            ),
        )


class CallOrFoldDrill(Drill):
    key = "call-or-fold"
    title = "Call or fold"
    concept = "pot-odds"
    tier = 1
    description = "Turn decision with a draw against a known hand: compare equity with pot odds."

    def make_question(self, rng: random.Random) -> Question:
        while True:
            cards = deal(rng, 8)
            hero, villain, board = cards[:2], cards[2:4], cards[4:]
            result = outs_against(hero, villain, board)
            if result.status >= 0 or result.count < 2:
                continue
            pot, bet, _ = _pot_and_bet(rng)
            equity = calculate_equity([(hero[0], hero[1]), (villain[0], villain[1])], board)
            mine = equity[0].equity
            need = odds.required_equity(pot, bet)
            if abs(mine - need) >= 0.03:
                break
        answer = "Call" if mine > need else "Fold"
        ev = odds.call_ev(pot, bet, mine)
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"Turn. Pot {_fmt(pot)}, villain bets {_fmt(bet)} and shows their hand. "
            "Call or fold?",
            kind=AnswerKind.CHOICE,
            answer=answer,
            choices=("Call", "Fold"),
            payload={
                "hole": card_list(hero),
                "villain": card_list(villain),
                "board": card_list(board),
                "pot": pot,
                "bet": bet,
            },
            explanation=(
                f"You have {result.count} outs: equity {pct(mine)}%.",
                f"You need {pct(need)}% to call.",
                f"Calling is worth {ev:+.1f} chips versus folding, so {answer.lower()}.",
            ),
            highlight=tuple(card_list(result.winning)),
        )


def _cards_of(rng: random.Random, ranks: list[int], suited: bool) -> list[Card]:
    if suited:
        suit = rng.randrange(4)
        return [make_card(r, suit) for r in ranks]
    suits = rng.sample(range(4), 2)
    return [make_card(r, s) for r, s in zip(ranks, suits, strict=True)]


def _pair(rng: random.Random, rank: int, avoid: list[Card]) -> list[Card]:
    options = [s for s in range(4) if make_card(rank, s) not in avoid]
    s1, s2 = rng.sample(options, 2)
    return [make_card(rank, s1), make_card(rank, s2)]


def _unpaired(rng: random.Random, high: int, low: int, avoid: list[Card]) -> list[Card]:
    while True:
        cards = _cards_of(rng, [high, low], rng.random() < 0.3)
        if not set(cards) & set(avoid):
            return cards


MatchupBuilder = Callable[[random.Random], tuple[list[Card], list[Card]]]


def _pair_vs_overs(rng: random.Random) -> tuple[list[Card], list[Card]]:
    pair = rng.randrange(0, 11)
    high, low = sorted(rng.sample(range(pair + 1, 13), 2), reverse=True)
    hero = _pair(rng, pair, [])
    return hero, _unpaired(rng, high, low, hero)


def _overpair(rng: random.Random) -> tuple[list[Card], list[Card]]:
    high, low = sorted(rng.sample(range(13), 2), reverse=True)
    hero = _pair(rng, high, [])
    return hero, _pair(rng, low, hero)


def _domination(rng: random.Random) -> tuple[list[Card], list[Card]]:
    top = rng.randrange(4, 13)
    k1, k2 = sorted(rng.sample(range(top), 2), reverse=True)
    hero = _unpaired(rng, top, k1, [])
    return hero, _unpaired(rng, top, k2, hero)


def _overs_vs_unders(rng: random.Random) -> tuple[list[Card], list[Card]]:
    a, b, c, d = sorted(rng.sample(range(13), 4), reverse=True)
    hero = _unpaired(rng, a, b, [])
    return hero, _unpaired(rng, c, d, hero)


def _pair_vs_one_over(rng: random.Random) -> tuple[list[Card], list[Card]]:
    pair = rng.randrange(1, 12)
    over, under = rng.randrange(pair + 1, 13), rng.randrange(0, pair)
    hero = _pair(rng, pair, [])
    return hero, _unpaired(rng, over, under, hero)


MATCHUPS: dict[str, tuple[MatchupBuilder, str]] = {
    "pair vs two overcards": (_pair_vs_overs, "about 55/45, the classic coin flip"),
    "overpair vs underpair": (_overpair, "about 80/20"),
    "dominated hand": (_domination, "about 70-75 / 25-30"),
    "two overcards vs two undercards": (_overs_vs_unders, "about 60-65 / 35-40"),
    "pair vs one overcard": (_pair_vs_one_over, "about 70/30"),
}


class PreflopEquityDrill(Drill):
    key = "preflop-equity"
    title = "Preflop all-in equity"
    concept = "preflop-equity"
    tier = 1
    description = "Estimate your all-in equity in a classic preflop matchup."
    samples: ClassVar[int] = 20_000

    def make_question(self, rng: random.Random) -> Question:
        name = rng.choice(list(MATCHUPS))
        builder, anchor = MATCHUPS[name]
        hero, villain = builder(rng)
        result = calculate_equity(
            [(hero[0], hero[1]), (villain[0], villain[1])],
            samples=self.samples,
            seed=rng.randrange(1 << 30),
            exact_limit=0,
        )
        mine = result[0]
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt="All in preflop. What is your equity?",
            kind=AnswerKind.NUMBER,
            answer=pct(mine.equity),
            unit="%",
            tolerance=5.0,
            payload={"hole": card_list(hero), "villain": card_list(villain)},
            explanation=(
                f"{class_of_combo(*hero)} vs {class_of_combo(*villain)} is {name}: {anchor}.",
                f"Simulated equity {pct(mine.equity)}% (win {pct(mine.win)}%, "
                f"tie {pct(mine.tie)}%).",
            ),
        )


class FlopEquityDrill(Drill):
    key = "flop-equity"
    title = "Flop equity"
    concept = "postflop-equity"
    tier = 1
    description = "Estimate your equity on the flop against a known hand, all in."

    def make_question(self, rng: random.Random) -> Question:
        cards = deal(rng, 7)
        hero, villain, board = cards[:2], cards[2:4], cards[4:]
        result = calculate_equity([(hero[0], hero[1]), (villain[0], villain[1])], board)
        mine = result[0]
        hint = outs_against(hero, villain, board)
        lines = [f"Exact equity over all 990 turn and river cards: {pct(mine.equity)}%."]
        if hint.status < 0:
            lines.append(
                f"You have {hint.count} outs on the turn; outs x 4 = {hint.count * 4}% "
                "is the quick estimate."
            )
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt="All in on the flop. What is your equity?",
            kind=AnswerKind.NUMBER,
            answer=pct(mine.equity),
            unit="%",
            tolerance=6.0,
            payload={
                "hole": card_list(hero),
                "villain": card_list(villain),
                "board": card_list(board),
            },
            explanation=tuple(lines),
        )


COMBO_CLASSES = ("AA", "KK", "QQ", "JJ", "TT", "AKo", "AK", "AQ", "KQ", "AKs", "QJs")


class CombosDrill(Drill):
    key = "combos"
    title = "Count combos"
    concept = "combinatorics"
    tier = 3
    description = "How many combos of a hand are possible given the cards you can see?"

    def make_question(self, rng: random.Random) -> Question:
        target = rng.choice(COMBO_CLASSES)
        classes = Range.parse(target)
        # Most of the time, put a card of the target's top rank on the flop to create a blocker.
        seeded: list[Card] = []
        if rng.random() < 0.6:
            rank = RANKS.index(normalize_class(next(iter(classes)))[0])
            seeded = [make_card(rank, rng.randrange(4))]
        hole = deal(rng, 2, seeded)
        board = [*seeded, *deal(rng, 3 - len(seeded), [*seeded, *hole])]
        visible = [*hole, *board]
        count = sum(len(live_combos(c, visible)) for c in classes)
        full = sum(len(live_combos(c)) for c in classes)
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"How many combos of {target} can villain hold?",
            kind=AnswerKind.NUMBER,
            answer=count,
            unit="combos",
            payload={"hole": card_list(hole), "board": card_list(board)},
            explanation=(
                f"{target} has {full} combos with no cards seen.",
                f"Removing combos that use a visible card leaves {count}.",
            ),
        )


class DefenseDrill(Drill):
    key = "defense"
    title = "MDF, alpha and bluff ratios"
    concept = "mdf"
    tier = 5
    description = "Defense frequency, bluff break-even and bluff share for a bet size."

    QUESTIONS: ClassVar[dict[str, tuple[str, Callable[[float, float], float], str]]] = {
        "mdf": (
            "What is the minimum defense frequency against this bet?",
            odds.minimum_defense_frequency,
            "MDF = pot / (pot + bet)",
        ),
        "alpha": (
            "How often must a pure bluff of this size work to break even?",
            odds.alpha,
            "alpha = bet / (pot + bet)",
        ),
        "bluff": (
            "What share of a polarized river betting range should be bluffs?",
            odds.bluff_share,
            "bluffs = bet / (pot + 2 x bet)",
        ),
    }

    def make_question(self, rng: random.Random) -> Question:
        size = rng.choice(BET_SIZES)
        which = rng.choice(list(self.QUESTIONS))
        prompt, func, formula = self.QUESTIONS[which]
        value = func(1.0, size)
        bluffs, values = odds.bluff_to_value(1.0, size)
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"Bet of {BET_SIZE_LABELS[size]} pot. {prompt}",
            kind=AnswerKind.NUMBER,
            answer=pct(value),
            unit="%",
            tolerance=2.0,
            payload={"size": size, "quantity": which},
            explanation=(
                f"{formula} = {pct(value)}%.",
                f"Bluff-to-value ratio at this size: {bluffs}:{values}.",
                "MDF applies to a single bet, and exploiting players who under-bluff means "
                "folding more than MDF.",
            ),
        )


DEALT_GROUPS = {
    "pocket aces": "AA",
    "any pocket pair": "22+",
    "ace-king (suited or not)": "AK",
    "ace-king suited": "AKs",
    "jacks or better, or ace-king": "JJ+, AK",
    "queens or better": "QQ+",
    "a suited connector (32s to AKs)": "32s, 43s, 54s, 65s, 76s, 87s, 98s, T9s, JTs, QJs, KQs, AKs",
}


class DealtOddsDrill(Drill):
    key = "dealt-odds"
    title = "Starting-hand odds"
    concept = "combinatorics"
    tier = 1
    description = "How often are you dealt a given starting hand?"

    def make_question(self, rng: random.Random) -> Question:
        name = rng.choice(list(DEALT_GROUPS))
        hand_range = Range.parse(DEALT_GROUPS[name])
        prob = odds.dealt_probability(hand_range)
        combos = hand_range.combo_count()
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"What is the chance of being dealt {name}?",
            kind=AnswerKind.NUMBER,
            answer=round(prob * 100, 2),
            unit="%",
            tolerance=max(0.1, round(prob * 100 * 0.15, 2)),
            payload={"group": name},
            explanation=(
                f"{combos:g} combos out of 1,326 = {prob * 100:.2f}%, about 1 in {1 / prob:.0f}.",
                "Pairs have 6 combos, suited hands 4, offsuit hands 12.",
            ),
        )


FlopEvent = Callable[[list[Card], list[Card]], bool]


def _set_or_better(hole: list[Card], flop: list[Card]) -> bool:
    return any(c // 4 == hole[0] // 4 for c in flop)


def _pair_or_better_with_hole(hole: list[Card], flop: list[Card]) -> bool:
    flop_ranks = {c // 4 for c in flop}
    return any(c // 4 in flop_ranks for c in hole)


def _flush_draw_or_better(hole: list[Card], flop: list[Card]) -> bool:
    suit = hole[0] % 4
    return sum(1 for c in flop if c % 4 == suit) >= 2


def _overcard(hole: list[Card], flop: list[Card]) -> bool:
    return any(c // 4 > hole[0] // 4 for c in flop)


def _open_ended_or_better(hole: list[Card], flop: list[Card]) -> bool:
    return category([*hole, *flop]) >= Category.STRAIGHT or draws(hole, flop).open_ended


FLOP_EVENTS: dict[str, tuple[str, FlopEvent]] = {
    "set": ("With a pocket pair, chance to flop a set or better?", _set_or_better),
    "pair": (
        "With two unpaired cards, chance to pair at least one of them?",
        _pair_or_better_with_hole,
    ),
    "flush-draw": (
        "With suited cards, chance to flop a flush draw or a flush?",
        _flush_draw_or_better,
    ),
    "overcard": ("With this pocket pair, chance at least one overcard flops?", _overcard),
    "straight-draw": (
        "With these connectors, chance to flop an open-ended draw or a straight?",
        _open_ended_or_better,
    ),
}


def flop_event_probability(hole: list[Card], event: FlopEvent) -> float:
    flops = list(itertools.combinations(remaining_deck(hole), 3))
    return sum(1 for f in flops if event(hole, list(f))) / len(flops)


class FlopOddsDrill(Drill):
    key = "flop-odds"
    title = "Flop odds"
    concept = "flop-odds"
    tier = 1
    description = "How often does the flop give you a set, a pair, a draw?"

    def make_question(self, rng: random.Random) -> Question:
        which = rng.choice(list(FLOP_EVENTS))
        prompt, event = FLOP_EVENTS[which]
        if which in ("set", "overcard"):
            rank = rng.randrange(4, 12) if which == "overcard" else rng.randrange(13)
            hole = _pair(rng, rank, [])
        elif which == "straight-draw":
            low = rng.randrange(3, 9)
            hole = _cards_of(rng, [low + 1, low], rng.random() < 0.5)
        else:
            high, low = sorted(rng.sample(range(13), 2), reverse=True)
            hole = _cards_of(rng, [high, low], which == "flush-draw")
        prob = flop_event_probability(hole, event)
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=prompt,
            kind=AnswerKind.NUMBER,
            answer=pct(prob),
            unit="%",
            tolerance=3.0,
            payload={"hole": card_list(hole), "event": which},
            explanation=(
                f"Counted over all 19,600 flops: {pct(prob)}%, about 1 in {1 / prob:.1f}.",
            ),
        )


SPR_SCENARIOS = (
    ("CO opens to 2.5bb, the big blind calls.", 2.5 + 2.5 + 0.5, 97.5),
    ("The button opens to 2.5bb, the big blind calls.", 2.5 + 2.5 + 0.5, 97.5),
    ("UTG opens to 3bb, the button calls, the blinds fold.", 3 + 3 + 1.5, 97.0),
    ("CO opens to 2.5bb, the button 3-bets to 8bb, CO calls.", 8 + 8 + 1.5, 92.0),
    (
        "The button opens to 2.5bb, the big blind 3-bets to 11bb, the button calls.",
        11 + 11 + 0.5,
        89.0,
    ),
    ("CO opens to 2.5bb, BTN 3-bets to 8bb, CO 4-bets to 20bb, BTN calls.", 20 + 20 + 1.5, 80.0),
)


class SprDrill(Drill):
    key = "spr"
    title = "Stack-to-pot ratio"
    concept = "spr"
    tier = 3
    description = "Work out the SPR on the flop from the preflop action at 100bb."

    def make_question(self, rng: random.Random) -> Question:
        action, pot, stack = rng.choice(SPR_SCENARIOS)
        spr = odds.stack_to_pot_ratio(stack, pot)
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"Everyone starts with 100bb. {action} What is the SPR on the flop?",
            kind=AnswerKind.NUMBER,
            answer=round(spr, 1),
            tolerance=max(0.3, round(spr * 0.08, 1)),
            payload={"action": action},
            explanation=(
                f"Pot {pot:g}bb, effective stack {stack:g}bb: SPR = {stack:g}/{pot:g} = {spr:.1f}.",
                "Low SPR (under about 4) means top pair is usually happy to get it in; "
                "high SPR needs stronger hands.",
            ),
        )


ALL_DRILLS: tuple[Drill, ...] = (
    HandRankingDrill(),
    ShowdownDrill(),
    NutsDrill(),
    OutsDrill(),
    DrawOddsDrill(),
    PotOddsDrill(),
    CallOrFoldDrill(),
    PreflopEquityDrill(),
    FlopEquityDrill(),
    DealtOddsDrill(),
    FlopOddsDrill(),
    CombosDrill(),
    SprDrill(),
    DefenseDrill(),
)

DRILLS: dict[str, Drill] = {d.key: d for d in ALL_DRILLS}
