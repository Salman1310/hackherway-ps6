# CLAUDE.md — HackHERway PS6: AI-Powered Access Approval

Full project context for AI assistants and new contributors.

---

## Project Overview

**Hackathon:** Sun Life HackHERway 2025 — Problem Statement 6
**Team:** 2 members (Salman + Varuni)
**Goal:** Replace Sun Life's manual, email-based access request process with an AI-powered chat interface that verifies employee identity, resolves their role, recommends access templates, runs risk/privilege checks, routes approvals via MS Teams, and provisions access automatically.

---

## Folder Structure

```
hackherway-ps6/
├── backend/                   ← Python FastAPI server (port 8000)
│   ├── src/
│   │   ├── main.py            ← FastAPI app entry point + CORS
│   │   ├── types.py           ← Pydantic models (SessionState, MessageRequest, etc.)
│   │   ├── agent/
│   │   │   └── index.py       ← Conversational agent — tool-use loop with Bedrock
│   │   │   ├── lib/
│   │   │   ├── bedrock.py     ← AWS Bedrock client + converse() + tool-use support
│   │   │   ├── sqlite.py      ← Direct sqlite3 for REST endpoints only (NOT agent)
│   │   │   └── logger.py      ← Color-coded logging utility ([AGENT], [BEDROCK], etc.)
│   │   ├── mock/
│   │   │   ├── workday.py     ← Mock Workday API (GET /mock/workday/employee/{acf2_id})
│   │   │   ├── ad.py          ← Mock AD/LDAP provisioning (POST /mock/ad/provision)
│   │   │   ├── jira.py        ← Mock Jira provisioning (POST /mock/jira/provision)
│   │   │   └── sam.py         ← Mock SAM provisioning (POST /mock/sam/provision/*)
│   │   └── routes/
│   │       ├── agent.py       ← POST /api/agent/message
│   │       └── conversations.py ← GET /api/conversations
│   ├── mcp_server/
│   │   └── sqlite_server.py   ← FastMCP SQLite server (query_db + execute_db tools)
│   ├── scripts/
│   │   └── seed_sqlite.py     ← Seeds 3 demo users + all tables into SQLite
│   ├── .env.example           ← AWS creds, Bedrock model ID, DB path
│   ├── requirements.txt
│   └── .gitignore
│
├── frontend/                  ← Next.js frontend (port 3000) — DO NOT MODIFY
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx       ← Root page — 3-panel layout
│   │   │   ├── layout.tsx     ← Root layout
│   │   │   ├── globals.css    ← Tailwind v4 + Sun Life theme tokens
│   │   │   └── api/
│   │   │       ├── agent/message/route.ts     ← Proxy → backend:8000
│   │   │       ├── conversations/route.ts      ← Proxy → backend:8000
│   │   │       └── mock/                       ← Mock Workday/AD/Jira/SAM (frontend copy)
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── ChatPanel.tsx
│   │   │   │   └── RightPanel.tsx
│   │   │   └── chat/
│   │   │       ├── MessageBubble.tsx
│   │   │       ├── ChatInput.tsx
│   │   │       └── TypingIndicator.tsx
│   │   ├── contexts/
│   │   │   └── SessionContext.tsx
│   │   ├── hooks/
│   │   │   └── useChat.ts
│   │   └── lib/
│   │       ├── types.ts
│   │       ├── config.ts
│   │       └── mockData.ts
│   ├── .env.example
│   ├── next.config.ts
│   └── package.json
│
├── docs/
│   └── phases/                ← Per-phase implementation documentation
│       ├── phase-00-foundation.md
│       ├── phase-01-agent-identity.md
│       ├── phase-02-role-resolver.md
│       ├── phase-03-template-ui.md
│       ├── phase-04-risk-privilege.md
│       ├── phase-05-servicenow-teams-orchestrator.md
│       ├── phase-06-status-nomatch-admin.md
│       └── phase-07-polish-demo.md
│
├── ADR.md                     ← All Architecture Decision Records
├── PHASES.md                  ← Phase map and task breakdown (Phases 0–7 + Stretch)
├── SETUP.md                   ← Full setup guide for new machines
└── CLAUDE.md                  ← This file
```

---

## Architecture

