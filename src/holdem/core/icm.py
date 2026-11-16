"""Independent Chip Model (Malmuth-Harville): turn chip stacks into shares of a prize pool."""

from __future__ import annotations

from collections.abc import Sequence
from functools import cache


def icm_equities(stacks: Sequence[float], payouts: Sequence[float]) -> tuple[float, ...]:
    """Expected prize for each player.

    Each player finishes first with probability stack / total chips; given who finished ahead,
    the next place goes the same way among the remaining players.
    """
    if any(s <= 0 for s in stacks):
        raise ValueError("stacks must be positive")
    if not stacks:
        raise ValueError("need at least one player")
    prizes = tuple(payouts[: len(stacks)])
    chips = tuple(float(s) for s in stacks)

    @cache
    def expected(remaining: frozenset[int], place: int) -> tuple[float, ...]:
        result = [0.0] * len(chips)
        if place >= len(prizes) or not remaining:
            return tuple(result)
        total = sum(chips[i] for i in remaining)
        for i in remaining:
            p = chips[i] / total
            result[i] += p * prizes[place]
            rest = expected(remaining - {i}, place + 1)
            for j in remaining - {i}:
                result[j] += p * rest[j]
        return tuple(result)

    return expected(frozenset(range(len(chips))), 0)


def risk_premium_call(
    stacks: Sequence[float], payouts: Sequence[float], hero: int, villain: int
) -> tuple[float, float]:
    """Equity needed to call an all-in under chip EV and under ICM.

    Hero calls villain's shove for the effective stack (blinds ignored). Returns
    (chip-EV break-even, ICM break-even) as fractions.
    """
    effective = min(stacks[hero], stacks[villain])
    pot = 2 * effective
    chip_need = effective / pot
    fold = icm_equities(stacks, payouts)[hero]
    win = list(stacks)
    win[hero] += effective
    win[villain] -= effective
    lose = list(stacks)
    lose[hero] -= effective
    lose[villain] += effective
    win_equity = _without_busted(win, payouts, hero)
    lose_equity = _without_busted(lose, payouts, hero)
    # p * win + (1 - p) * lose = fold  ->  p = (fold - lose) / (win - lose)
    return chip_need, (fold - lose_equity) / (win_equity - lose_equity)


def _without_busted(stacks: list[float], payouts: Sequence[float], hero: int) -> float:
    """Hero's ICM equity after an all-in, where a busted player takes the lowest paid place left."""
    alive = [i for i, s in enumerate(stacks) if s > 0]
    if hero not in alive:
        place = len(alive)  # finishes just behind every survivor
        return payouts[place] if place < len(payouts) else 0.0
    equities = icm_equities([stacks[i] for i in alive], list(payouts))
    return equities[alive.index(hero)]
