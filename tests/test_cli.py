"""End-to-end tests for the terminal front end."""

from __future__ import annotations

import io
import random
import unittest
import unittest.mock

from src import cli
from src.engine import GameConfig
from src.leaderboard import Leaderboard
from tests.support import IsolatedDataDir


class PlayTests(IsolatedDataDir):
    def test_a_full_match_reports_a_winner(self):
        out = io.StringIO()
        winner = cli.play(
            ["Ada", "Grace"],
            config=GameConfig(rounds=3),
            rng=random.Random(11),
            auto=True,
            out=out,
        )
        self.assertIn(winner, ("Ada", "Grace"))
        text = out.getvalue()
        self.assertIn(f"{winner} wins", text)
        self.assertIn("Round 3 of 3", text)

    def test_the_winner_is_written_to_the_leaderboard(self):
        out = io.StringIO()
        winner = cli.play(["Ada", "Grace"], rng=random.Random(11), auto=True, out=out)
        self.assertIsNotNone(Leaderboard.load().best_for(winner))

    def test_an_abandoned_game_returns_no_winner(self):
        out = io.StringIO()
        with unittest.mock.patch("builtins.input", side_effect=EOFError):
            self.assertIsNone(cli.play(["Ada", "Grace"], auto=False, out=out))
        self.assertIn("abandoned", out.getvalue())

    def test_the_same_seed_replays_the_same_match(self):
        def run():
            return cli.play(["Ada", "Grace"], rng=random.Random(4), auto=True, out=io.StringIO())

        self.assertEqual(run(), run())


class MainTests(IsolatedDataDir):
    def test_named_players_skip_the_login(self):
        with unittest.mock.patch("sys.stdout", new=io.StringIO()):
            code = cli.main(players=["Ada", "Grace"], seed=7, login=False, auto=True)
        self.assertEqual(code, 0)

    def test_a_cancelled_login_exits_non_zero(self):
        with unittest.mock.patch("builtins.input", side_effect=EOFError):
            with unittest.mock.patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(cli.main(auto=True), 1)


if __name__ == "__main__":
    unittest.main()
