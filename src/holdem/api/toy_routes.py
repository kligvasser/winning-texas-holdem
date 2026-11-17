"""Routes for the toy betting games."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from holdem.engine.toy import GAMES, OPPONENTS, ToySession, new_toy_session

MAX_SESSIONS = 20


class ToyRequest(BaseModel):
    game: str
    opponent: str
    seed: int | None = None


class ToyActRequest(BaseModel):
    action: str


def register_toy_routes(app: FastAPI) -> None:
    sessions: dict[str, ToySession] = {}
    app.state.toy_sessions = sessions

    @app.get("/api/toy")
    def toy_menu() -> dict[str, Any]:
        return {
            "games": [g.public() for g in GAMES.values()],
            "opponents": [o.public() for o in OPPONENTS.values()],
        }

    @app.post("/api/toy")
    def start_toy(body: ToyRequest) -> dict[str, Any]:
        try:
            toy = new_toy_session(body.game, body.opponent, body.seed)
        except KeyError as exc:
            raise HTTPException(404, f"unknown game or opponent {exc}") from exc
        sessions[toy.id] = toy
        while len(sessions) > MAX_SESSIONS:
            sessions.pop(next(iter(sessions)))
        return toy.state()

    @app.post("/api/toy/{session_id}/act")
    def toy_act(session_id: str, body: ToyActRequest) -> dict[str, Any]:
        toy = sessions.get(session_id)
        if toy is None:
            raise HTTPException(404, "session not found (the app may have restarted)")
        try:
            toy.act(body.action)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return toy.state()
