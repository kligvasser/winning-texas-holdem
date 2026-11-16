"""Hand stories: one hand, several graded decisions, written as data (TOML) instead of code.

A story names the hero's possible hands, the villain's range (from a baseline chart), and a list
of steps. Each step reveals a street, can put conditions on the cards ("hero flops a set", "the turn
is a blank"), narrows the villain's range by what they do, and asks one decision:

- ``chart``: a preflop decision graded by a baseline chart.
- ``call``: facing a bet; call when your equity against the villain's range beats the price.
- ``catch``: facing a bet from a stated betting range; same rule against that range.
- ``bluff``: bet or check; bet when the villain's folding share beats the bluff's break-even.
- ``value``: bet or check; bet when you are ahead of more than half of the hands that call.

Hero conditions must all hold. Villain filters keep a hand if *any* listed condition holds.
A condition name can be negated with ``not_``.
"""

from __future__ import annotations

import random
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from importlib import resources
from typing import Any

from holdem.core import odds
from holdem.core.board import STRAIGHTS, draws
from holdem.core.cards import Card, deal, pretty_cards, rank_of, suit_of
from holdem.core.equity import calculate_equity
from holdem.core.evaluator import Category, category, compare
from holdem.core.ranges import Combo, Range, class_of_combo, combos_of_class
from holdem.drills.base import AnswerKind, Drill, Question, card_list
from holdem.preflop import SPOTS_BY_ID

STREET_CARDS = {"preflop": 0, "flop": 3, "turn": 4, "river": 5}
MAX_DEALS = 4000

type Predicate = Callable[[Combo, list[Card]], bool]


def _ranks(cards: Sequence[Card]) -> list[int]:
    return [rank_of(c) for c in cards]


def _pocket(hole: Combo) -> bool:
    return rank_of(hole[0]) == rank_of(hole[1])


def _set(hole: Combo, board: list[Card]) -> bool:
    return _pocket(hole) and rank_of(hole[0]) in _ranks(board)


def _overpair(hole: Combo, board: list[Card]) -> bool:
    return _pocket(hole) and rank_of(hole[0]) > max(_ranks(board))


def _underpair_to_top(hole: Combo, board: list[Card]) -> bool:
    """A pocket pair below the board's top card that did not make a set."""
    return _pocket(hole) and not _set(hole, board) and rank_of(hole[0]) < max(_ranks(board))


def _top_pair(hole: Combo, board: list[Card]) -> bool:
    return not _pocket(hole) and max(_ranks(board)) in _ranks(hole)


def _made_straight_plus(hole: Combo, board: list[Card]) -> bool:
    return category([*hole, *board]) >= Category.STRAIGHT


def _two_pair_plus(hole: Combo, board: list[Card]) -> bool:
    hits = {r for r in _ranks(hole) if r in _ranks(board)}
    return _set(hole, board) or len(hits) == 2 or _made_straight_plus(hole, board)


def _pair_plus(hole: Combo, board: list[Card]) -> bool:
    hits = any(r in _ranks(board) for r in _ranks(hole))
    return _pocket(hole) or hits or _made_straight_plus(hole, board)


def _one_pair(hole: Combo, board: list[Card]) -> bool:
    return _pair_plus(hole, board) and not _two_pair_plus(hole, board)


def _flush_draw(hole: Combo, board: list[Card]) -> bool:
    return len(board) < 5 and draws(hole, board).flush_draw


def _oesd(hole: Combo, board: list[Card]) -> bool:
    return len(board) < 5 and draws(hole, board).open_ended


def _draw(hole: Combo, board: list[Card]) -> bool:
    if len(board) >= 5:
        return False
    found = draws(hole, board)
    return found.flush_draw or found.straight_outs_ranks > 0


PREDICATES: dict[str, Predicate] = {
    "set": _set,
    "overpair": _overpair,
    "underpair_to_top": _underpair_to_top,
    "top_pair": _top_pair,
    "top_pair_plus": lambda h, b: _top_pair(h, b) or _overpair(h, b) or _two_pair_plus(h, b),
    "two_pair_plus": _two_pair_plus,
    "pair_plus": _pair_plus,
    "one_pair": _one_pair,
    "weak_pair": lambda h, b: _one_pair(h, b) and not _top_pair(h, b) and not _overpair(h, b),
    "flush_draw": _flush_draw,
    "oesd": _oesd,
    "draw": _draw,
    "nothing": lambda h, b: not _pair_plus(h, b) and not _draw(h, b),
}


