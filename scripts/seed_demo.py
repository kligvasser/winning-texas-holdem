"""Fill a database with a plausible ten-day practice history (for screenshots and demos).

Usage: uv run python scripts/seed_demo.py data/demo
Then:  HOLDEM_DATA_DIR=data/demo uv run python -m holdem
"""

from __future__ import annotations

import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from holdem.db import make_engine, record_attempt
from holdem.drills.base import AnswerKind
from holdem.drills.math_lab import PreflopEquityDrill
from holdem.drills.registry import DRILLS
from holdem.scheduler import on_attempt

# drill -> (answers, chance of a correct answer)
HISTORY = {
    "hand-ranking": (12, 0.95),
    "showdown": (12, 0.85),
    "nuts": (9, 0.7),
    "dealt-odds": (9, 0.8),
    "outs": (12, 0.65),
    "draw-odds": (12, 0.75),
    "pot-odds": (15, 0.85),
    "call-or-fold": (9, 0.75),
    "preflop-equity": (9, 0.6),
    "flop-odds": (6, 0.65),
    "preflop-open": (24, 0.7),
    "preflop-defend": (15, 0.6),
}


def main(data_dir: str) -> None:
    path = Path(data_dir)
    path.mkdir(parents=True, exist_ok=True)
    for old in path.glob("holdem.sqlite*"):  # only ever the database, never the whole folder
        old.unlink()
    PreflopEquityDrill.samples = 3000
    rng = random.Random(7)
    engine = make_engine(f"sqlite:///{path / 'holdem.sqlite'}")
    start = datetime.now(UTC) - timedelta(days=10)
    with Session(engine) as session:
        for day in range(10):
            for key, (count, skill) in HISTORY.items():
                drill = DRILLS[key]
                for i in range(count // 10 + (day < count % 10)):
                    now = start + timedelta(days=day, minutes=5 * i + rng.randrange(60))
                    question = drill.make_question(random.Random(rng.randrange(1 << 30)))
                    correct = rng.random() < min(0.98, skill + day * 0.02)
                    if question.kind is AnswerKind.CHOICE:
                        wrong = [c for c in question.choices if c != question.answer]
                        response = question.answer if correct else rng.choice(wrong)
                        error = None
                    else:
                        expected = float(question.answer)
                        miss = question.tolerance + rng.uniform(1, 6)
                        offset = rng.uniform(-question.tolerance, question.tolerance)
                        error = round(offset if correct else rng.choice((-1, 1.4)) * miss, 2)
                        response = round(expected + error, 1)
                    record_attempt(
                        session,
                        drill=key,
                        concept=drill.concept,
                        question={"prompt": question.prompt, "payload": question.payload},
                        response=response,
                        expected=question.answer,
                        correct=correct,
                        error=error,
                        elapsed_ms=int(rng.gauss(6500 - day * 250, 1800)),
                        created_at=now,
                    )
                    on_attempt(session, key, now)
    engine.dispose()
    print(f"seeded {path / 'holdem.sqlite'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/demo")
