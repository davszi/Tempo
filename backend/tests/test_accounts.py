"""Accounts: sign-up, sign-in, sessions, Google sign-in and moving guest progress to a new account."""
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from backend.auth import AccountExists, Accounts, NotSetUp, hash_password, password_matches
from backend.store import Store

DEMO = Path(__file__).resolve().parents[1] / "tempo_demo.sqlite"
NOW = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)


def fresh_store():
    path = Path(tempfile.mkdtemp()) / "db.sqlite"
    shutil.copy(DEMO, path)
    return Store(path)


class Passwords(unittest.TestCase):
    def test_hash_is_salted_and_verifies(self):
        first, second = hash_password("correct horse"), hash_password("correct horse")
        self.assertNotEqual(first, second)
        self.assertNotIn("correct horse", first)
        self.assertTrue(password_matches("correct horse", first))
        self.assertFalse(password_matches("wrong horse", first))
        self.assertFalse(password_matches("x", "not-a-hash"))


class EmailAccounts(unittest.TestCase):
    def setUp(self):
        self.clock = [NOW]
        self.accounts = Accounts(fresh_store(), now=lambda: self.clock[0])

    def test_register_signs_in_and_the_session_finds_the_user(self):
        user, token = self.accounts.register("Priya", " Priya@Example.com ", "longenough")
        self.assertEqual(user["email"], "priya@example.com")
        self.assertTrue(user["has_password"])
        self.assertEqual(self.accounts.user_for_token(token)["user_id"], user["user_id"])
        self.assertTrue(self.accounts.is_registered(user["user_id"]))

    def test_rejects_bad_input_and_duplicate_email(self):
        with self.assertRaises(ValueError):
            self.accounts.register("Priya", "not-an-email", "longenough")
        with self.assertRaises(ValueError):
            self.accounts.register("Priya", "a@b.co", "short")
        with self.assertRaises(ValueError):
            self.accounts.register(" ", "a@b.co", "longenough")
        self.accounts.register("Priya", "a@b.co", "longenough")
        with self.assertRaises(AccountExists):
            self.accounts.register("Someone", "A@B.co", "anotherone")

    def test_login_checks_the_password(self):
        user, _ = self.accounts.register("Priya", "a@b.co", "longenough")
        logged_in, token = self.accounts.login("A@b.co", "longenough")
        self.assertEqual(logged_in["user_id"], user["user_id"])
        with self.assertRaises(PermissionError):
            self.accounts.login("a@b.co", "wrong-password")
        with self.assertRaises(PermissionError):
            self.accounts.login("nobody@b.co", "longenough")

    def test_logout_and_expiry_end_the_session(self):
        _, token = self.accounts.register("Priya", "a@b.co", "longenough")
        self.accounts.logout(token)
        self.assertIsNone(self.accounts.user_for_token(token))
        _, token = self.accounts.login("a@b.co", "longenough")
        self.clock[0] = NOW + timedelta(days=31)
        self.assertIsNone(self.accounts.user_for_token(token))
        self.assertIsNone(self.accounts.user_for_token("made-up-token"))

    def test_a_new_account_starts_empty_and_guest_progress_stays_with_the_guest(self):
        guest = uuid4().hex
        with self.accounts.store.transaction(write=True) as db:
            line_id = db.execute("SELECT line_id FROM opening_lines LIMIT 1").fetchone()[0]
            db.execute("""INSERT INTO player_lines (player_id, line_id, learned_at, next_review_at, fsrs_state)
                          VALUES (?, ?, '2026-11-15T10:00:00+00:00', '2026-11-16T10:00:00+00:00', '{}')""", (guest, line_id))
        user, _ = self.accounts.register("Priya", "a@b.co", "longenough")
        with self.accounts.store.transaction() as db:
            mine = db.execute("SELECT COUNT(*) FROM player_lines WHERE player_id = ?", (user["user_id"],)).fetchone()[0]
            guests = db.execute("SELECT COUNT(*) FROM player_lines WHERE player_id = ?", (guest,)).fetchone()[0]
        self.assertEqual((mine, guests), (0, 1))


class GoogleAccounts(unittest.TestCase):
    def info(self, **changes):
        return {"aud": "client-1", "iss": "https://accounts.google.com", "sub": "g-123", "email": "priya@gmail.com",
                "email_verified": "true", "name": "Priya", "exp": str(int((NOW + timedelta(hours=1)).timestamp())), **changes}

    def make(self, info, client_id="client-1"):
        return Accounts(fresh_store(), google_client_id=client_id, now=lambda: NOW, google_tokeninfo=lambda _: info)

    def test_not_set_up_without_a_client_id(self):
        with self.assertRaises(NotSetUp):
            self.make(self.info(), client_id=None).google("token")

    def test_first_google_sign_in_creates_the_account_and_later_ones_reuse_it(self):
        accounts = self.make(self.info())
        first, _ = accounts.google("token")
        again, _ = accounts.google("token")
        self.assertEqual(first["user_id"], again["user_id"])
        self.assertTrue(first["google"])
        self.assertFalse(first["has_password"])

    def test_google_links_to_an_existing_email_account(self):
        accounts = self.make(self.info())
        email_user, _ = accounts.register("Priya", "priya@gmail.com", "longenough")
        google_user, _ = accounts.google("token")
        self.assertEqual(google_user["user_id"], email_user["user_id"])
        self.assertTrue(google_user["google"])

    def test_rejects_tokens_for_another_app_unverified_or_expired(self):
        for bad in (self.info(aud="someone-else"), self.info(email_verified="false"),
                    self.info(exp=str(int((NOW - timedelta(minutes=1)).timestamp()))), self.info(iss="evil.example")):
            with self.subTest(info=bad), self.assertRaises(PermissionError):
                self.make(bad).google("token")


if __name__ == "__main__":
    unittest.main()
