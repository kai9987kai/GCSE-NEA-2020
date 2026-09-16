"""Persistent high scores.

Replaces the original ``add_winner`` / ``update_leaderboard`` /
``save_leaderboard`` trio, which had three demonstrable faults:

* ``update_leaderboard`` compared a score *string* against an ``int``, so a
  personal best was never actually updated - and on the one input where the
  comparison did match it called ``int()`` on a player name and raised
  ``ValueError``;
* every win was appended as a new row, so the file filled with duplicates;
* rows were sorted as text, which ranks ``User1,9`` above ``User1,28``.

The file keeps the legacy ``Name,Score`` layout so existing ``Leaderboard.txt``
files load unchanged; new rows gain an ISO date column, and readers tolerate
both shapes.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .paths import leaderboard_path


@dataclass(frozen=True)
class Entry:
    """One player's personal best."""

    name: str
    score: int
    achieved: str = ""

    def to_line(self) -> str:
        return f"{self.name},{self.score},{self.achieved}".rstrip(",")

    @classmethod
    def parse(cls, line: str) -> Entry | None:
        """Parse a stored row, returning ``None`` for anything malformed."""
        fields = [field.strip() for field in line.strip().split(",")]
        if len(fields) < 2 or not fields[0]:
            return None
        try:
            score = int(fields[1])
        except ValueError:
            return None
        achieved = fields[2] if len(fields) > 2 else ""
        return cls(name=fields[0], score=score, achieved=achieved)


class Leaderboard:
    """A player-keyed table of best scores, highest first."""

    def __init__(self, entries: Iterable[Entry] | None = None) -> None:
        self._entries: dict[str, Entry] = {}
        for entry in entries or ():
            self.record(entry.name, entry.score, entry.achieved)

    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, name: object) -> bool:
        return name in self._entries

    def best_for(self, name: str) -> int | None:
        entry = self._entries.get(name)
        return entry.score if entry else None

    def record(self, name: str, score: int, achieved: str | None = None) -> bool:
        """Store *score* for *name*, keeping only their best.

        Returns ``True`` when this is a new personal best.
        """
        name = name.strip()
        if not name:
            raise ValueError("a leaderboard entry needs a player name")
        previous = self._entries.get(name)
        if previous is not None and previous.score >= score:
            return False
        stamp = achieved if achieved is not None else date.today().isoformat()
        self._entries[name] = Entry(name=name, score=score, achieved=stamp)
        return True

    def top(self, limit: int | None = None) -> list[Entry]:
        """Entries ranked by score (descending), then name for stability."""
        ranked = sorted(self._entries.values(), key=lambda e: (-e.score, e.name))
        return ranked[:limit] if limit else ranked

    def rank_of(self, name: str) -> int | None:
        """1-based position of *name*, or ``None`` if they are not listed."""
        for position, entry in enumerate(self.top(), start=1):
            if entry.name == name:
                return position
        return None

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: str | Path | None = None) -> Leaderboard:
        """Read a leaderboard file, ignoring blank and malformed rows."""
        target = Path(path) if path is not None else leaderboard_path()
        board = cls()
        try:
            text = target.read_text(encoding="utf-8")
        except (FileNotFoundError, IsADirectoryError):
            return board
        except OSError:
            return board
        for line in text.splitlines():
            entry = Entry.parse(line)
            if entry is not None:
                board.record(entry.name, entry.score, entry.achieved)
        return board

    def save(self, path: str | Path | None = None) -> Path:
        """Write the table out atomically so a crash cannot truncate it."""
        target = Path(path) if path is not None else leaderboard_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(f"{entry.to_line()}\n" for entry in self.top())
        handle, temp_name = tempfile.mkstemp(
            dir=str(target.parent), prefix=".leaderboard-", suffix=".tmp"
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, target)
        except BaseException:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
            raise
        return target


def record_result(name: str, score: int, path: str | Path | None = None) -> bool:
    """Load, update and save in one step. Returns ``True`` on a personal best."""
    board = Leaderboard.load(path)
    improved = board.record(name, score)
    if improved:
        board.save(path)
    return improved
