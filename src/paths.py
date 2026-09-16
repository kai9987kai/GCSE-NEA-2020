"""Filesystem locations used by the game.

The original code opened ``Leaderboard.txt`` with a bare relative path, so the
leaderboard silently moved (or vanished) depending on which directory the game
was launched from.  Everything now resolves against the project root, with an
environment override so tests and packaged installs can redirect the data
directory without touching the code.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Repository root - ``src/paths.py`` -> ``src`` -> project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

#: Set ``DICE_GAME_DATA_DIR`` to keep saves somewhere other than the checkout.
DATA_DIR_ENV = "DICE_GAME_DATA_DIR"

LEADERBOARD_FILE = "Leaderboard.txt"
USERS_FILE = "users.json"


def data_dir() -> Path:
    """Return the directory holding saved data, creating it if needed."""
    override = os.environ.get(DATA_DIR_ENV)
    directory = Path(override).expanduser().resolve() if override else PROJECT_ROOT
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def data_path(filename: str) -> Path:
    """Return an absolute path to *filename* inside the data directory."""
    return data_dir() / filename


def leaderboard_path() -> Path:
    return data_path(LEADERBOARD_FILE)


def users_path() -> Path:
    return data_path(USERS_FILE)
