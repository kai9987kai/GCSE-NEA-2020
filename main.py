#!/usr/bin/env python3
"""Dice Game - entry point.

python main.py              # graphical version (needs tkinter)
python main.py --cli        # terminal version
python main.py --help       # all options
"""

from __future__ import annotations

import argparse
import sys

from src.engine import DEFAULT_ROUNDS, GameConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dice-game", description="A two-player dice game.")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="play in the terminal instead of opening a window",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=DEFAULT_ROUNDS,
        metavar="N",
        help=f"turns each player takes (default: {DEFAULT_ROUNDS})",
    )
    parser.add_argument(
        "--allow-negative",
        action="store_true",
        help="let scores fall below zero instead of stopping at 0",
    )
    parser.add_argument("--seed", type=int, help="seed the dice for a reproducible game")
    parser.add_argument(
        "--players",
        nargs=2,
        metavar=("ONE", "TWO"),
        help="skip the login and use these names (--cli only)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="play every turn automatically, for demos and smoke tests (--cli only)",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = GameConfig(rounds=args.rounds, floor_at_zero=not args.allow_negative)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.cli:
        from src import cli

        return cli.main(
            config=config,
            players=args.players,
            seed=args.seed,
            login=not args.players,
            auto=args.auto,
        )

    for flag, name in ((args.players, "--players"), (args.auto, "--auto")):
        if flag:
            print(f"error: {name} requires --cli", file=sys.stderr)
            return 2

    try:
        from src import gui
    except ImportError:
        print(
            "error: tkinter is not available, so the graphical version cannot "
            "start.\n       Install it (e.g. 'sudo apt install python3-tk') or "
            "run 'python main.py --cli'.",
            file=sys.stderr,
        )
        return 1
    return gui.main(config=config)


if __name__ == "__main__":
    raise SystemExit(main())
