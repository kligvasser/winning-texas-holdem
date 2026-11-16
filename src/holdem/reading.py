"""Hand reading: narrow a bot's range street by street, scored against its true range.

The bots' strategies are known exactly, so after any sequence of actions we can compute the
villain's real range: every hand it could hold, weighted by the probability that the bot would have
taken exactly those actions with it. That makes hand reading gradable, which it rarely is.

The score compares your painted range (each painted combo equally likely) with that weighted range:
``sum over hands of min(your share, true share)``. Painting too wide spreads your range over hands
the bot rarely has; painting too narrow misses hands it often has. Both lower the score.
"""

from __future__ import annotations

import itertools
import random
from collections import defaultdict
from dataclasses import dataclass

from holdem.core.cards import Card, pretty_cards
from holdem.core.range_score import best_match
from holdem.core.ranges import ALL_CLASSES, Combo, class_of_combo, grid_class
from holdem.drills.base import AnswerKind, Drill, Question, card_list
from holdem.engine.bots import STYLES, Bot, Style
from holdem.engine.headsup import Action, HeadsUpHand

HERO_STYLE = "tag"
MIN_CHECKPOINTS = 3
ALL_COMBOS: tuple[Combo, ...] = tuple(itertools.combinations(range(52), 2))  # type: ignore[assignment]


def describe(action: Action, names: tuple[str, str], hero: int) -> str:
    who = names[action.player]
    you = action.player == hero
    verb = {"fold": "fold", "check": "check", "call": "call", "bet": "bet", "raise": "raise"}
    word = verb[action.kind] if you else verb[action.kind] + "s"
    if action.kind == "call":
        return f"{who} {word} {action.amount / 2:g}bb"
    if action.kind in ("bet", "raise"):
        joiner = " to" if action.kind == "raise" else ""
        return f"{who} {word}{joiner} {action.to / 2:g}bb"
    return f"{who} {word}"


@dataclass(frozen=True)
class Checkpoint:
    street: str
    board: list[Card]
    lines: list[str]
    weights: dict[str, float]  # total probability weight per hand class
    combos: dict[str, int]  # live combos per hand class

    def density(self) -> dict[str, float]:
        """Weight per combo, scaled so the likeliest class is 1 (for the heat map)."""
        raw = {c: self.weights[c] / self.combos[c] for c in self.weights if self.combos[c]}
        top = max(raw.values(), default=0.0) or 1.0
        return {c: v / top for c, v in raw.items()}


@dataclass
class ReadHand:
    style: Style
    villain: int  # seat of the villain (0 or 1); the hero is the other seat
    hand: HeadsUpHand
    seed: int
    checkpoints: list[Checkpoint]


def _play(style: Style, villain: int, button: int, seed: int, rng: random.Random) -> HeadsUpHand:
    hand = HeadsUpHand([200, 200], button, random.Random(seed))
    bots = {villain: Bot(style, rng), 1 - villain: Bot(STYLES[HERO_STYLE], rng)}
    while not hand.finished:
        kind, to = bots[hand.current].decide(hand)
        hand.act(kind, to)
    return hand


def _checkpoints(style: Style, villain: int, hand: HeadsUpHand, seed: int) -> list[Checkpoint]:
    """Replay the hand, weighting every villain hand by how likely each action was with it."""
    hero = 1 - villain
    names = ("You", style.name) if villain == 1 else (style.name, "You")
    replay = HeadsUpHand(list(hand.stacks), hand.button, random.Random(seed))
    model = Bot(style, random.Random(0))
    dead = set(hand.hole[hero])
    weight = {c: 1.0 for c in ALL_COMBOS if not set(c) & dead}
    actual = hand.hole[villain]
    lines: list[str] = []
    checkpoints: list[Checkpoint] = []
    acted_this_street = False
    for action in [a for a in hand.log if a.kind != "post"]:
        if action.player == villain:
            acted_this_street = True
            for combo in list(weight):
                if set(combo) & set(replay.board):
                    del weight[combo]
                    continue
                if weight[combo] == 0:
                    continue
                replay.hole[villain] = combo
                p = sum(prob for kind, _, prob in model.options(replay) if kind == action.kind)
                weight[combo] *= p
            replay.hole[villain] = actual
        street = replay.street_name
        lines.append(f"{street.capitalize()}: {describe(action, names, hero)}")
        replay.act(action.kind, action.to if action.kind in ("bet", "raise") else None)
        if (replay.street_name != street or replay.finished) and acted_this_street:
            board = list(replay.board[: {"preflop": 0, "flop": 3, "turn": 4, "river": 5}[street]])
            live = {c: w for c, w in weight.items() if not set(c) & set(board)}
            per_class: dict[str, float] = defaultdict(float)
            counts: dict[str, int] = defaultdict(int)
            for combo, w in live.items():
                hand_class = class_of_combo(*combo)
                per_class[hand_class] += w
                counts[hand_class] += 1
            checkpoints.append(
                Checkpoint(street, board, list(lines), dict(per_class), dict(counts))
            )
            acted_this_street = False
    return checkpoints


