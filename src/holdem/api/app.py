"""FastAPI application: JSON API for the front end, plus the built front end itself."""

from __future__ import annotations

import random
from collections import OrderedDict
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from holdem.db import drill_stats, make_engine, record_attempt
from holdem.drills.base import Question, grade
from holdem.drills.math_lab import ALL_DRILLS, DRILLS

WEB_DIST = Path(__file__).resolve().parents[3] / "web" / "dist"


class QuestionStore:
    """Questions waiting for an answer, kept in memory (single local user)."""

    def __init__(self, capacity: int = 500) -> None:
        self.capacity = capacity
        self._items: OrderedDict[str, Question] = OrderedDict()

    def add(self, question: Question) -> None:
        self._items[question.id] = question
        while len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def pop(self, question_id: str) -> Question | None:
        return self._items.pop(question_id, None)

    def __len__(self) -> int:
        return len(self._items)


class QuestionRequest(BaseModel):
    seed: int | None = None


class AnswerRequest(BaseModel):
    question_id: str
    response: float | str
    elapsed_ms: int | None = Field(default=None, ge=0)


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def create_app(engine: Engine | None = None, web_dist: Path = WEB_DIST) -> FastAPI:
    app = FastAPI(title="Winning Texas Hold'em")
    app.state.engine = engine or make_engine()
    app.state.questions = QuestionStore()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/drills")
    def list_drills() -> list[dict[str, Any]]:
        return [d.meta() for d in ALL_DRILLS]

    @app.post("/api/drills/{key}/questions")
    def new_question(key: str, body: QuestionRequest, request: Request) -> dict[str, Any]:
        drill = DRILLS.get(key)
        if drill is None:
            raise HTTPException(404, f"unknown drill {key!r}")
        rng = random.Random(body.seed)
        question = drill.make_question(rng)
        request.app.state.questions.add(question)
        return question.public()

    @app.post("/api/answers")
    def answer(body: AnswerRequest, request: Request, session: SessionDep) -> dict[str, Any]:
        question: Question | None = request.app.state.questions.pop(body.question_id)
        if question is None:
            raise HTTPException(404, "question not found or already answered")
        try:
            result = grade(question, body.response)
        except ValueError as exc:
            request.app.state.questions.add(question)  # let the user try again
            raise HTTPException(400, str(exc)) from exc
        record_attempt(
            session,
            drill=question.drill,
            concept=question.concept,
            question={"prompt": question.prompt, "payload": question.payload},
            response=result.response,
            expected=result.expected,
            correct=result.correct,
            error=result.error,
            elapsed_ms=body.elapsed_ms,
        )
        return result.public()

    @app.get("/api/stats")
    def stats(session: SessionDep) -> list[dict[str, Any]]:
        return [s.public() for s in drill_stats(session)]

    if web_dist.is_dir():
        app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            candidate = (web_dist / path).resolve()
            if path and candidate.is_file() and candidate.is_relative_to(web_dist.resolve()):
                return FileResponse(candidate)
            return FileResponse(web_dist / "index.html")

    return app
