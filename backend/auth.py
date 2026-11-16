"""Player accounts: email and password, Google sign-in, and cookie sessions.

A signed-in player's ID is their account's user_id, so practice data is stored exactly as for a guest
(player_lines and practice_events keyed by player_id). A new account always starts empty: progress made
as a guest stays with the guest.
"""

import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import uuid4

from .store import run_statements, timestamp

ACCOUNT_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT,
    google_sub TEXT UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS auth_sessions_user ON auth_sessions (user_id);
"""

SESSION_DAYS = 30
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 200
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
GOOGLE_TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"


class AccountExists(Exception):
    """An account already uses this email address."""


class NotSetUp(Exception):
    """A sign-in method is not configured on this server."""


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"


def password_matches(password, stored):
    try:
        _, n, r, p, salt, expected = stored.split("$")
        digest = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt),
                                n=int(n), r=int(r), p=int(p), dklen=len(expected) // 2)
    except (AttributeError, ValueError):
        return False
    return hmac.compare_digest(digest.hex(), expected)


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _clean_email(email):
    if not isinstance(email, str) or not EMAIL_PATTERN.match(email.strip()):
        raise ValueError("Enter a valid email address")
    return email.strip().lower()


def _clean_name(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Enter your name")
    return name.strip()[:60]


def _check_password(password):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Use at least {MIN_PASSWORD_LENGTH} characters for your password")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError("That password is too long")


def fetch_google_tokeninfo(credential):
    """Ask Google to check an ID token from the Sign in with Google button."""
    with urlopen(f"{GOOGLE_TOKENINFO}?{urlencode({'id_token': credential})}", timeout=10) as response:
        return json.load(response)


class Accounts:
    def __init__(self, store, *, google_client_id=None, now=None, google_tokeninfo=fetch_google_tokeninfo):
        self.store = store
        self.google_client_id = google_client_id or None
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.google_tokeninfo = google_tokeninfo
        with store.transaction(write=True) as db:
            run_statements(db, ACCOUNT_SCHEMA)

    # ---- public account data

    @staticmethod
    def public(row):
        return {
            "user_id": row["user_id"], "name": row["name"], "email": row["email"],
            "has_password": row["password_hash"] is not None, "google": row["google_sub"] is not None,
        }

    def is_registered(self, player_id):
        with self.store.transaction() as db:
            return db.execute("SELECT 1 FROM users WHERE user_id = ?", (player_id,)).fetchone() is not None

    # ---- sign-up and sign-in

    def register(self, name, email, password):
        name, email = _clean_name(name), _clean_email(email)
        _check_password(password)
        with self.store.transaction(write=True) as db:
            if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
                raise AccountExists("An account with this email already exists. Sign in instead.")
            user_id = self._create_user(db, name, email, hash_password(password), None)
            return self._sign_in(db, user_id)

    def login(self, email, password):
        email = _clean_email(email)
        if not isinstance(password, str):
            raise ValueError("Enter your password")
        with self.store.transaction(write=True) as db:
            row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if row is None or row["password_hash"] is None or not password_matches(password, row["password_hash"]):
                raise PermissionError("That email and password don't match an account")
            return self._sign_in(db, row["user_id"])

    def google(self, credential):
        if not self.google_client_id:
            raise NotSetUp("Google sign-in isn't set up on this server yet")
        if not isinstance(credential, str) or not credential:
            raise ValueError("Missing Google credential")
        try:
            info = self.google_tokeninfo(credential)
        except Exception as error:   # network or Google rejected the token
            raise PermissionError("Google couldn't confirm this sign-in. Try again.") from error
        if (info.get("aud") != self.google_client_id or info.get("iss") not in GOOGLE_ISSUERS
                or str(info.get("email_verified")).lower() != "true"
                or int(info.get("exp", 0)) <= self.now().timestamp()):
            raise PermissionError("Google couldn't confirm this sign-in. Try again.")
        sub, email = info["sub"], _clean_email(info["email"])
        name = (info.get("name") or email.split("@")[0]).strip()[:60]
        with self.store.transaction(write=True) as db:
            row = (db.execute("SELECT * FROM users WHERE google_sub = ?", (sub,)).fetchone()
                   or db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone())
            if row is None:
                user_id = self._create_user(db, name, email, None, sub)
            else:
                user_id = row["user_id"]
                if row["google_sub"] is None:   # Google confirmed the email, so link it to that account
                    db.execute("UPDATE users SET google_sub = ? WHERE user_id = ?", (sub, user_id))
            return self._sign_in(db, user_id)

    # ---- sessions

    def user_for_token(self, token):
        if not token:
            return None
        with self.store.transaction() as db:
            row = db.execute(
                """SELECT u.* FROM auth_sessions AS s JOIN users AS u USING (user_id)
                   WHERE s.token_hash = ? AND s.expires_at > ?""",
                (_token_hash(token), timestamp(self.now())),
            ).fetchone()
        return self.public(row) if row else None

    def logout(self, token):
        if token:
            with self.store.transaction(write=True) as db:
                db.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (_token_hash(token),))

    # ---- account settings (the caller has already checked the session)

    def update_profile(self, user_id, name, email):
        name, email = _clean_name(name), _clean_email(email)
        with self.store.transaction(write=True) as db:
            taken = db.execute("SELECT 1 FROM users WHERE email = ? AND user_id != ?", (email, user_id)).fetchone()
            if taken:
                raise AccountExists("Another account already uses this email")
            db.execute("UPDATE users SET name = ?, email = ? WHERE user_id = ?", (name, email, user_id))
            return self.public(db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone())

    def change_password(self, user_id, current_password, new_password):
        """Change the password; an account made with Google may set its first password without a current one."""
        _check_password(new_password)
        with self.store.transaction(write=True) as db:
            row = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row["password_hash"] is not None and not (
                    isinstance(current_password, str) and password_matches(current_password, row["password_hash"])):
                raise PermissionError("Your current password isn't right")
            db.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (hash_password(new_password), user_id))
            return self.public(db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone())

    def delete_account(self, user_id, password=None, confirm=None):
        """Delete the account with its repertoire, practice history and sessions.

        A password account confirms with its password; an account without one confirms by typing DELETE.
        """
        with self.store.transaction(write=True) as db:
            row = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row["password_hash"] is not None:
                if not (isinstance(password, str) and password_matches(password, row["password_hash"])):
                    raise PermissionError("Your password isn't right")
            elif confirm != "DELETE":
                raise ValueError("Type DELETE to confirm")
            for table, column in (("auth_sessions", "user_id"), ("practice_events", "player_id"),
                                  ("player_lines", "player_id"), ("users", "user_id")):
                db.execute(f"DELETE FROM {table} WHERE {column} = ?", (user_id,))

    # ---- internal

    def _create_user(self, db, name, email, password_hash, google_sub):
        user_id = uuid4().hex
        db.execute(
            """INSERT INTO users (user_id, email, name, password_hash, google_sub, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, email, name, password_hash, google_sub, timestamp(self.now())),
        )
        return user_id

    def _sign_in(self, db, user_id):
        token = secrets.token_urlsafe(32)
        now = self.now()
        db.execute(
            "INSERT INTO auth_sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (_token_hash(token), user_id, timestamp(now), timestamp(now + timedelta(days=SESSION_DAYS))),
        )
        row = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return self.public(row), token