```
User ↔ Next.js Frontend (port 3000)
         ↕ HTTP (JSON)
       FastAPI Backend (port 8000)
         ↕
       Access Agent (single agent, 4 capabilities)
         │
         ├── SQLite MCP Server (agent generates SQL → MCP executes)
         ├── Mock APIs (Workday, AD/LDAP, Jira, SAM)
         ├── ServiceNow MCP (RITM ticket creation — Phase 5)
         └── Bedrock Claude Sonnet 4.6 (LLM only)

Approval events → Orchestrator (separate module, event-driven)
                     ├── SQLite MCP
                     ├── Mock provisioning APIs
                     └── MS Teams Incoming Webhook
```

**Key rules:**
- Frontend never calls Bedrock, SQLite, or MCP directly. All goes through FastAPI.
- FastAPI is the web server. The Agent is a separate Python module — not FastAPI itself.
- The Orchestrator is a separate Python module — event-driven, not conversational.
- Bedrock is used ONLY as the LLM. Not for infrastructure, not for MCP routing.
- One agent with four capabilities (not four separate agents).
- SQLite access goes through MCP only — no direct `sqlite3` calls from application code.

---

## Agent Capabilities

| Capability | What It Does | When It Activates |
|------------|-------------|-------------------|
| **Role Resolver** | Asks clarifying questions until role, seniority, and employment type are confirmed | After identity verification, when role input is vague |
| **Risk Scorer** | Computes 0–100 risk score with plain-language explanation, injected into Teams card | On access request submission |
| **Privilege Guard** | Checks user's existing permissions against dangerous combinations, warns before submission | Before submission — blocks if CRITICAL combo found |
| **Status Tracker** | Answers "what's the status of my request?" with live per-item approval state | Any time post-submission |

---

## Agent Pattern: Tool-Use Loop

The agent does NOT parse intent as JSON. It uses Bedrock's native tool-use (function calling):

1. User message arrives at FastAPI
2. Agent sends message + tool definitions to Bedrock Converse API
3. Bedrock decides which tool to call (e.g. `query_db`)
4. Agent generates SQL, FastAPI routes to SQLite MCP, returns result
5. Agent sends tool result back to Bedrock
6. Loop until Bedrock returns a final text response

**Tool definitions:**
- `query_db` — agent generates SQL → MCP executes → returns rows
- `check_privilege_accumulation` — queries `privilege_edges` + `dangerous_combinations`
- `get_request_status` — queries `approval_events` for current request
- `submit_access_request` — writes final bundle to `access_requests` via MCP

**Regex fallback:** If Bedrock fails entirely, pattern `[A-Z]{2,8}\d{2,6}` extracts ACF2 ID.

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Next.js 16.2.4 (Turbopack), React 19, TypeScript | App Router — frozen, do not modify |
| Styling | Tailwind CSS v4 | `@theme inline` syntax, no tailwind.config.js |
| Backend | Python 3.11+, FastAPI, uvicorn | Port 8000 |
| LLM | AWS Bedrock — Claude Sonnet 4.6 | Only LLM provider. Only used as LLM |
| Database | SQLite via official MCP server | Schema injected into agent system prompt |
| ITSM | ServiceNow MCP (with mock fallback) | Phase 5+ |
| Notifications | MS Teams Incoming Webhook + Adaptive Cards | Phase 5+ |
| Voice (stretch) | RetellAI | Voice I/O wrapper around FastAPI |
| Auth | `BYPASS_AUTH=true` | Azure AD/MSAL documented as production path |

**Dead technologies — do NOT use:**
- ~~MongoDB~~ → SQLite MCP
- ~~better-sqlite3~~ → SQLite MCP server
- ~~nomic-embed-text / Ollama~~ → Context stuffing
- ~~pgvector / Supabase~~ → SQLite MCP
- ~~Gemini API~~ → Bedrock only
- ~~Express / Node.js backend~~ → Python / FastAPI
- ~~RAG / embeddings~~ → Context stuffing (all templates in system prompt)

---

## Database Schema

All tables accessed via SQLite MCP only (no direct sqlite3 calls).

### Core entity model (3-table normalized role/access model)

