from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "data" / "tax_assistant_live.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.execute("PRAGMA journal_mode=OFF")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        # Create users table for authentication
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                full_name TEXT
            )
            """
        )
        # Create tax plans table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tax_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def register_user(username, password, full_name):
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password, full_name) VALUES (?, ?, ?)",
                (username, password, full_name)
            )
        return True
    except sqlite3.IntegrityError:
        return False


def verify_user(username, password):
    with get_connection() as conn:
        user = conn.execute(
            "SELECT full_name FROM users WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()
        return user[0] if user else None


def save_plan(username: str, payload: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO tax_plans (username, payload, created_at) VALUES (?, ?, ?)",
            (username.strip() or "guest", payload, datetime.utcnow().isoformat(timespec="seconds")),
        )
