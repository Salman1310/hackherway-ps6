# Team Build Plan - PS6 AI-Powered Access Approval

## Purpose

This document explains how the team should continue building from the current repository state. It replaces older planning notes that referenced RIYA001, Gemini, Ollama, Supabase, pgvector, RAG, and the old phase numbering.

Current stack:

```text
Frontend: Next.js + React + TypeScript + Tailwind CSS v4
Backend: FastAPI + Python
LLM: AWS Bedrock Claude Sonnet 4.6
Database: local SQLite
DB access pattern: local FastMCP SQLite wrapper
Mocks: Workday, AD, Jira, SAM
Future integrations: ServiceNow MCP or fallback, MS Teams webhook
```

## Current Project State

| Area | Status |
|------|--------|
| Frontend shell | Built |
| Backend FastAPI app | Built |
| Phase 0A foundation | Built |
| Phase 1 identity verification | Built |
| Phase 0B normalized schema | Built |
| Phase 2 role resolver | Built |
| Phase 3 submission flow | Next |

Phase 1 currently works around ACF2 identity:

- verifies known ACF2 IDs through Bedrock tool-use and SQLite
- locks identity after verification
- explains ACF2 without giving sample IDs
- exposes a reset chat control
- keeps frontend as a thin UI layer

Phase 2 currently works around role/template matching:

- continues after verified identity
- queries `designations` and `role_access_items` through Bedrock tool-use
- returns `resolved_role`, `selected_template`, and mandatory `final_bundle`
- writes confident matches to `user_designations`
- renders the selected template in the right panel
- does not submit access requests yet

## Demo Story

The demo should tell one simple story:

```text
New joinee asks for access
  -> AI verifies identity
  -> AI resolves role
  -> AI recommends role-based access
  -> user submits one bundle
  -> approvals are routed
  -> access is provisioned or tracked
  -> audit history is preserved
```

## Demo Users

| ACF2 ID | Name | Scenario |
|---------|------|----------|
| ARUN01 | Arun Mehta | Happy path and later Risk Scorer |
| NEHA02 | Neha Kapoor | Privilege Guard scenario |
| SARA03 | Sara Chen | No-match/admin ratification scenario |

Do not use old planning IDs such as RIYA001, JOHN002, PRIYA003, or SAM004.

## Build Order

### Step 1 - Phase 0B

Status: Built.

Goal: replace JSON-based designation access lists with normalized role/access tables.

Target tables:

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

Built work:

- remove legacy JSON access columns from `designations`
- add `role_access_items`
- add `user_designations`
- seed ARUN01 and NEHA02 role mappings
- leave SARA03 unmapped
- preserve existing demo users and access item names
- verify Phase 1 and Phase 2 tests pass

### Step 2 - Phase 2

Status: Built.

Goal: resolve role and match access template through tool-use queries.

Built work:

- continue agent flow after identity verification
- ask clarifying questions for vague role input
- query `designations` and `role_access_items`
- return structured `resolved_role` and `selected_template`
- write confident match to `user_designations`
- render selected template in the right panel

### Step 3 - Build Phase 3

Phase 3 is the next build step. Do not start it unless explicitly requested.

Goal: turn the selected template into a submit-ready access bundle.

Key work:

- right-panel template card
- mandatory items locked
- optional items toggleable
- user confirmation
- backend submission endpoint
- write `access_requests`

### Step 4 - Build Phase 4

Goal: add governance intelligence.

Key work:

- Risk Scorer for request anomaly score and explanation
- Privilege Guard for dangerous access combinations
- audit logs for warning/escalation events

### Step 5 - Build Phase 5

Goal: approval and provisioning workflow.

Key work:

- ServiceNow RITM creation or fallback
- Teams Adaptive Card
- approve/reject callbacks
- orchestrator for mock AD/Jira/SAM provisioning
- update approval events and audit logs

### Step 6 - Build Phase 6

Goal: status tracking and admin support.

Key work:

- ask "what is my status?"
- right-panel status tracker
- no-match draft templates
- admin ratification queue
- audit dashboard

### Step 7 - Polish

Goal: reliable 5-7 minute demo.

Key work:

- final seed reset
- error handling pass
- demo script
- backup recording
- final docs/ADR review

## Ownership Model

For a two-person team:

| Owner | Area |
|-------|------|
| Developer 1 | Frontend, right panel, demo flow, UX polish |
| Developer 2 | Backend, agent, database schema, seed data, integrations |

