from sqlalchemy.orm import Session

from holdem import __main__ as entry
from holdem.db import database_url, drill_stats, make_engine, record_attempt


def test_database_url_uses_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HOLDEM_DATA_DIR", str(tmp_path / "d"))
    url = database_url()
    assert url == f"sqlite:///{tmp_path / 'd' / 'holdem.sqlite'}"
    assert (tmp_path / "d").is_dir()
    engine = make_engine()
    assert str(engine.url) == url
    engine.dispose()


def test_stats_without_numeric_answers(engine):
    with Session(engine) as session:
        record_attempt(
            session,
            drill="showdown",
            concept="board-reading",
            question={},
            response="Player 1",
            expected="Player 2",
            correct=False,
            error=None,
            elapsed_ms=None,
        )
        [stats] = drill_stats(session)
    assert stats.accuracy == 0
    assert stats.mean_abs_error is None
    assert stats.bias is None
    assert stats.mean_ms is None


def test_main_runs_uvicorn(monkeypatch):
    calls = {}
    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: calls.update(kwargs, app=args[0]))
    entry.main(["--port", "9000"])
    assert calls["app"] == "holdem.api.app:create_app"
    assert calls["port"] == 9000
    assert calls["factory"] is True
