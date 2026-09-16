"""Player accounts and password checking.

The 2020 login read ``if password == password:`` - a tautology that let any
string through, and which the accompanying commented-out ``return username``
suggests was a debugging shortcut left in by mistake.  Credentials now live in
a JSON file as salted PBKDF2-SHA256 digests and are compared in constant time.

This is a local two-player game, not a security boundary: the store exists so
the login screen means something and so the file never contains a plaintext
password.  The demo accounts from the original game (``User1``..``User5``,
password ``password``) are seeded on first run and should be changed before
the game is used anywhere that matters.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .paths import users_path

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 240_000
SALT_BYTES = 16

#: Accounts created the first time the game runs, preserving the 2020 demo set.
DEFAULT_USERNAMES = ("User1", "User2", "User3", "User4", "User5")
DEFAULT_PASSWORD = "password"

MIN_PASSWORD_LENGTH = 4


class AuthError(Exception):
    """Raised for malformed account operations."""


def hash_password(password: str, salt: str | None = None, iterations: int | None = None) -> str:
    """Return a ``algorithm$iterations$salt$digest`` string for *password*.

    ``iterations`` defaults to :data:`ITERATIONS` at call time rather than at
    import time, so the cost can be lowered in tests without weakening it here.
    """
    if iterations is None:
        iterations = ITERATIONS
    if salt is None:
        salt = secrets.token_hex(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    return f"{ALGORITHM}${iterations}${salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time check of *password* against a stored hash."""
    try:
        algorithm, iterations, salt, _ = encoded.split("$", 3)
        if algorithm != ALGORITHM:
            return False
        candidate = hash_password(password, salt=salt, iterations=int(iterations))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, encoded)


@dataclass(frozen=True)
class User:
    username: str
    password_hash: str


class UserStore:
    """A JSON-backed collection of accounts."""

    def __init__(self, users: Iterable[User] | None = None) -> None:
        self._users: dict[str, User] = {user.username: user for user in users or ()}

    def __len__(self) -> int:
        return len(self._users)

    def __contains__(self, username: object) -> bool:
        return username in self._users

    @property
    def usernames(self) -> list[str]:
        return sorted(self._users)

    def add(self, username: str, password: str) -> User:
        """Create an account. Raises :class:`AuthError` if it already exists."""
        username = username.strip()
        if not username:
            raise AuthError("username cannot be blank")
        if username in self._users:
            raise AuthError(f"user {username!r} already exists")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise AuthError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
        user = User(username=username, password_hash=hash_password(password))
        self._users[username] = user
        return user

    def set_password(self, username: str, password: str) -> None:
        if username not in self._users:
            raise AuthError(f"unknown user {username!r}")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise AuthError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
        self._users[username] = User(username, hash_password(password))

    def authenticate(self, username: str, password: str) -> bool:
        """Return ``True`` only for a known user with the right password."""
        user = self._users.get(username.strip())
        if user is None:
            # Hash anyway so a missing account is not faster than a wrong
            # password, which would leak which usernames exist.
            hash_password(password)
            return False
        return verify_password(password, user.password_hash)

    # ------------------------------------------------------------------
    @classmethod
    def seeded(cls) -> UserStore:
        """A store holding the original demo accounts."""
        store = cls()
        for username in DEFAULT_USERNAMES:
            store.add(username, DEFAULT_PASSWORD)
        return store

    @classmethod
    def load(cls, path: str | Path | None = None, seed_if_missing: bool = True) -> UserStore:
        """Load accounts, seeding and saving the demo set on first run."""
        target = Path(path) if path is not None else users_path()
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
        except (FileNotFoundError, IsADirectoryError):
            if not seed_if_missing:
                return cls()
            store = cls.seeded()
            store.save(target)
            return store
        except (OSError, json.JSONDecodeError):
            return cls.seeded() if seed_if_missing else cls()

        users = []
        for username, record in sorted((raw.get("users") or {}).items()):
            password_hash = (record or {}).get("password_hash")
            if isinstance(password_hash, str) and password_hash:
                users.append(User(username=username, password_hash=password_hash))
        store = cls(users)
        if not store and seed_if_missing:
            store = cls.seeded()
            store.save(target)
        return store

    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path is not None else users_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {
                "version": 1,
                "users": {
                    user.username: {"password_hash": user.password_hash}
                    for user in (self._users[name] for name in self.usernames)
                },
            },
            indent=2,
        )
        handle, temp_name = tempfile.mkstemp(
            dir=str(target.parent), prefix=".users-", suffix=".tmp"
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(payload + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, target)
            os.chmod(target, 0o600)
        except BaseException:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
            raise
        return target