def deal_read(rng: random.Random) -> ReadHand:
    """A hand worth reading: it reaches the turn and the villain never folds."""
    # Pick the style first: retrying styles would favour the ones that rarely fold.
    style = STYLES[rng.choice(sorted(STYLES))]
    while True:
        villain = rng.randrange(2)
        seed = rng.randrange(1 << 30)
        hand = _play(style, villain, rng.randrange(2), seed, rng)
        folded = any(a.kind == "fold" and a.player == villain for a in hand.log)
        if folded or len(hand.board) < 4:
            continue
        checkpoints = _checkpoints(style, villain, hand, seed)
        if len(checkpoints) >= MIN_CHECKPOINTS and all(
            sum(c.weights.values()) > 0 for c in checkpoints
        ):
            return ReadHand(style, villain, hand, seed, checkpoints)


def _grid(values: dict[str, float]) -> list[list[float]]:
    return [[round(values.get(grid_class(r, c), 0.0), 3) for c in range(13)] for r in range(13)]


def _examples(classes: list[str], count: int = 6) -> list[str]:
    """A few members in grid order (AA, AKs, AQs...), which reads better than ties in any order."""
    members = set(classes)
    return [c for c in ALL_CLASSES if c in members][:count]


class HandReadingDrill(Drill):
    key = "hand-reading"
    title = "Read the bot's range"
    concept = "hand-reading"
    tier = 4
    description = "Watch a hand and narrow the villain's range after every street."

    def make_question(self, rng: random.Random) -> Question:
        read = deal_read(rng)
        hero = 1 - read.villain
        position = "the button" if read.hand.button == read.villain else "the big blind"
        actual = class_of_combo(*read.hand.hole[read.villain])
        question: Question | None = None
        total = len(read.checkpoints)
        for index in range(total - 1, -1, -1):
            point = read.checkpoints[index]
            best, best_range = best_match(point.weights, point.combos)
            last = index == total - 1
            lines = [
                "Darker cells are hands the bot plays this way more often.",
                f"A range that scores best here has {len(best_range)} hand classes, "
                f"for example {', '.join(_examples(best_range))}.",
            ]
            if last:
                lines.append(
                    f"{read.style.name} actually had {pretty_cards(read.hand.hole[read.villain])}."
                )
            question = Question(
                drill=self.key,
                concept=self.concept,
                prompt=f"After the {point.street}: which hands can {read.style.name} have? "
                "Remove what its actions rule out, then lock in.",
                kind=AnswerKind.RANGE,
                answer=round(best * 100, 1),
                unit="%",
                payload={
                    "hole": card_list(read.hand.hole[hero]),
                    **({"board": card_list(point.board)} if point.board else {}),
                    "lines": point.lines,
                    "facts": [
                        {"label": "Villain", "value": f"{read.style.name} on {position}"},
                        {"label": "Step", "value": f"{index + 1} of {total}"},
                    ],
                },
                explanation=tuple(lines),
                highlight=tuple(card_list(read.hand.hole[read.villain])) if last else (),
                reveal={
                    "weights": _grid(point.density()),
                    "hand": actual if last else None,
                    "villain": read.style.name,
                    "class_weights": point.weights,
                    "class_combos": point.combos,
                    "best": best,
                    "label": f"{read.style.name}'s real range",
                },
                follow_up=question,
            )
        assert question is not None
        return question
