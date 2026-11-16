"""A heads-up session against one bot, and the review of every decision you made.

Stacks reset to 100bb each hand (a cash game with automatic top-ups). After each hand, every
decision where you faced a bet is graded by your equity against the bot's estimated range (its
preflop range from its style and actions) compared with the price. This is an estimate: it ignores
later betting and narrows the bot's range by preflop actions only.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from typing import Any

from holdem.core.cards import cards_str
from holdem.core.equity import calculate_equity
from holdem.engine.bots import STYLES, Bot, Style, estimated_range
from holdem.engine.headsup import BIG_BLIND, Action, HeadsUpHand

HERO, BOT = 0, 1
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
    range_share: float  # share of all starting hands in the bot's estimated range
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
            "range_share": round(self.range_share, 3),
            "need": None if self.need is None else round(self.need, 4),
            "loss_bb": self.loss_bb,
            "verdict": self.verdict,
            "note": self.note,
        }


def equity_against(
    style: Style, hand: HeadsUpHand, log: list[Action], street: str
) -> tuple[float, float]:
    """Hero's equity against the bot's estimated range at a point in the hand."""
    board = hand.board[: BOARD_CARDS[street]]
    villain = estimated_range(style, log, BOT, hand.button)
    combos = villain.combos([*hand.hole[HERO], *board])
    result = calculate_equity(
        [hand.hole[HERO], combos], board, samples=1500, seed=len(log), exact_limit=300_000
    )
    return result[0].equity, villain.fraction()


def review(style: Style, hand: HeadsUpHand) -> list[Decision]:
    decisions = []
    for index, action in enumerate(hand.log):
        if action.player != HERO or action.kind == "post":
            continue
        prior = hand.log[:index]
        equity, share = equity_against(style, hand, prior, action.street)
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
                f"against the bot's likely range (top {share:.0%}) you had about {equity:.0%}."
            )
            if action.kind == "raise":
                note += " Raises are not graded: they depend on how often the bot folds."
        else:
            note = (
                f"You {action.kind} with about {equity:.0%} equity against the bot's likely range "
                f"(top {share:.0%}). Checks and bets are not graded."
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
                range_share=share,
                need=need,
                loss_bb=loss,
                verdict=verdict,
                note=note,
            )
        )
    return decisions


@dataclass
class PlaySession:
    style: Style
    seed: int
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    hands_played: int = 0
    net: int = 0  # chips across finished hands
    hand: HeadsUpHand = field(init=False)
    decisions: list[Decision] = field(init=False, default_factory=list)
    _rng: random.Random = field(init=False)
    _bot: Bot = field(init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self._bot = Bot(self.style, random.Random(self.seed + 1))
        self.new_hand()

    def new_hand(self) -> None:
        button = self.hands_played % 2  # alternate the button
        self.hand = HeadsUpHand([STACK, STACK], button, random.Random(self._rng.randrange(1 << 30)))
        self.decisions = []
        self._bots_turn()

    def act(self, kind: str, to: int | None = None) -> None:
        if self.hand.finished or self.hand.current != HERO:
            raise ValueError("it is not your turn")
        self.hand.act(kind, to)
        self._bots_turn()

    def _bots_turn(self) -> None:
        while not self.hand.finished and self.hand.current == BOT:
            kind, to = self._bot.decide(self.hand)
            self.hand.act(kind, to)
        if self.hand.finished:
            self.hands_played += 1
            self.net += self.hand.net()[HERO]
            self.decisions = review(self.style, self.hand)

    def coach(self) -> dict[str, Any]:
        """Price and equity for the decision you face now."""
        if self.hand.finished or self.hand.current != HERO:
            raise ValueError("there is no decision to coach")
        legal = self.hand.legal()
        pot = self.hand.total_pot
        equity, share = equity_against(self.style, self.hand, self.hand.log, self.hand.street_name)
        need = legal.to_call / (pot + legal.to_call) if legal.to_call else None
        return {
            "to_call_bb": bb(legal.to_call),
            "pot_bb": bb(pot),
            "need": None if need is None else round(need, 4),
            "equity": round(equity, 4),
            "range_share": round(share, 3),
        }

    def state(self) -> dict[str, Any]:
        hand = self.hand
        view = hand.public(viewer=HERO)
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
            "style": self.style.public(),
            "hand": view,
            "legal": legal,
            "hands_played": self.hands_played,
            "net_bb": bb(self.net),
            "decisions": [d.public() for d in self.decisions] if hand.finished else [],
        }

    def record(self) -> dict[str, Any]:
        """Everything needed to replay and review a finished hand."""
        return {
            "style": self.style.key,
            "hand": self.hand.public(viewer=HERO, reveal=True),
            "net_bb": bb(self.hand.net()[HERO]),
            "decisions": [d.public() for d in self.decisions],
        }


def new_session(style_key: str, seed: int | None = None) -> PlaySession:
    if style_key not in STYLES:
        raise KeyError(style_key)
    return PlaySession(STYLES[style_key], random.randrange(1 << 30) if seed is None else seed)
