# Winning Texas Hold'em

A local training app for No-Limit Texas Hold'em, built around MIT 15.S50. Drill the maths until it is
automatic, with every answer computed by the engine and explained.

## Run

Needs [uv](https://docs.astral.sh/uv/) and Node.js.

```sh
cd web && npm install && npm run build && cd ..
uv run python -m holdem          # open http://127.0.0.1:8000
```

For front-end development, run `uv run python -m holdem --reload` and `npm run dev` in `web/`
(Vite proxies `/api` to the Python server).

Your answers are stored in `data/holdem.sqlite` (set `HOLDEM_DATA_DIR` to move it).

## Test

```sh
uv run pytest -n 8               # Python, fails below 100% line and branch coverage
uv run ruff check src tests && uv run pyright
cd web
npm run coverage                 # Vitest component and unit tests with coverage gates
npm run check                    # svelte-check and TypeScript
npm run e2e                      # Playwright against the real backend (desktop and phone)
```

## Layout

- `src/holdem/core` – cards, evaluation, ranges, equity, outs, odds (no web imports)
- `src/holdem/drills` – drill generators, grading and explanations
- `src/holdem/api` – FastAPI app; serves the built front end
- `web/` – Svelte 5 + TypeScript front end
