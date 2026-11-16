"""Shared drill interface.

Every drill builds a :class:`Question` from a seeded RNG and grades a response into a :class:`Grade`
with an explanation. The expected answer stays on the server; only :meth:`Question.public` is sent
to the browser.
"""

from __future__ import annotations

import math
import random
import re
import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from holdem.core.cards import Card, cards_str


class AnswerKind(StrEnum):
    NUMBER = "number"
    CHOICE = "choice"


@dataclass(frozen=True)
class Question:
    drill: str
    concept: str
    prompt: str
    kind: AnswerKind
    answer: float | str
    payload: dict[str, Any] = field(default_factory=dict)
    choices: tuple[str, ...] = ()
    unit: str = ""
    tolerance: float = 0.0
    explanation: tuple[str, ...] = ()
    highlight: tuple[str, ...] = ()
    reveal: dict[str, Any] = field(default_factory=dict)  # extra data shown after answering
    follow_up: Question | None = None  # next step of a multi-street scenario
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "drill": self.drill,
            "concept": self.concept,
            "prompt": self.prompt,
            "kind": self.kind.value,
            "payload": self.payload,
            "choices": list(self.choices),
            "unit": self.unit,
        }


@dataclass(frozen=True)
class Grade:
    correct: bool
    expected: float | str
    response: float | str
    error: float | None  # signed (response - expected) for numeric answers
    explanation: tuple[str, ...]
    highlight: tuple[str, ...]
    reveal: dict[str, Any] = field(default_factory=dict)
    tolerance: float = 0.0
    follow_up: Question | None = None

    def public(self) -> dict[str, Any]:
        return {
            "tolerance": self.tolerance,
            "correct": self.correct,
            "expected": self.expected,
            "response": self.response,
            "error": self.error,
            "explanation": list(self.explanation),
            "highlight": list(self.highlight),
            "reveal": self.reveal,
        }


THOUSANDS = re.compile(r"-?\d{1,3}(,\d{3})+(\.\d+)?")


def parse_number(response: object) -> float:
    """Accept 25, "25", "25%", " 25 % ", a decimal comma ("0,5") and thousands ("1,326").

    Rejects NaN and infinity.
    """
    text = str(response).strip().removesuffix("%").strip()
    text = text.replace(",", "") if THOUSANDS.fullmatch(text) else text.replace(",", ".")
    try:
        value = float(text)
    except ValueError as exc:
        raise ValueError(f"expected a number, got {response!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"expected a finite number, got {response!r}")
    return value


def grade(question: Question, response: float | str) -> Grade:
    """Grade a response against the question's stored answer."""
    if question.kind is AnswerKind.NUMBER:
        value = parse_number(response)
        expected = float(question.answer)
        error = value - expected
        correct = abs(error) <= question.tolerance + 1e-9
        return Grade(
            correct,
            expected,
            value,
            round(error, 4),
            question.explanation,
            question.highlight,
            question.reveal,
            question.tolerance,
            question.follow_up,
        )
    if response not in question.choices:
        raise ValueError(f"{response!r} is not one of the choices")
    return Grade(
        response == question.answer,
        question.answer,
        response,
        None,
        question.explanation,
        question.highlight,
        question.reveal,
        question.tolerance,
        question.follow_up,
    )


class Drill(ABC):
    """A drill type. Subclasses set the metadata and implement :meth:`make_question`."""

    key: str
    title: str
    concept: str
    tier: int
    description: str
    speed: bool = False  # quick multiple choice: offered in 60-second speed rounds

    @abstractmethod
    def make_question(self, rng: random.Random) -> Question: ...

    def meta(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "concept": self.concept,
            "tier": self.tier,
            "description": self.description,
            "speed": self.speed,
        }


def card_list(cards: Sequence[Card]) -> list[str]:
    return [cards_str([c]) for c in cards]


def pct(value: float) -> float:
    """A fraction as a percentage rounded to one decimal."""
    return round(value * 100, 1)
