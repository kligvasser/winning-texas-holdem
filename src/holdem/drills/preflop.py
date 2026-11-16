"""Preflop chart drills: opening ranges and facing a raise, sampled near range boundaries."""

from __future__ import annotations

import random

from holdem.core.ranges import ALL_CLASSES, combos_of_class
from holdem.drills.base import AnswerKind, Drill, Question, card_list
from holdem.preflop import SOURCE, SPOTS, Spot

BOUNDARY_SHARE = 0.75


def sample_class(spot: Spot, rng: random.Random) -> str:
    """Mostly hands next to a range edge; trivially in or out hands teach little."""
    boundary = [c for c in ALL_CLASSES if spot.is_boundary(c)]
    pool = boundary if rng.random() < BOUNDARY_SHARE else list(ALL_CLASSES)
    return rng.choice(pool)


class PreflopDrill(Drill):
    def __init__(self, kind: str, key: str, title: str, concept: str, description: str) -> None:
        self.kind = kind
        self.key = key
        self.title = title
        self.concept = concept
        self.tier = 2
        self.description = description
        self.speed = True
        self.spots = tuple(s for s in SPOTS if s.kind == kind)

    def make_question(self, rng: random.Random) -> Question:
        spot = rng.choice(self.spots)
        hand_class = sample_class(spot, rng)
        combo = rng.choice(combos_of_class(hand_class))
        action = spot.action_for(hand_class)
        share = spot.frequency(action)
        return Question(
            drill=self.key,
            concept=self.concept,
            prompt=f"{spot.position}: {spot.situation} What do you do?",
            kind=AnswerKind.CHOICE,
            answer=action,
            choices=spot.choices,
            payload={
                "hole": card_list(combo),
                "position": spot.position,
                "situation": spot.situation,
                "spot": spot.id,
            },
            explanation=(
                f"{hand_class}: {action.lower()} in this chart "
                f"({action.lower()} is {share:.0%} of all hands here).",
                spot.note,
                f"Source: {SOURCE}.",
            ),
            reveal={"grid": spot.grid(), "hand": hand_class, "choices": list(spot.choices)},
        )


PREFLOP_DRILLS: tuple[Drill, ...] = (
    PreflopDrill(
        "open",
        "preflop-open",
        "Open or fold",
        "preflop-ranges",
        "Folded to you: raise or fold from each seat, mostly hands near the range edge.",
    ),
    PreflopDrill(
        "defend",
        "preflop-defend",
        "Facing a raise",
        "facing-a-raise",
        "Someone opened: 3-bet, call or fold.",
    ),
)
