"""The curriculum: concepts in tiers, their prerequisites, lecture links and short study notes.

Tiers and dependencies follow the skill tree in the research notes. Lecture references point to the
MIT OpenCourseWare pages for 15.S50 (2016, Will Ma) and 15.S50 (2015, Kevin Desmond).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

OCW_2016 = "https://ocw.mit.edu/courses/15-s50-how-to-win-at-texas-holdem-poker-january-iap-2016/"
OCW_2015 = "https://ocw.mit.edu/courses/15-s50-poker-theory-and-analytics-january-iap-2015/"
VIDEOS_2016 = OCW_2016 + "video_galleries/lecture-videos/"
SLIDES_2016 = OCW_2016 + "pages/lecture-slides/"
ASSIGNMENTS_2016 = OCW_2016 + "pages/assignments/"


@dataclass(frozen=True)
class Lecture:
    label: str
    url: str


@dataclass(frozen=True)
class Concept:
    id: str
    title: str
    tier: int
    summary: str
    points: tuple[str, ...]
    prerequisites: tuple[str, ...] = ()
    lectures: tuple[Lecture, ...] = ()
    drills: tuple[str, ...] = field(default=())

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "tier": self.tier,
            "summary": self.summary,
            "points": list(self.points),
            "prerequisites": list(self.prerequisites),
            "lectures": [{"label": lec.label, "url": lec.url} for lec in self.lectures],
            "drills": list(self.drills),
        }


L16_1 = Lecture("2016 L1 · Overview and Introduction", VIDEOS_2016)
L16_2 = Lecture("2016 L2 · Introduction to Postflop Play", VIDEOS_2016)
L16_3 = Lecture("2016 L3 · Tournaments vs. Cash Games", VIDEOS_2016)
L16_4 = Lecture("2016 L4 · Preflop Re-raising Theory", VIDEOS_2016)
L16_6 = Lecture("2016 L6 · Independent Chip Model", VIDEOS_2016)
L16_7 = Lecture("2016 L7 · Combinatorial Hand Analysis", VIDEOS_2016)
PS1 = Lecture("2016 Problem Set 1 (with solutions)", ASSIGNMENTS_2016)
PS2 = Lecture("2016 Problem Set 2: the Jen vs Bill game", ASSIGNMENTS_2016)
SLIDES = Lecture("2016 lecture slides", SLIDES_2016)
L15_1 = Lecture("2015 L1 · Introduction to Poker Theory", OCW_2015)
L15_2 = Lecture("2015 L2 · Analytical Techniques", OCW_2015)
L15_3 = Lecture("2015 L3 · Basic Strategy", OCW_2015)
L15_4 = Lecture("2015 L4 · Preflop Analysis", OCW_2015)
L15_5 = Lecture("2015 L5 · Tournament Play", OCW_2015)
L15_7 = Lecture("2015 L7 · Game Theory (Bill Chen)", OCW_2015)

CONCEPTS: tuple[Concept, ...] = (
    Concept(
        id="hand-rankings",
        title="Hand rankings",
        tier=0,
        summary="The nine hand categories and how ties are broken.",
        points=(
            "From best to worst: straight flush, four of a kind, full house, flush, straight, "
            "three of a kind, two pair, one pair, high card.",
            "You always play the best five cards from your two hole cards and the five on the "
            "board. You may use both, one or none of your hole cards.",
            "Ties are broken by the ranks inside the category, then by kickers. Suits never "
            "break ties.",
            "A-2-3-4-5 (the wheel) is the lowest straight; the ace plays low only there.",
        ),
        lectures=(L16_1,),
        drills=("hand-ranking",),
    ),
    Concept(
        id="board-reading",
        title="Reading the board",
        tier=0,
        summary="Finding the nuts and working out what beats you.",
        points=(
            "Start with the board: is it paired (full houses possible), are there three of a "
            "suit (flushes), three cards within a five-rank window (straights)?",
            "The nuts is the best hand possible given the board. On an unpaired board without "
            "three of a suit, it is usually a straight or a set.",
            "When the board plays (your hole cards do not improve it), the pot is split.",
        ),
        prerequisites=("hand-rankings",),
        lectures=(L16_1, PS1),
        drills=("showdown", "nuts"),
    ),
    Concept(
        id="combinatorics",
        title="Combos and starting hands",
        tier=1,
        summary="1,326 starting combos, how many each hand has, and how blockers remove them.",
        points=(
            "A pocket pair has 6 combos, a suited hand 4, an offsuit hand 12, so an unpaired "
            "hand like AK has 16.",
            "Being dealt a specific pair (say AA) is 6 / 1,326 = 1 in 221. Any pair is 78 / "
            "1,326, about 1 in 17.",
            "Each visible card removes combos: if an ace is on the board, AA has 3 combos left "
            "and AK has 12.",
            "Combo counting is how you weigh value hands against bluffs in a range.",
        ),
        prerequisites=("hand-rankings",),
        lectures=(PS1, L16_7),
        drills=("dealt-odds",),
    ),
    Concept(
        id="outs",
        title="Counting outs",
        tier=1,
        summary="Cards that turn a losing hand into the winner.",
        points=(
            "Common counts: flush draw 9, open-ended straight draw 8, gutshot 4, two overcards "
            "6, pocket pair to a set 2.",
            "Combination draws add up, minus overlap: flush draw plus open-ender is 15.",
            "Tainted outs improve your hand but also give the opponent a better one (a flush "
            "card that pairs the board against a set). Do not count them.",
        ),
        prerequisites=("board-reading",),
        lectures=(L16_1, PS1),
        drills=("outs",),
    ),
    Concept(
        id="outs-to-odds",
        title="Outs to probability",
        tier=1,
        summary="Turning outs into a percentage, exactly and with the rule of 2 and 4.",
        points=(
            "One card to come: outs / 47 on the flop, outs / 46 on the turn.",
            "Both cards (all in on the flop): 1 - C(47 - outs, 2) / C(47, 2).",
            "Rule of 2 and 4: outs x 2 with one card to come, outs x 4 with two. Above about 8 "
            "outs the x 4 rule overestimates (15 outs: 60% vs 54%).",
            "The two-card figure only applies when you see both cards for one price.",
        ),
        prerequisites=("outs",),
        lectures=(L16_1,),
        drills=("draw-odds",),
    ),
    Concept(
        id="pot-odds",
        title="Pot odds and EV",
        tier=1,
        summary="Comparing your equity with the price of a call.",
        points=(
            "Equity needed to call = call / (pot after you call). Facing a bet b into pot P: "
            "b / (P + 2b).",
            "Half-pot needs 25%, two-thirds needs 28.6%, pot needs 33.3%.",
            "Call when your equity beats the price; the difference times the final pot is your "
            "expected value.",
            "Judge decisions by EV, not by whether the river card came: results vary, good "
            "decisions win in the long run.",
        ),
        prerequisites=("outs-to-odds",),
        lectures=(L16_1, L15_1),
        drills=("pot-odds", "call-or-fold"),
    ),
    Concept(
        id="preflop-equity",
        title="Preflop all-in equity",
        tier=1,
        summary="The handful of matchups that cover almost every preflop all-in.",
        points=(
            "Pair vs two overcards: about 55/45 (QQ vs AKo is 57/43).",
            "Overpair vs underpair: about 80/20 (AA vs KK is 81/19).",
            "Dominated hand (AK vs AQ, AK vs KQ): about 70-75 / 25-30.",
            "Two overcards vs two undercards: about 60-65 / 35-40, less against suited connectors.",
            "Pair vs one overcard and one undercard: about 70/30.",
        ),
        prerequisites=("combinatorics",),
        lectures=(L15_4,),
        drills=("preflop-equity",),
    ),
    Concept(
        id="postflop-equity",
        title="Equity on the flop",
        tier=1,
        summary="Estimating how often you win when all the money goes in on the flop.",
        points=(
            "Start from your outs and the rule of 4, then adjust for tainted outs and for "
            "backdoor draws.",
            "Top pair vs a flush draw is roughly 60/40, closer to 55/45 when the draw also has "
            "an overcard; a set vs a flush draw is roughly 73/27.",
            "Big combination draws (15 outs) are slight favourites even against an overpair.",
        ),
        prerequisites=("outs-to-odds",),
        lectures=(L16_2,),
        drills=("flop-equity",),
    ),
    Concept(
        id="flop-odds",
        title="Flop odds",
        tier=1,
        summary="How often the flop helps you.",
        points=(
            "A pocket pair flops a set or better 11.8% of the time, about 1 in 8.5.",
            "Two unpaired cards pair at least one of them 32.4% of the time.",
            "Suited cards flop a flush draw about 11% of the time and a flush under 1%.",
            "This is why set-mining needs deep stacks: you miss about seven times in eight.",
        ),
        prerequisites=("combinatorics",),
        lectures=(L16_1,),
        drills=("flop-odds",),
    ),
    Concept(
        id="preflop-ranges",
        title="Opening ranges by position",
        tier=2,
        summary="Which hands to open when it is folded to you, seat by seat.",
        points=(
            "Later position means more hands: in the baseline chart UTG opens about 19% of "
            "hands, the cutoff about 29% and the button about 44%.",
            "Learn the structure, not cells: pairs, suited aces and suited broadways open almost "
            "everywhere; offsuit hands and small suited connectors are added as you move "
            "towards the button.",
            "Course-era ranges are dated; modern charts are wider on the button and tighter "
            "early. The built-in charts are a self-authored baseline, not solver output.",
        ),
        prerequisites=("preflop-equity",),
        lectures=(L15_3, L15_4),
        drills=("preflop-open",),
    ),
    Concept(
        id="facing-a-raise",
        title="Facing a raise",
        tier=2,
        summary="3-bet, call or fold against an open, depending on who opened and where you sit.",
        points=(
            "Defend tighter against early-position opens: their range is stronger.",
            "The big blind closes the action and gets a good price, so it defends the widest.",
            "3-bet hands that are well ahead of the opener's range for value, plus some suited "
            "hands with blockers (A5s, A4s) or playability as bluffs.",
            "Out of position in the small blind, a 3-bet-or-fold strategy avoids playing a "
            "bloated multiway pot without position.",
        ),
        prerequisites=("preflop-ranges", "pot-odds"),
        lectures=(L16_4, L15_4),
        drills=("preflop-defend",),
    ),
    Concept(
        id="spr",
        title="Stack-to-pot ratio",
        tier=3,
        summary="How deep the stacks are relative to the pot on the flop.",
        points=(
            "SPR = effective stack / pot on the flop.",
            "At 100bb a single-raised pot has SPR around 13-18; a 3-bet pot around 4; a 4-bet "
            "pot under 2.",
            "Low SPR: top pair and overpairs are happy to get all in. High SPR: you need "
            "stronger hands to stack off.",
            "Three pot-sized bets get in 13 times the flop pot; two get in 4 times.",
        ),
        prerequisites=("pot-odds",),
        lectures=(L16_2,),
        drills=("spr",),
    ),
    Concept(
        id="blockers",
        title="Blockers and combo counting",
        tier=3,
        summary="Counting how many combos of a hand remain once you see some cards.",
        points=(
            "Start from the full count (pair 6, suited 4, offsuit 12) and remove every combo "
            "that uses a card you can see.",
            "A pair with one card of its rank visible has 3 combos; with two visible, 1.",
            "AK with one ace visible has 12 combos instead of 16; with an ace and a king, 9.",
            "Holding a blocker to the nuts makes a bluff more credible and a call less likely "
            "to be beaten.",
        ),
        prerequisites=("combinatorics",),
        lectures=(L16_7,),
        drills=("combos",),
    ),
    Concept(
        id="range-equity",
        title="Equity against a range",
        tier=3,
        summary="Thinking in ranges: how often a range hits a flop, and how you fare against it.",
        points=(
            "Villains do not hold one hand; they hold every hand their actions allow. Weigh "
            "your equity across all of them.",
            "Unpaired flops miss most ranges: a typical opening range makes a pair or better "
            "only about a third of the time.",
            "Ask two questions: what share of the range am I ahead of now, and how often do I "
            "improve against the rest?",
        ),
        prerequisites=("postflop-equity", "preflop-ranges"),
        lectures=(L16_7, L16_2),
        drills=("range-hits", "range-equity"),
    ),
    Concept(
        id="implied-odds",
        title="Implied odds",
        tier=3,
        summary="Calling a draw without the direct price, counting on winning more when you hit.",
        points=(
            "If your hit chance is below the pot odds, a call needs extra winnings later.",
            "Break-even extra = bet / hit chance - pot - 2 x bet.",
            "Implied odds are best with disguised draws and deep stacks, worst when the "
            "draw is obvious or the opponent cannot pay you.",
            "Reverse implied odds: when you hit but still lose (a weaker flush), the draw is "
            "worth less than its outs suggest.",
        ),
        prerequisites=("pot-odds", "spr"),
        lectures=(L16_2,),
        drills=("implied-odds",),
    ),
    Concept(
        id="fold-equity",
        title="Bluffs and fold equity",
        tier=4,
        summary="Why betting wins pots you cannot win at showdown.",
        points=(
            "EV of a bet = fold% x pot + call% x (your result when called).",
            "A pure bluff breaks even when villain folds bet / (pot + bet) of the time.",
            "Semi-bluffs add the equity of your draw when called, so they need fewer folds.",
            "Bluff where the opponent's range is weak and capped, not into strength.",
        ),
        prerequisites=("pot-odds",),
        lectures=(L16_2, L15_3),
        drills=("bluff-ev",),
    ),
    Concept(
        id="street-by-street",
        title="Playing a hand street by street",
        tier=4,
        summary="Chaining preflop ranges, pot odds and fold equity through one hand.",
        points=(
            "Each street narrows the opponent's range: use their actions to decide which "
            "hands are left.",
            "Facing a bet with a draw: compare your one-card equity with the price, then "
            "decide whether implied odds make up the gap.",
            "When the draw misses, your hand can only win by betting: bluff when the "
            "opponent's range folds often enough.",
        ),
        prerequisites=("facing-a-raise", "fold-equity", "implied-odds"),
        lectures=(L16_2, L16_7),
        drills=("hand-story",),
    ),
    Concept(
        id="bluff-catching",
        title="Bluff-catching",
        tier=5,
        summary="Calling a river bet with a hand that only beats bluffs.",
        points=(
            "With a pure bluff-catcher your equity is simply the share of bluffs in their "
            "betting range.",
            "Call when bluffs / (value + bluffs) beats the price: bet / (pot + 2 x bet).",
            "Count combos: a few extra bluff combos can turn a fold into a clear call.",
            "Against players who rarely bluff the river, fold more than the balance math says.",
        ),
        prerequisites=("mdf", "blockers"),
        lectures=(L16_7, L15_7),
        drills=("bluff-catch",),
    ),
    Concept(
        id="mdf",
        title="MDF, alpha and bluff ratios",
        tier=5,
        summary="How often to defend, and how many bluffs a bet size supports.",
        points=(
            "Minimum defense frequency = pot / (pot + bet). Against a pot bet you defend 50%.",
            "Alpha = bet / (pot + bet): how often a pure bluff must work to break even.",
            "On the river a polarized betting range should be bet / (pot + 2 x bet) bluffs, the "
            "same number as the caller's required equity: 1 bluff to 2 value for a pot bet.",
            "MDF is a study benchmark. Against players who bluff too little, fold more.",
        ),
        prerequisites=("pot-odds", "spr"),
        lectures=(L16_4, L15_7, PS2),
        drills=("defense",),
    ),
    Concept(
        id="icm",
        title="Push/fold and ICM",
        tier=6,
        summary="Short-stack tournament play: shove-or-fold decisions and prize equity.",
        points=(
            "Under about 10-15bb, shoving or folding is close to optimal: no room to raise "
            "and fold.",
            "Shove EV = fold% x the blinds + call% x (equity x final pot - your stack); "
            "compare it with folding.",
            "ICM converts chip stacks into prize equity: chips you lose are worth more than "
            "chips you win, so calls near the money need more equity than chip odds say.",
            "Short stacks are worth more than their chip share and big stacks less.",
        ),
        prerequisites=("preflop-equity", "pot-odds"),
        lectures=(L16_3, L16_6, L15_5),
        drills=("push-fold", "icm-equity"),
    ),
)

CONCEPTS_BY_ID: dict[str, Concept] = {c.id: c for c in CONCEPTS}
CONCEPT_OF_DRILL: dict[str, str] = {d: c.id for c in CONCEPTS for d in c.drills}
COURSE_MATERIALS = (SLIDES, Lecture("2015 course home", OCW_2015))
