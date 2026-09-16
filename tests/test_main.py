"""Tests for the command line entry point."""

from __future__ import annotations

import io
import unittest
import unittest.mock

import main
from tests.support import IsolatedDataDir


class ParserTests(unittest.TestCase):
    def test_defaults(self):
        args = main.build_parser().parse_args([])
        self.assertFalse(args.cli)
        self.assertEqual(args.rounds, 5)
        self.assertFalse(args.allow_negative)

    def test_options_are_parsed(self):
        args = main.build_parser().parse_args(
            ["--cli", "--rounds", "3", "--seed", "9", "--players", "A", "B"]
        )
        self.assertTrue(args.cli)
        self.assertEqual(args.rounds, 3)
        self.assertEqual(args.seed, 9)
        self.assertEqual(args.players, ["A", "B"])


class DispatchTests(IsolatedDataDir):
    def test_a_full_cli_game_exits_cleanly(self):
        with unittest.mock.patch("sys.stdout", new=io.StringIO()):
            code = main.main(["--cli", "--players", "Ada", "Grace", "--auto", "--seed", "3"])
        self.assertEqual(code, 0)

    def test_zero_rounds_is_rejected(self):
        with unittest.mock.patch("sys.stderr", new=io.StringIO()) as err:
            self.assertEqual(main.main(["--rounds", "0"]), 2)
        self.assertIn("at least one round", err.getvalue())

    def test_cli_only_flags_are_rejected_for_the_gui(self):
        with unittest.mock.patch("sys.stderr", new=io.StringIO()) as err:
            self.assertEqual(main.main(["--players", "A", "B"]), 2)
        self.assertIn("--players requires --cli", err.getvalue())

    def test_a_missing_tkinter_explains_itself(self):
        with unittest.mock.patch.dict("sys.modules", {"src.gui": None}):
            with unittest.mock.patch("sys.stderr", new=io.StringIO()) as err:
                code = main.main([])
        self.assertEqual(code, 1)
        self.assertIn("--cli", err.getvalue())


if __name__ == "__main__":
    unittest.main()
