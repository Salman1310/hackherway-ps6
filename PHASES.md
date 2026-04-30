# Build Phases - PS6: AI-Powered Access Approval

HackHERway | Sun Life

## Principles

- Every phase ends with something testable.
- Every completed phase has a file in `docs/phases/`.
- ADR.md must be updated when architecture, ownership, schema, or provider decisions change.
- Frontend remains UI-only. Backend owns AI, database access, webhooks, and business logic.
- Changes and completed phases should be committed and pushed to GitHub.

## Current Architecture

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

## Demo Users

| ACF2 ID | Name | Team | Scenario |
|---------|------|------|----------|
| ARUN01 | Arun Mehta | Cloud Infrastructure | Happy path and later Risk Scorer demo |
| NEHA02 | Neha Kapoor | Finance Analytics | Later Privilege Guard demo |
| SARA03 | Sara Chen | TBD | Later no-match/admin ratification demo |

## Template Matching Strategy

Phase 2 will use Bedrock reasoning plus tool-use queries over normalized SQLite role/access tables.

The agent should query `designations` and `role_access_items` through `query_db`, reason over returned candidate rows, and return structured selected-template data to the frontend. Do not context-stuff all templates into the system prompt.

Confirmed user-to-role mappings are stored in `user_designations`.

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 0A | Foundation shipped | Done |
| 0B | Normalized role/access schema rework | Next |
| 1 | Agent Core + Identity Verification | Done |
| 2 | Role Resolver + Template Matching | Planned after Phase 0B |
| 3 | Template UI + Submission Flow | Not started |
| 4 | Risk Scorer + Privilege Guard | Not started |
| 5 | ServiceNow + Teams + Orchestrator | Not started |
| 6 | Status Tracker + No-Match + Admin Dashboard | Not started |
| 7 | Polish + Demo Prep | Not started |
| Stretch | RetellAI Voice Layer | Not started |

## Phase 0A - Foundation Shipped

Phase 0A created the current repo foundation:

- `frontend/` Next.js app
- `backend/` FastAPI app
- SQLite seed script
- local FastMCP SQLite wrapper
- mock Workday, AD, Jira, and SAM APIs
- logging utility
- demo users
- initial JSON-based designation templates
- dangerous combinations and privilege edges
- synthetic approval events for future risk scoring

Phase doc: `docs/phases/phase-00-foundation.md`

## Phase 0B - Normalized Role/Access Schema Rework

Phase 0B must be completed before Phase 2.

Current Phase 0A schema stores access template items as JSON:

```text
designations.mandatory_items
designations.optional_items
```

Target Phase 0B schema:

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

Required changes:

| Task | Notes |
|------|-------|
| Rework `designations` | Keep id/title/description/team_hint/dept_hint only |
| Add `role_access_items` | One row per access item with mandatory flag, owner team, display metadata, and ServiceNow catalog item ID |
| Add `user_designations` | One row per resolved user role |
| Seed ARUN01 and NEHA02 role mappings | ARUN01 -> devops_cloud_engineer, NEHA02 -> finance_analyst |
| Leave SARA03 without role mapping | Preserves no-match scenario |
| Keep existing users, risks, privilege, routing, mock data | Names and access item IDs should remain consistent |
| Reset local DB cleanly | Delete `backend/hackherway.db` and re-run seed script |

Exit criteria:

- `python scripts/seed_sqlite.py` creates the normalized tables.
- `SELECT * FROM users WHERE acf2_id = 'ARUN01'` returns Arun.
- `SELECT * FROM user_designations WHERE acf2_id = 'ARUN01'` returns a role.
- `SELECT * FROM role_access_items WHERE designation_id = 'devops_cloud_engineer'` returns individual rows.
- Phase 1 backend tests still pass.
- Workday mock still returns ARUN01.

## Phase 1 - Agent Core + Identity Verification

Status: Done.

Phase 1 verifies identity through the Bedrock tool-use loop and SQLite MCP query path.

Current behavior:

- user enters an ACF2 ID
- agent uses Bedrock tool-use to call `query_db`
- backend enforces SELECT-only SQL
- a verified user updates session state
- unknown IDs are hard-blocked
- ACF2 explanation questions are answered by Bedrock without sample IDs
- Bedrock outages return an explicit service-unavailable message
- verified identity is locked until reset
- frontend reset button clears session and restarts chat

Phase doc: `docs/phases/phase-01-agent-identity.md`

## Phase 2 - Role Resolver + Template Matching

