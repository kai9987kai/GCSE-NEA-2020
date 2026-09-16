"""Tests for the dice rules."""

from __future__ import annotations

import random
import unittest

from src.rules import (
    DIE_FACES,
    EVEN_BONUS,
    ODD_PENALTY,
    TurnResult,
    play_turn,
    roll_die,
    score_dice,
)
from tests.support import ScriptedRandom


class ScoreDiceTests(unittest.TestCase):
    def test_even_total_earns_the_bonus(self):
        self.assertEqual(score_dice((2, 4)), EVEN_BONUS)

    def test_odd_total_takes_the_penalty(self):
        self.assertEqual(score_dice((1, 4)), ODD_PENALTY)


class TurnResultTests(unittest.TestCase):
    def test_points_combine_dice_adjustment_and_bonus(self):
        result = TurnResult(dice=(3, 3), adjustment=EVEN_BONUS, bonus_die=4)
        self.assertEqual(result.dice_total, 6)
        self.assertEqual(result.points, 6 + 10 + 4)
        self.assertTrue(result.is_double)

    def test_a_non_double_has_no_bonus_die(self):
        result = TurnResult(dice=(2, 5), adjustment=ODD_PENALTY)
        self.assertFalse(result.is_double)
        self.assertEqual(result.points, 7 - 5)

    def test_describe_mentions_the_double(self):
        result = TurnResult(dice=(6, 6), adjustment=EVEN_BONUS, bonus_die=2)
        self.assertIn("double", result.describe())


class PlayTurnTests(unittest.TestCase):
    def test_a_double_triggers_exactly_one_bonus_die(self):
        result = play_turn(ScriptedRandom([5, 5, 3]))
        self.assertEqual(result.dice, (5, 5))
        self.assertEqual(result.bonus_die, 3)
        self.assertEqual(result.points, 10 + EVEN_BONUS + 3)

    def test_no_bonus_die_without_a_double(self):
        result = play_turn(ScriptedRandom([2, 3]))
        self.assertIsNone(result.bonus_die)

    def test_the_same_seed_replays_the_same_turn(self):
        first = play_turn(random.Random(99))
        second = play_turn(random.Random(99))
        self.assertEqual(first, second)

    def test_dice_stay_within_range(self):
        rng = random.Random(4)
        for _ in range(500):
            for die in play_turn(rng).dice:
                self.assertIn(die, range(1, DIE_FACES + 1))

    def test_roll_die_uses_the_module_rng_by_default(self):
        self.assertIn(roll_die(), range(1, DIE_FACES + 1))


if __name__ == "__main__":
    unittest.main()
