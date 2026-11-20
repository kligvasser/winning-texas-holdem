"""SQLite persistence: every graded answer is logged for stats, leaks and scheduling."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, String, create_engine, event, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from holdem.engine.play import SIX_MAX  # older heads-up hands are kept but not shown
from holdem.table_stats import table_report

DEFAULT_DATA_DIR = Path("data")


def to_naive_utc(moment: datetime) -> datetime:
    """Storage form for timestamps. A naive input is taken to be UTC already."""
    if moment.tzinfo is None:
        return moment
    return moment.astimezone(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(index=True)  # naive UTC
    drill: Mapped[str] = mapped_column(String(64), index=True)
    concept: Mapped[str] = mapped_column(String(64), index=True)
    question: Mapped[str]  # JSON: prompt and payload
    response: Mapped[str]
    expected: Mapped[str]
    correct: Mapped[bool]
    error: Mapped[float | None]
    elapsed_ms: Mapped[int | None]


class ReviewCard(Base):
    """Spaced-repetition state for one drill, stored as py-fsrs JSON."""

    __tablename__ = "review_cards"

    drill: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime]  # naive UTC
    card: Mapped[str]


class PlayedHand(Base):
    """A finished hand against a bot, with its review, stored as JSON."""

    __tablename__ = "played_hands"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(index=True)  # naive UTC
    style: Mapped[str] = mapped_column(String(32))
    net_bb: Mapped[float]
    worst_loss_bb: Mapped[float]
    record: Mapped[str]


def database_url() -> str:
    data_dir = Path(os.environ.get("HOLDEM_DATA_DIR", DEFAULT_DATA_DIR))
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)  # private to this user
    return f"sqlite:///{data_dir / 'holdem.sqlite'}"


def make_engine(url: str | None = None) -> Engine:
    engine = create_engine(url or database_url())

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


def record_attempt(
    session: Session,
    *,
    drill: str,
    concept: str,
    question: dict[str, Any],
    response: float | str,
    expected: float | str,
    correct: bool,
    error: float | None,
    elapsed_ms: int | None,
    created_at: datetime | None = None,
) -> Attempt:
    attempt = Attempt(
        created_at=to_naive_utc(created_at or datetime.now(UTC)),
        drill=drill,
        concept=concept,
        question=json.dumps(question),
        response=str(response),
        expected=str(expected),
        correct=correct,
        error=error,
        elapsed_ms=elapsed_ms,
    )
    session.add(attempt)
    session.commit()
    return attempt


@dataclass(frozen=True)
class DrillStats:
    drill: str
    attempts: int
    correct: int
    mean_abs_error: float | None
    bias: float | None  # mean signed error: positive means you overestimate
    mean_ms: float | None

    @property
    def accuracy(self) -> float:
        return self.correct / self.attempts

    def public(self) -> dict[str, Any]:
        return {
            "drill": self.drill,
            "attempts": self.attempts,
            "correct": self.correct,
            "accuracy": round(self.accuracy, 4),
            "mean_abs_error": self.mean_abs_error,
            "bias": self.bias,
            "mean_ms": self.mean_ms,
        }


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def drill_stats(session: Session) -> list[DrillStats]:
    rows = session.scalars(select(Attempt).order_by(Attempt.id)).all()
    grouped: dict[str, list[Attempt]] = defaultdict(list)
    for row in rows:
        grouped[row.drill].append(row)
    result = []
    for drill, attempts in sorted(grouped.items()):
        errors = [a.error for a in attempts if a.error is not None]
        times = [float(a.elapsed_ms) for a in attempts if a.elapsed_ms is not None]
        result.append(
            DrillStats(
                drill=drill,
                attempts=len(attempts),
                correct=sum(a.correct for a in attempts),
                mean_abs_error=_mean([abs(e) for e in errors]),
                bias=_mean(errors),
                mean_ms=_mean(times),
            )
        )
    return result


def save_hand(session: Session, record: dict[str, Any], now: datetime) -> PlayedHand:
    losses = [d["loss_bb"] for d in record["decisions"]]
    row = PlayedHand(
        created_at=to_naive_utc(now),
        style=record["style"],
        net_bb=record["net_bb"],
        worst_loss_bb=max(losses, default=0.0),
        record=json.dumps(record),
    )
    session.add(row)
    session.commit()
    return row


def hand_summary(row: PlayedHand) -> dict[str, Any]:
    record = json.loads(row.record)
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat(),
        "style": row.style,
        "net_bb": row.net_bb,
        "worst_loss_bb": row.worst_loss_bb,
        "hole": record["hand"]["hole"][0],
        "board": record["hand"]["board"],
        "mistakes": sum(d["verdict"] == "mistake" for d in record["decisions"]),
    }


def play_stats(session: Session) -> dict[str, Any]:
    """Your numbers across stored hands: results, frequencies by position and leaks."""
    rows = session.scalars(select(PlayedHand).where(PlayedHand.style == SIX_MAX)).all()
    n = len(rows)
    net = round(sum(r.net_bb for r in rows), 2)
    return {
        "hands": n,
        "net_bb": net,
        "bb_per_100": round(net / n * 100, 1) if n else None,
        **table_report([json.loads(r.record) for r in rows]),
    }