| Table | Purpose |
|-------|---------|
| `users` | ACF2 ID, name, team, manager, dept, employment_type. **No designation column** — link lives in `user_designations` |
| `user_designations` | One row per user (PK = `acf2_id`) → designation_id. Enforces 1 role per user. Absence of row = no role assigned (e.g. SARA03 no-match scenario) |
| `designations` | id, title, description. **No JSON columns** — items normalized into `role_access_items` |
| `role_access_items` | designation_id, access_item, mandatory (0/1), description, owner_team, servicenow_catalog_item_id. ~80 rows total (8 roles × ~10 items) |

### Request / approval / audit tables

| Table | Purpose |
|-------|---------|
| `access_requests` | Submitted requests: id (= REQ ticket), acf2_id, final bundle, risk score, status |
| `approval_events` | Per-item approval state (= per RITM): request_id, access_item, ritm_id, status (pending/approved/rejected) |
| `approver_routing` | Maps access items → approver webhook URL |
| `audit_log` | Append-only trail of all state changes |
| `privilege_edges` | User's existing permissions (for Privilege Guard) |
| `dangerous_combinations` | Permission combos that trigger warnings |
| `template_drafts` | No-match flow draft templates pending admin ratification |
| `conversations` | Conversation records per ACF2 ID |
| `messages` | Chat message history |

### Status tracking path (Phase 6)

```
users.acf2_id
  → access_requests.acf2_id (= REQ ticket)
    → approval_events.request_id (= per-item RITM tickets)
      → ServiceNow API (live state per RITM)
```
`user_designations` and `role_access_items` are **not** in the status path — they drive Phase 2 (role resolution) and Phase 3 (template UI), not status.

---

## Environment Variables

### `backend/.env` (AWS creds live HERE — never in frontend)

| Variable | Required | Value |
|----------|----------|-------|
| `AWS_ACCESS_KEY_ID` | Yes | From company credentials |
| `AWS_SECRET_ACCESS_KEY` | Yes | From company credentials |
| `AWS_SESSION_TOKEN` | If temp creds | Company sessions require this |
| `AWS_REGION` | Yes | `us-east-1` |
| `BEDROCK_MODEL_ID` | Yes | Find in AWS Console → Bedrock → Model catalog |
| `SQLITE_DB_PATH` | No | Default: `./hackherway.db` |
| `SERVICENOW_INSTANCE_URL` | Phase 5+ | ServiceNow instance URL |
| `SERVICENOW_USERNAME` | Phase 5+ | ServiceNow username |
| `SERVICENOW_PASSWORD` | Phase 5+ | ServiceNow password |
| `TEAMS_WEBHOOK_URL` | Phase 5+ | Teams Incoming Webhook URL |
| `PORT` | No | Default: `8000` |

### `frontend/.env` (frontend only)

| Variable | Required | Value |
|----------|----------|-------|
| `BACKEND_URL` | Yes | `http://localhost:8000` |
| `PUBLIC_BASE_URL` | Phase 5+ | `http://localhost:3000` (or ngrok URL) |

---

## How to Run

### First-time setup

```bash
# 1. Clone
git clone https://github.com/Salman1310/hackherway-ps6.git
cd hackherway-ps6

# 2. Backend setup (Python)
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # fill in AWS credentials + BEDROCK_MODEL_ID
python scripts/seed_sqlite.py   # creates hackherway.db with demo users

# 3. Frontend setup
cd ../frontend
npm install
copy .env.example .env          # set BACKEND_URL=http://localhost:8000
```

### Every run (two terminals)

