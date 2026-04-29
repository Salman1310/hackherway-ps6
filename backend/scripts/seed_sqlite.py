"""
Seed SQLite DB with demo users.
Usage (from backend/ folder):
    python scripts/seed_sqlite.py
"""

import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DB_PATH = os.environ.get(
    "SQLITE_DB_PATH",
    str(Path(__file__).parent.parent / "hackherway.db"),
)

USERS = [
    {
        "acf2_id": "RIYA001",
        "name": "Riya Sharma",
        "team": "Payments Backend",
        "manager": "Anjali Singh",
        "dept": "Technology",
        "employment_type": "full-time",
    },
    {
        "acf2_id": "JOHN002",
        "name": "John Mathews",
        "team": "Cloud Infrastructure",
        "manager": "Raj Kumar",
        "dept": "Technology",
        "employment_type": "full-time",
    },
    {
        "acf2_id": "PRIYA003",
        "name": "Priya Nair",
        "team": "Finance Analytics",
        "manager": "Deepa Menon",
        "dept": "Finance",
        "employment_type": "contract",
    },
    {
        "acf2_id": "SAM004",
        "name": "Sam Wilson",
        "team": "TBD",
        "manager": "TBD",
        "dept": "TBD",
        "employment_type": "full-time",
    },
]

db = sqlite3.connect(DB_PATH)
db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        acf2_id TEXT PRIMARY KEY, name TEXT NOT NULL,
        team TEXT, manager TEXT, dept TEXT, employment_type TEXT
    );
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY, acf2_id TEXT NOT NULL,
        created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('user','bot')),
        content TEXT NOT NULL, created_at INTEGER NOT NULL,
        FOREIGN KEY(conversation_id) REFERENCES conversations(id)
    );
    CREATE TABLE IF NOT EXISTS ritm_requests (
        id TEXT PRIMARY KEY, acf2_id TEXT NOT NULL,
        conversation_id TEXT, template_id TEXT,
        status TEXT DEFAULT 'pending', snow_request_id TEXT,
        created_at INTEGER NOT NULL
    );
""")

for user in USERS:
    db.execute(
        """INSERT INTO users (acf2_id, name, team, manager, dept, employment_type)
           VALUES (:acf2_id, :name, :team, :manager, :dept, :employment_type)
           ON CONFLICT(acf2_id) DO UPDATE SET
             name=excluded.name, team=excluded.team, manager=excluded.manager,
             dept=excluded.dept, employment_type=excluded.employment_type""",
        user,
    )
    print(f"  seeded: {user['acf2_id']} — {user['name']}")

db.commit()
db.close()
print(f"\nDone. DB at: {DB_PATH}")
