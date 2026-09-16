"""Tests for the match state machine, including the 2020 regressions."""

from __future__ import annotations

import random
import unittest

from src.engine import DiceGame, GameConfig, GameError, GameState
from tests.support import ScriptedRandom


def one_round_game(values, **kwargs):
    config = GameConfig(rounds=kwargs.pop("rounds", 1), **kwargs)
    return DiceGame(["One", "Two"], config=config, rng=ScriptedRandom(values))


class SetupTests(unittest.TestCase):
    def test_two_players_are_required(self):
        with self.assertRaises(GameError):
            DiceGame(["Solo"])

    def test_duplicate_names_are_rejected(self):
        """The 2020 login let the same account take both seats."""
        with self.assertRaises(GameError):
            DiceGame(["User1", "User1"])

    def test_a_match_needs_at_least_one_round(self):
        with self.assertRaises(ValueError):
            GameConfig(rounds=0)

    def test_players_start_on_zero(self):
        game = DiceGame(["One", "Two"])
        self.assertEqual(game.scores, {"One": 0, "Two": 0})
        self.assertEqual(game.current_player, "One")
        self.assertIs(game.state, GameState.IN_PROGRESS)


class ScoringTests(unittest.TestCase):
    def test_a_turn_applies_dice_adjustment_and_bonus(self):
        game = one_round_game([3, 3, 4, 1, 2])
        event = game.take_turn()
        self.assertEqual(event.player, "One")
        self.assertEqual(event.score_after, 6 + 10 + 4)

    def test_scores_stop_at_zero_by_default(self):
        game = one_round_game([3, 3, 4, 1, 2])
        game.take_turn()
        second = game.take_turn()
        self.assertEqual(second.score_after, 0)

    def test_negative_scores_are_allowed_when_configured(self):
        game = one_round_game([3, 3, 4, 1, 2], floor_at_zero=False)
        game.take_turn()
        self.assertEqual(game.take_turn().score_after, -2)

    def test_turns_alternate(self):
        game = one_round_game([1, 2, 3, 4], rounds=2)
        self.assertEqual([game.take_turn().player for _ in range(2)], ["One", "Two"])


class RoundTests(unittest.TestCase):
    def test_both_players_get_the_same_number_of_turns(self):
        """2020 ended after five *total* rolls, so player one got three."""
        game = DiceGame(["One", "Two"], rng=random.Random(5))
        while not game.is_finished:
            game.take_turn()
        turns = [event.player for event in game.history if not event.is_tie_break]
        self.assertEqual(turns.count("One"), 5)
        self.assertEqual(turns.count("Two"), 5)

    def test_round_counter_advances_once_per_full_round(self):
        game = DiceGame(["One", "Two"], config=GameConfig(rounds=3), rng=random.Random(1))
        self.assertEqual(game.round_number, 1)
        game.take_turn()
        self.assertEqual(game.round_number, 1)
        game.take_turn()
        self.assertEqual(game.round_number, 2)

    def test_playing_on_after_the_final_whistle_is_an_error(self):
        game = one_round_game([6, 4, 1, 2])
        game.take_turn()
        game.take_turn()
        self.assertTrue(game.is_finished)
        with self.assertRaises(GameError):
            game.take_turn()


class TieBreakTests(unittest.TestCase):
    def test_a_draw_goes_to_sudden_death_instead_of_hanging(self):
        """2020 left a drawn match unplayable: no winner, no way to continue."""
        game = one_round_game([1, 3, 1, 3, 2, 2, 5, 3])
        game.take_turn()
        game.take_turn()
        self.assertIs(game.state, GameState.TIE_BREAK)
        self.assertEqual(game.scores, {"One": 14, "Two": 14})

        # First roll-off is also level, so it repeats.
        game.take_turn()
        game.take_turn()
        self.assertIs(game.state, GameState.TIE_BREAK)

        game.take_turn()
        game.take_turn()
        self.assertTrue(game.is_finished)
        self.assertEqual(game.winner, "One")

    def test_tie_break_rolls_do_not_change_the_score(self):
        game = one_round_game([1, 3, 1, 3, 6, 2])
        game.take_turn()
        game.take_turn()
        scores = dict(game.scores)
        game.take_turn()
        game.take_turn()
        self.assertEqual(game.scores, scores)
        self.assertEqual(game.winner, "One")

    def test_every_match_reaches_a_winner(self):
        for seed in range(200):
            game = DiceGame(["One", "Two"], rng=random.Random(seed))
            for _ in range(500):
                if game.is_finished:
                    break
                game.take_turn()
            self.assertTrue(game.is_finished, f"seed {seed} never finished")
            self.assertIn(game.winner, ("One", "Two"))


class ReportingTests(unittest.TestCase):
    def test_standings_are_ordered_by_score(self):
        game = one_round_game([6, 4, 1, 2])
        game.take_turn()
        game.take_turn()
        self.assertEqual([name for name, _ in game.standings()], ["One", "Two"])

    def test_status_line_reports_the_winner_once_finished(self):
        game = one_round_game([6, 4, 1, 2])
        game.take_turn()
        game.take_turn()
        self.assertIn("One wins", game.status_line())

    def test_leader_is_none_while_the_scores_are_level(self):
        self.assertIsNone(DiceGame(["One", "Two"]).leader)

    def test_history_records_every_turn(self):
        game = one_round_game([6, 4, 1, 2])
        game.take_turn()
        game.take_turn()
        self.assertEqual(len(game.history), 2)
        self.assertIn("One", game.history[0].describe())

    def test_reset_starts_a_fresh_match_with_the_same_players(self):
        game = one_round_game([6, 4, 1, 2])
        game.take_turn()
        game.take_turn()
        game.reset()
        self.assertFalse(game.is_finished)
        self.assertEqual(game.scores, {"One": 0, "Two": 0})
        self.assertEqual(game.history, [])
        self.assertEqual(game.current_player, "One")


if __name__ == "__main__":
    unittest.main()
