"""Scoring a painted range against a weighted "true" range (used by the hand-reading drill)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from holdem.core.ranges import ALL_CLASSES


def range_match(painted: Iterable[str], weights: dict[str, float], combos: dict[str, int]) -> float:
    """Overlap between a uniform painted range and the weighted true range (0 to 1)."""
    chosen = [c for c in set(painted) if combos.get(c, 0)]
    painted_combos = sum(combos[c] for c in chosen)
    total = sum(weights.values())
    if not painted_combos or not total:
        return 0.0
    return sum(min(combos[c] / painted_combos, weights.get(c, 0.0) / total) for c in chosen)


def best_match(weights: dict[str, float], combos: dict[str, int]) -> tuple[float, list[str]]:
    """The best score any painted range can reach, and that range.

    Adding classes from most to least likely per combo, the best range is one of the prefixes.
    """
    ordered = sorted(
        (c for c in weights if combos.get(c, 0) and weights[c] > 0),
        key=lambda c: -weights[c] / combos[c],
    )
    best, best_size = 0.0, 0
    for size in range(1, len(ordered) + 1):
        score = range_match(ordered[:size], weights, combos)
        if score > best:
            best, best_size = score, size
    return best, ordered[:best_size]


def grade_range(painted: list[str], reveal: dict[str, Any]) -> tuple[float, float, list[str]]:
    """Score a painted range against a reading question's reveal data, with feedback lines."""
    weights: dict[str, float] = reveal["class_weights"]
    combos: dict[str, int] = reveal["class_combos"]
    best: float = reveal["best"]
    score = range_match(painted, weights, combos)
    chosen = set(painted)
    total = sum(weights.values()) or 1.0
    densest = max((weights[c] / combos[c] for c in weights if combos.get(c)), default=1.0)
    missed = sorted(
        (c for c in weights if c not in chosen and weights[c] / total > 0.01),
        key=lambda c: (-weights[c], ALL_CLASSES.index(c)),  # ties: strongest hands first
    )
    unlikely = [
        c
        for c in ALL_CLASSES
        if c in chosen and combos.get(c) and weights.get(c, 0.0) / combos[c] < 0.05 * densest
    ]
    lines = [
        f"Your range matched {score:.0%} of {reveal['villain']}'s real range; the best possible "
        f"is {best:.0%}."
    ]
    if missed:
        lines.append(f"Likely hands you removed: {', '.join(missed[:6])}.")
    if unlikely:
        lines.append(
            f"You kept {len(unlikely)} hand classes it almost never plays this way, "
            f"such as {', '.join(unlikely[:6])}."
        )
    if not chosen:
        lines.append("You removed every hand: keep at least the ones it could still hold.")
    return score, best, lines
