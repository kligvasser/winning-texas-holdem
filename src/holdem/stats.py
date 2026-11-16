"""Leak reports built from the answer log."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from holdem.core.cards import parse_card
from holdem.core.ranges import class_of_combo
from holdem.db import Attempt
from holdem.preflop import SPOTS_BY_ID

PREFLOP_DRILLS = ("preflop-open", "preflop-defend")
WORST_HANDS = 5


@dataclass(frozen=True)
class SpotLeak:
    spot: str
    attempts: int
    correct: int
    missed_hands: tuple[tuple[str, int], ...]  # (hand class, times wrong), most frequent first

    @property
    def accuracy(self) -> float:
        return self.correct / self.attempts

    def public(self) -> dict[str, Any]:
        spot = SPOTS_BY_ID[self.spot]
        return {
            "spot": self.spot,
            "position": spot.position,
            "situation": spot.situation,
            "attempts": self.attempts,
            "correct": self.correct,
            "accuracy": round(self.accuracy, 4),
            "missed_hands": [{"hand": h, "count": n} for h, n in self.missed_hands],
        }


def preflop_leaks(session: Session) -> list[SpotLeak]:
    """Accuracy per preflop spot, worst first, with the hands you miss most."""
    rows = session.scalars(select(Attempt).where(Attempt.drill.in_(PREFLOP_DRILLS))).all()
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    misses: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        payload = json.loads(row.question).get("payload", {})
        spot = payload.get("spot")
        if spot not in SPOTS_BY_ID:
            continue
        totals[spot][0] += 1
        if row.correct:
            totals[spot][1] += 1
        else:
            a, b = (parse_card(c) for c in payload["hole"])
            misses[spot][class_of_combo(a, b)] += 1
    leaks = [
        SpotLeak(spot, n, ok, tuple(misses[spot].most_common(WORST_HANDS)))
        for spot, (n, ok) in totals.items()
    ]
    return sorted(leaks, key=lambda leak: (leak.accuracy, -leak.attempts))
