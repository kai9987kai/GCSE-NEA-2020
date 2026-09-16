"""Shared test helpers."""

from __future__ import annotations

import os
import random
import tempfile
import unittest
from collections.abc import Iterable
from pathlib import Path

from src.paths import DATA_DIR_ENV


class ScriptedRandom(random.Random):
    """A ``random.Random`` that hands back queued values, for exact scenarios."""

    def __init__(self, values: Iterable[int]) -> None:
        super().__init__(0)
        self.values: list[int] = list(values)

    def randint(self, a: int, b: int) -> int:  # noqa: D102 - matches stdlib
        if not self.values:
            raise AssertionError("ScriptedRandom ran out of queued dice")
        return self.values.pop(0)


class IsolatedDataDir(unittest.TestCase):
    """Base case that points the game's save files at a temp directory."""

    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self._previous = os.environ.get(DATA_DIR_ENV)
        os.environ[DATA_DIR_ENV] = self._tmp.name
        self.data_dir = Path(self._tmp.name)
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        if self._previous is None:
            os.environ.pop(DATA_DIR_ENV, None)
        else:
            os.environ[DATA_DIR_ENV] = self._previous
        self._tmp.cleanup()
