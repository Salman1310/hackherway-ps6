# CLAUDE.md — HackHERway PS6: AI-Powered Access Approval

Full project context for AI assistants and new contributors.

---

## Project Overview

**Hackathon:** Sun Life HackHERway 2025 — Problem Statement 6
**Team:** 2 members (Salman + Varuni)
**Goal:** Replace Sun Life's manual, email-based access request process with an AI-powered chat interface that verifies employee identity, recommends access templates, routes approvals to the right people via MS Teams, and provisions access automatically.

---

## Folder Structure

```
hackherway-ps6/
├── backend/                   ← Express agent server (port 8000)
│   ├── src/
│   │   ├── index.ts           ← Express app entry point
│   │   ├── types.ts           ← Shared TypeScript types
│   │   ├── agent/
│   │   │   └── index.ts       ← Conversational agent logic (Bedrock)
│   │   ├── lib/
│   │   │   ├── bedrock.ts     ← AWS Bedrock client + converse()
│   │   │   └── sqlite.ts      ← SQLite singleton + schema init
│   │   └── routes/
│   │       ├── agent.ts       ← POST /api/agent/message
│   │       └── conversations.ts ← GET /api/conversations
│   ├── scripts/
│   │   └── seed-sqlite.mjs    ← Seeds 4 demo users into SQLite
│   ├── .env.example           ← AWS creds, Bedrock model ID, DB path
│   ├── package.json
│   └── tsconfig.json
│
├── web/                       ← Next.js frontend (port 3000)
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx       ← Root page — 3-panel layout
│   │   │   ├── layout.tsx     ← Root layout
│   │   │   ├── globals.css    ← Tailwind v4 + Sun Life theme tokens
│   │   │   └── api/
│   │   │       ├── agent/message/route.ts     ← Proxy → backend:8000
│   │   │       ├── conversations/route.ts      ← Proxy → backend:8000
│   │   │       └── mock/                       ← Mock Workday/AD/Jira/SAM APIs
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx       ← History panel
│   │   │   │   ├── ChatPanel.tsx     ← Message list + input
│   │   │   │   └── RightPanel.tsx    ← Template cards + status tracker
│   │   │   └── chat/
│   │   │       ├── MessageBubble.tsx
│   │   │       ├── ChatInput.tsx
│   │   │       └── TypingIndicator.tsx
│   │   ├── contexts/
│   │   │   └── SessionContext.tsx    ← Global session + messages state
│   │   ├── hooks/
│   │   │   └── useChat.ts            ← Send message → backend → update state
│   │   └── lib/
│   │       ├── types.ts              ← TypeScript types (session, message)
│   │       ├── config.ts             ← Env var exports
│   │       └── mockData.ts           ← 4 demo employee records (for mock APIs)
│   ├── .env.example           ← Only BACKEND_URL (no AWS creds here)
│   ├── next.config.ts
│   └── package.json
│
├── docs/
│   └── phases/                ← Per-phase implementation documentation
│       ├── phase-00-foundation.md
│       ├── phase-01-ui-shell.md
│       └── phase-02-identity-verification.md
│
├── ADR.md                     ← All Architecture Decision Records (ADR-001 to ADR-016)
├── PHASES.md                  ← Phase map and task breakdown (Phases 0–15)
├── SETUP.md                   ← Full setup guide for new machines
└── CLAUDE.md                  ← This file
```

---

## Architecture

```
Browser (port 3000)
    │
    │  HTTP
    ▼
Next.js Frontend (web/)
    │  No LLM, no DB
    │  Proxies API calls via Next.js API routes
    │
    │  HTTP → localhost:8000
    ▼
Express Backend (backend/)
    ├── Agent (Bedrock Claude Sonnet 4.6)
    │     Conversational AI — understands natural language,
    │     extracts ACF2 ID, generates personalised responses
    ├── SQLite (hackherway.db)
    │     Local DB — users, conversations, messages, ritm_requests
    └── Future: ServiceNow MCP, Teams webhooks, provisioning
```

**Key principle:** Frontend never holds LLM credentials. All AI and DB logic lives in the backend.

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Next.js 16.2.4 (Turbopack), React 19, TypeScript | App Router |
| Styling | Tailwind CSS v4 | `@theme inline` syntax, no tailwind.config.js |
| Backend | Express 4, TypeScript, ts-node-dev | Port 8000 |
| LLM | AWS Bedrock — Claude Sonnet 4.6 | `us.anthropic.claude-sonnet-4-6-*` |
| Local DB | SQLite (`better-sqlite3`) | WAL mode, gitignored `.db` file |
| Cloud DB | MongoDB Atlas M0 | Blocked by corporate firewall — unused in dev |
| Tickets | ServiceNow MCP | Phase 7+ |
| Notifications | MS Teams Incoming Webhook + Adaptive Cards | Phase 7+ |
| Auth | `BYPASS_AUTH=true` (bypassed for hackathon) | Azure AD/MSAL documented in ADR-013 |

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
| `PORT` | No | Default: `8000` |

### `web/.env` (frontend only)

| Variable | Required | Value |
|----------|----------|-------|
| `BACKEND_URL` | Yes | `http://localhost:8000` |
| `PUBLIC_BASE_URL` | Phase 7+ | `http://localhost:3000` (or ngrok URL) |
| `TEAMS_WEBHOOK_URL` | Phase 7+ | From Teams channel setup |

---

## How to Run

