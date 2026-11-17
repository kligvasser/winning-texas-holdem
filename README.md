# ♠ Winning Texas Hold'em

Learn No-Limit Hold'em by doing: short drills, preflop charts, and a six-seat table against five
cartoon bots that reviews every decision you make. It runs on your own machine.

<p align="center">
  <img src="docs/images/play-table.png" alt="The six-seat table with five cartoon bots, chips and bet buttons" width="820">
</p>

## What you get

- **Play** six-max against Rocky, Finn, Roxy, Moby and Blaze. Each has its own style, and your
  calls, folds, bets and raises are graded after every hand.
- **Review** any hand step by step, see your numbers by position, and get a drill for each leak.
- **Drill** the maths: outs, pot odds, equity, combos, hand reading. Every answer shows the working.
- **Memorise** preflop charts for every seat, then paint them from memory.
- **Toy games** (AKQ and a 1-to-10 card game) make bluffing and calling frequencies concrete.
- **Come back daily.** The app schedules each drill just before you would forget it.

## Run it

You need [uv](https://docs.astral.sh/uv/) and Node.js.

```sh
git clone https://github.com/kligvasser/winning-texas-holdem.git
cd winning-texas-holdem
cd web && npm install && npm run build && cd ..
uv run python -m holdem
```

Then open http://127.0.0.1:8000.

## Test it

```sh
uv run pytest -n 8                      # Python
cd web && npm run coverage && npm run e2e   # front end
```

The charts and the play review are estimates, not solver output. For study only.
