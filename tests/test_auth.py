"""Tests for account storage and password checking."""

from __future__ import annotations

import json
import unittest
import unittest.mock

from src.auth import (
    DEFAULT_PASSWORD,
    DEFAULT_USERNAMES,
    AuthError,
    UserStore,
    hash_password,
    verify_password,
)
from tests.support import IsolatedDataDir

#: Real hashing is deliberately slow; tests only need it to be correct.
FAST_ITERATIONS = 1000


class HashingTests(unittest.TestCase):
    def test_a_password_verifies_against_its_own_hash(self):
        encoded = hash_password("correct horse", iterations=FAST_ITERATIONS)
        self.assertTrue(verify_password("correct horse", encoded))

    def test_a_different_password_does_not_verify(self):
        encoded = hash_password("correct horse", iterations=FAST_ITERATIONS)
        self.assertFalse(verify_password("Correct Horse", encoded))

    def test_each_hash_gets_its_own_salt(self):
        self.assertNotEqual(
            hash_password("pw", iterations=FAST_ITERATIONS),
            hash_password("pw", iterations=FAST_ITERATIONS),
        )

    def test_the_hash_never_contains_the_password(self):
        self.assertNotIn("hunter2", hash_password("hunter2", iterations=FAST_ITERATIONS))

    def test_a_corrupt_hash_fails_closed(self):
        for encoded in ("", "garbage", "md5$1$salt$digest", "pbkdf2_sha256$x$y$z"):
            self.assertFalse(verify_password("pw", encoded), encoded)


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.store = UserStore()
        self.store.add("Ada", "lovelace")

    def test_the_right_password_is_accepted(self):
        self.assertTrue(self.store.authenticate("Ada", "lovelace"))

    def test_the_wrong_password_is_rejected(self):
        """2020 read 'if password == password', so anything was accepted."""
        self.assertFalse(self.store.authenticate("Ada", "anything at all"))
        self.assertFalse(self.store.authenticate("Ada", ""))

    def test_an_unknown_user_is_rejected(self):
        self.assertFalse(self.store.authenticate("Nobody", "lovelace"))

    def test_surrounding_whitespace_in_a_username_is_ignored(self):
        self.assertTrue(self.store.authenticate("  Ada  ", "lovelace"))

    def test_duplicate_accounts_are_refused(self):
        with self.assertRaises(AuthError):
            self.store.add("Ada", "another")

    def test_a_blank_username_is_refused(self):
        with self.assertRaises(AuthError):
            self.store.add("  ", "password")

    def test_short_passwords_are_refused(self):
        with self.assertRaises(AuthError):
            self.store.add("Bob", "no")

    def test_a_password_can_be_changed(self):
        self.store.set_password("Ada", "difference engine")
        self.assertFalse(self.store.authenticate("Ada", "lovelace"))
        self.assertTrue(self.store.authenticate("Ada", "difference engine"))

    def test_changing_an_unknown_password_is_an_error(self):
        with self.assertRaises(AuthError):
            self.store.set_password("Nobody", "whatever")


class StorageTests(IsolatedDataDir):
    def setUp(self):
        super().setUp()
        patcher = unittest.mock.patch("src.auth.ITERATIONS", FAST_ITERATIONS)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_first_run_seeds_the_original_demo_accounts(self):
        store = UserStore.load()
        self.assertEqual(store.usernames, sorted(DEFAULT_USERNAMES))
        self.assertTrue(store.authenticate("User1", DEFAULT_PASSWORD))
        self.assertTrue((self.data_dir / "users.json").exists())

    def test_accounts_survive_a_reload(self):
        store = UserStore.load()
        store.add("Ada", "lovelace")
        store.save()
        self.assertTrue(UserStore.load().authenticate("Ada", "lovelace"))

    def test_no_plaintext_password_is_ever_written(self):
        store = UserStore.load()
        store.add("Ada", "sekrit-passphrase")
        store.save()
        text = (self.data_dir / "users.json").read_text()
        self.assertNotIn("sekrit-passphrase", text)
        # The demo password appears nowhere but the "password_hash" key name.
        self.assertNotIn(f'"{DEFAULT_PASSWORD}"', text)
        self.assertIn("pbkdf2_sha256$", text)

    def test_the_stored_file_is_not_world_readable(self):
        path = UserStore.load().save()
        self.assertEqual(path.stat().st_mode & 0o077, 0)

    def test_a_corrupt_file_falls_back_to_the_demo_accounts(self):
        (self.data_dir / "users.json").write_text("{not json")
        self.assertTrue(UserStore.load().authenticate("User1", DEFAULT_PASSWORD))

    def test_records_without_a_hash_are_skipped(self):
        (self.data_dir / "users.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "users": {
                        "Broken": {},
                        "Ada": {"password_hash": hash_password("pw", iterations=FAST_ITERATIONS)},
                    },
                }
            )
        )
        store = UserStore.load()
        self.assertEqual(store.usernames, ["Ada"])

    def test_seeding_can_be_switched_off(self):
        self.assertEqual(len(UserStore.load(seed_if_missing=False)), 0)


if __name__ == "__main__":
    unittest.main()
