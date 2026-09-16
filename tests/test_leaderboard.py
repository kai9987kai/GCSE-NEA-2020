"""Tests for high-score persistence, including the 2020 regressions."""

from __future__ import annotations

import unittest

from src.leaderboard import Entry, Leaderboard, record_result
from tests.support import IsolatedDataDir


class EntryParsingTests(unittest.TestCase):
    def test_legacy_two_column_rows_still_load(self):
        entry = Entry.parse("User1,28")
        self.assertEqual((entry.name, entry.score, entry.achieved), ("User1", 28, ""))

    def test_rows_with_a_date_column_load(self):
        entry = Entry.parse("User1,28,2020-06-01")
        self.assertEqual(entry.achieved, "2020-06-01")

    def test_surrounding_whitespace_is_tolerated(self):
        entry = Entry.parse("  User1 , 28 \n")
        self.assertEqual((entry.name, entry.score), ("User1", 28))

    def test_malformed_rows_are_skipped_rather_than_crashing(self):
        for line in ("", "   ", "no-comma", "User1,not-a-number", ",20"):
            self.assertIsNone(Entry.parse(line), line)


class RecordingTests(unittest.TestCase):
    def test_only_a_players_best_score_is_kept(self):
        """2020 appended a new row per win, so the file filled with duplicates."""
        board = Leaderboard()
        self.assertTrue(board.record("User1", 20))
        self.assertTrue(board.record("User1", 28))
        self.assertFalse(board.record("User1", 25))
        self.assertEqual(len(board), 1)
        self.assertEqual(board.best_for("User1"), 28)

    def test_ranking_is_numeric_not_alphabetical(self):
        """Text sorting used to rank 'User1,9' above 'User1,28'."""
        board = Leaderboard([Entry("Low", 9), Entry("High", 28), Entry("Mid", 10)])
        self.assertEqual([e.score for e in board.top()], [28, 10, 9])

    def test_equal_scores_are_ordered_by_name_for_a_stable_display(self):
        board = Leaderboard([Entry("Zoe", 10), Entry("Ada", 10)])
        self.assertEqual([e.name for e in board.top()], ["Ada", "Zoe"])

    def test_top_can_be_limited(self):
        board = Leaderboard([Entry(f"P{i}", i) for i in range(10)])
        self.assertEqual(len(board.top(3)), 3)

    def test_rank_of_reports_position_or_none(self):
        board = Leaderboard([Entry("Ada", 30), Entry("Zoe", 10)])
        self.assertEqual(board.rank_of("Ada"), 1)
        self.assertEqual(board.rank_of("Zoe"), 2)
        self.assertIsNone(board.rank_of("Nobody"))

    def test_a_blank_name_is_rejected(self):
        with self.assertRaises(ValueError):
            Leaderboard().record("   ", 10)

    def test_a_name_that_is_not_a_number_does_not_raise(self):
        """update_leaderboard used to call int() on the player name."""
        board = Leaderboard([Entry("User1", 20)])
        board.record("User1", 35)
        self.assertEqual(board.best_for("User1"), 35)


class PersistenceTests(IsolatedDataDir):
    def test_round_trip_through_a_file(self):
        board = Leaderboard()
        board.record("Ada", 42, achieved="2024-01-02")
        path = board.save()
        reloaded = Leaderboard.load(path)
        self.assertEqual(reloaded.best_for("Ada"), 42)
        self.assertEqual(reloaded.top()[0].achieved, "2024-01-02")

    def test_a_missing_file_loads_as_an_empty_board(self):
        self.assertEqual(len(Leaderboard.load(self.data_dir / "nope.txt")), 0)

    def test_a_legacy_file_with_duplicates_collapses_to_best_scores(self):
        path = self.data_dir / "Leaderboard.txt"
        path.write_text("User2,20\nUser1,28\nUser1,25\nUser1,20\nTest,40\n")
        board = Leaderboard.load(path)
        self.assertEqual(len(board), 3)
        self.assertEqual(board.best_for("User1"), 28)
        self.assertEqual(board.top()[0].name, "Test")

    def test_saving_does_not_leave_temporary_files_behind(self):
        Leaderboard([Entry("Ada", 1)]).save()
        stray = [p.name for p in self.data_dir.iterdir() if p.name.startswith(".")]
        self.assertEqual(stray, [])

    def test_record_result_only_writes_on_a_personal_best(self):
        self.assertTrue(record_result("Ada", 30))
        self.assertFalse(record_result("Ada", 10))
        self.assertEqual(Leaderboard.load().best_for("Ada"), 30)

    def test_the_default_path_follows_the_data_directory(self):
        record_result("Ada", 30)
        self.assertTrue((self.data_dir / "Leaderboard.txt").exists())


if __name__ == "__main__":
    unittest.main()
