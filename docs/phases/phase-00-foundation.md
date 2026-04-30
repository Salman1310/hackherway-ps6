# Phase 0 - Foundation

## Status

Phase 0A is built and verified. It established the current FastAPI backend, SQLite database, local MCP wrapper, mock APIs, seed data, and logging.

Phase 0B is the required next foundation change before Phase 2 begins. Phase 0B is not built yet. It replaces JSON-based access template storage with a normalized role/access schema that Phase 2 can query reliably through tool-use.

Phase 1 identity verification only reads the `users` table, so the Phase 0B schema rework should not affect the working ACF2 flow.

## Phase 0A - What Shipped

| Deliverable | Location | Purpose |
|-------------|----------|---------|
| SQLite seed script | `backend/scripts/seed_sqlite.py` | Creates and seeds the local demo database |
| Demo users | `backend/scripts/seed_sqlite.py` | Seeds ARUN01, NEHA02, and SARA03 |
| JSON-based designations | `backend/scripts/seed_sqlite.py` | Seeds 8 role templates using `mandatory_items` and `optional_items` JSON columns |
| Dangerous combinations | `backend/scripts/seed_sqlite.py` | Seeds privilege combinations for Phase 4 |
| NEHA02 privilege edges | `backend/scripts/seed_sqlite.py` | Seeds existing access for Privilege Guard demos |
| ARUN01 approval history | `backend/scripts/seed_sqlite.py` | Seeds synthetic data for later Risk Scorer demos |
| Approver routing | `backend/scripts/seed_sqlite.py` | Routes access items to a demo Teams webhook target |
| SQLite MCP wrapper | `backend/mcp_server/sqlite_server.py` | Exposes `query_db` and `execute_db` tools over FastMCP |
| Mock Workday API | `backend/src/mock/workday.py` | Returns employee records by ACF2 ID |
| Mock provisioning APIs | `backend/src/mock/ad.py`, `backend/src/mock/jira.py`, `backend/src/mock/sam.py` | Provide local provisioning targets for later phases |
| Backend logging utility | `backend/src/lib/logger.py` | Provides `[AGENT]`, `[BEDROCK]`, `[MCP]`, `[MOCK]`, and related log prefixes |
| Environment examples | `backend/.env.example`, `frontend/.env.example` | Documents required local environment variables |

## Current Phase 0A Schema

The currently shipped database contains these core tables:

```text
users
designations             # currently includes mandatory_items and optional_items JSON columns
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

The current `designations` table is useful for early demos, but it is not the right shape for Phase 2 and Phase 3 because access items are embedded as JSON arrays. That makes it harder to query, attach ServiceNow catalog IDs, route approvals per item, and render individual mandatory/optional rows cleanly.

## Phase 0B - Required Schema Rework

Phase 0B should reset and re-seed the local database with a normalized role/access model:

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

### Target Tables

#### `users`

Stores identity and Workday-style employee context.

```text
acf2_id TEXT PRIMARY KEY
name TEXT NOT NULL
team TEXT
manager TEXT
dept TEXT
employment_type TEXT
```

No designation column should be added here. Role assignment belongs in `user_designations`.

#### `designations`

Stores one row per role template.

```text
id TEXT PRIMARY KEY
title TEXT NOT NULL
description TEXT
team_hint TEXT
dept_hint TEXT
```

The JSON columns `mandatory_items` and `optional_items` should be removed.

#### `role_access_items`

Stores one row per access item in each role template.

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

This table is the source for Phase 2 matching details, Phase 3 right-panel rendering, Phase 4 privilege checks, and Phase 5 ServiceNow item mapping.

#### `user_designations`

Stores the resolved role for a user.

```text
acf2_id TEXT PRIMARY KEY
designation_id TEXT NOT NULL
assigned_at INTEGER NOT NULL
source TEXT NOT NULL
```

Planned seed rows:

```text
ARUN01 -> devops_cloud_engineer
NEHA02 -> finance_analyst
```

SARA03 should intentionally have no `user_designations` row so the no-match path remains available for later phases.

## Phase 0B Seed Plan

Seed these 8 designations:

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

For each designation, seed role access items as individual `role_access_items` rows. Each row should include:

```text
designation_id
access_item
display_name
system
description
mandatory
owner_team
servicenow_catalog_item_id
sort_order
```

The same access item names should continue to be used by `approver_routing`, `privilege_edges`, and `dangerous_combinations`.

## Migration Approach

Because this is a local hackathon demo database and no real user data exists yet, Phase 0B can be a clean reset:

1. Stop backend and frontend processes.
2. Delete `backend/hackherway.db`.
3. Update `backend/scripts/seed_sqlite.py` to create the normalized schema.
4. Run `python scripts/seed_sqlite.py`.
5. Verify Phase 1 identity still works for ARUN01, NEHA02, and SARA03.

No production migration script is needed at this stage.

## How To Verify Phase 0B When Built

From `backend/`:

```bash
python scripts/seed_sqlite.py
python -m unittest discover -s tests
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
- `role_access_items` contains individual mandatory/optional rows.
- Existing Phase 1 identity tests still pass.
- Workday mock still returns ARUN01 and 404s unknown IDs.

## Decisions Made

- Phase 0A shipped with JSON template fields to unblock identity verification quickly.
- Phase 0B will normalize role/access data before Phase 2.
- `users` remains stable and is the only table Phase 1 depends on.
- Seed/setup scripts may use direct `sqlite3`; application flows continue to use the MCP tool path.
- The local MCP server is the Python FastMCP wrapper in `backend/mcp_server/sqlite_server.py`.
- No real data exists yet, so a clean database reset is acceptable for Phase 0B.
