# CLAUDE.md - HackHERway PS6: AI-Powered Access Approval

This file is the current contributor and AI-assistant guide for the project.

## Project Overview

Hackathon: Sun Life HackHERway 2025 - Problem Statement 6

Goal: replace manual, fragmented access request workflows with an AI-powered chat interface that verifies identity, resolves role, recommends access templates, routes approvals, provisions mock systems, and preserves audit history.

## Current Status

| Phase | Status |
|-------|--------|
| Phase 0A - Foundation shipped | Done |
| Phase 0B - Normalized role/access schema rework | Done |
| Phase 1 - Agent identity verification | Done |
| Phase 2 - Role resolver + template matching | Done |
| Phase 3 - Template submission flow | Done |

Do not start Phase 4 until Phase 3 is explicitly accepted as the baseline for the next build.

## Architecture

```text
User
  <-> Next.js frontend on port 3000
  <-> FastAPI backend on port 8000
      <-> Access Agent
          <-> AWS Bedrock Claude Sonnet 4.6
          <-> local SQLite MCP wrapper
          <-> Mock Workday / AD / Jira / SAM APIs
      <-> future Orchestrator
          <-> SQLite MCP wrapper
          <-> ServiceNow MCP or fallback
          <-> Teams webhook
```

## Repository Structure

```text
backend/
  src/
    main.py
    types.py
    agent/index.py
    lib/bedrock.py
    lib/sqlite.py
    lib/logger.py
    mock/
    routes/
  mcp_server/sqlite_server.py
  scripts/seed_sqlite.py
  requirements.txt

frontend/
  src/app/
  src/components/
  src/contexts/
  src/hooks/
  src/lib/
  package.json

docs/phases/
  phase-00-foundation.md
  phase-01-agent-identity.md
  phase-02-role-resolver.md

ADR.md
PHASES.md
SETUP.md
TEAM_BUILD_PLAN.md
```

## Hard Boundaries

- Frontend is UI-only.
- Backend owns AI calls, database access, webhooks, approval logic, and secrets.
- Frontend never imports or calls Bedrock, boto3, SQLite, MCP, ServiceNow, or Teams webhooks directly.
- Frontend API routes are thin proxies only.
- Backend never imports React, Next.js, UI frameworks, or browser APIs.
- Secrets live only in `backend/.env`.
- Application database flows use the MCP tool path.
- Seed/setup scripts may use direct `sqlite3`.
- Completed changes and phases should be committed and pushed to GitHub.

## Technology

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4 |
| Backend | Python, FastAPI, uvicorn |
| LLM | AWS Bedrock Claude Sonnet 4.6 |
| Database | Local SQLite |
| MCP | Local Python FastMCP wrapper at `backend/mcp_server/sqlite_server.py` |
| Mock APIs | Workday, AD, Jira, SAM |
| Future approval channel | MS Teams Incoming Webhook |
| Future ITSM | ServiceNow MCP or fallback |

Do not add MongoDB, Supabase, pgvector, Ollama, Gemini, Express backend, or RAG.

## Current Phase 1 Behavior

Phase 1 is built.

The agent:

- asks for ACF2 ID
- uses Bedrock tool-use to call `query_db`
- verifies users through the `users` table
- returns `session_update` with `acf2_id` and Workday-style context
- hard-blocks unknown IDs
- answers ACF2 clarification questions without sample IDs
- returns an explicit Bedrock-unavailable message when Bedrock is down
- keeps replies plain text
- locks identity after verification
- requires reset chat before a different ACF2 ID can be used

Frontend reset is implemented in the chat header.

## Current Schema

The shipped database uses the Phase 0B normalized role/access model:

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

The old Phase 0A JSON template columns are no longer part of the seeded schema.

### `users`

```text
acf2_id TEXT PRIMARY KEY
name TEXT NOT NULL
team TEXT
manager TEXT
dept TEXT
employment_type TEXT
```

### `designations`

```text
id TEXT PRIMARY KEY
title TEXT NOT NULL
description TEXT
team_hint TEXT
dept_hint TEXT
```

