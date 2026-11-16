"""Routes for playing heads-up against a bot and reviewing stored hands."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from holdem.api.deps import SessionDep
from holdem.db import PlayedHand, hand_summary, play_stats, save_hand
from holdem.engine.bots import STYLES
from holdem.engine.headsup import IllegalActionError
from holdem.engine.play import PlaySession, new_session

MAX_SESSIONS = 20


class PlayRequest(BaseModel):
    style: str
    seed: int | None = None


class ActRequest(BaseModel):
    kind: str
    to: int | None = None


def register_play_routes(app: FastAPI, clock: Callable[[], datetime]) -> None:
    sessions: dict[str, PlaySession] = {}
    app.state.play_sessions = sessions

    def find(session_id: str) -> PlaySession:
        found = sessions.get(session_id)
        if found is None:
            raise HTTPException(404, "session not found (the app may have restarted)")
        return found

    def respond(play: PlaySession, db: Session) -> dict[str, Any]:
        state = play.state()
        if play.hand.finished:
            state["hand_id"] = save_hand(db, play.record(), clock()).id
        return state

    @app.get("/api/play/styles")
    def play_styles() -> list[dict[str, str]]:
        return [s.public() for s in STYLES.values()]

    @app.post("/api/play")
    def start_play(body: PlayRequest, session: SessionDep) -> dict[str, Any]:
        try:
            play = new_session(body.style, body.seed)
        except KeyError as exc:
            raise HTTPException(404, f"unknown opponent {body.style!r}") from exc
        sessions[play.id] = play
        while len(sessions) > MAX_SESSIONS:
            sessions.pop(next(iter(sessions)))
        return respond(play, session)

    @app.post("/api/play/{session_id}/act")
    def play_act(session_id: str, body: ActRequest, session: SessionDep) -> dict[str, Any]:
        play = find(session_id)
        try:
            play.act(body.kind, body.to)
        except (IllegalActionError, ValueError) as exc:
            raise HTTPException(400, str(exc)) from exc
        return respond(play, session)

    @app.post("/api/play/{session_id}/next")
    def play_next(session_id: str, session: SessionDep) -> dict[str, Any]:
        play = find(session_id)
        if not play.hand.finished:
            raise HTTPException(400, "finish the current hand first")
        play.new_hand()
        return respond(play, session)

    @app.get("/api/play/{session_id}/coach")
    def play_coach(session_id: str) -> dict[str, Any]:
        play = find(session_id)
        try:
            return play.coach()
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/hands")
    def hands(session: SessionDep, limit: int = 50) -> dict[str, Any]:
        rows = session.scalars(
            select(PlayedHand).order_by(PlayedHand.id.desc()).limit(min(limit, 500))
        ).all()
        return {"hands": [hand_summary(r) for r in rows], "stats": play_stats(session)}

    @app.get("/api/hands/{hand_id}")
    def hand_detail(hand_id: int, session: SessionDep) -> dict[str, Any]:
        row = session.get(PlayedHand, hand_id)
        if row is None:
            raise HTTPException(404, "hand not found")
        return {**hand_summary(row), "record": json.loads(row.record)}
