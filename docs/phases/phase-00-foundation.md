# Phase 0 - Foundation

## Status

Done.

Phase 0 is now split historically into:

- Phase 0A: initial FastAPI, SQLite, MCP wrapper, mocks, logging, demo users, and JSON template seed.
- Phase 0B: normalized role/access schema rework required by Phase 2.

Both Phase 0A and Phase 0B are built. The current seed script recreates the local demo database in the Phase 0B normalized shape.

## What Was Built

| Deliverable | Location | Purpose |
|-------------|----------|---------|
| SQLite seed script | `backend/scripts/seed_sqlite.py` | Recreates and seeds the local demo database |
| Demo users | `backend/scripts/seed_sqlite.py` | Seeds ARUN01, NEHA02, and SARA03 |
| Normalized designations | `backend/scripts/seed_sqlite.py` | Seeds 8 role templates with id/title/description/hints |
| Role access rows | `backend/scripts/seed_sqlite.py` | Seeds one row per mandatory or optional access item |
| User role mappings | `backend/scripts/seed_sqlite.py` | Seeds ARUN01 and NEHA02 in `user_designations`; leaves SARA03 unmapped |
| Dangerous combinations | `backend/scripts/seed_sqlite.py` | Seeds privilege combinations for Phase 4 |
| NEHA02 privilege edges | `backend/scripts/seed_sqlite.py` | Seeds existing access for future Privilege Guard demos |
| ARUN01 approval history | `backend/scripts/seed_sqlite.py` | Seeds synthetic approval data for future Risk Scorer demos |
| Approver routing | `backend/scripts/seed_sqlite.py` | Routes access items to a demo Teams webhook target |
| SQLite MCP wrapper | `backend/mcp_server/sqlite_server.py` | Exposes `query_db` and `execute_db` |
| Mock Workday API | `backend/src/mock/workday.py` | Returns employee records by ACF2 ID |
| Mock provisioning APIs | `backend/src/mock/ad.py`, `backend/src/mock/jira.py`, `backend/src/mock/sam.py` | Provide local provisioning targets for later phases |
| Backend logging utility | `backend/src/lib/logger.py` | Provides readable subsystem log prefixes |

## Current Schema

The current database has exactly these 13 application tables:

```text
users
user_designations
designations
role_access_items
access_requests
approval_events
approver_routing
audit_log
privilege_edges
dangerous_combinations
template_drafts
conversations
messages
```

### `users`

```text
acf2_id TEXT PRIMARY KEY
name TEXT NOT NULL
team TEXT
manager TEXT
dept TEXT
employment_type TEXT
```

No designation column exists on `users`. Role assignment belongs in `user_designations`.

### `designations`

```text
id TEXT PRIMARY KEY
title TEXT NOT NULL
description TEXT
team_hint TEXT
dept_hint TEXT
```

The Phase 0A JSON access columns are removed.

### `role_access_items`

```text
id TEXT PRIMARY KEY
designation_id TEXT NOT NULL
access_item TEXT NOT NULL
display_name TEXT
system TEXT
description TEXT
mandatory INTEGER NOT NULL
owner_team TEXT
servicenow_catalog_item_id TEXT
sort_order INTEGER
```

This table is the source for Phase 2 template rendering, Phase 3 bundle review, Phase 4 privilege checks, and Phase 5 ServiceNow item mapping.

### `user_designations`

```text
acf2_id TEXT PRIMARY KEY
designation_id TEXT NOT NULL
assigned_at INTEGER NOT NULL
source TEXT NOT NULL
```

Seeded mappings:

```text
ARUN01 -> devops_cloud_engineer
NEHA02 -> finance_analyst
```

SARA03 intentionally has no seeded designation so later no-match/admin-ratification demos remain possible.

## Seeded Designations

```text
backend_developer
devops_cloud_engineer
data_analyst
finance_analyst
intern
manager_team_lead
auditor
contractor
```

Each designation has individual `role_access_items` rows with display labels, systems, descriptions, owner teams, ServiceNow catalog item placeholders, mandatory flags, and sort order.

## How To Verify

From `backend/`:

```bash
python scripts/seed_sqlite.py
python -m unittest discover -s tests
python -m compileall src mcp_server scripts tests
```

Database checks:

```sql
SELECT * FROM users WHERE acf2_id = 'ARUN01';
SELECT * FROM user_designations WHERE acf2_id = 'ARUN01';
SELECT * FROM designations WHERE id = 'devops_cloud_engineer';
SELECT * FROM role_access_items WHERE designation_id = 'devops_cloud_engineer' ORDER BY sort_order;
SELECT * FROM role_access_items WHERE servicenow_catalog_item_id IS NOT NULL LIMIT 5;
```

Expected outcomes:

- `users` returns all 3 demo users.
- `user_designations` contains ARUN01 and NEHA02 only.
- `designations` has 8 rows with no JSON access columns.
- `role_access_items` contains individual mandatory and optional rows.
- Phase 1 identity tests still pass.
- Phase 2 role resolver tests pass.

## Decisions Made

- Phase 0A used JSON template fields only to unblock the initial demo.
- Phase 0B normalized role/access data before Phase 2 was built.
- `users` remains stable and is the only table Phase 1 identity verification depends on.
- Seed/setup scripts may use direct `sqlite3`; application flows continue to use the MCP tool path.
- The local MCP server is the Python FastMCP wrapper in `backend/mcp_server/sqlite_server.py`.
- Clean local database recreation is acceptable for this hackathon phase.