def _test(name: str, hole: Combo, board: list[Card]) -> bool:
    if name.startswith("not_"):
        return not PREDICATES[name[4:]](hole, board)
    return PREDICATES[name](hole, board)


def hero_ok(names: Sequence[str], hole: Combo, board: list[Card]) -> bool:
    return all(_test(n, hole, board) for n in names)


def villain_keeps(names: Sequence[str], hole: Combo, board: list[Card]) -> bool:
    return not names or any(_test(n, hole, board) for n in names)


def _board_ok(names: Sequence[str], before: list[Card], new: list[Card]) -> bool:
    """Board conditions on the cards a street adds: "unpaired" and "blank"."""
    for name in names:
        if name == "unpaired" and len(set(_ranks(before + new))) != len(before + new):
            return False
        if name == "blank":
            # No pair, no third card of a suit, and no four cards within one straight.
            ranks = _ranks(before)
            suits = [suit_of(c) for c in before]
            if any(rank_of(c) in ranks or suits.count(suit_of(c)) >= 2 for c in new):
                return False
            after = set(ranks) | set(_ranks(new))
            if any(len(window & after) >= 4 for window in STRAIGHTS):
                return False
    return True


@dataclass(frozen=True)
class Step:
    street: str
    decision: str
    prompt: str
    size: float | tuple[float, ...] = 0.0  # fraction of the pot; a list picks one at random
    hero: tuple[str, ...] = ()
    board: tuple[str, ...] = ()
    villain: tuple[str, ...] = ()  # narrows the range from this street on
    setup: str = ""
    setup_bet: float = 0.0
    spot: str = ""
    expect: str = ""
    folds: tuple[str, ...] = ()
    calls: tuple[str, ...] = ()
    bets: tuple[str, ...] = ()
    lesson: str = ""


def _step(raw: dict[str, Any]) -> Step:
    """TOML arrays become tuples so steps stay hashable and immutable."""
    fields: dict[str, Any] = {k: tuple(v) if isinstance(v, list) else v for k, v in raw.items()}
    return Step(**fields)


@dataclass(frozen=True)
class Story:
    key: str
    title: str
    description: str
    pot: float
    hero_classes: tuple[str, ...]
    villain_name: str
    villain_spot: str
    villain_action: str
    villain_classes: str
    steps: tuple[Step, ...] = field(default=())

    @classmethod
    def from_toml(cls, data: dict[str, Any]) -> Story:
        hero = data["hero"]
        villain = data["villain"]
        steps = tuple(_step(raw) for raw in data["steps"])
        story = cls(
            key=data["key"],
            title=data["title"],
            description=data["description"],
            pot=float(data["pot"]),
            hero_classes=tuple(Range.parse(hero["classes"])),
            villain_name=villain["name"],
            villain_spot=villain["spot"],
            villain_action=villain["action"],
            villain_classes=villain.get("classes", ""),
            steps=steps,
        )
        story.validate()
        return story

    def validate(self) -> None:
        if not self.steps or self.steps[0].decision != "chart":
            raise ValueError(f"{self.key}: the first step must be a preflop chart decision")
        for step in self.steps:
            if step.street not in STREET_CARDS:
                raise ValueError(f"{self.key}: unknown street {step.street!r}")
            if step.decision not in DECISIONS:
                raise ValueError(f"{self.key}: unknown decision {step.decision!r}")
            for name in (*step.hero, *step.villain, *step.folds, *step.calls, *step.bets):
                if name.removeprefix("not_") not in PREDICATES:
                    raise ValueError(f"{self.key}: unknown condition {name!r}")
        if not self.playable_classes():
            raise ValueError(f"{self.key}: no hero hand matches the preflop chart")

    def playable_classes(self) -> list[str]:
        """Hero hands for which the chart takes the story's preflop line."""
        first = self.steps[0]
        spot = SPOTS_BY_ID[first.spot]
        return [c for c in self.hero_classes if spot.action_for(c) == first.expect]

    def villain_range(self) -> Range:
        spot = SPOTS_BY_ID[self.villain_spot]
        classes = [c for c, a in spot.chart.items() if a == self.villain_action]
        if self.villain_classes:
            allowed = Range.parse(self.villain_classes)
            classes = [c for c in classes if c in allowed]
        return Range.of(classes)


def _half(value: float) -> float:
    return round(value * 2) / 2


