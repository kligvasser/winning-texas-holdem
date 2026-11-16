"""Compute each starting hand's all-in equity against a random hand (writes a data file).

Usage: uv run python scripts/hand_strength.py
The table ranks hands for "top X% of hands" calling ranges in the push/fold drill.
"""

from __future__ import annotations

import json
from pathlib import Path

from holdem.core.equity import calculate_equity
from holdem.core.ranges import ALL_CLASSES, Range, combos_of_class

OUT = Path(__file__).resolve().parents[1] / "src" / "holdem" / "data" / "hand_strength.json"
SAMPLES = 30_000


def main() -> None:
    everything = Range.of(ALL_CLASSES)
    table = {}
    for i, hand_class in enumerate(ALL_CLASSES):
        combo = combos_of_class(hand_class)[0]
        result = calculate_equity([combo, everything], samples=SAMPLES, seed=i, exact_limit=0)
        table[hand_class] = round(result[0].equity, 4)
    OUT.write_text(json.dumps(dict(sorted(table.items(), key=lambda kv: -kv[1])), indent=1) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
