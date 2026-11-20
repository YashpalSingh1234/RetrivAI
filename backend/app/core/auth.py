"""Password hashing and signed, short-lived session tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from backend.app.core.database import database, get_auth_secret, utc_now


PBKDF2_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, encoded_salt, encoded_digest = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        expected = _unb64(encoded_digest)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _unb64(encoded_salt), int(iterations)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_user(email: str, password: str) -> dict[str, str]:
    import uuid

    user = {
        "id": str(uuid.uuid4()),
        "email": email.strip().lower(),
        "created_at": utc_now(),
    }
    with database() as connection:
        connection.execute(
            "INSERT INTO users(id, email, password_hash, created_at) VALUES(?, ?, ?, ?)",
            (user["id"], user["email"], hash_password(password), user["created_at"]),
        )
    return user


def authenticate_user(email: str, password: str) -> dict[str, str] | None:
    with database() as connection:
        row = connection.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    if row is None or not verify_password(password, row["password_hash"]):
        return None
    return {"id": row["id"], "email": row["email"], "created_at": row["created_at"]}


def get_user(user_id: str) -> dict[str, str] | None:
    with database() as connection:
        row = connection.execute(
            "SELECT id, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def issue_session(user_id: str, expires_in_seconds: int) -> str:
    payload = json.dumps(
        {"sub": user_id, "exp": int(time.time()) + expires_in_seconds},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    body = _b64(payload)
    signature = hmac.new(get_auth_secret(), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"


def read_session(token: str) -> str | None:
    try:
        body, encoded_signature = token.split(".", 1)
        signature = _unb64(encoded_signature)
        expected = hmac.new(
            get_auth_secret(), body.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(signature, expected):
            return None
        payload: dict[str, Any] = json.loads(_unb64(body))
        if int(payload.get("exp", 0)) <= int(time.time()):
            return None
        subject = payload.get("sub")
        return subject if isinstance(subject, str) and subject else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