**Terminal 1 — Backend:**
```bash
cd backend
.venv\Scripts\activate
uvicorn src.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

---

## Demo Users

| ACF2 ID | Name | Team | Dept | Type | Demo Scenario |
|---------|------|------|------|------|---------------|
| `ARUN01` | Arun Mehta | Cloud Infrastructure | Technology | Full-time | Happy path + Risk Scorer (anomaly score ~78) |
| `NEHA02` | Neha Kapoor | Finance Analytics | Finance | Contract | Privilege Guard fires — dangerous combination detected |
| `SARA03` | Sara Chen | TBD | TBD | Full-time | No-match → template generation → admin ratification |

**Demo sequence (5–7 min):**
1. **ARUN01** — Full happy path: ACF2 → identity → role → template → submit → RITM → Teams card with Risk Scorer (~78, amber/red)
2. **NEHA02** — Same flow but Privilege Guard interrupts before submission
3. **SARA03** — Role doesn't match any template → agent drafts one → admin ratification

---

## Backend Logging Standard

Every backend module uses the shared logging utility (`backend/src/lib/logger.py`):

| Prefix | Color | Used For |
|--------|-------|----------|
| `[AGENT]` | Cyan | User messages received, agent state transitions |
| `[BEDROCK]` | Yellow | LLM calls: token counts, tool_call decisions, final responses |
| `[MCP]` | Blue | SQL queries sent, row counts returned, errors |
| `[MOCK]` | Magenta | Mock API calls: Workday, AD, Jira, SAM |
| `[TEAMS]` | Green | Webhook POST attempts, card sent confirmations |
| `[SERVICENOW]` | Green | RITM creation, status updates |
| `[ORCHESTRATOR]` | White | Provisioning triggers, parallel call results |
| `[ERROR]` | Red | Any failure — always includes context |

---

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 0 | Foundation | 🔲 Not started (needs rework for new schema/MCP/users) |
| 1 | Agent Core + Identity Verification | 🔲 Not started (needs tool-use loop) |
| 2 | Role Resolver + Template Matching | 🔲 Not started |
| 3 | Template UI + Submission Flow | 🔲 Not started |
| 4 | Risk Scorer + Privilege Guard | 🔲 Not started |
| 5 | ServiceNow MCP + Teams + Orchestrator | 🔲 Not started |
| 6 | Status Tracker + No-Match + Admin Dashboard | 🔲 Not started |
| 7 | Polish + Demo Prep | 🔲 Not started |
| Stretch | RetellAI Voice Layer | 🔲 Not started |

> Note: Prior session built UI shell (frozen as frontend/) and initial ACF2 identity verification. The backend agent architecture is being reworked to use SQLite MCP + tool-use loop per this plan.

---

## Rules for AI Coding Tools

1. **Frontend (`frontend/`) is frozen.** Do not modify any frontend files. Communication is HTTP only.
2. **Frontend never imports or calls:** Bedrock, SQLite, MCP, boto3, any AWS SDK, any database driver.
3. **Backend never imports or calls:** React, Next.js, any UI framework, any browser API.
4. **Frontend API routes are thin proxies.** Zero business logic.
5. **All secrets live in `backend/.env` only.** Frontend `.env` contains only `BACKEND_URL` and public config.
6. **Every backend action must produce a log line** using the logging utility with the correct prefix.
7. **Tailwind CSS v4 syntax** — `@import "tailwindcss"` and `@theme inline {}`, NOT `tailwind.config.js`.
8. **Next.js App Router** — route handlers use `export async function POST(request: Request)`.
9. **Python backend uses FastAPI + uvicorn.** No Express, no Node.js in backend.
10. **SQLite access goes through MCP only.** No direct `sqlite3` calls from application code.
11. **On phase completion:** create `docs/phases/phase-XX-name.md` before moving to next phase.
12. **Never commit:** `.env`, `credentials.txt`, `*.token`, `node_modules/`, `.next/`, `__pycache__/`, `*.db`

---

## Key Architecture Decisions

See `ADR.md` for full log. Key ones:

| ADR | Decision | Reason |
|-----|----------|--------|
| ADR-002 | Session state in React context | Stateless backend, all state in frontend session |
| ADR-003 | MongoDB Atlas → SQLite locally | Corporate firewall blocks Atlas port 27017 |
| ADR-005 | ServiceNow MCP + mock APIs | Real ITSM tickets; provisioning targets mocked |
| ADR-010 | AWS Bedrock sole LLM provider | Company has AWS credentials; no Gemini/Ollama needed |
| ADR-011 | Context stuffing (templates in prompt) | Eliminates need for RAG/embeddings/Ollama |
| ADR-013 | Auth bypassed (BYPASS_AUTH=true) | Azure AD/MSAL out of hackathon scope |
| ADR-016 | GitHub private repo (Salman1310/hackherway-ps6) | Collaboration between personal and company laptops |
