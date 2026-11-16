"""Spaced repetition and the daily session.

Each drill has one FSRS card. Once a card is due, the next ``BLOCK_SIZE`` answers for that drill
(from the daily session or free practice) are graded together into a single review. That keeps a
burst of quick answers from inflating the interval.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fsrs import Card, Rating, Scheduler
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from holdem.curriculum import CONCEPTS, CONCEPTS_BY_ID
from holdem.db import Attempt, ReviewCard, to_naive_utc
from holdem.drills.registry import ALL_DRILLS, DRILLS

BLOCK_SIZE = 3
SLOW_MS = 25_000
QUESTIONS_PER_DRILL = 3
MAX_DUE = 5
NEW_PER_DAY = 2
EXTRA_DRILLS = 2
MASTERY_WINDOW = 20
MASTERED_AT = 0.85
MASTERED_MIN_ATTEMPTS = 10

SCHEDULER = Scheduler(enable_fuzzing=False)
NEW_CARD_DUE = datetime(2000, 1, 1, tzinfo=UTC)


def _naive(moment: datetime) -> datetime:
    return to_naive_utc(moment)


def rating_for(results: Sequence[tuple[bool, int | None]]) -> Rating:
    """Rate a block of (correct, elapsed ms) answers."""
    correct = sum(ok for ok, _ in results)
    if correct <= len(results) - 2:
        return Rating.Again
    if correct < len(results):
        return Rating.Hard
    times = sorted(ms for _, ms in results if ms is not None)
    if times and times[len(times) // 2] > SLOW_MS:
        return Rating.Hard
    return Rating.Good


def load_card(session: Session, drill: str) -> Card | None:
    row = session.get(ReviewCard, drill)
    return Card.from_json(row.card) if row else None


def save_card(session: Session, drill: str, card: Card, now: datetime) -> None:
    """Insert or update atomically, so two concurrent answers cannot both insert the card."""
    data = card.to_json()
    statement = (
        sqlite_insert(ReviewCard)
        .values(drill=drill, card=data, created_at=_naive(now))
        .on_conflict_do_update(index_elements=[ReviewCard.drill], set_={"card": data})
    )
    session.execute(statement)
    session.commit()
    session.expire_all()


@dataclass(frozen=True)
class ReviewOutcome:
    rating: Rating
    due: datetime

    def public(self) -> dict[str, Any]:
        return {"rating": self.rating.name.lower(), "due": self.due.isoformat()}


def on_attempt(session: Session, drill: str, now: datetime) -> ReviewOutcome | None:
    """Review the drill's card if it is due and a full block of answers has come in."""
    stored = load_card(session, drill)
    card = stored or Card(due=NEW_CARD_DUE)
    if card.due > now:
        return None
    rows = session.scalars(
        select(Attempt)
        .where(Attempt.drill == drill, Attempt.created_at >= _naive(card.due))
        .order_by(Attempt.id.desc())
        .limit(BLOCK_SIZE)
    ).all()
    if len(rows) < BLOCK_SIZE:
        if stored is None:
            save_card(session, drill, card, now)  # the drill is now started
        return None
    rating = rating_for([(r.correct, r.elapsed_ms) for r in rows])
    card, _ = SCHEDULER.review_card(card, rating, now)
    save_card(session, drill, card, now)
    return ReviewOutcome(rating, card.due)


@dataclass(frozen=True)
class ConceptProgress:
    concept: str
    attempts: int
    mastery: float  # smoothed recent accuracy, (correct + 1) / (n + 2)
    status: str  # "new", "learning" or "mastered"

    def public(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "attempts": self.attempts,
            "mastery": round(self.mastery, 3),
            "status": self.status,
        }


def concept_progress(session: Session) -> dict[str, ConceptProgress]:
    result = {}
    for concept in CONCEPTS:
        rows = (
            session.scalars(
                select(Attempt.correct)
                .where(Attempt.drill.in_(concept.drills))
                .order_by(Attempt.id.desc())
                .limit(MASTERY_WINDOW)
            ).all()
            if concept.drills
            else []
        )
        n, correct = len(rows), sum(rows)
        mastery = (correct + 1) / (n + 2)
        if n == 0:
            status = "new"
        elif n >= MASTERED_MIN_ATTEMPTS and mastery >= MASTERED_AT:
            status = "mastered"
        else:
            status = "learning"
        result[concept.id] = ConceptProgress(concept.id, n, mastery, status)
    return result


def pick_new_drills(
    progress: dict[str, ConceptProgress], started_drills: set[str], limit: int
) -> list[str]:
    """New drills whose prerequisites are started, in tier order.

    A drill picked here counts as started, so prerequisites can be introduced and followed up in
    the same session.
    """
    started = {cid for cid, p in progress.items() if p.status != "new"}
    candidates = [
        d for d in sorted(ALL_DRILLS, key=lambda d: d.tier) if d.key not in started_drills
    ]
    picked: list[str] = []
    # Repeat passes: a prerequisite may sit later in the same tier.
    while len(picked) < limit:
        ready = next(
            (
                d
                for d in candidates
                if all(p in started for p in CONCEPTS_BY_ID[d.concept].prerequisites)
            ),
            None,
        )
        if ready is None:
            break
        picked.append(ready.key)
        candidates.remove(ready)
        started.add(ready.concept)
    return picked


@dataclass(frozen=True)
class DailyPlan:
    due: list[str]
    new: list[str]
    extra: list[str]
    queue: list[str]

    def public(self) -> dict[str, Any]:
        return {"due": self.due, "new": self.new, "extra": self.extra, "queue": self.queue}


def interleave(drills: Sequence[str], per_drill: int) -> list[str]:
    """Round-robin: A B C A B C ... so the same drill never repeats back to back."""
    return [drill for _ in range(per_drill) for drill in drills]


def daily_plan(session: Session, now: datetime) -> DailyPlan:
    rows = session.scalars(select(ReviewCard)).all()
    cards = {r.drill: Card.from_json(r.card) for r in rows if r.drill in DRILLS}
    due = sorted((d for d, c in cards.items() if c.due <= now), key=lambda d: cards[d].due)
    due = due[:MAX_DUE]

    day_start = _naive(now) - timedelta(hours=24)
    started_recently = sum(1 for r in rows if r.created_at >= day_start)
    new = pick_new_drills(
        concept_progress(session), set(cards), max(0, NEW_PER_DAY - started_recently)
    )

    extra: list[str] = []
    if not due and not new and cards:
        by_recall = sorted(cards, key=lambda d: SCHEDULER.get_card_retrievability(cards[d], now))
        extra = by_recall[:EXTRA_DRILLS]
    return DailyPlan(due, new, extra, interleave([*due, *new, *extra], QUESTIONS_PER_DRILL))


def card_summary(session: Session, now: datetime) -> dict[str, dict[str, Any]]:
    """Per-drill scheduling state for the curriculum view."""
    summary = {}
    for row in session.scalars(select(ReviewCard)).all():
        card = Card.from_json(row.card)
        reviewed = card.last_review is not None
        summary[row.drill] = {
            "due": card.due.isoformat() if reviewed else None,
            "is_due": card.due <= now,
            "recall": round(SCHEDULER.get_card_retrievability(card, now), 3) if reviewed else None,
        }
    return summary
