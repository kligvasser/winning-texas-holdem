from datetime import UTC, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from holdem.db import record_attempt
from holdem.progress import HISTORY_DAYS, activity

NOW = datetime(2026, 11, 16, 12, tzinfo=UTC)


def log(session, when, correct=True):
    record_attempt(
        session,
        drill="pot-odds",
        concept="pot-odds",
        question={},
        response="1",
        expected="1",
        correct=correct,
        error=None,
        elapsed_ms=None,
        created_at=when,
    )


def test_empty_history(engine):
    with Session(engine) as session:
        result = activity(session, NOW, UTC)
    assert result.streak == 0
    assert result.best_streak == 0
    assert result.total == 0
    assert len(result.history) == HISTORY_DAYS
    assert result.history[-1] == (NOW.date(), 0, 0)
    assert result.public()["practiced_today"] is False


def test_streaks_and_today(engine):
    with Session(engine) as session:
        for days_ago in (0, 1, 2, 5, 6, 7, 8):
            log(session, NOW - timedelta(days=days_ago))
        log(session, NOW, correct=False)
        result = activity(session, NOW, UTC)
    assert result.answered_today == 2
    assert result.correct_today == 1
    assert result.streak == 3
    assert result.best_streak == 4
    assert result.total == 8
    public = result.public()
    assert public["history"][-1] == {"date": "2026-11-16", "answers": 2, "correct": 1}
    assert public["practiced_today"] is True


def test_streak_survives_until_you_practise_today(engine):
    with Session(engine) as session:
        log(session, NOW - timedelta(days=1))
        log(session, NOW - timedelta(days=2))
        assert activity(session, NOW, UTC).streak == 2
        assert activity(session, NOW + timedelta(days=1), UTC).streak == 0


def test_days_follow_the_local_time_zone(engine):
    late_evening_utc = datetime(2026, 11, 15, 23, 30, tzinfo=UTC)
    with Session(engine) as session:
        log(session, late_evening_utc)
        in_utc = activity(session, NOW, UTC)
        in_israel = activity(session, NOW, timezone(timedelta(hours=2)))
    assert in_utc.history[-2][1] == 1  # 15 November
    assert in_israel.history[-1][1] == 1  # already 16 November locally
