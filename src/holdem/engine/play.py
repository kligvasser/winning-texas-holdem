"""A six-max session against five bots, one of each style, and a review of your decisions.

Stacks reset to 100bb each hand (a cash game with automatic top-ups) and the button moves one seat
per hand. After each hand, every decision where you faced a bet is graded by your equity against
the estimated ranges of the opponents in the pot (from their style, position and preflop actions)
compared with the price. This is an estimate: it ignores later betting.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from typing import Any

from holdem.core.cards import cards_str
from holdem.core.equity import calculate_equity
from holdem.engine.bots import STYLES, SeatBot, Style, seat_range
from holdem.engine.headsup import BIG_BLIND, Action
from holdem.engine.table import TableHand

HERO = 0
SEATS = 6
STACK = 200  # chips: 100bb
BOARD_CARDS = {"preflop": 0, "flop": 3, "turn": 4, "river": 5}
MISTAKE_BB = 1.0
LEAK_BB = 0.25


def bb(chips: float) -> float:
    return round(chips / BIG_BLIND, 2)


@dataclass(frozen=True)
class Decision:
    index: int  # position in the hand's action log
    street: str
    board: list[str]
    action: str
    amount: int
    pot: int
    to_call: int
    equity: float
    opponents: int  # how many ranges the equity is measured against
    need: float | None
    loss_bb: float  # estimated EV given up, in big blinds (0 when not graded)
    verdict: str  # good, leak, mistake, info
    note: str

    def public(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "street": self.street,
            "board": self.board,
            "action": self.action,
            "amount_bb": bb(self.amount),
            "pot_bb": bb(self.pot),
            "to_call_bb": bb(self.to_call),
            "equity": round(self.equity, 4),
            "opponents": self.opponents,
            "need": None if self.need is None else round(self.need, 4),
            "loss_bb": self.loss_bb,
            "verdict": self.verdict,
            "note": self.note,
        }


def opponents_in_pot(hand: TableHand, log: list[Action], street: str) -> list[int]:
    """The seats whose ranges you are up against at a point in the hand.

    After the flop that is everyone who has not folded. Before it, players still to act mostly
    fold, so only those who called or raised count (or the big blind when nobody has yet).
    """
    folded = {a.player for a in log if a.kind == "fold"}
    live = [s for s in range(1, hand.seats) if s not in folded]
    if street != "preflop":
        return live
    entered = {a.player for a in log if a.kind in ("call", "raise")}
    return [s for s in live if s in entered] or [hand.positions.index("BB")]


def equity_against(
    styles: list[Style], hand: TableHand, log: list[Action], street: str
) -> tuple[float, int]:
    """Hero's equity against the estimated ranges of the opponents in the pot, and their number."""
    board = hand.board[: BOARD_CARDS[street]]
    seats = opponents_in_pot(hand, log, street)
    ranges = [seat_range(styles[s - 1], log, s, hand.positions[s]) for s in seats]
    result = calculate_equity(
        [hand.hole[HERO], *ranges], board, samples=1500, seed=len(log), exact_limit=300_000
    )
    return result[0].equity, len(seats)


def _against(opponents: int) -> str:
    return "the bot's likely range" if opponents == 1 else f"{opponents} bots' likely ranges"


def review(styles: list[Style], hand: TableHand) -> list[Decision]:
    decisions = []
    for index, action in enumerate(hand.log):
        if action.player != HERO or action.kind == "post":
            continue
        equity, opponents = equity_against(styles, hand, hand.log[:index], action.street)
        board = [cards_str([c]) for c in hand.board[: BOARD_CARDS[action.street]]]
        need = None
        loss = 0.0
        verdict = "info"
        if action.to_call:
            need = action.to_call / (action.pot + action.to_call)
            call_ev = equity * (action.pot + action.to_call) - action.to_call
            if action.kind == "fold":
                loss = max(0.0, call_ev)
            elif action.kind == "call":
                loss = max(0.0, -call_ev)
            loss = bb(loss)
            if action.kind in ("fold", "call"):
                verdict = "mistake" if loss >= MISTAKE_BB else "leak" if loss >= LEAK_BB else "good"
            note = (
                f"Facing {bb(action.to_call):g}bb into {bb(action.pot):g}bb you needed {need:.0%}; "
                f"against {_against(opponents)} you had about {equity:.0%}."
            )
            if action.kind == "raise":
                note += " Raises are not graded: they depend on how often the bots fold."
        else:
            note = (
                f"You {action.kind} with about {equity:.0%} equity against {_against(opponents)}. "
                "Checks and bets are not graded."
            )
        decisions.append(
            Decision(
                index=index,
                street=action.street,
                board=board,
                action=action.kind,
                amount=action.amount,
                pot=action.pot,
                to_call=action.to_call,
                equity=equity,
                opponents=opponents,
                need=need,
                loss_bb=loss,
                verdict=verdict,
                note=note,
            )
        )
    return decisions


