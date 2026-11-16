from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from holdem.api.app import QuestionStore, create_app
from holdem.drills.base import AnswerKind, Question
from holdem.drills.math_lab import PreflopEquityDrill


@pytest.fixture(autouse=True)
def fast_preflop(monkeypatch):
    monkeypatch.setattr(PreflopEquityDrill, "samples", 1000)


@pytest.fixture
def client(engine, tmp_path):
    return TestClient(create_app(engine, web_dist=tmp_path / "missing"))


def ask(client, key="pot-odds", seed=1):
    response = client.post(f"/api/drills/{key}/questions", json={"seed": seed})
    assert response.status_code == 200
    return response.json()


def stored_answer(client, question_id):
    question = client.app.state.questions._items[question_id]
    return question.answer


def test_health_and_drill_list(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    drills = client.get("/api/drills").json()
    assert {d["key"] for d in drills} >= {"outs", "pot-odds", "hand-ranking"}


def test_question_hides_answer_and_is_seeded(client):
    first = ask(client, seed=7)
    second = ask(client, seed=7)
    assert "answer" not in first
    assert first["prompt"] == second["prompt"]
    assert first["id"] != second["id"]


def test_unknown_drill(client):
    assert client.post("/api/drills/nope/questions", json={}).status_code == 404


def test_answer_flow_records_stats(client):
    question = ask(client)
    expected = stored_answer(client, question["id"])
    result = client.post(
        "/api/answers",
        json={"question_id": question["id"], "response": expected, "elapsed_ms": 1500},
    ).json()
    assert result["correct"]
    assert result["explanation"]

    wrong = ask(client, seed=2)
    expected = stored_answer(client, wrong["id"])
    result = client.post(
        "/api/answers", json={"question_id": wrong["id"], "response": expected + 20}
    ).json()
    assert not result["correct"]
    assert result["error"] == pytest.approx(20)

    stats = client.get("/api/stats").json()
    assert stats == [
        {
            "drill": "pot-odds",
            "attempts": 2,
            "correct": 1,
            "accuracy": 0.5,
            "mean_abs_error": 10.0,
            "bias": 10.0,
            "mean_ms": 1500.0,
        }
    ]


def test_choice_answers(client):
    question = ask(client, key="showdown")
    expected = stored_answer(client, question["id"])
    result = client.post(
        "/api/answers", json={"question_id": question["id"], "response": expected}
    ).json()
    assert result["correct"]
    assert result["error"] is None


def test_answer_errors(client):
    assert (
        client.post("/api/answers", json={"question_id": "missing", "response": 1}).status_code
        == 404
    )
    question = ask(client)
    bad = client.post("/api/answers", json={"question_id": question["id"], "response": "abc"})
    assert bad.status_code == 400
    # The question survives a malformed answer, but not a real one.
    ok = client.post("/api/answers", json={"question_id": question["id"], "response": 10})
    assert ok.status_code == 200
    again = client.post("/api/answers", json={"question_id": question["id"], "response": 10})
    assert again.status_code == 404


def test_answers_drive_reviews_and_today(engine, tmp_path):
    now = datetime(2026, 11, 16, 12, tzinfo=UTC)
    client = TestClient(create_app(engine, web_dist=tmp_path / "missing", clock=lambda: now))
    today = client.get("/api/today").json()
    assert today["new"] == ["hand-ranking", "showdown"]
    assert today["queue"][:2] == ["hand-ranking", "showdown"]

    reviews = []
    for seed in range(3):
        question = ask(client, key="hand-ranking", seed=seed)
        expected = stored_answer(client, question["id"])
        body = {"question_id": question["id"], "response": expected, "elapsed_ms": 2000}
        reviews.append(client.post("/api/answers", json=body).json()["review"])
    assert reviews[:2] == [None, None]
    assert reviews[2]["rating"] == "good"

    curriculum = client.get("/api/curriculum").json()
    concepts = {c["id"]: c for c in curriculum["concepts"]}
    assert concepts["hand-rankings"]["attempts"] == 3
    assert concepts["hand-rankings"]["status"] == "learning"
    assert concepts["pot-odds"]["status"] == "new"
    assert concepts["outs"]["lectures"]
    assert curriculum["cards"]["hand-ranking"]["is_due"] is False
    assert curriculum["materials"]


def test_question_store_capacity():
    store = QuestionStore(capacity=2)
    questions = [Question("d", "c", "p", AnswerKind.NUMBER, 1.0) for _ in range(3)]
    for q in questions:
        store.add(q)
    assert len(store) == 2
    assert store.pop(questions[0].id) is None
    assert store.pop(questions[2].id) is questions[2]


def test_serves_built_front_end(engine, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    (dist / "favicon.svg").write_text("<svg/>")
    client = TestClient(create_app(engine, web_dist=dist))
    assert client.get("/").text == "<html>app</html>"
    assert client.get("/math-lab").text == "<html>app</html>"  # SPA fallback
    assert client.get("/favicon.svg").text == "<svg/>"
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/../secret").text == "<html>app</html>"