No legacy JSON access columns exist on `designations`.

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

### `user_designations`

```text
acf2_id TEXT PRIMARY KEY
designation_id TEXT NOT NULL
assigned_at INTEGER NOT NULL
source TEXT NOT NULL
```

Seed ARUN01 and NEHA02 mappings. Leave SARA03 unmapped.

## Current Phase 2 Behavior

Phase 2 is built.

The agent:

- continues after identity verification
- keeps the Phase 1 identity lock active
- uses Bedrock tool-use to query normalized SQLite tables
- queries `designations` and `role_access_items`
- asks a focused clarification question for vague role input
- returns structured `resolved_role`, `selected_template`, and mandatory `final_bundle`
- writes confident matches to `user_designations` through MCP `execute_db`
- keeps replies plain text

Do not context-stuff the full template catalog into the prompt.

Frontend behavior:

- The right panel renders the backend-selected template.
- Mandatory and optional items are displayed.

## Current Phase 3 Behavior

Phase 3 is built.

The agent:

- activates when `session.selected_template` is set (after Phase 2)
- lists available optional access items and asks which the user wants
- confirms the final access bundle (mandatory + chosen optional)
- calls `execute_db` to INSERT into `access_requests` with a pre-generated UUID
- returns `session_update` with `final_bundle` and `request_id` after successful submission
- keeps replies plain text
- uses `SUBMISSION_TOOL_SPECS` (query_db + execute_db) — execute_db not available in Phase 1/2

Frontend behavior:

- Right panel template display unchanged from Phase 2.
- `final_bundle` and `request_id` stored in session but not displayed (Phase 5/6 will use them).
- No submit button exists in the frozen frontend; all submission goes through chat.

Agent routing order:

```text
no acf2_id          → Phase 1 (identity)
acf2_id + ACF2 msg  → identity lock
selected_template   → Phase 3 (submission)
else                → Phase 2 (role resolver)
```

## Demo Users

| ACF2 ID | Name | Scenario |
|---------|------|----------|
| ARUN01 | Arun Mehta | Happy path and later Risk Scorer |
| NEHA02 | Neha Kapoor | Later Privilege Guard |
| SARA03 | Sara Chen | Later no-match/admin ratification |

## Environment Variables

### `backend/.env`

```env
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=
SQLITE_DB_PATH=./hackherway.db
SERVICENOW_INSTANCE_URL=
SERVICENOW_USERNAME=
SERVICENOW_PASSWORD=
TEAMS_WEBHOOK_URL=
PORT=8000
```

### `frontend/.env`

```env
BACKEND_URL=http://localhost:8000
PUBLIC_BASE_URL=http://localhost:3000
```

## How To Run

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts/seed_sqlite.py
uvicorn src.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

From repo root, frontend can also be launched with:

```bash
npm run dev
```

## Verification Commands

Backend:

```bash
cd backend
python -m unittest discover -s tests
python -m compileall src mcp_server scripts tests
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Repo root frontend scripts:

```bash
npm run lint
npm run build
```

## Backend Logging

| Prefix | Used For |
|--------|----------|
| `[AGENT]` | Agent state and user-message flow |
| `[BEDROCK]` | LLM calls and tool-use |
| `[MCP]` | SQL queries and row counts |
| `[MOCK]` | Mock API calls |
| `[TEAMS]` | Teams webhook attempts |
| `[SERVICENOW]` | ServiceNow activity |
| `[ORCHESTRATOR]` | Provisioning orchestration |
| `[ERROR]` | Failures with context |

## ADRs To Respect

- ADR-001: two-process frontend/backend architecture
- ADR-002: single conversational agent
- ADR-003: SQLite via MCP tool path
- ADR-010: AWS Bedrock as only LLM provider
- ADR-011: tool-query template matching over normalized role tables
- ADR-013: auth bypassed for hackathon; Azure AD/MSAL as production path
- ADR-015: three seeded ACF2 demo users
- ADR-016: GitHub workflow convention

## Files Never To Commit

```text
.env
credentials.txt
token.txt
*.token
node_modules/
.next/
__pycache__/
*.db
```
