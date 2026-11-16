"""Every drill the app knows, in curriculum order within each module."""

from __future__ import annotations

from holdem.drills.base import Drill
from holdem.drills.math_lab import ALL_DRILLS as MATH_DRILLS
from holdem.drills.preflop import PREFLOP_DRILLS
from holdem.drills.scenarios import SCENARIO_DRILLS

ALL_DRILLS: tuple[Drill, ...] = (*MATH_DRILLS, *PREFLOP_DRILLS, *SCENARIO_DRILLS)
DRILLS: dict[str, Drill] = {d.key: d for d in ALL_DRILLS}