@dataclass
class _Context:
    """Running state while a story is dealt and graded."""

    story: Story
    hero: Combo
    board: list[Card]
    pot: float
    rng: random.Random
    filters: list[tuple[tuple[str, ...], str]] = field(default_factory=list)  # (names, street)

    def visible(self, street: str) -> list[Card]:
        return self.board[: STREET_CARDS[street]]

    def villain_combos(self, street: str, extra: tuple[str, ...] = ()) -> list[Combo]:
        shown = self.visible(street)
        dead = [*self.hero, *shown]
        combos = [c for c, _ in self.story.villain_range().combos(dead)]
        # Each filter is judged on the board of the street where the villain acted.
        for names, at in [*self.filters, (extra, street)]:
            seen = self.visible(at)
            combos = [c for c in combos if villain_keeps(names, c, seen)]
        return combos


def _equity(hero: Combo, villain: list[Combo], board: list[Card]) -> float:
    return calculate_equity([hero, [(c, 1.0) for c in villain]], board)[0].equity


def _decide(step: Step, ctx: _Context) -> dict[str, Any] | None:
    """Answer, choices and explanation for one step, or None if the spot is too close to call."""
    shown = ctx.visible(step.street)
    size = ctx.rng.choice(step.size) if isinstance(step.size, tuple) else step.size
    bet = _half(ctx.pot * size)
    if step.decision == "chart":
        spot = SPOTS_BY_ID[step.spot]
        hand = class_of_combo(*ctx.hero)
        return {
            "answer": spot.action_for(hand),
            "choices": spot.choices,
            "lines": [f"{hand}: {spot.action_for(hand).lower()} in the baseline chart.", spot.note],
            "bet": 0.0,
        }
    if step.decision in ("call", "catch"):
        villain = ctx.villain_combos(step.street, step.bets)
        if len(villain) < 4:
            return None
        equity = _equity(ctx.hero, villain, shown)
        need = odds.required_equity(ctx.pot, bet)
        if abs(equity - need) < 0.02:
            return None
        answer = "Call" if equity > need else "Fold"
        come = {
            3: "with two cards to come (if no more betting)",
            4: "with one card to come",
            5: "at showdown",
        }[len(shown)]
        return {
            "answer": answer,
            "choices": ("Call", "Fold"),
            "lines": [
                f"Against the {len(villain)} combos that {ctx.story.villain_name} bets here you "
                f"have {equity:.1%} equity {come}.",
                f"Calling {bet:g} to win {ctx.pot + bet:g} needs {need:.1%}, so {answer.lower()}.",
            ],
            "bet": bet,
            "narrow": step.bets,
        }
    if step.decision == "bluff":
        villain = ctx.villain_combos(step.street)
        if len(villain) < 4:
            return None
        folding = [c for c in villain if villain_keeps(step.folds, c, shown)]
        share = len(folding) / len(villain)
        alpha = odds.alpha(ctx.pot, bet)
        if abs(share - alpha) < 0.03:
            return None
        answer = "Bet" if share > alpha else "Check"
        ev = share * ctx.pot - (1 - share) * bet
        return {
            "answer": answer,
            "choices": ("Bet", "Check"),
            "lines": [
                f"{len(folding)} of {ctx.story.villain_name}'s {len(villain)} combos fold "
                f"({share:.1%}); a {bet:g} bluff needs {alpha:.1%}.",
                f"EV of betting = {share:.2f} x {ctx.pot:g} - {1 - share:.2f} x {bet:g} = "
                f"{ev:+.1f}, so {answer.lower()}.",
            ],
            "bet": bet,
            "outcome": lambda v: (
                "your bluff wins the pot" if villain_keeps(step.folds, v, shown) else "they call"
            ),
        }
    # value
    callers = ctx.villain_combos(step.street, step.calls)
    if len(callers) < 4:
        return None
    equity = _equity(ctx.hero, callers, shown)
    if abs(equity - 0.5) < 0.03:
        return None
    answer = "Bet" if equity > 0.5 else "Check"
    return {
        "answer": answer,
        "choices": ("Bet", "Check"),
        "lines": [
            f"{ctx.story.villain_name} calls with {len(callers)} combos; against those you have "
            f"{equity:.1%}.",
            "Bet for value when you beat more than half of the hands that call, so "
            f"{answer.lower()}.",
        ],
        "bet": bet,
        "narrow": step.calls,
    }


DECISIONS = ("chart", "call", "catch", "bluff", "value")


def _deal(story: Story, rng: random.Random, hero: Combo) -> list[Card] | None:
    for _ in range(MAX_DEALS):
        board = deal(rng, 5, list(hero))
        ok = True
        for step in story.steps:
            n = STREET_CARDS[step.street]
            if n == 0:
                continue
            before = {3: 0, 4: 3, 5: 4}[n]
            if not _board_ok(step.board, board[:before], board[before:n]) or not hero_ok(
                step.hero, hero, board[:n]
            ):
                ok = False
                break
        if ok:
            return board
    return None


