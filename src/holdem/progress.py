"""Practice activity: daily streaks, today's count and a day-by-day history for the heatmap."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from holdem.db import Attempt

HISTORY_DAYS = 84  # twelve weeks


def _streak_ending(days: set[date], end: date) -> int:
    streak = 0
    while end - timedelta(days=streak) in days:
        streak += 1
    return streak


def _run_length(days: set[date], start: date) -> int:
    length = 0
    while start + timedelta(days=length) in days:
        length += 1
    return length


def _best_streak(days: set[date]) -> int:
    starts = [d for d in days if d - timedelta(days=1) not in days]
    return max((_run_length(days, d) for d in starts), default=0)


@dataclass(frozen=True)
class Activity:
    today: date
    answered_today: int
    correct_today: int
    streak: int  # consecutive days practised, ending today (or yesterday if not yet today)
    best_streak: int
    total: int
    history: list[tuple[date, int, int]]  # (day, answers, correct), oldest first

    def public(self) -> dict[str, Any]:
        return {
            "today": self.today.isoformat(),
            "answered_today": self.answered_today,
            "correct_today": self.correct_today,
            "practiced_today": self.answered_today > 0,
            "streak": self.streak,
            "best_streak": self.best_streak,
            "total": self.total,
            "history": [
                {"date": d.isoformat(), "answers": n, "correct": c} for d, n, c in self.history
            ],
        }


def activity(session: Session, now: datetime, tz: tzinfo) -> Activity:
    """Summarise practice by local calendar day in time zone ``tz``."""
    rows = session.execute(select(Attempt.created_at, Attempt.correct)).all()
    answers: Counter[date] = Counter()
    correct: Counter[date] = Counter()
    for created_at, ok in rows:
        day = created_at.replace(tzinfo=UTC).astimezone(tz).date()
        answers[day] += 1
        correct[day] += ok
    today = now.astimezone(tz).date()
    days = set(answers)
    streak = _streak_ending(days, today) or _streak_ending(days, today - timedelta(days=1))
    history = [
        (d, answers[d], correct[d])
        for d in (today - timedelta(days=i) for i in range(HISTORY_DAYS - 1, -1, -1))
    ]
    return Activity(
        today=today,
        answered_today=answers[today],
        correct_today=correct[today],
        streak=streak,
        best_streak=_best_streak(days),
        total=len(rows),
        history=history,
    )
