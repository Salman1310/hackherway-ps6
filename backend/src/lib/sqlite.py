"""
SQLite direct-access helper — HackHERway PS6

IMPORTANT: This module is used ONLY by simple REST endpoints (e.g. conversations list).
The agent uses the SQLite MCP server (mcp_server/sqlite_server.py) via tool calls —
never this module directly.

Rule: No agent business logic here. Only thin DB access for non-agent routes.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional

_db: Optional[sqlite3.Connection] = None


def get_db() -> sqlite3.Connection:
    global _db
    if _db is None:
        db_path = os.environ.get(
            "SQLITE_DB_PATH",
            str(Path(__file__).parent.parent.parent / "hackherway.db"),
        )
        _db = sqlite3.connect(db_path, check_same_thread=False)
        _db.row_factory = sqlite3.Row
        _db.execute("PRAGMA journal_mode=WAL")
        _init_schema(_db)
    return _db


def _init_schema(db: sqlite3.Connection) -> None:
    """
    Create tables needed by non-agent REST endpoints.
    Full schema (including agent tables) is created by seed_sqlite.py.
    Using IF NOT EXISTS so this is safe to run even after seeding.
    """
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            acf2_id         TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            team            TEXT,
            manager         TEXT,
            dept            TEXT,
            employment_type TEXT
        );

        CREATE TABLE IF NOT EXISTS user_auth (
            acf2_id       TEXT PRIMARY KEY,
            password      TEXT NOT NULL,
            created_at    INTEGER NOT NULL,
            last_login_at INTEGER,
            FOREIGN KEY(acf2_id) REFERENCES users(acf2_id)
        );

        INSERT OR IGNORE INTO user_auth (acf2_id, password, created_at, last_login_at)
        SELECT 'ARUN01', 'arun123', 1777593600, NULL
        WHERE EXISTS (SELECT 1 FROM users WHERE acf2_id = 'ARUN01');

        INSERT OR IGNORE INTO user_auth (acf2_id, password, created_at, last_login_at)
        SELECT 'NEHA02', 'neha123', 1777593600, NULL
        WHERE EXISTS (SELECT 1 FROM users WHERE acf2_id = 'NEHA02');

        INSERT OR IGNORE INTO user_auth (acf2_id, password, created_at, last_login_at)
        SELECT 'SARA03', 'sara123', 1777593600, NULL
        WHERE EXISTS (SELECT 1 FROM users WHERE acf2_id = 'SARA03');

        CREATE TABLE IF NOT EXISTS conversations (
            id         TEXT PRIMARY KEY,
            acf2_id    TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            session_json TEXT
        );

        CREATE TABLE IF NOT EXISTS messages (
            id              TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role            TEXT NOT NULL CHECK(role IN ('user', 'bot')),
            content         TEXT NOT NULL,
            created_at      INTEGER NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        );
    """)
    conversation_columns = {
        row["name"] for row in db.execute("PRAGMA table_info(conversations)")
    }
    if "session_json" not in conversation_columns:
        db.execute("ALTER TABLE conversations ADD COLUMN session_json TEXT")
    db.commit()
