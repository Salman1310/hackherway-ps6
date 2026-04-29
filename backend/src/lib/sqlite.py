import sqlite3
import os
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
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            acf2_id          TEXT PRIMARY KEY,
            name             TEXT NOT NULL,
            team             TEXT,
            manager          TEXT,
            dept             TEXT,
            employment_type  TEXT
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id          TEXT PRIMARY KEY,
            acf2_id     TEXT NOT NULL,
            created_at  INTEGER NOT NULL,
            updated_at  INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id               TEXT PRIMARY KEY,
            conversation_id  TEXT NOT NULL,
            role             TEXT NOT NULL CHECK(role IN ('user', 'bot')),
            content          TEXT NOT NULL,
            created_at       INTEGER NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        );

        CREATE TABLE IF NOT EXISTS ritm_requests (
            id               TEXT PRIMARY KEY,
            acf2_id          TEXT NOT NULL,
            conversation_id  TEXT,
            template_id      TEXT,
            status           TEXT DEFAULT 'pending',
            snow_request_id  TEXT,
            created_at       INTEGER NOT NULL
        );
    """)
    db.commit()
