"""Closed-form poker maths: draw probabilities, pot odds, MDF, bluff ratios, SPR, dealt-hand odds.

Bet-size formulas take the pot *before* the bet and the bet size, in the same units (bb or chips).
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from fractions import Fraction

from holdem.core.ranges import HandClass, Range

STARTING_COMBOS = 1326


def hit_probability(outs: int, unseen: int, draws: int) -> float:
    """Chance that at least one of ``outs`` cards appears in ``draws`` cards from ``unseen``."""
    if not 0 <= outs <= unseen or not 0 <= draws <= unseen:
        raise ValueError("need 0 <= outs, draws <= unseen")
    return 1 - math.comb(unseen - outs, draws) / math.comb(unseen, draws)


def draw_probability(outs: int, street: str) -> float:
    """Chance of hitting with ``outs``: ``"flop_turn"``, ``"turn_river"`` or ``"flop_river"``."""
    match street:
        case "flop_turn":
            return hit_probability(outs, 47, 1)
        case "turn_river":
            return hit_probability(outs, 46, 1)
        case "flop_river":
            return hit_probability(outs, 47, 2)
        case _:
            raise ValueError(f"unknown street {street!r}")


def rule_of_2_and_4(outs: int, cards_to_come: int) -> float:
    """Shortcut: outs x 2 % with one card to come, outs x 4 % with two (as a fraction)."""
    if cards_to_come not in (1, 2):
        raise ValueError("cards_to_come must be 1 or 2")
    return min(outs * 2 * cards_to_come, 100) / 100


def _check_bet(pot: float, bet: float) -> None:
    if pot <= 0 or bet <= 0:
        raise ValueError("pot and bet must be positive")


def required_equity(pot: float, bet: float) -> float:
    """Equity needed to call a ``bet`` into ``pot``: bet / (pot + 2 * bet)."""
    _check_bet(pot, bet)
    return bet / (pot + 2 * bet)


def pot_odds_ratio(pot: float, bet: float) -> float:
    """The X in "X to 1" pot odds when calling: (pot + bet) / bet."""
    _check_bet(pot, bet)
    return (pot + bet) / bet


def minimum_defense_frequency(pot: float, bet: float) -> float:
    """Share of the range to continue so a pure bluff cannot profit: pot / (pot + bet)."""
    _check_bet(pot, bet)
    return pot / (pot + bet)


def alpha(pot: float, bet: float) -> float:
    """Fold frequency a pure bluff needs to break even: bet / (pot + bet)."""
    _check_bet(pot, bet)
    return bet / (pot + bet)


def bluff_share(pot: float, bet: float) -> float:
    """Bluff share of a polarized river betting range that makes calls break even."""
    return required_equity(pot, bet)


def bluff_to_value(pot: float, bet: float) -> tuple[int, int]:
    """Bluff-to-value ratio in small whole numbers, e.g. (1, 2) for a pot-sized bet.

    With bet fraction b = bet / pot, bluffs : value = b : (1 + b).
    """
    _check_bet(pot, bet)
    b = bet / pot
    ratio = Fraction(b / (1 + b)).limit_denominator(20)
    return ratio.numerator, ratio.denominator


def stack_to_pot_ratio(effective_stack: float, pot: float) -> float:
    if pot <= 0 or effective_stack < 0:
        raise ValueError("pot must be positive and stack non-negative")
    return effective_stack / pot


def bet_ev(
    pot: float, bet: float, fold_probability: float, equity_when_called: float = 0.0
) -> float:
    """EV of betting, relative to checking back with no further equity.

    Win the pot when villain folds; when called, win ``equity`` of the final pot and lose the bet.
    """
    _check_bet(pot, bet)
    if not 0 <= fold_probability <= 1 or not 0 <= equity_when_called <= 1:
        raise ValueError("probabilities must be in [0, 1]")
    called = 1 - fold_probability
    return fold_probability * pot + called * (equity_when_called * (pot + 2 * bet) - bet)


def call_ev(pot: float, bet: float, equity: float) -> float:
    """EV of calling a ``bet`` into ``pot`` with ``equity``, relative to folding."""
    _check_bet(pot, bet)
    if not 0 <= equity <= 1:
        raise ValueError("equity must be in [0, 1]")
    return equity * (pot + 2 * bet) - bet


def dealt_probability(hands: Range | Iterable[HandClass]) -> float:
    """Probability of being dealt any hand in ``hands`` (full weights for plain class lists)."""
    hand_range = hands if isinstance(hands, Range) else Range.of(hands)
    return hand_range.combo_count() / STARTING_COMBOS


def odds_against(probability: float) -> float:
    """Convert a probability into "X to 1 against"."""
    if not 0 < probability <= 1:
        raise ValueError("probability must be in (0, 1]")
    return (1 - probability) / probability