@dataclass
class PlaySession:
    seed: int
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    hands_played: int = 0
    net: int = 0  # chips across finished hands
    hand: TableHand = field(init=False)
    decisions: list[Decision] = field(init=False, default_factory=list)
    styles: list[Style] = field(init=False)  # seats 1 to 5, clockwise from you
    frames: list[dict[str, Any]] = field(init=False, default_factory=list)
    _rng: random.Random = field(init=False)
    _bots: list[SeatBot] = field(init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self.styles = list(STYLES.values())
        self._rng.shuffle(self.styles)
        self._bots = [
            SeatBot(style, random.Random(self.seed + seat))
            for seat, style in enumerate(self.styles, start=1)
        ]
        self.new_hand()

    def new_hand(self) -> None:
        button = self.hands_played % SEATS  # the button moves one seat each hand
        self.hand = TableHand([STACK] * SEATS, button, random.Random(self._rng.randrange(1 << 30)))
        self.decisions = []
        self.frames = [self._frame()]
        self._bots_turn()

    def act(self, kind: str, to: int | None = None) -> None:
        if self.hand.finished or self.hand.current != HERO:
            raise ValueError("it is not your turn")
        self.hand.act(kind, to)
        self.frames = [self._frame()]
        self._bots_turn()

    def _frame(self) -> dict[str, Any]:
        """The table after one action, for the browser to animate step by step."""
        view = self.hand.public(viewer=HERO)
        del view["log"]
        return view

    def _bots_turn(self) -> None:
        while not self.hand.finished and self.hand.current != HERO:
            kind, to = self._bots[self.hand.current - 1].decide(self.hand)
            self.hand.act(kind, to)
            self.frames.append(self._frame())
        if self.hand.finished:
            self.hands_played += 1
            self.net += self.hand.net()[HERO]
            self.decisions = review(self.styles, self.hand)

    def coach(self) -> dict[str, Any]:
        """Price and equity for the decision you face now."""
        if self.hand.finished:
            raise ValueError("there is no decision to coach")
        hand = self.hand
        legal = hand.legal()
        pot = hand.total_pot
        equity, opponents = equity_against(self.styles, hand, hand.log, hand.street_name)
        need = legal.to_call / (pot + legal.to_call) if legal.to_call else None
        return {
            "to_call_bb": bb(legal.to_call),
            "pot_bb": bb(pot),
            "need": None if need is None else round(need, 4),
            "equity": round(equity, 4),
            "opponents": opponents,
        }

    def seats(self) -> list[dict[str, str]]:
        you = {"key": "hero", "name": "You", "character": "You", "blurb": ""}
        return [you, *(style.public() for style in self.styles)]

    def state(self) -> dict[str, Any]:
        hand = self.hand
        legal = None
        if not hand.finished:
            options = hand.legal()
            legal = {
                "to_call": options.to_call,
                "can_check": options.can_check,
                "can_raise": options.can_raise,
                "min_raise_to": options.min_raise_to,
                "max_raise_to": options.max_raise_to,
            }
        return {
            "id": self.id,
            "seats": self.seats(),
            "hand": hand.public(viewer=HERO),
            "frames": self.frames,
            "legal": legal,
            "hands_played": self.hands_played,
            "net_bb": bb(self.net),
            "decisions": [d.public() for d in self.decisions] if hand.finished else [],
        }

    def record(self) -> dict[str, Any]:
        """Everything needed to replay and review a finished hand."""
        return {
            "style": "6-max",
            "seats": self.seats(),
            "hand": self.hand.public(viewer=HERO, reveal=True),
            "net_bb": bb(self.hand.net()[HERO]),
            "decisions": [d.public() for d in self.decisions],
        }


def new_session(seed: int | None = None) -> PlaySession:
    return PlaySession(random.randrange(1 << 30) if seed is None else seed)
