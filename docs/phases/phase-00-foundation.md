# Phase 0 — Foundation

> **Schema rework planned (not yet built).** This document describes Phase 0 as it shipped: 11 tables with `designations` carrying access items as JSON arrays. A schema rework is queued before Phase 2 begins:
>
> - **Drop:** `designations.mandatory_items` and `designations.optional_items` JSON columns
> - **Add:** `user_designations(acf2_id PK, designation_id, assigned_at, source)` — separate user→role mapping table (1 user → 1 role)
> - **Add:** `role_access_items(designation_id, access_item, mandatory, description, owner_team, servicenow_catalog_item_id)` — normalized per-item rows; ~80 rows total. Carries ServiceNow catalog item IDs for Phase 5 SN integration.
> - **Re-seed:** delete current `hackherway.db`, re-run seed script. No real data exists yet — safe.
>
> Phase 1 code uses only the `users` table — unaffected by this rework.
> See `CLAUDE.md` § Database Schema for the target shape.

## What Was Built

| Deliverable | Location | Purpose |
|-------------|----------|---------|
| Full SQLite schema (11 tables) | `backend/scripts/seed_sqlite.py` | All tables created with IF NOT EXISTS |
| 3 demo users seeded | `backend/scripts/seed_sqlite.py` | ARUN01, NEHA02, SARA03 |
| 8 designation templates | `backend/scripts/seed_sqlite.py` | Context stuffing source for agent |
| Dangerous combinations table | `backend/scripts/seed_sqlite.py` | 5 entries — Privilege Guard source |
| Privilege edges for NEHA02 | `backend/scripts/seed_sqlite.py` | finance_data_read + prod_db_read |
| Approval events for Risk Scorer | `backend/scripts/seed_sqlite.py` | 10 baseline + 5 ARUN01 anomalies |
| Approver routing (all items) | `backend/scripts/seed_sqlite.py` | All → Teams webhook |
| SQLite MCP Server | `backend/mcp_server/sqlite_server.py` | FastMCP — query_db + execute_db tools |
| Color-coded logging utility | `backend/src/lib/logger.py` | [AGENT] [BEDROCK] [MCP] [MOCK] [TEAMS] etc. |
| Mock Workday API | `backend/src/mock/workday.py` | GET /mock/workday/employee/{acf2_id} |
| Mock AD/LDAP API | `backend/src/mock/ad.py` | POST /mock/ad/provision |
| Mock Jira API | `backend/src/mock/jira.py` | POST /mock/jira/provision |
| Mock SAM API | `backend/src/mock/sam.py` | POST /mock/sam/provision/* |
| FastAPI startup logging | `backend/src/main.py` | Logs routes on startup |
| Stale folder cleanup | root | Removed agent/, mock-apis/, orchestrator/, schema/ |

## Why It Was Built

Phase 0 establishes the full infrastructure foundation before any agent logic is built. Without this phase:
- Agent has no DB to query (missing tables)
- Risk Scorer has no historical data to score against
- Privilege Guard has no dangerous_combinations or privilege_edges to check
- Demo has wrong users (old RIYA001/JOHN002 data)
- No logging — impossible to debug agent/MCP/Bedrock interactions
- No mock APIs — Orchestrator (Phase 5) has nothing to call

## How It Works

### Database Schema

11 tables, all created with `IF NOT EXISTS` so the script is idempotent:

```
users                 — ACF2 ID, name, team, manager, dept, employment_type
designations          — 8 role templates with mandatory/optional access items (JSON arrays)
access_requests       — submitted requests with final bundle, risk score, status
approval_events       — per-item approval state (pending/approved/rejected)
approver_routing      — access_item → Teams webhook URL
audit_log             — append-only trail of all state changes
privilege_edges       — user's existing permissions (Privilege Guard source)
dangerous_combinations— permission combos that trigger warnings
template_drafts       — no-match flow draft templates (Phase 6)
conversations         — chat sessions per ACF2 ID
messages              — individual chat messages
```

### Demo User Scenarios

| ACF2 ID | Scenario | Key Seed Data |
|---------|----------|---------------|
| ARUN01  | Happy path + Risk Scorer ~78 | 5 anomalous approval_events (2 off-hours, 3 rejected, 1 escalated) |
| NEHA02  | Privilege Guard fires | privilege_edges: finance_data_read + prod_db_read |
| SARA03  | No-match → template generation | No matched designation template |

### Risk Scorer Seed Data (ARUN01)

The 15 seeded approval_events produce a risk score of ~78 for ARUN01 because:

| Signal | Value | Baseline |
|--------|-------|---------|
| Off-hours rate | 2/5 = 40% | ~0% |
| Rejection rate | 3/5 = 60% | ~10% |
| Re-request velocity | prod_db_write twice in 3 days | Rare |
| Escalation | 1 manager override | None in baseline |
| Item deviation | prod_db_write is unusual for DevOps role | Not in standard template |

### Privilege Guard Seed Data (NEHA02)

```
NEHA02 existing privileges (privilege_edges):
  finance_data_read   — granted 2025-01-15 by Deepa Menon
  prod_db_read        — granted 2025-03-01 by Deepa Menon

Finance Analyst template optional items:
  finance_systems_write
  external_reporting_api  ← triggers danger_003

Dangerous combination danger_003:
  finance_data_read + external_reporting_api = HIGH
  Reason: Finance data exfiltration vector to external systems
```

### SQLite MCP Server

```bash
# Start the MCP server (from backend/ folder)
python -m mcp_server.sqlite_server

# The server exposes two tools via MCP protocol:
#   query_db(sql)   — SELECT only
#   execute_db(sql) — INSERT / UPDATE (blocks DROP/TRUNCATE/ALTER)
```

The agent (Phase 1+) connects to this server via stdio and generates SQL using Bedrock's tool-use.

### Mock APIs

All mock routes are mounted on the FastAPI app:

```
GET  /mock/workday/employee/{acf2_id}   → employee record or 404
POST /mock/ad/provision                 → {"success": true, "reference_id": "AD-xxxx"}
POST /mock/jira/provision               → {"success": true, "reference_id": "JIRA-xxxx"}
POST /mock/sam/provision/github-copilot → {"success": true, "reference_id": "SAM-COP-xxxx"}
POST /mock/sam/provision/non-primary-id → {"success": true, "reference_id": "SAM-NPI-xxxx"}
```

### Logging

All backend modules import from `backend/src/lib/logger.py`:

```python
from src.lib.logger import agent, bedrock, mcp, mock, teams, snow, orch, error

agent("User ARUN01 message received")
bedrock("tool_call → query_db")
mcp("SQL: SELECT * FROM users WHERE acf2_id = 'ARUN01' → 1 row")
mock("Workday lookup OK → Arun Mehta (Cloud Infrastructure)")
```

## How to Test

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env  # fill in AWS creds
python scripts/seed_sqlite.py
```

Expected output:
```
Users:
  seeded: ARUN01 - Arun Mehta
  seeded: NEHA02 - Neha Kapoor
  seeded: SARA03 - Sara Chen

Designation templates:
  template: backend_developer
  template: devops_cloud_engineer
  template: data_analyst
  template: finance_analyst
  template: intern
  template: manager_team_lead
  template: auditor
  template: contractor

Dangerous combinations:
  [CRITICAL] prod_db_write + deploy_pipeline_write
  [HIGH] prod_db_read + deploy_pipeline_write
  [HIGH] finance_data_read + external_reporting_api
  [CRITICAL] finance_systems_write + external_reporting_api
  [HIGH] npe_environment + prod_db_write

Privilege edges (NEHA02):
  edge: NEHA02 → finance_data_read
  edge: NEHA02 → prod_db_read

Approver routing: 37 access items → Teams webhook

Approval events:
  baseline (normal): 10 events (HIST001-006, devops role)
  ARUN01 anomalies:  5 events (2 off-hours, 3 rejections → score ~78)

Done. DB at: ...\hackherway-ps6\backend\hackherway.db
```

Start the backend and verify mock Workday:

```bash
uvicorn src.main:app --reload --port 8000
# Open: http://localhost:8000/mock/workday/employee/ARUN01
```

Expected response:
```json
{
  "status": "found",
  "employee": {
    "acf2_id": "ARUN01",
    "name": "Arun Mehta",
    "team": "Cloud Infrastructure",
    "manager": "Raj Kumar",
    ...
  }
}
```

Verify MCP server standalone:

```bash
python -m mcp_server.sqlite_server
# Server starts — ready for MCP client connections
# Agent will connect to this in Phase 1
```

## Decisions Made

- **SQLite MCP server built with FastMCP** (not official `mcp-server-sqlite` npm package) — pure Python, no Node.js dependency in backend, fully MCP protocol compliant. Registered as ADR candidate.
- **Seed script uses direct sqlite3** — utility scripts (not application code) are exempt from the "MCP only" rule. Application agent code will use MCP exclusively.
- **Mocks placed in `backend/src/mock/`** — follows existing `backend/src/routes/` pattern for clean relative imports. Matches FastAPI router structure.
- **All 37 access items pre-routed** — approver_routing seeded for all items upfront so Phase 5 Teams card integration has routing data ready.
- **Stale folders removed** — `agent/`, `mock-apis/`, `orchestrator/`, `schema/` from old TypeScript architecture deleted. Only `frontend/`, `backend/`, `docs/` remain.
