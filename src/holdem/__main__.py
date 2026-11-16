"""Run the app: ``uv run python -m holdem`` then open http://127.0.0.1:8000."""

from __future__ import annotations

import argparse

import uvicorn


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Winning Texas Hold'em trainer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="reload on code changes")
    args = parser.parse_args(argv)
    uvicorn.run(
        "holdem.api.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
