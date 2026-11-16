"""Baseline preflop charts for 6-max cash at 100bb, and the logic to query and grade them.

These ranges are a self-authored baseline in the shape of modern charts (wider on the button,
tighter up front, a linear-ish 3-bet value region plus suited-ace and suited-connector bluffs).
They are not solver output. Open sizes are assumed at 2.5bb (3bb from the small blind).

Each spot lists its actions in priority order; a hand takes the first action whose range contains
it and folds otherwise.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property
from typing import Any

from holdem.core.ranges import (
    ALL_CLASSES,
    HandClass,
    Range,
    class_combo_count,
    class_grid_position,
    grid_class,
)

SOURCE = "Baseline chart (self-authored, not solver output)"
FOLD = "Fold"


@dataclass(frozen=True)
class Spot:
    id: str
    position: str
    situation: str
    kind: str  # "open" or "defend"
    actions: tuple[tuple[str, str], ...]  # (action label, range notation), priority order
    note: str

    @cached_property
    def ranges(self) -> dict[str, Range]:
        return {label: Range.parse(text) for label, text in self.actions}

    @property
    def choices(self) -> tuple[str, ...]:
        return (*(label for label, _ in self.actions), FOLD)

    def action_for(self, hand_class: HandClass) -> str:
        for label, _ in self.actions:
            if hand_class in self.ranges[label]:
                return label
        return FOLD

    @cached_property
    def chart(self) -> dict[HandClass, str]:
        return {c: self.action_for(c) for c in ALL_CLASSES}

    def frequency(self, action: str) -> float:
        """Share of all 1,326 combos that take ``action``."""
        combos = sum(class_combo_count(c) for c, a in self.chart.items() if a == action)
        return combos / 1326

    def grid(self) -> list[list[str]]:
        return [[self.chart[grid_class(r, c)] for c in range(13)] for r in range(13)]

    def is_boundary(self, hand_class: HandClass) -> bool:
        """True when a neighbouring grid cell takes a different action."""
        row, col = class_grid_position(hand_class)
        action = self.chart[hand_class]
        neighbours = [
            grid_class(r, c)
            for r in range(max(row - 1, 0), min(row + 2, 13))
            for c in range(max(col - 1, 0), min(col + 2, 13))
            if (r, c) != (row, col)
        ]
        return any(self.chart[n] != action for n in neighbours)

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "position": self.position,
            "situation": self.situation,
            "kind": self.kind,
            "choices": list(self.choices),
            "note": self.note,
            "source": SOURCE,
            "grid": self.grid(),
            "frequencies": {a: round(self.frequency(a), 4) for a in self.choices},
        }


SPOTS: tuple[Spot, ...] = (
    Spot(
        id="utg-open",
        position="UTG",
        situation="Folded to you under the gun.",
        kind="open",
        actions=(("Raise", "22+, A2s+, K9s+, Q9s+, J9s+, T9s, 98s, 87s, 76s, 65s, ATo+, KJo+"),),
        note="Five players act after you, so open only hands that play well when called or "
        "3-bet: pairs, suited aces, strong broadways and the best suited connectors.",
    ),
    Spot(
        id="hj-open",
        position="HJ",
        situation="Folded to you in the hijack.",
        kind="open",
        actions=(
            (
                "Raise",
                "22+, A2s+, K7s+, Q9s+, J9s+, T8s+, 98s, 87s, 76s, 65s, 54s, A9o+, KTo+, QTo+, JTo",
            ),
        ),
        note="One fewer player behind than UTG: add weaker suited kings, more suited "
        "connectors and offsuit broadways.",
    ),
    Spot(
        id="co-open",
        position="CO",
        situation="Folded to you in the cutoff.",
        kind="open",
        actions=(
            (
                "Raise",
                "22+, A2s+, K5s+, Q8s+, J8s+, T8s+, 97s+, 86s+, 75s+, 65s, 54s, A8o+, A5o, "
                "KTo+, QTo+, JTo",
            ),
        ),
        note="Only the button and blinds remain. Open most suited hands with some "
        "playability and offsuit aces down to about A8.",
    ),
    Spot(
        id="btn-open",
        position="BTN",
        situation="Folded to you on the button.",
        kind="open",
        actions=(
            (
                "Raise",
                "22+, A2s+, K2s+, Q5s+, J7s+, T7s+, 96s+, 85s+, 74s+, 64s+, 53s+, 43s, A2o+, "
                "K8o+, Q9o+, J9o+, T9o, 98o, 87o",
            ),
        ),
        note="You will have position on both blinds for the rest of the hand: open close to "
        "half of all hands, including every suited king and every ace.",
    ),
    Spot(
        id="sb-open",
        position="SB",
        situation="Folded to you in the small blind (raise or fold).",
        kind="open",
        actions=(
            (
                "Raise",
                "22+, A2s+, K4s+, Q6s+, J7s+, T7s+, 96s+, 86s+, 75s+, 64s+, 54s, A4o+, K9o+, "
                "Q9o+, J9o+, T9o",
            ),
        ),
        note="Only the big blind is left, but you will be out of position. A raise-or-fold "
        "strategy keeps it simple; open a little tighter than the button.",
    ),
    Spot(
        id="bb-vs-btn",
        position="BB",
        situation="The button opens to 2.5bb, the small blind folds.",
        kind="defend",
        actions=(
            ("3-bet", "TT+, AQs+, AKo, A5s-A3s, K9s, T8s, 76s, 65s"),
            (
                "Call",
                "22+, A2s+, K2s+, Q2s+, J4s+, T6s+, 96s+, 85s+, 74s+, 63s+, 53s+, 43s, A2o+, "
                "K7o+, Q8o+, J8o+, T8o+, 98o, 87o",
            ),
        ),
        note="You close the action and need only about 27% equity to call 1.5bb into 4bb, so "
        "defend very wide. 3-bet strong hands for value and some suited hands with "
        "blockers or playability as bluffs.",
    ),
    Spot(
        id="bb-vs-co",
        position="BB",
        situation="The cutoff opens to 2.5bb, the others fold.",
        kind="defend",
        actions=(
            ("3-bet", "JJ+, AQs+, AKo, A5s-A4s, K9s, 76s"),
            (
                "Call",
                "22+, A2s+, K2s+, Q5s+, J6s+, T6s+, 96s+, 85s+, 75s+, 64s+, 54s, A7o+, K9o+, "
                "Q9o+, J9o+, T9o",
            ),
        ),
        note="The cutoff's range is stronger than the button's, so defend a bit tighter, "
        "especially with offsuit hands.",
    ),
    Spot(
        id="bb-vs-utg",
        position="BB",
        situation="UTG opens to 2.5bb, the others fold.",
        kind="defend",
        actions=(
            ("3-bet", "QQ+, AKs, AKo, A5s"),
            (
                "Call",
                "22+, A2s+, K8s+, Q9s+, J9s+, T8s+, 97s+, 86s+, 75s+, 65s, 54s, ATo+, KJo+, QJo",
            ),
        ),
        note="An early-position range is strong: fold most offsuit hands and keep the 3-bet "
        "range mostly to premium value.",
    ),
    Spot(
        id="btn-vs-co",
        position="BTN",
        situation="The cutoff opens to 2.5bb.",
        kind="defend",
        actions=(
            ("3-bet", "TT+, AJs+, KQs, AQo+, A5s-A4s, K9s, 65s"),
            ("Call", "22+, A9s+, KTs+, QTs+, JTs, T9s, 98s, 87s, 76s, AJo, KQo"),
        ),
        note="With position you can flat some hands, but the blinds behind can squeeze, so "
        "lean towards 3-betting rather than calling with marginal hands.",
    ),
    Spot(
        id="sb-vs-btn",
        position="SB",
        situation="The button opens to 2.5bb (3-bet or fold).",
        kind="defend",
        actions=(("3-bet", "88+, A8s+, A5s-A4s, KTs+, QTs+, JTs, T9s, ATo+, KJo+"),),
        note="Calling from the small blind invites the big blind in and leaves you out of "
        "position; a 3-bet-or-fold strategy is simpler and close to as good.",
    ),
)

SPOTS_BY_ID: dict[str, Spot] = {s.id: s for s in SPOTS}


@dataclass(frozen=True)
class PaintResult:
    correct: tuple[HandClass, ...]
    missed: tuple[HandClass, ...]  # in the chart's range but not painted
    extra: tuple[HandClass, ...]  # painted but not in the chart's range
    combos_wrong: int
    accuracy: float  # share of all combos classified correctly

    def public(self) -> dict[str, Any]:
        return {
            "correct": list(self.correct),
            "missed": list(self.missed),
            "extra": list(self.extra),
            "combos_wrong": self.combos_wrong,
            "accuracy": round(self.accuracy, 4),
        }


def grade_paint(spot: Spot, action: str, painted: Iterable[HandClass]) -> PaintResult:
    """Compare a painted set of hand classes with the classes that take ``action`` in the chart."""
    if action not in spot.choices or action == FOLD:
        raise ValueError(f"{action!r} is not a paintable action for {spot.id}")
    target = {c for c, a in spot.chart.items() if a == action}
    painted_set = set(Range.of(painted))
    missed = sorted(target - painted_set, key=ALL_CLASSES.index)
    extra = sorted(painted_set - target, key=ALL_CLASSES.index)
    correct = sorted(target & painted_set, key=ALL_CLASSES.index)
    wrong = sum(class_combo_count(c) for c in [*missed, *extra])
    return PaintResult(
        correct=tuple(correct),
        missed=tuple(missed),
        extra=tuple(extra),
        combos_wrong=wrong,
        accuracy=1 - wrong / 1326,
    )
