import pytest
from fastapi.testclient import TestClient

from holdem.api.app import create_app

LOCAL = "http://127.0.0.1:8000"


@pytest.fixture
def client(engine, tmp_path):
    return TestClient(create_app(engine, web_dist=tmp_path / "missing"), base_url=LOCAL)


def test_toy_game_flow(client):
    menu = client.get("/api/toy").json()
    assert [g["key"] for g in menu["games"]] == ["akq", "ten"]
    assert {o["character"] for o in menu["opponents"]} == {"Finn", "Moby", "Rocky", "Blaze"}
    start = {"game": "akq", "opponent": "nit", "seed": 5}
    assert client.post("/api/toy", json={**start, "game": "chess"}).status_code == 404
    assert client.post("/api/toy", json={**start, "opponent": "nobody"}).status_code == 404
    state = client.post("/api/toy", json=start).json()
    assert state["game"]["key"] == "akq" and state["opponent"]["character"] == "Rocky"
    assert state["last"] is None and state["hand"]["role"] == "bettor"
    sid = state["id"]
    assert client.post("/api/toy/nope/act", json={"action": "bet"}).status_code == 404
    bad = client.post(f"/api/toy/{sid}/act", json={"action": "call"})
    assert bad.status_code == 400 and "bet or check" in bad.json()["detail"]
    state = client.post(f"/api/toy/{sid}/act", json={"action": "bet"}).json()
    assert state["last"]["action"] == "bet"
    assert state["hands_played"] >= 1
    assert len(state["summary"]["cards"]) == 3


def test_toy_sessions_are_capped(client):
    start = {"game": "ten", "opponent": "tag"}
    first = client.post("/api/toy", json={**start, "seed": 1}).json()["id"]
    for seed in range(20):
        client.post("/api/toy", json={**start, "seed": seed + 2})
    assert client.post(f"/api/toy/{first}/act", json={"action": "bet"}).status_code == 404