Status: Planned after Phase 0B.

Goal:

After identity verification, the user describes their role. The agent asks focused clarification questions if needed, queries the normalized role/access catalog, chooses the best template, and returns structured data for the frontend right panel.

Tasks:

| Task | Notes |
|------|-------|
| Extend agent beyond Phase 1 placeholder | Continue after `session.acf2_id` is set |
| Add role-resolution prompt rules | Resolve role, seniority, employment type, team, and department |
| Query `designations` and `role_access_items` | Use tool-use, not full catalog context stuffing |
| Return structured selected-template data | Include confidence, reasoning, mandatory access, optional access |
| Support top-3 candidates | For medium confidence matches |
| Write confirmed role mapping | Insert/update `user_designations` after confident confirmation |
| Preserve no-match path | Return `no_match: true` for low confidence; no write to `user_designations` |
| Add tests | Direct match, vague role, gibberish, no-match, identity lock |

Exit criteria:

- ARUN01 -> identity -> "I am a backend developer" returns a matching template.
- Vague role input triggers clarification.
- Gibberish input re-prompts gracefully.
- Low-confidence SARA03 flow returns `no_match: true`.
- Backend logs show tool queries and matching reasoning.

Phase doc: `docs/phases/phase-02-role-resolver.md`

## Phase 3 - Template UI + Submission Flow

Goal:

Render the selected template in the right panel, let users review mandatory and optional access, and submit a request.

Tasks:

- template card in right panel
- mandatory items locked
- optional items toggleable
- support top-3 candidate selection
- submit final bundle through backend
- write `access_requests` through MCP write path
- update session with `final_bundle` and `request_id`

## Phase 4 - Risk Scorer + Privilege Guard

Goal:

Add governance intelligence before and during submission.

Risk Scorer:

- compute 0-100 risk score
- use approval history signals
- generate plain-language explanation
- store score and explanation on request

Privilege Guard:

- compare requested bundle with `privilege_edges`
- check `dangerous_combinations`
- warn or block depending on severity
- write audit log entries

## Phase 5 - ServiceNow + Teams + Orchestrator

Goal:

Create or mock ServiceNow RITMs, send Teams approval cards, handle approve/reject callbacks, and provision approved access through mock APIs.

Tasks:

- ServiceNow MCP or fallback
- Teams Adaptive Card
- approve/reject backend endpoints
- approval event state machine
- orchestrator for mock provisioning
- audit log for all state changes

## Phase 6 - Status Tracker + No-Match + Admin Dashboard

Goal:

Add request status tracking, no-match draft handling, and an admin view for audit/template ratification.

Tasks:

- status tracker tool
- live per-item approval state
- template draft creation for no-match roles
- admin ratification queue
- audit dashboard

## Phase 7 - Polish + Demo Prep

Goal:

Make the demo reliable and easy to run.

Tasks:

- graceful Bedrock/MCP/Teams/ServiceNow errors
- final seed verification
- demo script
- backup screen recording
- final docs review
- final ADR review

## Stretch - RetellAI Voice Layer

Goal:

Add optional voice input/output as a wrapper around the same FastAPI chat endpoint.

## Backend Logging Standard

| Prefix | Used For |
|--------|----------|
| `[AGENT]` | Agent state transitions and user-message handling |
| `[BEDROCK]` | LLM calls, stop reasons, and tool calls |
| `[MCP]` | SQL queries and row counts |
| `[MOCK]` | Mock Workday/provisioning calls |
| `[TEAMS]` | Teams webhook attempts |
| `[SERVICENOW]` | ServiceNow/RITM activity |
| `[ORCHESTRATOR]` | Provisioning orchestration |
| `[ERROR]` | Failures with context |

## Rules For AI Coding Tools

1. Frontend is UI-only.
2. Backend owns Bedrock, database access, webhooks, and business logic.
3. Secrets live only in `backend/.env`.
4. SQLite access for application flows goes through the MCP tool path.
5. Seed/setup scripts may use direct `sqlite3`.
6. Tailwind CSS v4 uses `@import "tailwindcss"` and `@theme inline`.
7. No MongoDB, Supabase, pgvector, Ollama, Gemini, Express backend, or RAG.
8. Update phase docs and ADRs when architecture changes.
9. Push completed changes to GitHub.

## Phase Documentation Template

```markdown
# Phase X - Name

## Status

## Goal

## What Was Built / Planned Work

## How It Works

## How To Test

## Decisions Made
```
