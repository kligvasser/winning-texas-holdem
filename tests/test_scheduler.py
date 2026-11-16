from datetime import UTC, datetime, timedelta

import pytest
from fsrs import Card, Rating
from sqlalchemy.orm import Session

from holdem import scheduler
from holdem.db import ReviewCard, record_attempt
from holdem.drills.math_lab import ALL_DRILLS, DRILLS
from holdem.scheduler import (
    BLOCK_SIZE,
    NEW_PER_DAY,
    QUESTIONS_PER_DRILL,
    card_summary,
    concept_progress,
    daily_plan,
    interleave,
    load_card,
    on_attempt,
    pick_new_drills,
    rating_for,
    save_card,
)

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


def answer(session, drill, correct=True, elapsed_ms=4000, now=NOW):
    record_attempt(
        session,
        drill=drill,
        concept=DRILLS[drill].concept,
        question={},
        response="1",
        expected="1",
        correct=correct,
        error=None,
        elapsed_ms=elapsed_ms,
        created_at=now,
    )
    return on_attempt(session, drill, now)


@pytest.mark.parametrize(
    ("results", "rating"),
    [
        ([(True, 3000)] * 3, Rating.Good),
        ([(True, 30000)] * 3, Rating.Hard),
        ([(True, None)] * 3, Rating.Good),
        ([(True, 3000), (True, 3000), (False, 3000)], Rating.Hard),
        ([(True, 3000), (False, 3000), (False, 3000)], Rating.Again),
        ([(False, 3000)] * 3, Rating.Again),
    ],
)
def test_rating_for(results, rating):
    assert rating_for(results) is rating


def test_interleave():
    assert interleave(["a", "b"], 2) == ["a", "b", "a", "b"]


def test_first_block_creates_and_reviews_a_card(session):
    assert answer(session, "pot-odds") is None
    started = load_card(session, "pot-odds")
    assert started is not None
    assert started.last_review is None
    assert answer(session, "pot-odds") is None
    outcome = answer(session, "pot-odds")
    assert outcome is not None
    assert outcome.rating is Rating.Good
    assert outcome.due > NOW
    assert outcome.public()["rating"] == "good"
    # Not due any more: further answers do not review again.
    assert answer(session, "pot-odds") is None


def test_failed_block_rates_again(session):
    for _ in range(BLOCK_SIZE - 1):
        answer(session, "outs", correct=False)
    outcome = answer(session, "outs", correct=False)
    assert outcome is not None
    assert outcome.rating is Rating.Again


def test_due_card_counts_answers_after_it_became_due(session):
    for _ in range(BLOCK_SIZE):
        answer(session, "spr")
    card = load_card(session, "spr")
    assert card is not None
    later = card.due + timedelta(minutes=1)
    # Answers from before the card became due do not count towards the next block.
    assert answer(session, "spr", now=later) is None
    assert answer(session, "spr", now=later) is None
    outcome = answer(session, "spr", now=later)
    assert outcome is not None
    assert outcome.due > card.due


def test_save_card_updates_existing_row(session):
    save_card(session, "nuts", Card(due=NOW), NOW)
    save_card(session, "nuts", Card(due=NOW + timedelta(days=1)), NOW)
    stored = load_card(session, "nuts")
    assert stored is not None
    assert stored.due == NOW + timedelta(days=1)
    assert session.query(ReviewCard).count() == 1


def test_concept_progress_statuses(session):
    progress = concept_progress(session)
    assert progress["pot-odds"].status == "new"
    assert progress["pot-odds"].mastery == 0.5
    assert progress["preflop-ranges"].attempts == 0  # concept without drills yet
    for _ in range(12):
        answer(session, "pot-odds")
    answer(session, "hand-ranking", correct=False)
    progress = concept_progress(session)
    assert progress["pot-odds"].status == "mastered"
    assert progress["hand-rankings"].status == "learning"
    assert progress["pot-odds"].public()["mastery"] == pytest.approx(13 / 14, abs=0.001)


def test_daily_plan_for_a_new_learner(session):
    plan = daily_plan(session, NOW)
    assert plan.due == []
    # Hand rankings has no prerequisites; picking it unlocks board reading in the same plan.
    assert plan.new == ["hand-ranking", "showdown"][:NEW_PER_DAY]
    assert plan.queue == interleave(plan.new, QUESTIONS_PER_DRILL)
    assert plan.public()["extra"] == []


def test_daily_plan_limits_new_drills_per_day(session):
    answer(session, "hand-ranking")
    answer(session, "showdown")
    plan = daily_plan(session, NOW)
    assert plan.new == []
    # Started but unreviewed drills are due straight away.
    assert set(plan.due) == {"hand-ranking", "showdown"}


def test_daily_plan_unlocks_by_prerequisite(session):
    answer(session, "hand-ranking", now=NOW - timedelta(days=2))
    answer(session, "showdown", now=NOW - timedelta(days=2))
    plan = daily_plan(session, NOW)
    # Hand rankings and board reading are started: outs and combinatorics drills open up.
    assert plan.new == ["nuts", "outs"]
    assert "preflop-equity" not in plan.new  # needs combinatorics first


def test_daily_plan_offers_extra_practice_when_nothing_is_due(session, monkeypatch):
    monkeypatch.setattr(scheduler, "NEW_PER_DAY", 0)
    for drill in ("pot-odds", "spr", "nuts"):
        for _ in range(BLOCK_SIZE):
            answer(session, drill)
    plan = daily_plan(session, NOW + timedelta(minutes=5))
    assert plan.due == []
    assert len(plan.extra) == 2
    assert plan.queue == interleave(plan.extra, QUESTIONS_PER_DRILL)


def test_daily_plan_ignores_cards_for_removed_drills(session):
    save_card(session, "retired-drill", Card(due=NOW), NOW)
    assert "retired-drill" not in daily_plan(session, NOW).due


def test_card_summary(session):
    answer(session, "nuts")
    for _ in range(BLOCK_SIZE):
        answer(session, "spr")
    summary = card_summary(session, NOW)
    assert summary["nuts"] == {"due": None, "is_due": True, "recall": None}
    assert summary["spr"]["is_due"] is False
    assert 0 < summary["spr"]["recall"] <= 1


def test_pick_new_drills_follows_prerequisite_order(session):
    picked = pick_new_drills(concept_progress(session), set(), limit=100)
    assert sorted(picked) == sorted(d.key for d in ALL_DRILLS)
    position = {key: i for i, key in enumerate(picked)}
    assert position["hand-ranking"] < position["showdown"] < position["outs"]
    assert position["outs"] < position["draw-odds"] < position["pot-odds"]
