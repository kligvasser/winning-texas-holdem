from holdem.table_stats import table_report

ORDER = ["BTN", "SB", "BB", "UTG", "HJ", "CO"]


def act(street, player, kind, to_call=0):
    return {"street": street, "player": player, "kind": kind, "to_call": to_call}


def record(
    position="BTN",
    preflop=(),
    flop=(),
    board=("Kh", "7d", "2c"),
    showdown=False,
    won=False,
    folded=False,
    net=0.0,
    decisions=(),
):
    start = ORDER.index(position)
    return {
        "net_bb": net,
        "decisions": [{"action": a, "verdict": v, "loss_bb": loss} for a, v, loss in decisions],
        "hand": {
            "positions": ORDER[start:] + ORDER[:start],
            "board": list(board),
            "showdown": showdown,
            "folded": [folded, False, False, False, False, False],
            "winners": [0] if won else [1],
            "log": [act("preflop", 1, "post"), *preflop, *flop],
        },
    }


def test_empty_history():
    report = table_report([])
    assert report["vpip"] is None
    assert report["three_bet"] is None
    assert report["positions"] == []
    assert report["leaks"] == []


def test_frequencies_and_positions():
    records = [
        # Opened, bet the flop when checked to, won at showdown.
        record(
            "BTN",
            preflop=[act("preflop", 0, "raise"), act("preflop", 2, "call")],
            flop=[act("flop", 2, "check"), act("flop", 0, "bet")],
            showdown=True,
            won=True,
            net=12.5,
        ),
        # Opened, checked the flop back, lost at showdown.
        record(
            "CO",
            preflop=[act("preflop", 0, "raise"), act("preflop", 2, "call")],
            flop=[act("flop", 2, "check"), act("flop", 0, "check")],
            showdown=True,
            net=-3.0,
            decisions=[("call", "mistake", 2.0), ("bet", "leak", 0.5), ("fold", "good", 0.0)],
        ),
        # Re-raised an open and got it in before the flop: no flop action to count.
        record(
            "SB",
            preflop=[act("preflop", 3, "raise"), act("preflop", 0, "raise", 5)],
            showdown=True,
            won=True,
            net=100.0,
        ),
        # Called an open, then faced a bet on the flop and folded.
        record(
            "BB",
            preflop=[act("preflop", 3, "raise"), act("preflop", 0, "call", 3)],
            flop=[act("flop", 3, "bet"), act("flop", 0, "fold", 4)],
            folded=True,
            net=-2.5,
        ),
        # Raised first but somebody re-raised: facing a bet on the flop is not a c-bet spot.
        record(
            "UTG",
            preflop=[
                act("preflop", 0, "raise"),
                act("preflop", 3, "raise"),
                act("preflop", 0, "call", 10),
            ],
            flop=[act("flop", 3, "bet"), act("flop", 0, "call", 8)],
        ),
        # Opened and was donk-bet into: also not a c-bet spot.
        record(
            "HJ",
            preflop=[act("preflop", 0, "raise"), act("preflop", 2, "call")],
            flop=[act("flop", 2, "bet"), act("flop", 0, "call", 5)],
        ),
        # Folded before the flop; the others showed down.
        record("UTG", preflop=[act("preflop", 0, "fold")], showdown=True, folded=True, net=0.0),
        # A walk in the big blind: no action at all.
        record("BB", board=(), net=0.5),
    ]
    report = table_report(records)
    assert report["vpip"] == 0.75
    assert report["pfr"] == 0.625
    assert report["three_bet_chances"] == 2
    assert report["three_bet"] == 0.5
    assert report["cbet_chances"] == 2
    assert report["cbet"] == 0.5
    assert report["flops_seen"] == 6
    assert report["showdowns"] == 3
    assert report["wtsd"] == 0.5
    assert report["wsd"] == round(2 / 3, 3)
    assert [p["position"] for p in report["positions"]] == ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
    cutoff = report["positions"][2]
    assert cutoff == {
        "position": "CO",
        "hands": 1,
        "net_bb": -3.0,
        "vpip": 1.0,
        "pfr": 1.0,
        "loss_bb": 2.5,
        "mistakes": 1,
    }
    assert report["positions"][-1]["hands"] == 2
    assert report["leaks"] == []  # too few hands to call anything a leak


def keys(report):
    return [leak["key"] for leak in report["leaks"]]


def test_loose_passive_and_costly_leaks():
    limp = [act("preflop", 0, "call", 2)]
    records = [
        record(
            "CO",
            preflop=limp,
            showdown=True,
            net=-4.0,
            decisions=[("call", "mistake", 1.5), ("fold", "leak", 0.5), ("raise", "mistake", 2.0)],
        )
        for _ in range(20)
    ]
    report = table_report(records)
    assert keys(report) == ["loose", "passive", "position", "call", "fold", "push", "showdown"]
    position = report["leaks"][2]
    assert position["page"] == "preflop" and position["arg"] == "co-open"
    assert "80bb over 20 hands" in position["detail"]
    assert "40bb over 20 decisions" in report["leaks"][5]["title"]
    assert all(leak["label"] and leak["detail"] for leak in report["leaks"])


def test_tight_leak_and_healthy_numbers():
    fold = [act("preflop", 0, "fold", 2)]
    tight = table_report([record("BTN", preflop=fold, board=()) for _ in range(20)])
    assert keys(tight) == ["tight"]
    opened = [act("preflop", 0, "raise")]
    healthy = [record("BTN", preflop=opened if i < 5 else fold, board=()) for i in range(20)]
    assert keys(table_report(healthy)) == []
    # A few cheap slips in one seat are not a leak yet.
    cheap = [record("SB", preflop=fold, decisions=[("call", "leak", 0.3)]) for _ in range(5)]
    assert keys(table_report(cheap)) == []
    # Ten showdowns and most of them won.
    winner = [record("BTN", preflop=opened, showdown=True, won=True) for _ in range(10)]
    assert keys(table_report(winner)) == []
