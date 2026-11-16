import pytest

from holdem.core.cards import parse_cards
from holdem.core.equity import calculate_equity
from holdem.curriculum import CONCEPT_OF_DRILL, CONCEPTS, CONCEPTS_BY_ID
from holdem.drills.math_lab import ALL_DRILLS


def test_ids_unique_and_prerequisites_valid():
    assert len(CONCEPTS_BY_ID) == len(CONCEPTS)
    for concept in CONCEPTS:
        assert concept.points
        for prereq in concept.prerequisites:
            assert prereq in CONCEPTS_BY_ID
            assert CONCEPTS_BY_ID[prereq].tier <= concept.tier


def test_prerequisites_are_acyclic():
    visiting, done = set(), set()

    def visit(cid):
        assert cid not in visiting, f"cycle through {cid}"
        if cid in done:
            return
        visiting.add(cid)
        for prereq in CONCEPTS_BY_ID[cid].prerequisites:
            visit(prereq)
        visiting.discard(cid)
        done.add(cid)

    for concept in CONCEPTS:
        visit(concept.id)


def test_every_drill_belongs_to_its_concept():
    for drill in ALL_DRILLS:
        assert CONCEPT_OF_DRILL[drill.key] == drill.concept
        assert drill.tier == CONCEPTS_BY_ID[drill.concept].tier


def test_lecture_links_are_ocw():
    for concept in CONCEPTS:
        for lecture in concept.lectures:
            assert lecture.url.startswith("https://ocw.mit.edu/courses/15-s50-")


def test_public_shape():
    data = CONCEPTS_BY_ID["outs"].public()
    assert data["drills"] == ["outs"]
    assert data["lectures"][0]["url"].startswith("https://")


def equity(hero, villain, board):
    a, b = parse_cards(hero)
    c, d = parse_cards(villain)
    return calculate_equity([(a, b), (c, d)], parse_cards(board))[0].equity


def test_postflop_equity_notes_match_the_engine():
    """The study notes quote these numbers; keep them honest."""
    board = "Kh7h2c"
    assert equity("AsKd", "QhJh", board) == pytest.approx(0.60, abs=0.03)
    assert equity("KsQd", "Ah5h", board) == pytest.approx(0.55, abs=0.03)
    assert equity("7s7d", "QhJh", board) == pytest.approx(0.73, abs=0.02)
    assert 0.5 < equity("JhTh", "AsAd", "9h8h2c") < 0.6
