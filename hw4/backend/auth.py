"""Customer accounts: sign up, log in, log out.

Passwords use the same recipe as the seed data: PBKDF2-HMAC-SHA256, 120,000
iterations, a per-user random salt, stored as ``pbkdf2_sha256$salt$hash``
(salt as text, hash as hex). The real password is never stored or logged.
"""

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs.db"

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000

MAX_FAILED_ATTEMPTS = 3
LOCKOUT_SECONDS = 30 * 60
SESSION_COOKIE = "cc_session"
SESSION_SECONDS = 7 * 24 * 60 * 60

GENERIC_LOGIN_ERROR = "Email or password is incorrect."

router = APIRouter(prefix="/api/auth")

# Failed-login counters live in memory (a restart clears lockouts). Sessions are stored in the
# database so logins survive restarts, including uvicorn --reload during development.
_failures: dict[str, dict] = {}  # email -> {"count": int, "locked_until": float}


# ---------- Password hashing ----------

def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS)
    return f"{ALGORITHM}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Re-hash what was typed with the stored salt and compare in constant time."""
    try:
        algorithm, salt, expected = stored.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    candidate = hash_password(password, salt).split("$")[2]
    return hmac.compare_digest(candidate, expected)


# Used when an email isn't found, so a wrong email takes as long as a wrong password.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def password_problems(password: str) -> list[str]:
    """Strength rules for new passwords. Existing accounts are grandfathered in."""
    problems = []
    if len(password) < 12:
        problems.append("at least 12 characters")
    if not re.search(r"[A-Z]", password):
        problems.append("a capital letter")
    if not re.search(r"[a-z]", password):
        problems.append("a lowercase letter")
    if not re.search(r"\d", password):
        problems.append("a number")
    if not re.search(r"[^A-Za-z0-9]", password):
        problems.append("a symbol")
    return problems


# ---------- Helpers ----------

@contextmanager
def connect():
    """Open the database, commit on success, and always close it."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def public_user(row: sqlite3.Row) -> dict:
    first = row["first_name"] or (row["name"] or "").split(" ")[0]
    return {"id": row["id"], "first_name": first, "last_name": row["last_name"] or "", "email": row["email"]}


def ensure_sessions_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )


def _token_hash(token: str) -> str:
    """Only a fingerprint of the session token is stored, never the token itself."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def start_session(response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    now = time.time()
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (_token_hash(token), user_id, now + SESSION_SECONDS),
        )
    response.set_cookie(
        SESSION_COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite="lax", path="/"
    )


def current_user_id(token: str | None) -> int | None:
    if not token:
        return None
    with connect() as conn:
        row = conn.execute(
            "SELECT user_id, expires_at FROM sessions WHERE token_hash = ?", (_token_hash(token),)
        ).fetchone()
        if row is None:
            return None
        if row["expires_at"] < time.time():
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
            return None
        return row["user_id"]


def minutes_left(locked_until: float) -> int:
    return max(1, round((locked_until - time.time()) / 60))


# ---------- Endpoints ----------

class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/signup")
def signup(body: SignupRequest, response: Response) -> dict:
    first, last = body.first_name.strip(), body.last_name.strip()
    email = normalize_email(body.email)

    if not first or not last or len(first) > 60 or len(last) > 60:
        raise HTTPException(400, "Please enter your first and last name.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or len(email) > 254:
        raise HTTPException(400, "Please enter a valid email address.")
    if body.password != body.confirm_password:
        raise HTTPException(400, "Those passwords don't match.")
    problems = password_problems(body.password)
    if problems:
        raise HTTPException(400, "Password needs " + ", ".join(problems) + ".")
    if len(body.password) > 256:
        raise HTTPException(400, "That password is too long.")

    with connect() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone()
        if exists:
            raise HTTPException(409, "An account with that email already exists. Try logging in.")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
            (f"{first} {last}", email, hash_password(body.password), first, last),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()

    start_session(response, row["id"])
    return public_user(row)


@router.post("/login")
def login(body: LoginRequest, response: Response) -> dict:
    email = normalize_email(body.email)
    record = _failures.get(email)
    now = time.time()

    if record and record["locked_until"] > now:
        raise HTTPException(
            429,
            f"Too many failed attempts. Please wait {minutes_left(record['locked_until'])} minutes and try again.",
        )

    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()

    if row is None:
        verify_password(body.password, _DUMMY_HASH)
        ok = False
    else:
        ok = verify_password(body.password, row["password_hash"])

    if not ok:
        if not record or record["locked_until"]:
            record = {"count": 0, "locked_until": 0.0}  # fresh start after an expired lockout
        record["count"] += 1
        if record["count"] >= MAX_FAILED_ATTEMPTS:
            record["locked_until"] = now + LOCKOUT_SECONDS
            _failures[email] = record
            raise HTTPException(
                429, "Too many failed attempts. Please wait 30 minutes and try again."
            )
        _failures[email] = record
        raise HTTPException(401, GENERIC_LOGIN_ERROR)

    _failures.pop(email, None)
    start_session(response, row["id"])
    return public_user(row)


@router.post("/logout")
def logout(response: Response, cc_session: str | None = Cookie(default=None)) -> dict:
    if cc_session:
        with connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(cc_session),))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(cc_session: str | None = Cookie(default=None)) -> dict:
    user_id = current_user_id(cc_session)
    if user_id is None:
        return {"user": None}
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return {"user": public_user(row) if row else None}
