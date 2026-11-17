"""Your numbers at the six-max table, by position, and the leaks they point to.

Everything is computed from stored hand records (see ``PlaySession.record``). Rates come with the
number of chances behind them, because a 3-bet percentage over four hands means little.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

HERO = 0
POSITIONS = ("UTG", "HJ", "CO", "BTN", "SB", "BB")
MIN_HANDS = 20  # before a frequency is called a leak
MIN_SPOTS = 3  # graded decisions of one kind before their cost is called a leak
COSTLY_BB = 3.0
CHARTS = {
    "UTG": "utg-open",
    "HJ": "hj-open",
    "CO": "co-open",
    "BTN": "btn-open",
    "SB": "sb-open",
    "BB": "bb-vs-btn",
}


def _rate(taken: int, chances: int) -> float | None:
    return round(taken / chances, 3) if chances else None


def _hand_facts(record: dict[str, Any]) -> dict[str, Any]:
    hand = record["hand"]
    log = hand["log"]
    preflop = [a for a in log if a["street"] == "preflop" and a["kind"] != "post"]
    mine = [i for i, a in enumerate(preflop) if a["player"] == HERO]
    kinds = [preflop[i]["kind"] for i in mine]
    raises_before_me = sum(a["kind"] == "raise" for a in preflop[: mine[0]]) if mine else 0
    raisers = [a["player"] for a in preflop if a["kind"] == "raise"]
    flop = [a for a in log if a["street"] == "flop" and a["player"] == HERO]
    saw_flop = len(hand["board"]) >= 3 and "fold" not in kinds
    cbet_chance = saw_flop and bool(raisers) and raisers[-1] == HERO and bool(flop)
    cbet_chance = cbet_chance and flop[0]["to_call"] == 0
    showdown = hand["showdown"] and not hand["folded"][HERO]
    return {
        "position": hand["positions"][HERO],
        "vpip": "call" in kinds or "raise" in kinds,
        "pfr": "raise" in kinds,
        "three_bet_chance": raises_before_me == 1,
        "three_bet": raises_before_me == 1 and kinds[0] == "raise",
        "cbet_chance": cbet_chance,
        "cbet": cbet_chance and flop[0]["kind"] == "bet",
        "saw_flop": saw_flop,
        "showdown": showdown,
        "won_showdown": showdown and HERO in hand["winners"],
    }


def _leak(key: str, title: str, detail: str, page: str, arg: str, label: str) -> dict[str, str]:
    return {"key": key, "title": title, "detail": detail, "page": page, "arg": arg, "label": label}


def _leaks(
    hands: int,
    rates: dict[str, float | None],
    showdowns: int,
    positions: list[dict[str, Any]],
    costs: dict[str, list[float]],
) -> list[dict[str, str]]:
    leaks = []
    vpip, pfr, wsd = rates["vpip"], rates["pfr"], rates["wsd"]
    if hands >= MIN_HANDS and vpip is not None and pfr is not None:
        if vpip > 0.35:
            leaks.append(
                _leak(
                    "loose",
                    f"You play {vpip:.0%} of hands",
                    "A solid six-max player plays about 20 to 30%. Tighten up, most of all "
                    "from early position.",
                    "math-lab",
                    "preflop-open",
                    "Drill opening ranges",
                )
            )
        elif vpip < 0.15:
            leaks.append(
                _leak(
                    "tight",
                    f"You play only {vpip:.0%} of hands",
                    "You are folding hands that make money, most of all on the button.",
                    "math-lab",
                    "preflop-open",
                    "Drill opening ranges",
                )
            )
        if vpip - pfr > 0.15:
            leaks.append(
                _leak(
                    "passive",
                    f"You call far more than you raise ({vpip:.0%} played, {pfr:.0%} raised)",
                    "Entering pots by calling lets the bots see cheap flops. Raise or fold more.",
                    "math-lab",
                    "preflop-defend",
                    "Drill facing a raise",
                )
            )
    worst = max(positions, key=lambda p: p["loss_bb"] / p["hands"], default=None)
    if worst and worst["hands"] >= 5 and worst["loss_bb"] >= COSTLY_BB:
        leaks.append(
            _leak(
                "position",
                f"Your costliest seat is {worst['position']}",
                f"Reviewed mistakes there cost {worst['loss_bb']:g}bb over {worst['hands']} hands.",
                "preflop",
                CHARTS[worst["position"]],
                f"Study the {worst['position']} chart",
            )
        )
    for kind, title, detail, drill, label in (
        (
            "call",
            "Calling too light",
            "Compare the price with your equity before you call.",
            "call-or-fold",
            "Drill call or fold",
        ),
        (
            "fold",
            "Folding with the right price",
            "You are giving up pots where the odds were good enough.",
            "pot-odds",
            "Drill pot odds",
        ),
        (
            "push",
            "Bets and raises that lose money",
            "Bluff the bots that fold, value bet the ones that call.",
            "bluff-ev",
            "Drill bluff maths",
        ),
    ):
        losses = costs[kind]
        if len(losses) >= MIN_SPOTS and sum(losses) >= COSTLY_BB:
            leaks.append(
                _leak(
                    kind,
                    f"{title}: {round(sum(losses), 1):g}bb over {len(losses)} decisions",
                    detail,
                    "math-lab",
                    drill,
                    label,
                )
            )
    if showdowns >= 10 and wsd is not None and wsd < 0.4:
        leaks.append(
            _leak(
                "showdown",
                f"You win only {wsd:.0%} of showdowns",
                "You are reaching showdown with hands that are usually beaten.",
                "math-lab",
                "bluff-catch",
                "Drill bluff-catching",
            )
        )
    return leaks


def table_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Frequencies, results by position and leaks across finished hands."""
    count: dict[str, int] = defaultdict(int)
    seats: dict[str, dict[str, Any]] = {}
    costs: dict[str, list[float]] = {"call": [], "fold": [], "push": []}
    for record in records:
        facts = _hand_facts(record)
        for key, value in facts.items():
            if key != "position":
                count[key] += value
        loss = 0.0
        mistakes = 0
        for decision in record["decisions"]:
            if decision["verdict"] in ("leak", "mistake"):
                kind = decision["action"] if decision["action"] in ("call", "fold") else "push"
                costs[kind].append(decision["loss_bb"])
                loss += decision["loss_bb"]
                mistakes += decision["verdict"] == "mistake"
        seat = seats.setdefault(
            facts["position"],
            {"hands": 0, "net_bb": 0.0, "vpip": 0, "pfr": 0, "loss_bb": 0.0, "mistakes": 0},
        )
        seat["hands"] += 1
        seat["net_bb"] += record["net_bb"]
        seat["vpip"] += facts["vpip"]
        seat["pfr"] += facts["pfr"]
        seat["loss_bb"] += loss
        seat["mistakes"] += mistakes
    hands = len(records)
    positions = [
        {
            "position": name,
            "hands": seat["hands"],
            "net_bb": round(seat["net_bb"], 2),
            "vpip": _rate(seat["vpip"], seat["hands"]),
            "pfr": _rate(seat["pfr"], seat["hands"]),
            "loss_bb": round(seat["loss_bb"], 2),
            "mistakes": seat["mistakes"],
        }
        for name in POSITIONS
        if (seat := seats.get(name))
    ]
    rates = {
        "vpip": _rate(count["vpip"], hands),
        "pfr": _rate(count["pfr"], hands),
        "three_bet": _rate(count["three_bet"], count["three_bet_chance"]),
        "cbet": _rate(count["cbet"], count["cbet_chance"]),
        "wtsd": _rate(count["showdown"], count["saw_flop"]),
        "wsd": _rate(count["won_showdown"], count["showdown"]),
    }
    return {
        **rates,
        "three_bet_chances": count["three_bet_chance"],
        "cbet_chances": count["cbet_chance"],
        "flops_seen": count["saw_flop"],
        "showdowns": count["showdown"],
        "positions": positions,
        "leaks": _leaks(hands, rates, count["showdown"], positions, costs),
    }