For a larger team:

| Owner | Area |
|-------|------|
| Frontend owner | Chat UI, right panel, status/admin views |
| Agent owner | Bedrock prompts, tool-use loop, role resolver, risk explanations |
| Data owner | SQLite schema, seed data, dangerous combinations, audit queries |
| Integration owner | ServiceNow, Teams, approval callbacks, orchestrator |

## Shared Contracts

### Session State

```json
{
  "acf2_id": "ARUN01",
  "workday_context": {
    "name": "Arun Mehta",
    "team": "Cloud Infrastructure",
    "manager": "Raj Kumar",
    "dept": "Technology",
    "employment_type": "full-time"
  },
  "resolved_role": {
    "role": "Backend Developer",
    "designation_id": "backend_developer",
    "seniority": "Junior",
    "employment_type": "full-time",
    "team": "Cloud Infrastructure",
    "dept": "Technology",
    "confidence": 0.96
  },
  "selected_template": {
    "id": "backend_developer",
    "name": "Backend Developer",
    "description": "Software engineer building server-side services and APIs",
    "confidence": 0.96,
    "reasoning": "Role description maps to backend development in Technology.",
    "mandatory_access": [],
    "optional_access": []
  },
  "final_bundle": [],
  "request_id": null
}
```

### Current Endpoint Contracts

```text
POST /api/agent/message
GET  /api/conversations
GET  /mock/workday/employee/{acf2_id}
POST /mock/ad/provision
POST /mock/jira/provision
POST /mock/sam/provision/github-copilot
POST /mock/sam/provision/non-primary-id
```

Future endpoints should stay backend-owned and frontend-proxied.

### Selected Template Shape

```json
{
  "id": "backend_developer",
  "name": "Backend Developer",
  "confidence": 0.93,
  "reasoning": "Role description maps to backend development in Technology.",
  "mandatory_access": [
    {
      "id": "github_repo_access",
      "name": "GitHub repository access",
      "system": "GitHub",
      "reason": "Required for source code work",
      "mandatory": true,
      "owner_team": "Engineering Tools",
      "servicenow_catalog_item_id": "SN-GITHUB-REPO",
      "sort_order": 10
    }
  ],
  "optional_access": []
}
```

## Engineering Rules

- Keep frontend UI-only.
- Keep backend business logic in FastAPI/agent modules.
- Keep secrets out of frontend and git.
- Use AWS Bedrock only for LLM.
- Use SQLite MCP tool path for application database flows.
- Seed/setup scripts may use direct `sqlite3`.
- Do not add Gemini, Ollama, Supabase, pgvector, MongoDB, Express backend, or RAG.
- Update docs and ADRs when schema or architecture changes.
- Push completed changes to GitHub.

## Verification Checklist

Before calling a phase complete:

- [ ] Backend tests pass.
- [ ] Backend source compiles.
- [ ] Frontend lint passes.
- [ ] Frontend build passes.
- [ ] Seed script runs cleanly if schema/data changed.
- [ ] Phase doc is updated.
- [ ] ADR is updated if architecture changed.
- [ ] Changes are committed and pushed.

Recommended commands:

```bash
cd backend
python scripts/seed_sqlite.py
python -m unittest discover -s tests
python -m compileall src mcp_server scripts tests

cd ../frontend
npm run lint
npm run build
```

## Cut Line If Time Runs Short

Must have:

- ACF2 identity verification
- role/template match
- template display
- bundled request submission
- approval routing demo or mock
- audit/status visibility

Should have:

- Privilege Guard
- Risk Scorer
- Teams card

Cuttable:

- RetellAI voice
- full admin dashboard editing
- full ServiceNow live integration if fallback is working
- adaptive persona learning

## Demo Rehearsal Checklist

- [ ] ARUN01 identity and happy path works.
- [ ] Role resolver picks an access template.
- [ ] Template appears in the right panel.
- [ ] Request can be submitted.
- [ ] NEHA02 privilege warning works if Phase 4 is included.
- [ ] SARA03 no-match path works if Phase 6 is included.
- [ ] Teams channel is ready if Phase 5 is included.
- [ ] Backend logs are readable.
- [ ] Database is freshly seeded.
- [ ] Backup recording exists.

## One-Line Pitch

```text
We turn fragmented access provisioning into an AI-guided, role-based, approval-routed, and auditable workflow.
```
