#!/usr/bin/env python3
"""
SQLite MCP Server — HackHERway PS6

Exposes the hackherway SQLite database as MCP tools.
The access agent calls these tools instead of using sqlite3 directly.

Tools exposed:
  query_db(sql)   — SELECT queries only
  execute_db(sql) — INSERT / UPDATE (no DROP / TRUNCATE / ALTER)

Run (from backend/ folder):
    python -m mcp_server.sqlite_server
"""

import json
import os
import sqlite3
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ModuleNotFoundError:
    pass

from mcp.server.fastmcp import FastMCP

DB_PATH = os.environ.get(
    "SQLITE_DB_PATH",
    str(Path(__file__).parent.parent / "hackherway.db"),
)

_BLOCKED_WRITE_PREFIXES = ("DROP", "TRUNCATE", "ALTER", "ATTACH", "DETACH", "VACUUM", "PRAGMA")

mcp = FastMCP("hackherway-sqlite")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@mcp.tool()
def query_db(sql: str) -> str:
    """
    Execute a read-only SQL SELECT query against the hackherway database.

    Only SELECT statements are permitted. Use this to look up users,
    check privilege_edges, read designations, query approval_events, etc.

    Schema tables available:
      users, designations, access_requests, approval_events, approver_routing,
      audit_log, privilege_edges, dangerous_combinations, template_drafts,
      conversations, messages

    Args:
        sql: A valid SQL SELECT statement. Embed values directly (no ? placeholders).

    Returns:
        JSON-encoded array of result rows (each row is a dict).
        Returns {"error": "..."} string on failure.

    Examples:
        query_db("SELECT * FROM users WHERE acf2_id = 'ARUN01'")
        query_db("SELECT * FROM designations")
        query_db("SELECT * FROM privilege_edges WHERE acf2_id = 'NEHA02'")
        query_db("SELECT * FROM dangerous_combinations")
    """
    sql_stripped = sql.strip()
    first_word = sql_stripped.split()[0].upper() if sql_stripped else ""
    if first_word != "SELECT":
        return json.dumps({
            "error": "query_db only permits SELECT statements. Use execute_db for INSERT/UPDATE."
        })
    try:
        conn = _connect()
        rows = conn.execute(sql_stripped).fetchall()
        conn.close()
        return json.dumps([dict(r) for r in rows])
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
def execute_db(sql: str) -> str:
    """
    Execute a write SQL statement (INSERT or UPDATE) against the hackherway database.

    Use this to create access requests, write audit log entries, update approval
    event status, insert template drafts, etc.

    DROP, TRUNCATE, ALTER, ATTACH, and VACUUM statements are blocked.

    Args:
        sql: A valid SQL INSERT or UPDATE statement. Embed values directly.

    Returns:
        JSON with {"rows_affected": N, "success": true} on success.
        Returns {"error": "..."} string on failure.

    Examples:
        execute_db("INSERT INTO access_requests (id, acf2_id, designation_id, status, created_at)
                    VALUES ('req-uuid', 'ARUN01', 'devops_cloud_engineer', 'pending', 1738549020)")
        execute_db("UPDATE approval_events SET status = 'approved', resolved_at = 1738549020
                    WHERE id = 'event-uuid'")
    """
    sql_stripped = sql.strip()
    first_word = sql_stripped.split()[0].upper() if sql_stripped else ""
    if first_word in _BLOCKED_WRITE_PREFIXES:
        return json.dumps({
            "error": f"Statement type '{first_word}' is not permitted via execute_db."
        })
    try:
        conn = _connect()
        cursor = conn.execute(sql_stripped)
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        return json.dumps({"rows_affected": rows_affected, "success": True})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


if __name__ == "__main__":
    mcp.run()
