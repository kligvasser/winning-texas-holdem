"""Starting-hand classes, combos and ranges.

There are 169 hand classes: 13 pairs (``"TT"``), 78 suited (``"AKs"``) and 78 offsuit (``"AKo"``).
On the 13x13 grid, ranks run from ace (index 0) to deuce (index 12). The diagonal holds pairs, cells
above it suited hands and cells below it offsuit hands.

A :class:`Range` maps hand classes to a weight in (0, 1], the fraction of that class's combos the
range contains.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field

from holdem.core.cards import RANKS, Card, make_card, rank_of, suit_of

type HandClass = str
type Combo = tuple[Card, Card]

GRID_RANKS = RANKS[::-1]  # "AKQJT98765432"


def _rank_index(char: str) -> int:
    idx = RANKS.find(char.upper())
    if idx < 0:
        raise ValueError(f"invalid rank {char!r}")
    return idx


def class_name(high: int, low: int, suited: bool) -> HandClass:
    """Class name for two ranks (0 = deuce .. 12 = ace)."""
    hi, lo = max(high, low), min(high, low)
    if hi == lo:
        return RANKS[hi] * 2
    return RANKS[hi] + RANKS[lo] + ("s" if suited else "o")


def grid_class(row: int, col: int) -> HandClass:
    """Hand class at a 13x13 grid cell."""
    if not (0 <= row < 13 and 0 <= col < 13):
        raise ValueError(f"grid cell out of range: {row},{col}")
    r1, r2 = 12 - row, 12 - col
    return class_name(r1, r2, suited=row < col)


def class_grid_position(hand_class: HandClass) -> tuple[int, int]:
    high, low, kind = parse_class(hand_class)
    row, col = 12 - high, 12 - low
    if kind == "o":
        row, col = col, row
    return row, col


ALL_CLASSES: tuple[HandClass, ...] = tuple(grid_class(r, c) for r in range(13) for c in range(13))


def parse_class(hand_class: HandClass) -> tuple[int, int, str]:
    """Return (high rank, low rank, kind) where kind is ``"p"``, ``"s"`` or ``"o"``."""
    text = hand_class.strip()
    if len(text) == 2 and text[0].upper() == text[1].upper():
        rank = _rank_index(text[0])
        return rank, rank, "p"
    if len(text) == 3 and text[2].lower() in "so":
        a, b = _rank_index(text[0]), _rank_index(text[1])
        if a == b:
            raise ValueError(f"a pair cannot be suited or offsuit: {hand_class!r}")
        return max(a, b), min(a, b), text[2].lower()
    raise ValueError(f"invalid hand class {hand_class!r}")


def normalize_class(hand_class: HandClass) -> HandClass:
    high, low, kind = parse_class(hand_class)
    return class_name(high, low, suited=kind == "s")


def combos_of_class(hand_class: HandClass) -> list[Combo]:
    high, low, kind = parse_class(hand_class)
    if kind == "p":
        return [
            (make_card(high, s1), make_card(high, s2))
            for s1, s2 in itertools.combinations(range(4), 2)
        ]
    if kind == "s":
        return [(make_card(high, s), make_card(low, s)) for s in range(4)]
    return [
        (make_card(high, s1), make_card(low, s2)) for s1 in range(4) for s2 in range(4) if s1 != s2
    ]


def class_of_combo(c1: Card, c2: Card) -> HandClass:
    if c1 == c2:
        raise ValueError("a combo needs two different cards")
    return class_name(rank_of(c1), rank_of(c2), suited=suit_of(c1) == suit_of(c2))


def class_combo_count(hand_class: HandClass) -> int:
    kind = parse_class(hand_class)[2]
    return {"p": 6, "s": 4, "o": 12}[kind]


def live_combos(hand_class: HandClass, dead: Iterable[Card] = ()) -> list[Combo]:
    """Combos of a class that do not use any dead card (blockers)."""
    dead_set = set(dead)
    return [c for c in combos_of_class(hand_class) if c[0] not in dead_set and c[1] not in dead_set]


def _expand_token(token: str) -> list[HandClass]:
    """Expand one range token (without weight) into hand classes."""
    if "-" in token:
        start, end = (normalize_class(part) for part in token.split("-", 1))
        s_hi, s_lo, s_kind = parse_class(start)
        e_hi, e_lo, e_kind = parse_class(end)
        if s_kind != e_kind:
            raise ValueError(f"range endpoints differ in kind: {token!r}")
        if s_kind == "p":
            lo, hi = sorted((s_hi, e_hi))
            return [class_name(r, r, False) for r in range(lo, hi + 1)]
        if s_hi != e_hi:
            raise ValueError(f"range endpoints need the same top card: {token!r}")
        lo, hi = sorted((s_lo, e_lo))
        return [class_name(s_hi, r, s_kind == "s") for r in range(lo, hi + 1)]

    plus = token.endswith("+")
    body = token[:-1] if plus else token
    if len(body) == 2 and body[0].upper() != body[1].upper():
        # "AK" or "AK+" means both suited and offsuit.
        return _expand_token(body + "s" + ("+" if plus else "")) + _expand_token(
            body + "o" + ("+" if plus else "")
        )
    high, low, kind = parse_class(body)
    if not plus:
        return [class_name(high, low, kind == "s")]
    if kind == "p":
        return [class_name(r, r, False) for r in range(high, 13)]
    return [class_name(high, r, kind == "s") for r in range(low, high)]


@dataclass(frozen=True)
class Range:
    """A weighted set of hand classes."""

    weights: Mapping[HandClass, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        clean: dict[HandClass, float] = {}
        for hand_class, weight in self.weights.items():
            if not 0 <= weight <= 1:
                raise ValueError(f"weight for {hand_class} must be in [0, 1], got {weight}")
            if weight > 0:
                clean[normalize_class(hand_class)] = float(weight)
        object.__setattr__(self, "weights", clean)

    @classmethod
    def parse(cls, text: str) -> Range:
        """Parse standard range notation, e.g. ``"TT+, AJs+, KQo, A5s-A2s, 76s:0.5"``."""
        weights: dict[HandClass, float] = {}
        for raw in text.replace(";", ",").split(","):
            token = raw.strip()
            if not token:
                continue
            weight = 1.0
            if ":" in token:
                token, weight_text = token.split(":", 1)
                weight = float(weight_text)
            for hand_class in _expand_token(token.strip()):
                weights[hand_class] = weight
        return cls(weights)

    @classmethod
    def of(cls, classes: Iterable[HandClass], weight: float = 1.0) -> Range:
        return cls(dict.fromkeys(classes, weight))

    def __contains__(self, hand_class: object) -> bool:
        return isinstance(hand_class, str) and normalize_class(hand_class) in self.weights

    def __iter__(self) -> Iterator[HandClass]:
        return iter(self.weights)

    def __len__(self) -> int:
        return len(self.weights)

    def weight(self, hand_class: HandClass) -> float:
        return self.weights.get(normalize_class(hand_class), 0.0)

    def combo_count(self) -> float:
        return sum(class_combo_count(c) * w for c, w in self.weights.items())

    def fraction(self) -> float:
        """Share of all 1,326 starting combos in the range."""
        return self.combo_count() / 1326

    def combos(self, dead: Iterable[Card] = ()) -> list[tuple[Combo, float]]:
        """Live combos with their weights, removing any combo that uses a dead card."""
        dead_list = list(dead)
        return [
            (combo, weight)
            for hand_class, weight in self.weights.items()
            for combo in live_combos(hand_class, dead_list)
        ]

    def to_text(self) -> str:
        """Plain listing in grid order (not compressed), weights shown when below 1."""
        parts = []
        for hand_class in ALL_CLASSES:
            weight = self.weights.get(hand_class)
            if weight is None:
                continue
            parts.append(hand_class if weight == 1 else f"{hand_class}:{weight:g}")
        return ", ".join(parts)
