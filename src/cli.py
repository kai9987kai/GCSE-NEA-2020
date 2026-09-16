"""Terminal front end.

Useful in its own right, and useful because it exercises the whole game -
login, rules, scoring, tie-breaks and the leaderboard - on machines with no
display or no ``python3-tk`` installed, where the GUI cannot even be imported.
"""

from __future__ import annotations

import getpass
import random
from collections.abc import Sequence
from typing import TextIO

from .auth import UserStore
from .engine import DiceGame, GameConfig
from .leaderboard import Leaderboard

BANNER = r"""
  ____  _         ____
 |  _ \(_) ___ ___ / ___| __ _ _ __ ___   ___
 | | | | |/ __/ _ \ |  _ / _` | '_ ` _ \ / _ \
 | |_| | | (_|  __/ |_| | (_| | | | | | |  __/
 |____/|_|\___\___|\____|\__,_|_| |_| |_|\___|
"""


def _prompt_login(store: UserStore, seat: int, taken: Sequence[str], out: TextIO) -> str | None:
    """Ask for credentials until they check out, or the user gives up."""
    while True:
        try:
            username = input(f"Player {seat} username: ").strip()
            if not username:
                print("Username cannot be blank.", file=out)
                continue
            if username in taken:
                print(f"{username} is already playing.", file=out)
                continue
            password = getpass.getpass(f"Player {seat} password: ")
        except (EOFError, KeyboardInterrupt):
            print("\nLogin cancelled.", file=out)
            return None
        if store.authenticate(username, password):
            print(f"Welcome, {username}.\n", file=out)
            return username
        print("Invalid username or password.", file=out)


def _show_leaderboard(out: TextIO, highlight: str | None = None) -> None:
    entries = Leaderboard.load().top(10)
    if not entries:
        return
    print("\nLeaderboard", file=out)
    print("-" * 34, file=out)
    for rank, entry in enumerate(entries, start=1):
        marker = " <-" if entry.name == highlight else ""
        print(f"{rank:>2}. {entry.name:<14} {entry.score:>5}{marker}", file=out)


def play(
    players: Sequence[str],
    config: GameConfig | None = None,
    rng: random.Random | None = None,
    auto: bool = False,
    out: TextIO | None = None,
) -> str | None:
    """Run one match to completion and return the winner's name."""
    import sys

    out = out or sys.stdout
    game = DiceGame(list(players), config=config or GameConfig(), rng=rng)

    while not game.is_finished:
        print(f"\n{game.status_line()}", file=out)
        if not auto:
            try:
                input("Press Enter to roll... ")
            except (EOFError, KeyboardInterrupt):
                print("\nGame abandoned.", file=out)
                return None
        event = game.take_turn()
        print(f"  {event.describe()}", file=out)
        scores = "   ".join(f"{name}: {score}" for name, score in game.standings())
        print(f"  Scores -> {scores}", file=out)

    winner = game.winner
    assert winner is not None
    score = game.scores[winner]
    print(f"\n*** {winner} wins with {score} points! ***", file=out)

    board = Leaderboard.load()
    if board.record(winner, score):
        board.save()
        print(f"New personal best - ranked #{board.rank_of(winner)}.", file=out)
    _show_leaderboard(out, highlight=winner)
    return winner


def main(
    config: GameConfig | None = None,
    players: Sequence[str] | None = None,
    seed: int | None = None,
    login: bool = True,
    auto: bool = False,
) -> int:
    import sys

    out = sys.stdout
    print(BANNER, file=out)

    names: list[str] = list(players or ())
    if login and not names:
        store = UserStore.load()
        while len(names) < 2:
            username = _prompt_login(store, len(names) + 1, names, out)
            if username is None:
                return 1
            names.append(username)
    elif not names:
        names = ["Player 1", "Player 2"]

    rng = random.Random(seed) if seed is not None else random.Random()
    winner = play(names, config=config, rng=rng, auto=auto, out=out)
    return 0 if winner else 1
