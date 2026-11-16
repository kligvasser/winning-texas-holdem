import json

from sqlalchemy.orm import Session

from holdem.db import record_attempt
from holdem.stats import preflop_leaks


def log(session, drill, payload, correct):
    record_attempt(
        session,
        drill=drill,
        concept="preflop-ranges",
        question={"prompt": "", "payload": payload},
        response="Raise",
        expected="Fold",
        correct=correct,
        error=None,
        elapsed_ms=None,
    )


def test_preflop_leaks_ranks_worst_spots_first(engine):
    with Session(engine) as session:
        log(session, "preflop-open", {"spot": "utg-open", "hole": ["7c", "2d"]}, False)
        log(session, "preflop-open", {"spot": "utg-open", "hole": ["7h", "2s"]}, False)
        log(session, "preflop-open", {"spot": "utg-open", "hole": ["As", "Ad"]}, True)
        log(session, "preflop-open", {"spot": "btn-open", "hole": ["As", "Ad"]}, True)
        log(session, "preflop-open", {"spot": "retired-spot", "hole": ["As", "Ad"]}, False)
        log(session, "preflop-open", {}, False)
        leaks = preflop_leaks(session)
    assert [leak.spot for leak in leaks] == ["utg-open", "btn-open"]
    worst = leaks[0].public()
    assert worst["attempts"] == 3
    assert worst["accuracy"] == round(1 / 3, 4)
    assert worst["missed_hands"] == [{"hand": "72o", "count": 2}]
    assert json.dumps(worst)
