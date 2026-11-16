# ♠ Winning Texas Hold'em

**A local, interactive trainer for No-Limit Texas Hold'em.** Drill the maths until it is automatic,
learn preflop charts by painting them from memory, and let spaced repetition bring each skill back
just before you forget it. Built around MIT's
[15.S50 *How to Win at Texas Hold'em*](https://ocw.mit.edu/courses/15-s50-how-to-win-at-texas-holdem-poker-january-iap-2016/).

![Python 3.13](https://img.shields.io/badge/python-3.13-3776ab?logo=python&logoColor=white)
![Svelte 5](https://img.shields.io/badge/svelte-5-ff3e00?logo=svelte&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Python coverage](https://img.shields.io/badge/python%20coverage-100%25-2ea44f)
![Tests](https://img.shields.io/badge/tests-pytest%20%7C%20vitest%20%7C%20playwright-6e40c9)

<p align="center">
  <img src="docs/images/home.png" alt="Home page with the felt-green hero and links to Learn, Math Lab, Preflop and Progress" width="880">
</p>

Every number the app shows is computed by its own engine (exact enumeration where it is feasible,
seeded Monte Carlo otherwise), and every graded answer comes with the working, not just a verdict.

---

## Contents

- [What you can do](#what-you-can-do)
- [How it teaches](#how-it-teaches)
- [Curriculum map](#curriculum-map)
- [Architecture](#architecture)
- [Getting started](#getting-started)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Sources and caveats](#sources-and-caveats)

## What you can do

### Math Lab: the numbers behind every decision

Fourteen fast, keyboard-driven drills: hand rankings, reading the board, outs, outs to percent,
pot odds, call or fold, preflop and flop equity, starting-hand odds, flop odds, combos and
blockers, stack-to-pot ratio, and MDF / alpha / bluff ratios.

<table>
  <tr>
    <td width="50%"><img src="docs/images/drill-call-or-fold.png" alt="Call-or-fold drill: equity versus the price of the call, with the EV of calling"></td>
    <td width="50%"><img src="docs/images/drill-outs.png" alt="Outs drill: the winning cards, tainted outs, and the key cards drawn below"></td>
  </tr>
  <tr>
    <td><b>Call or fold.</b> Your equity against the price, and what the call is worth in chips.</td>
    <td><b>Count your outs.</b> The exact out cards, plus the tainted ones that improve you but still lose.</td>
  </tr>
</table>

### Preflop: charts you can actually remember

Opening ranges for every 6-max seat and defending ranges against opens, at 100bb. Drills sample
mostly hands **near the edge of a range**, because AA and 72o teach nothing. After each answer the
full chart appears with your hand outlined.

<table>
  <tr>
    <td width="50%"><img src="docs/images/preflop-drill.png" alt="Preflop drill feedback with the 13x13 chart and the dealt hand outlined"></td>
    <td width="50%"><img src="docs/images/paint-the-range.png" alt="Paint-the-range result with missed hands outlined in blue"></td>
  </tr>
  <tr>
    <td><b>Spot drills</b> reveal the chart and the reasoning for the seat.</td>
    <td><b>Paint the range</b> from memory (drag with mouse or finger), then see what you missed, scored in combos.</td>
  </tr>
</table>

<img src="docs/images/preflop-overview.png" alt="Preflop overview with the weakest-spots table and the list of charts" width="880">

The Preflop page ranks your **weakest spots** and the hands you miss most in each, so you know
exactly what to drill next.

### Today: a daily session that schedules itself

<table>
  <tr>
    <td width="50%"><img src="docs/images/today.png" alt="Today page listing drills due for review and new drills"></td>
    <td width="50%"><img src="docs/images/learn.png" alt="Curriculum page with mastery badges and progress bars"></td>
  </tr>
  <tr>
    <td><b>Today</b> mixes drills that are due with a couple of new ones, interleaved.</td>
    <td><b>Learn</b> shows each concept's study notes, lecture links and your mastery.</td>
  </tr>
</table>

### Progress: where your estimates go wrong

<img src="docs/images/progress.png" alt="Progress table with accuracy, mean error, signed bias and average time per drill" width="880">

Besides accuracy and speed, every numeric drill tracks your **bias**: the average signed error.
"You underestimate preflop equity by 1.7 points" is more useful than "you got it wrong".

<details>
<summary>Dark mode</summary>

<img src="docs/images/dark-mode.png" alt="Flop equity drill in dark mode" width="880">

</details>

## How it teaches

The design follows the learning-science results that hold up best: retrieval practice, spacing,
interleaving and immediate, explained feedback.

```mermaid
flowchart LR
    A["Learn a concept<br/>notes + MIT lecture"] --> B["Drill it<br/>blocked practice"]
    B --> C["Instant feedback<br/>answer + working + key cards"]
    C --> D["FSRS review card<br/>3 answers = 1 review"]
    D --> E["Today's session<br/>due + new, interleaved"]
    E --> C
    C --> F["Progress and leaks<br/>accuracy · bias · weakest spots"]
    F -->|"practise this"| B
```

- **Spaced repetition.** Each drill has an [FSRS](https://github.com/open-spaced-repetition/py-fsrs)
  card. Once it is due, your next three answers for that drill are graded together into one review:
  3/3 is *good* (or *hard* if slow), 2/3 *hard*, otherwise *again*. Bursts of quick answers cannot
  inflate the interval.
- **Prerequisites.** New drills unlock in curriculum order, and a drill introduced today unlocks
  its follow-ups in the same session.
- **Interleaving.** Daily sessions go round-robin (A B C A B C …) instead of blocks of one drill.
- **Honest sources.** Exact maths, baseline charts and (later) heuristic advice are labelled as
  such in the UI.

## Curriculum map

Concepts and their prerequisites, generated from
[`src/holdem/curriculum.py`](src/holdem/curriculum.py). Tier 4 (postflop play) arrives with the
bot table.

```mermaid
flowchart LR
  subgraph T0["Tier 0 · Mechanics"]
    hand_rankings["Hand rankings"]
    board_reading["Reading the board"]
  end
  subgraph T1["Tier 1 · Core maths"]
    combinatorics["Combos and starting hands"]
    outs["Counting outs"]
    outs_to_odds["Outs to probability"]
    pot_odds["Pot odds and EV"]
    preflop_equity["Preflop all-in equity"]
    postflop_equity["Equity on the flop"]
    flop_odds["Flop odds"]
  end
  subgraph T2["Tier 2 · Preflop"]
    preflop_ranges["Opening ranges by position"]
    facing_a_raise["Facing a raise"]
  end
  subgraph T3["Tier 3 · Ranges"]
    spr["Stack-to-pot ratio"]
    blockers["Blockers and combo counting"]
  end
  subgraph T5["Tier 5 · Game theory"]
    mdf["MDF, alpha and bluff ratios"]
  end
  subgraph T6["Tier 6 · Tournaments"]
    icm["Push/fold and ICM"]
  end
  hand_rankings --> board_reading
  hand_rankings --> combinatorics
  board_reading --> outs
  outs --> outs_to_odds
  outs_to_odds --> pot_odds
  combinatorics --> preflop_equity
  outs_to_odds --> postflop_equity
  combinatorics --> flop_odds
  preflop_equity --> preflop_ranges
  preflop_ranges --> facing_a_raise
  pot_odds --> facing_a_raise
  pot_odds --> spr
  combinatorics --> blockers
  pot_odds --> mdf
  spr --> mdf
  preflop_equity --> icm
  pot_odds --> icm
```

## Architecture

All poker logic lives in a pure Python package with no web imports; the browser only renders and
collects input.

```mermaid
flowchart TB
    subgraph Browser["Browser · Svelte 5 + TypeScript (Vite)"]
        UI["Pages: Today · Learn · Math Lab · Preflop · Progress"]
        Grid["RangeGrid: 13x13 display and drag-to-paint"]
    end
    subgraph Server["FastAPI · src/holdem/api"]
        API["JSON API<br/>questions · answers · today · curriculum · preflop · stats"]
    end
    subgraph Core["Pure Python"]
        Drills["drills/<br/>make_question · grade · explain"]
        Sched["scheduler.py<br/>FSRS · daily plan · mastery"]
        Pre["preflop.py<br/>charts · paint grading"]
        Eng["core/<br/>cards · evaluator · ranges · equity · outs · odds"]
    end
    DB[("SQLite<br/>answers · review cards")]
    UI <--> API
    Grid <--> API
    API --> Drills
    API --> Sched
    API --> Pre
    Drills --> Eng
    Pre --> Eng
    Sched --> DB
    API --> DB
    Eng -.-> PH["phevaluator<br/>(C hand evaluator)"]
```

| Layer | Choice |
|---|---|
| Hand evaluation | [`phevaluator`](https://github.com/HenryRLee/PokerHandEvaluator), about 2.6M seven-card evaluations per second from Python |
| Equity | Exact enumeration on the flop and turn and for preflop hand-vs-hand; seeded Monte Carlo for preflop ranges and multiway |
| Scheduling | [`fsrs`](https://github.com/open-spaced-repetition/py-fsrs) (FSRS-6) |
| Server and storage | FastAPI, SQLAlchemy 2, SQLite |
| Front end | Svelte 5 runes, TypeScript, Vite; cards drawn in CSS with a four-colour deck |

## Getting started

You need [uv](https://docs.astral.sh/uv/) and Node.js (`brew install uv node` on macOS).

```sh
git clone https://github.com/kligvasser/winning-texas-holdem.git
cd winning-texas-holdem
cd web && npm install && npm run build && cd ..
uv run python -m holdem            # then open http://127.0.0.1:8000
```

Your answers are stored in `data/holdem.sqlite` (set `HOLDEM_DATA_DIR` to move it).

**Front-end development:** run `uv run python -m holdem --reload` and, in `web/`, `npm run dev`
(Vite proxies `/api` to the Python server).

**Demo data:** `uv run python scripts/seed_demo.py data/demo` creates a ten-day practice history;
start the app with `HOLDEM_DATA_DIR=data/demo` to explore the progress pages.

## Testing

```sh
uv run pytest -n 8                 # Python; fails below 100% line and branch coverage
uv run ruff check src tests && uv run pyright
cd web
npm run coverage                   # Vitest component and unit tests with coverage gates
npm run check                      # svelte-check and TypeScript
npm run e2e                        # Playwright against the real backend, desktop and phone
npm run screenshots                # regenerate the images in this README
```

- **Reference numbers are test fixtures.** The engine must reproduce the published 5-card hand
  frequencies, the outs table, the bet-size table (pot odds, MDF, alpha, bluff ratios), flop
  texture frequencies and 16 classic preflop all-in matchups by exhaustive enumeration.
- **Study notes are tested too.** Equity figures quoted in the curriculum are recomputed by the
  engine, so the notes cannot drift from the maths.
- **Coverage gates:** Python 100% line and branch; TypeScript modules 100%; Svelte components
  100% lines, statements and functions. Svelte branch coverage is gated at 85% because the
  compiler wraps every template value in `?? ""` and v8 counts each one as a branch.

## Roadmap

- [x] **Engine:** cards, evaluation, ranges, exact and Monte Carlo equity, outs, board texture, odds
- [x] **Math Lab:** 14 drills with explanations, answer log, per-drill stats and bias
- [x] **Scheduler and curriculum:** FSRS reviews, daily session, prerequisites, Learn pages
- [x] **Preflop trainer:** baseline charts, edge-weighted spot drills, paint-the-range, leak report
- [ ] **Play and review:** 6-max table against bot archetypes (nit, TAG, LAG, calling station, maniac), hand histories, review sorted by biggest mistake
- [ ] **Ranges and postflop:** range vs board, range advantage, hand-reading drill scored against the bot's true range
- [ ] **Tournaments and toy games:** push/fold Nash trainer, ICM quiz, the MIT problem-set betting game
- [ ] **Solver reference (optional):** offline heads-up flop solutions for postflop grading

## Sources and caveats

- **Course:** MIT OpenCourseWare 15.S50,
  [2016 (Will Ma)](https://ocw.mit.edu/courses/15-s50-how-to-win-at-texas-holdem-poker-january-iap-2016/)
  and [2015 (Kevin Desmond)](https://ocw.mit.edu/courses/15-s50-poker-theory-and-analytics-january-iap-2015/).
  Lecture links in the app point there.
- **Preflop charts are a self-authored baseline, not solver output.** They are shaped like modern
  charts and tested for sanity (opening ranges widen towards the button and nest inside each other),
  and every screen that shows them says so. Swap in charts you trust in
  [`src/holdem/preflop.py`](src/holdem/preflop.py).
- **For study only.** This is a training tool for play money and study, not an assistant for live
  play on poker sites.