### First-time setup

```bash
# 1. Clone
git clone https://github.com/Salman1310/hackherway-ps6.git
cd hackherway-ps6

# 2. Backend setup
cd backend
npm install
copy .env.example .env    # fill in AWS credentials
npm run seed              # creates hackherway.db with 4 demo users

# 3. Frontend setup
cd ../web
npm install
copy .env.example .env    # set BACKEND_URL=http://localhost:8000
```

### Every run (two terminals)

**Terminal 1 — Backend:**
```bash
cd backend
npm run dev
# → Running on http://localhost:8000
```

**Terminal 2 — Frontend:**
```bash
cd web
npm run dev
# → Running on http://localhost:3000
```

---

## Demo Users

| ACF2 ID | Name | Team | Dept | Type | Demo Scenario |
|---------|------|------|------|------|---------------|
| `RIYA001` | Riya Sharma | Payments Backend | Technology | Full-time | Standard onboarding |
| `JOHN002` | John Mathews | Cloud Infrastructure | Technology | Full-time | High anomaly score (Phase 10) |
| `PRIYA003` | Priya Nair | Finance Analytics | Finance | Contract | Dangerous privilege combo (Phase 11) |
| `SAM004` | Sam Wilson | TBD | TBD | Full-time | No-template path (Phase 14) |

---

## Agent Design

The backend agent is conversational — not a keyword matcher. It uses Bedrock to understand **intent** from natural language before acting.

### ACF2 Phase (current — Phase 2)

User says anything → agent calls Bedrock to classify intent:

| User says | Intent | Agent does |
|-----------|--------|------------|
| `"RIYA001"` | `provide_acf2` | Verify in SQLite → greeting |
| `"Yes, my ID is RIYA001"` | `provide_acf2` | Verify in SQLite → greeting |
| `"What's an ACF2 ID?"` | `explain` | Returns explanation |
| `"I can't find my ID"` | `help_find` | Returns guidance |
| `"Hello"` | `redirect` | Gently redirects |
| Unknown ACF2 ID | — | Hard block message |

**Fallback:** If Bedrock fails, regex pattern `[A-Z]{2,8}\d{2,6}` extracts ACF2 ID from message. Flow never breaks.

### Future phases (3–15)

Once ACF2 verified, the agent transitions to:
- Phase 3: Role resolution (ambiguity questions)
- Phase 4: Template retrieval (context stuffing, 8 personas in system prompt)
- Phase 5: Template display in right panel
- Phase 6–8: Approval routing + provisioning
- Phase 9–11: Status queries, anomaly scoring, privilege checks
- Phase 12–14: D1 learning, admin dashboard, template generation

---

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 0 | Foundation | ✅ Done |
| 1 | UI Shell | ✅ Done |
| 2 | Identity Verification | ✅ Done |
| 3 | Agent A: Role Resolution | 🔲 Not started |
| 4 | Template Retrieval | 🔲 Not started |
| 5 | Template UI + Customisation | 🔲 Not started |
| 6 | Approval Engine | 🔲 Not started |
| 7 | MS Teams Adaptive Cards | 🔲 Not started |
| 8 | Orchestrator + Provisioning | 🔲 Not started |
| 9 | Agent C: Status Queries | 🔲 Not started |
| 10 | D2: Anomaly Scoring | 🔲 Not started |
| 11 | Agent B: Privilege Check | 🔲 Not started |
| 12 | D1: Adaptive Learning | 🔲 Not started |
| 13 | Admin Dashboard | 🔲 Not started |
| 14 | Template Generation | 🔲 Not started |
| 15 | Polish + Demo Prep | 🔲 Not started |

---

## Key Architecture Decisions

See `ADR.md` for full decision log. Key ones:

| ADR | Decision | Reason |
|-----|----------|--------|
| ADR-002 | Session state in React context | Stateless backend, all state in frontend session |
| ADR-003 | MongoDB Atlas M0 → SQLite locally | Corporate firewall blocks Atlas port 27017 |
| ADR-005 | ServiceNow MCP + SAM mock | Real ITSM tickets; SAM mocked for NPE/Copilot |
| ADR-010 | AWS Bedrock sole LLM provider | Company has AWS credentials; no Gemini/Ollama needed |
| ADR-011 | LLM context stuffing (8 templates in prompt) | Eliminates need for RAG/embeddings/Ollama |
| ADR-013 | Auth bypassed (BYPASS_AUTH=true) | Azure AD/MSAL out of hackathon scope |
| ADR-016 | GitHub private repo (Salman1310/hackherway-ps6) | Collaboration between personal and company laptops |

---

## Important Notes for AI Assistants

1. **Frontend never calls Bedrock or SQLite directly.** All such calls go through `backend/`.
2. **Frontend API routes are thin proxies** — they forward requests to `BACKEND_URL` and return the response.
3. **Tailwind v4 syntax** — uses `@import "tailwindcss"` and `@theme inline {}`, NOT `tailwind.config.js`.
4. **Next.js 16 App Router** — route handlers use `export async function POST(request: Request)`.
5. **Two processes required** — backend on 8000, frontend on 3000. Both must be running.
6. **SQLite db lives in `backend/hackherway.db`** — gitignored, seeded per machine with `npm run seed`.
7. **Agent intent detection uses Bedrock** — with regex fallback if Bedrock fails.
8. **Session state lives in frontend** — `SessionContext.tsx`. Backend is stateless per request.
