import pytest
from fastapi.testclient import TestClient

from holdem.api.app import create_app
from holdem.api.security import (
    HEADERS,
    MAX_BODY_BYTES,
    extra_hosts,
    host_allowed,
    host_name,
    same_origin,
)

LOCAL = "http://127.0.0.1:8000"


@pytest.fixture
def app(engine, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>")
    return create_app(engine, web_dist=dist)


@pytest.fixture
def client(app):
    return TestClient(app, base_url=LOCAL)


@pytest.mark.parametrize(
    ("header", "name"),
    [
        ("127.0.0.1:8000", "127.0.0.1"),
        ("LocalHost:8000", "localhost"),
        ("localhost", "localhost"),
        ("[::1]:8000", "::1"),
        ("::1", "::1"),
        ("evil.example:8000", "evil.example"),
    ],
)
def test_host_name(header, name):
    assert host_name(header) == name


@pytest.mark.parametrize("host", ["127.0.0.1:8000", "localhost:8000", "[::1]:8000", "192.168.1.7"])
def test_local_hosts_are_allowed(host):
    assert host_allowed(host, frozenset())


@pytest.mark.parametrize("host", ["evil.example:8000", "", "127.0.0.1.evil.example", "testserver"])
def test_names_are_refused(host):
    assert not host_allowed(host, frozenset())


def test_extra_hosts_come_from_the_environment(monkeypatch):
    monkeypatch.delenv("HOLDEM_ALLOWED_HOSTS", raising=False)
    assert extra_hosts() == frozenset()
    monkeypatch.setenv("HOLDEM_ALLOWED_HOSTS", " Poker.lan , ,trainer.home")
    assert extra_hosts() == {"poker.lan", "trainer.home"}
    assert host_allowed("poker.lan:8000", extra_hosts())


def test_same_origin():
    assert same_origin("http://127.0.0.1:8000", "127.0.0.1:8000")
    assert not same_origin("http://127.0.0.1:9000", "127.0.0.1:8000")
    assert not same_origin("https://evil.example", "127.0.0.1:8000")
    assert not same_origin("null", "127.0.0.1:8000")


def test_a_rebinding_host_is_refused(app):
    response = TestClient(app, base_url="http://evil.example:8000").get("/api/health")
    assert response.status_code == 400
    assert response.headers["x-frame-options"] == "DENY"


def test_an_allowed_name_gets_through(engine, tmp_path, monkeypatch):
    monkeypatch.setenv("HOLDEM_ALLOWED_HOSTS", "poker.lan")
    app = create_app(engine, web_dist=tmp_path / "missing")
    assert TestClient(app, base_url="http://poker.lan:8000").get("/api/health").status_code == 200


def test_posts_from_another_site_are_refused(client):
    refused = client.post("/api/play", json={}, headers={"Origin": "https://evil.example"})
    assert refused.status_code == 403
    assert client.app.state.play_sessions == {}
    own = client.post("/api/play", json={"seed": 1}, headers={"Origin": LOCAL})
    assert own.status_code == 200
    assert client.post("/api/play", json={"seed": 1}).status_code == 200  # curl sends no Origin


def test_reads_from_another_site_are_not_blocked_by_origin(client):
    assert client.get("/api/health", headers={"Origin": "https://evil.example"}).status_code == 200


def test_a_form_post_is_not_read_as_json(client):
    response = client.post(
        "/api/play", content='{"seed": 1}', headers={"Content-Type": "text/plain"}
    )
    assert response.status_code == 422


def test_big_and_unsized_bodies_are_refused(client):
    big = client.post("/api/answers", content=b"x" * (MAX_BODY_BYTES + 1))
    assert big.status_code == 413
    odd = client.post("/api/answers", content=b"{}", headers={"Content-Length": "abc"})
    assert odd.status_code == 413

    def chunks():
        yield b"{}"

    assert client.post("/api/answers", content=chunks()).status_code == 411


def test_long_fields_are_refused(client):
    assert (
        client.post("/api/answers", json={"question_id": "q" * 201, "response": 1}).status_code
        == 422
    )
    paint = {"spot": "co-open", "action": "Raise", "classes": ["AA"] * 170}
    assert client.post("/api/preflop/paint", json=paint).status_code == 422
    assert client.post("/api/play/x/act", json={"kind": "raise", "to": 10**9}).status_code == 422
    assert client.post("/api/toy", json={"game": "g" * 41, "opponent": "o"}).status_code == 422
    assert client.post("/api/toy/x/act", json={"action": "a" * 21}).status_code == 422


def test_every_reply_carries_the_security_headers(client):
    for path in ("/api/health", "/", "/api/nope/nope", "/%00"):
        response = client.get(path)
        for name, value in HEADERS.items():
            assert response.headers[name] == value
    assert client.get("/api/health").headers["cache-control"] == "no-store"
    assert "cache-control" not in client.get("/").headers


def test_reads_started_by_another_site_are_refused(client):
    cross = {"Sec-Fetch-Site": "cross-site"}
    assert client.get("/api/hands", headers=cross).status_code == 403
    assert client.get("/", headers=cross).status_code == 200  # following a link here is fine
    assert client.get("/api/hands", headers={"Sec-Fetch-Site": "same-origin"}).status_code == 200


def test_unknown_api_paths_are_not_given_the_page(client):
    assert client.get("/api/nope").status_code == 404
    assert client.get("/api").status_code == 404
    assert client.get("/apiary").text == "<html>app</html>"


@pytest.mark.parametrize("path", ["/%00", "/" + "a" * 3000])
def test_odd_paths_fall_back_to_the_page(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.text == "<html>app</html>"


def test_the_interactive_docs_are_off(client):
    for path in ("/openapi.json", "/docs", "/redoc"):
        assert client.get(path).text == "<html>app</html>"


@pytest.mark.parametrize(
    "path",
    [
        "/../pyproject.toml",
        "/..%2f..%2fpyproject.toml",
        "/assets/..%2f..%2f..%2fpyproject.toml",
        "/%2e%2e/%2e%2e/pyproject.toml",
        "//etc/passwd",
        "/..\\..\\pyproject.toml",
    ],
)
def test_files_outside_the_front_end_are_never_served(client, path):
    response = client.get(path)
    assert "[project]" not in response.text
    assert "root:" not in response.text