def _fill(text: str, ctx: _Context, values: dict[str, Any]) -> str:
    board = ctx.board
    return text.format(
        hand=class_of_combo(*ctx.hero),
        villain=ctx.story.villain_name,
        flop=pretty_cards(board[:3]),
        turn=pretty_cards(board[3:4]),
        river=pretty_cards(board[4:5]),
        **values,
    )


def build_story(story: Story, rng: random.Random, drill_key: str, concept: str) -> Question | None:
    """Deal one instance of a story and chain its steps, or None if this deal does not work."""
    hand_class = rng.choice(story.playable_classes())
    hero = rng.choice(combos_of_class(hand_class))
    board = _deal(story, rng, hero)
    if board is None:
        return None
    ctx = _Context(story, hero, board, story.pot, rng)
    built: list[dict[str, Any]] = []
    for index, step in enumerate(story.steps):
        if step.villain:
            ctx.filters.append((step.villain, step.street))
        setup_bet = _half(ctx.pot * step.setup_bet)
        ctx.pot += 2 * setup_bet
        decision = _decide(step, ctx)
        if decision is None:
            return None
        values = {
            "pot": f"{ctx.pot:g}",
            "bet": f"{decision['bet']:g}",
            "setup_bet": f"{setup_bet:g}",
        }
        prompt = " ".join(
            p for p in (_fill(step.setup, ctx, values), _fill(step.prompt, ctx, values)) if p
        )
        built.append(
            {
                "step": step,
                "index": index,
                "prompt": prompt,
                "pot": ctx.pot,
                **decision,
            }
        )
        if decision.get("narrow"):
            ctx.filters.append((decision["narrow"], step.street))
        ctx.pot += 2 * decision["bet"]

    final = ctx.villain_combos("river")
    if not final:
        return None
    villain_hand = rng.choice(final)
    return _chain(story, built, ctx, villain_hand, drill_key, concept)


def _chain(
    story: Story,
    built: list[dict[str, Any]],
    ctx: _Context,
    villain_hand: Combo,
    drill_key: str,
    concept: str,
) -> Question:
    question: Question | None = None
    total = len(built)
    for item in reversed(built):
        step: Step = item["step"]
        shown = ctx.visible(step.street)
        lines = list(item["lines"])
        if step.lesson:
            lines.append(step.lesson)
        highlight: tuple[str, ...] = ()
        if item["index"] == total - 1:
            result = compare(ctx.hero, villain_hand, ctx.board)
            showdown = {1: "you win at showdown", 0: "you split", -1: "you lose at showdown"}[
                result
            ]
            outcome = item["outcome"](villain_hand) if "outcome" in item else showdown
            lines.append(
                f"{story.villain_name} actually had {pretty_cards(villain_hand)}: {outcome}."
            )
            highlight = tuple(card_list(villain_hand))
        payload: dict[str, Any] = {
            "hole": card_list(ctx.hero),
            "facts": [
                {
                    "label": "Street",
                    "value": f"{step.street.capitalize()} · step {item['index'] + 1} of {total}",
                },
                {"label": "Villain", "value": story.villain_name},
            ],
        }
        if shown:
            payload["board"] = card_list(shown)
        if step.street != "preflop":
            payload["pot"] = item["pot"]
            payload["bet"] = item["bet"]  # every post-flop decision involves a bet
        question = Question(
            drill=drill_key,
            concept=concept,
            prompt=item["prompt"],
            kind=AnswerKind.CHOICE,
            answer=item["answer"],
            choices=tuple(item["choices"]),
            payload=payload,
            explanation=tuple(lines),
            highlight=highlight,
            follow_up=question,
        )
    assert question is not None
    return question


class StoryDrill(Drill):
    concept = "street-by-street"
    tier = 4

    def __init__(self, story: Story) -> None:
        self.story = story
        self.key = story.key
        self.title = story.title
        self.description = story.description

    def make_question(self, rng: random.Random) -> Question:
        while True:
            question = build_story(self.story, rng, self.key, self.concept)
            if question is not None:
                return question


def load_stories() -> list[Story]:
    folder = resources.files("holdem.data").joinpath("stories")
    files = sorted((f for f in folder.iterdir() if f.name.endswith(".toml")), key=lambda f: f.name)
    return [Story.from_toml(tomllib.loads(f.read_text())) for f in files]


STORY_DRILLS: tuple[Drill, ...] = tuple(StoryDrill(s) for s in load_stories())
