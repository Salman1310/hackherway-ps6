# Build Phases — PS6: AI-Powered Access Approval
## HackHERway | Sun Life

> **Principle:** Every phase ends with something demoable and testable. No phase ends with half-built infrastructure.
> Every phase produces a documentation file in `docs/phases/` covering what was built, why, and how.
> ADR.md must be updated on any phase that changes a structural decision.

---

## Architecture Summary

```
User ↔ Next.js Frontend (port 3000)
         ↕ HTTP (JSON)
       FastAPI Backend (port 8000)
         ↕
       Access Agent (single agent, 4 capabilities)
         │
         ├── SQLite MCP Server (reads/writes via LLM-generated SQL)
         ├── Mock APIs (Workday, AD/LDAP, Jira, SAM)
         ├── ServiceNow MCP (RITM ticket creation)
         └── Bedrock Claude Sonnet 4.6 (LLM only — no other Bedrock usage)

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

---

## Agent Capabilities

| Capability | What It Does | When It Activates |
|------------|-------------|-------------------|
| **Role Resolver** | Asks clarifying questions until role, seniority, and employment type are confirmed | After identity verification, when role input is vague |
| **Risk Scorer** | Computes 0–100 risk score with plain-language explanation, injected into Teams card | On access request submission |
| **Privilege Guard** | Checks user's existing permissions against dangerous combinations, warns before submission | Before submission — blocks if CRITICAL combo found |
| **Status Tracker** | Answers "what's the status of my request?" with live per-item approval state | Any time post-submission |

---

## Demo Users

| ACF2 ID | Name | Team | Dept | Type | Demo Scenario |
|---------|------|------|------|------|---------------|
| `ARUN01` | Arun Mehta | Cloud Infrastructure | Technology | Full-time | Happy path + Risk Scorer (anomaly score ~78) |
| `NEHA02` | Neha Kapoor | Finance Analytics | Finance | Contract | Privilege Guard fires — dangerous combination detected |
| `SARA03` | Sara Chen | TBD | TBD | Full-time | No-match → template generation → admin ratification |

**Demo sequence (5–7 minutes):**
1. **ARUN01** — Full happy path: ACF2 → identity → role → template → submit → ServiceNow RITM → Teams card with Risk Scorer (score ~78, amber/red). Judges see the complete flow AND the anomaly intelligence.
2. **NEHA02** — Same flow, but Privilege Guard interrupts before submission. "You already have prod DB read access. Adding deploy pipeline write access would create a critical privilege combination." Judges see the contrast.
3. **SARA03** (if time) — Role doesn't match any template → agent drafts one → admin ratification queue. Shows edge case handling.

---

## Template Matching Strategy

Context stuffing — all designation templates injected into the agent's system prompt. Claude sees all templates simultaneously and selects the best match based on resolved role, seniority, team, and department.

MCP (SQLite) is used for everything else: user lookup, privilege checks, writes.

Templates are NOT retrieved via MCP/SQL because natural language roles don't map cleanly to SQL WHERE clauses. Claude's reasoning is better suited for fuzzy matching across 8 templates than SQL LIKE queries.

---

## Phase Map

```
Phase 0   → Foundation: schema, SQLite MCP, mocks, logging, rules
Phase 1   → Agent Core + Identity Verification (full stack)
Phase 2   → Role Resolver + Template Matching
Phase 3   → Template UI + Submission Flow
Phase 4   → Risk Scorer + Privilege Guard (wired into agent flow)
Phase 5   → ServiceNow MCP + Teams Adaptive Cards + Orchestrator
Phase 6   → Status Tracker + No-Match Flow + Admin Dashboard
Phase 7   → Polish + Demo Prep
Stretch   → RetellAI Voice Layer
```

**At the end of any phase from Phase 3 onward, you have a demoable product.**

| Phase | Name | Status |
|-------|------|--------|
| 0 | Foundation | 🔲 Not started |
| 1 | Agent Core + Identity Verification | 🔲 Not started |
| 2 | Role Resolver + Template Matching | 🔲 Not started |
| 3 | Template UI + Submission Flow | 🔲 Not started |
| 4 | Risk Scorer + Privilege Guard | 🔲 Not started |
| 5 | ServiceNow MCP + Teams + Orchestrator | 🔲 Not started |
| 6 | Status Tracker + No-Match + Admin Dashboard | 🔲 Not started |
| 7 | Polish + Demo Prep | 🔲 Not started |
| Stretch | RetellAI Voice Layer | 🔲 Not started |

---

## Phase 0 — Foundation

**Goal:** Repo structure finalized, SQLite schema created and seeded, MCP server responding, mock APIs running, backend logging working. Zero features — but everything is ready to build on.

| Task | Notes |
|------|-------|
| Finalize folder structure: `frontend/`, `backend/`, `docs/phases/` | Remove any stale folders from old architecture |
| Create SQLite schema — all tables | `users`, `designations`, `access_requests`, `approval_events`, `approver_routing`, `audit_log`, `privilege_edges`, `dangerous_combinations`, `template_drafts` |
| Seed 3 demo users: ARUN01, NEHA02, SARA03 | With correct team/dept/manager data per demo scenarios |
| Seed 5–8 designation templates into `designations` | Backend Dev, DevOps, Data Analyst, Finance Analyst, Intern, Manager, Auditor, Contractor |
| Seed `dangerous_combinations` table | Prod DB write + deploy pipeline write = CRITICAL. Prod DB read + deploy pipeline write = HIGH. Any prod access + intern seniority = HIGH. Finance data + external API = HIGH. NPE + intern seniority = HIGH |
| Seed `privilege_edges` for NEHA02 | Pre-existing permissions that will trigger Privilege Guard in Phase 4 |
| Seed synthetic `approval_events` for ARUN01 | Historical data that produces Risk Scorer anomaly score ~78 |
| Seed `approver_routing` table | All entries point to single Teams webhook URL for demo |
| Install and configure official SQLite MCP server | Verify: MCP server accepts SQL, returns results |
| Inject full SQLite schema into agent system prompt design | Agent needs schema awareness for SQL generation |
| Create mock APIs: Workday, AD/LDAP, Jira, SAM | Workday returns employee record by ACF2 ID. Others return success responses for provisioning |
| Build backend logging utility | Color-coded prefixes: `[AGENT]`, `[BEDROCK]`, `[MCP]`, `[MOCK]`, `[TEAMS]`, `[SERVICENOW]`. Log every LLM call, tool call, MCP query, mock API hit, and error |
| Create `.env.example` for backend | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_REGION`, `BEDROCK_MODEL_ID`, `SQLITE_DB_PATH`, `PORT` |
| Wire `BYPASS_AUTH=true` flag | Hardcoded session context for dev/demo |

**Exit criteria:**
- `python scripts/seed_sqlite.py` creates and seeds the database
- SQLite MCP server accepts `SELECT * FROM users WHERE acf2_id = 'ARUN01'` and returns Arun Mehta's record
- Mock Workday responds to `GET /mock/workday/employee/ARUN01`
- Backend terminal shows color-coded log output on any API call
- Both `.env.example` files committed

**Phase doc:** `docs/phases/phase-00-foundation.md`

---

## Phase 1 — Agent Core + Identity Verification

**Goal:** User types ACF2 ID in chat → agent generates SQL via Bedrock → queries SQLite MCP → verifies identity → greets user by name with team/manager context. Hard block on unknown ID. Full stack working: frontend chat → FastAPI → agent → MCP → response in chat.

| Task | Notes |
|------|-------|
| FastAPI server scaffolding | `POST /api/agent/message` — receives user message, returns agent response |
| Agent module: conversation loop with Bedrock | System prompt + tool definitions → send to Bedrock Converse API → handle tool_use responses → loop until final text |
| Tool definition: `query_db` | Agent generates SQL, FastAPI routes to SQLite MCP, returns result |
| Agent system prompt: identity verification flow | "When user provides an ACF2 ID, query the users table. If found, greet by name and confirm team/manager. If not found, respond with IT support message and stop." |
| Few-shot SQL examples in system prompt | `SELECT * FROM users WHERE acf2_id = 'ARUN01'` — prevents malformed queries |
| SQL validation in FastAPI | Basic sanitization before forwarding to MCP. Reject DROP, DELETE, UPDATE from agent-generated queries (read-only for identity phase) |
| Hard block on unknown ACF2 ID | Agent says: "I wasn't able to verify your identity. Please contact IT support." Flow stops |
| Hard block on Workday mock failure | Same message, same stop |
| Session state: populate `acf2_id` and `workday_context` on successful verification | Stored in conversation context for subsequent turns |
| Next.js frontend: proxy route `POST /api/agent/message` → FastAPI | Thin proxy, zero logic — already built, do not modify |
| Frontend chat: send message → show response | Already built — do not modify |
| Regex fallback for ACF2 extraction | If Bedrock fails entirely, pattern `[A-Z]{2,8}\d{2,6}` extracts ACF2 from message |

**Exit criteria:**
- Type `ARUN01` → see "Hi Arun, I can see you're joining the Cloud Infrastructure team under [manager]. What will your role be?"
- Type `FAKE99` → see IT support block message
- Type `"Yes my ID is ARUN01"` → agent extracts ACF2 from natural language, verifies successfully
- Backend terminal shows: `[BEDROCK] tool_call → query_db`, `[MCP] SQL: SELECT...`, `[MCP] 1 row returned`

**Phase doc:** `docs/phases/phase-01-agent-identity.md`

---

## Phase 2 — Role Resolver + Template Matching

**Goal:** After identity verification, user states their role. If vague, agent asks clarifying questions until role, seniority, and employment type are resolved. Once resolved, agent matches to a designation template using context stuffing. Agent announces the match in chat and signals the frontend to display the template.

| Task | Notes |
|------|-------|
| Extend agent system prompt: Role Resolver capability | "After identity is confirmed, ask the user about their role. If role, seniority, or employment_type is missing or ambiguous, ask targeted follow-up questions. Team is pre-filled from the user record. Do not proceed to template matching until all fields are resolved." |
| System prompt: inject all designation templates | Context stuffing — all 8 templates with their mandatory and optional access items |
| System prompt: template matching instructions | "Given the resolved role, select the best matching designation template. Return match_id, confidence (0–1), and reasoning. If confidence < 0.70 for all templates, return no_match: true." |
| Structured output from agent for template match | Agent returns JSON with selected template, confidence, and reasoning. Frontend parses this to render in right panel |
| Top-3 selection logic | Confidence 0.70–0.95 → return top 3 with scores, user picks one. Confidence > 0.95 → serve directly |
| No-match flag | `no_match: true` → handled in Phase 6. For now: agent says "I couldn't find an exact match for your role. Let me flag this for review." |
| Session state: populate `resolved_role` and `selected_template` | Carried forward to submission |
| Test: "I do backend stuff" → 2 clarifying questions → resolves to Backend Developer | Verifies multi-turn resolution |
| Test: "Junior Backend Developer, full-time" → resolves in one turn | Verifies direct match |
| Test: gibberish input → agent asks again gracefully | Verifies error handling |

**Exit criteria:**
- ARUN01 → verify identity → "I'm a backend developer" → agent matches to Backend Developer template with confidence and reasoning
- Vague input triggers follow-up questions
- Gibberish input doesn't crash — agent re-asks
- Backend logs show template matching reasoning

**Phase doc:** `docs/phases/phase-02-role-resolver.md`

---

## Phase 3 — Template UI + Submission Flow

**Goal:** Selected template renders in the right panel. Mandatory items locked, optional items toggleable. User submits → access request written to SQLite via MCP. Chat confirms submission.

| Task | Notes |
|------|-------|
| Right panel: template card component | Displays template name, match confidence, reasoning |
| Template card: mandatory access items | Auto-checked, greyed out, tooltip "Required for this role". Cannot be unchecked |
| Template card: optional access items | Unchecked by default, toggleable by user |
| If top-3 served: show 3 cards with match % | User clicks one to expand. Others collapse |
| If exact match (>0.95): single template expanded immediately | Skip selection step |
| "Confirm & Submit" button | Active only after user acknowledges mandatory items (checkbox: "I confirm the mandatory access above is correct for my role") |
| On submit: agent generates INSERT SQL via MCP | New row in `access_requests` with final bundle, status `pending`, timestamp |
| Chat confirmation | "Your request has been submitted. I'm sending it to the relevant approvers now." |
| API contract: frontend sends selected template + toggles to backend | Backend receives final bundle (mandatory + selected optional) |
| Session state: populate `final_bundle` and `request_id` | UUID generated for the request |

**Exit criteria:**
- Complete flow: ARUN01 → identity → role → template appears in right panel → toggle optional items → submit → `access_requests` row created in SQLite
- Mandatory items cannot be unchecked
- Optional items toggle correctly
- Chat shows submission confirmation
- Backend logs: `[MCP] INSERT INTO access_requests...`

**Phase doc:** `docs/phases/phase-03-template-ui.md`

---

## Phase 4 — Risk Scorer + Privilege Guard

**Goal:** Two intelligence capabilities wired into the agent flow. Risk Scorer computes a 0–100 score on submission. Privilege Guard checks existing permissions against dangerous combinations before submission and warns in chat.

### Risk Scorer

| Task | Notes |
|------|-------|
| Risk scoring function in agent module | Queries `approval_events` history for similar role/team combinations via MCP |
| Scoring signals | Role-baseline deviation, off-hours flag (based on submission time), request velocity (how many requests this user has made recently), privilege escalation patterns |
| LLM-generated explanation | One-sentence plain-language reasoning: "This role has never requested prod DB access — 94% of similar requests were rejected by security." |
| Score + explanation stored on access request | Written to `access_requests` or a new field, passed to Teams card in Phase 5 |
| ARUN01 pre-scripted to produce score ~78 | Seeded `approval_events` data ensures deterministic score for demo |
| Color coding logic | Green < 40, Amber 40–70, Red > 70 |

### Privilege Guard

| Task | Notes |
|------|-------|
| Tool definition: `check_privilege_accumulation` | Agent generates SQL to query `privilege_edges` for user's existing permissions, then cross-references `dangerous_combinations` |
| Agent calls this tool BEFORE `submit_access_request` — not after | System prompt explicitly requires this step |
| If match found: agent warns in chat | "You already have read access to the production database. Adding deploy pipeline write access would create a critical privilege combination that could allow unauthorized code deployment." |
| HIGH match: warn and ask user to confirm | User can proceed or modify their request |
| CRITICAL match: warn and auto-escalate to security | Agent informs user: "This combination has been flagged for security review regardless of your response." |
| NEHA02 pre-seeded to trigger HIGH or CRITICAL combo | Existing `privilege_edges` data + requested bundle creates dangerous combination |
| Privilege Guard flag written to `audit_log` via MCP | Every trigger is logged |

**Exit criteria:**
- Submit ARUN01 request → Risk Scorer produces score ~78 with explanation sentence
- Start NEHA02 flow → select template → before submission, Privilege Guard fires in chat with specific warning about the dangerous combination
- CRITICAL combo for NEHA02 → auto-escalation flag written to audit_log
- Backend logs: `[AGENT] Privilege Guard triggered`, `[MCP] SELECT FROM privilege_edges...`, `[MCP] SELECT FROM dangerous_combinations...`

**Phase doc:** `docs/phases/phase-04-risk-privilege.md`

---

## Phase 5 — ServiceNow MCP + Teams Adaptive Cards + Orchestrator

**Goal:** On submission, ServiceNow MCP creates a real RITM ticket. Teams Adaptive Card sent to approver with full request details + Risk Scorer data. Approve/Reject buttons callback to FastAPI. Orchestrator fires mock provisioning on approval.

### ServiceNow Integration

| Task | Notes |
|------|-------|
| Verify ServiceNow MCP server availability | If unavailable: fall back to ServiceNow Table REST API, or mock |
| On submission: create RITM via ServiceNow MCP | `create_request_item(short_description, category, items[])` → returns `ritm_number` |
| Store RITM number on `access_requests.servicenow_ritm` via SQLite MCP | Displayed on Teams card for traceability |
| On approve/reject: update RITM status via ServiceNow MCP | `update_request_item(ritm_number, state, comments)` |

### Teams Adaptive Cards

| Task | Notes |
|------|-------|
| Teams Incoming Webhook configured | URL in `backend/.env` as `TEAMS_WEBHOOK_URL` |
| Public HTTPS callback URL | ngrok or equivalent. `PUBLIC_BASE_URL` in `frontend/.env` so Teams buttons can call back |
| Adaptive Card template | Joinee info, access items list, ServiceNow RITM reference, Risk Scorer score (color-coded), explanation sentence, Approve/Reject buttons |
| Card color-coding based on Risk Scorer | Green/Amber/Red header or accent based on score |
| `POST /api/approve` endpoint | Updates `approval_events.status` to `approved` via MCP |
| `POST /api/reject` endpoint | Updates `approval_events.status` to `rejected` via MCP |

### Approval Engine + Orchestrator

| Task | Notes |
|------|-------|
| On submission: split request into per-access-item `approval_events` | One row per access item, status `pending` |
| Approver routing: query `approver_routing` table for each item | All point to demo webhook for now |
| Approval state machine | `pending → approved / rejected`. Optional items: `pending_manager → pending_team → approved / rejected` |
| Orchestrator: triggers on `approval_events.status = approved` | Event-driven, separate module |
| Orchestrator: fire provisioning calls to mock APIs in parallel | AD/LDAP, Jira, SAM — all mock. Each returns `{ success, reference_id }` |
| Partial failure handling | If one mock fails, others complete, failure logged |
| `access_requests.status` updated | `provisioned`, `partially_provisioned`, or `failed` |
| `privilege_edges` updated with newly granted access | Required for Privilege Guard to work on future requests |
| All state changes written to `audit_log` | Append-only |

**Exit criteria:**
- Submit ARUN01 → ServiceNow RITM created (or mocked) → Teams card appears with score ~78 in amber/red → click Approve → `approval_events` updated → mock APIs provisioned → `audit_log` populated
- Backend logs show full flow: `[SERVICENOW] RITM0012345 created`, `[TEAMS] Card sent`, `[MOCK] AD provisioned`, `[MCP] INSERT INTO audit_log...`

**Phase doc:** `docs/phases/phase-05-servicenow-teams-orchestrator.md`

---

## Phase 6 — Status Tracker + No-Match Flow + Admin Dashboard

**Goal:** Three remaining features: Status Tracker capability in the agent, SARA03's no-match flow, and a basic admin dashboard for compliance and template ratification.

### Status Tracker

| Task | Notes |
|------|-------|
| Tool definition: `get_request_status` | Agent generates SQL to query `approval_events` for current request |
| Agent responds conversationally | "CyberArk has been approved. AWS access is still pending with the Cloud team." |
| Available any time post-submission | User can ask "what's my status?" at any point |
| Right panel bottom: live status tracker | Per-item status: Pending / Approved ✓ / Rejected ✗. Updates on page refresh or polling |

### No-Match Flow (SARA03)

| Task | Notes |
|------|-------|
| No-match path activates when confidence < 0.70 for all templates | Agent detects no suitable template |
| Agent generates a draft template using LLM reasoning | Based on role + team + dept context. Drafts mandatory and optional access items |
| Draft written to `template_drafts` table via MCP | Status: `pending_ratification` |
| Agent informs user | "No template exists for your role yet. I've created a draft for admin review. Your request is on hold until the template is approved." |
| Admin can view, edit, approve, or reject draft in Admin Dashboard | On approval: template written to `designations` table |

### Admin Dashboard

| Task | Notes |
|------|-------|
| New page or panel in frontend | Read-only audit view |
| Audit view: who has what access, when granted, who approved, any Risk Scorer / Privilege Guard flags | Reads from `audit_log` + `approval_events` |
| Filter by: ACF2 ID, system, date range, flag status | Basic filters |
| Template ratification queue | Drafts from no-match flow. Admin can approve/reject |
| Approver routing table viewer | View current routing (editing optional) |

**Exit criteria:**
- Post-approval, ask "what's my status?" → agent responds with per-item state
- Right panel shows live status per access item
- SARA03 → role resolution → no match → agent drafts template → draft appears in admin dashboard → admin approves → `designations` table updated
- Audit dashboard shows full trail for ARUN01's provisioned request

**Phase doc:** `docs/phases/phase-06-status-nomatch-admin.md`

---

## Phase 7 — Polish + Demo Prep

**Goal:** 5–7 minute demo runs clean start to finish. No crashes. Backup recording exists. All documentation finalized.

| Task | Notes |
|------|-------|
| Error handling: Bedrock failure → graceful chat message | "I'm having trouble processing your request. Please try again in a moment." |
| Error handling: MCP failure → graceful fallback | Don't crash. Log error, show user-friendly message |
| Error handling: Teams webhook failure → approval state still correct in DB | UI reflects status even if Teams card fails to send |
| Error handling: ServiceNow failure → mock fallback | Log error, create mock RITM, continue flow |
| Demo data fully seeded and verified | ARUN01, NEHA02, SARA03 all produce expected results |
| Demo script written | 5–7 minute walkthrough with timing notes for each key moment |
| SQLite warm-up verified | DB responds instantly — no cold start concerns |
| Teams channel cleared of test cards | Fresh channel for demo |
| Screen recording backup | Complete flow recorded in case of live demo issues |
| All phase docs in `docs/phases/` reviewed | Each doc has what/why/how sections complete |
| ADR.md final review | All decisions documented, stale entries updated |
| README updated | Setup instructions for judges/reviewers |
| `PHASES.md` finalized | Phase status column updated |

**Exit criteria:**
- Full demo rehearsal completes in under 7 minutes with no errors
- Backup recording saved
- All `docs/phases/` files committed
- ADR.md and architecture match actual build

**Phase doc:** `docs/phases/phase-07-polish-demo.md`

---

## Stretch — RetellAI Voice Layer

**Goal:** Voice input/output as an alternative to text chat. RetellAI handles speech-to-text and text-to-speech. Your Bedrock agent handles all logic.

| Task | Notes |
|------|-------|
| RetellAI account setup | Create agent in RetellAI dashboard |
| Configuration: RetellAI as voice I/O wrapper | RetellAI transcribes speech → sends text to your FastAPI `POST /api/agent/message` as a custom function → receives text response → speaks it |
| Bedrock remains the only LLM | RetellAI's built-in LLM is not used for reasoning — only for basic conversation scaffolding to call your custom function |
| Test: speak ACF2 ID → hear identity confirmation | Full flow via voice |
| Frontend: toggle between text and voice mode | Simple UI switch |

**Exit criteria:**
- Speak "My ACF2 ID is ARUN01" → hear identity confirmation spoken back
- Full happy path works via voice
- Text mode still works independently

**Phase doc:** `docs/phases/stretch-retellai-voice.md` (if built)

---

## Phase Documentation Template

Every completed phase produces a file in `docs/phases/` with this structure:

```markdown
# Phase X — [Name]

## What was built
- Feature list with brief descriptions

## Why it was built
- Which problem statement requirement this addresses
- How it connects to the previous phase

## How it works
- Architecture/flow diagram for this phase
- Key files created or changed
- API contracts added or modified
- Database changes (new tables, new columns, new seed data)

## How to test
- Step-by-step verification instructions
- Expected inputs → expected outputs

## Decisions made
- Any ADR-level choices during this phase
- Link to ADR.md entry if applicable
```

---

## Backend Logging Standard

Every backend module uses the shared logging utility. Format:

```
[PREFIX]  Message with relevant data
```

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

## Rules for AI Coding Tools (Claude Code / Codex)

These rules must be followed by any AI assistant building this project:

1. **Frontend (`frontend/`) is frozen.** Do not modify any frontend files. Communication is HTTP only.
2. **Frontend never imports or calls:** Bedrock, SQLite, MCP, boto3, any AWS SDK, any database driver.
3. **Backend never imports or calls:** React, Next.js, any UI framework, any browser API.
4. **Frontend API routes are thin proxies.** They forward requests to `BACKEND_URL` and return the response. Zero business logic.
5. **All environment variables with secrets live in `backend/.env` only.** Frontend `.env` contains only `BACKEND_URL` and public config.
6. **Every backend action must produce a log line** using the logging utility with the correct prefix.
7. **Tailwind CSS v4 syntax** — uses `@import "tailwindcss"` and `@theme inline {}`, NOT `tailwind.config.js`.
8. **Next.js App Router** — route handlers use `export async function POST(request: Request)`.
9. **Python backend uses FastAPI + uvicorn.** No Express, no Node.js in backend.
10. **SQLite access goes through MCP only.** No direct `sqlite3` calls from application code.
11. **On phase completion:** create `docs/phases/phase-XX-name.md` documenting what/why/how before moving to the next phase.
12. **Never commit:** `.env`, `credentials.txt`, `token.txt`, `*.token`, `node_modules/`, `.next/`, `__pycache__/`, `*.db`

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| ServiceNow MCP unavailable | Medium | Fallback to ServiceNow Table REST API or mock. Verify availability at start of Phase 5 |
| Teams webhook setup fails | High | Test in Phase 5 immediately. Incoming webhook is simple — 20 min setup max |
| Bedrock rate limit during demo | Low | Not reachable in a 5–7 min demo. Graceful error message if it happens |
| Agent generates malformed SQL | Medium | Schema in system prompt + few-shot examples + FastAPI validation layer |
| Privilege Guard false positives | Medium | `dangerous_combinations` table carefully seeded. Test all 3 ACF2 IDs before Phase 7 |
| NEHA02 privilege warning doesn't fire | High | Verify seeded `privilege_edges` data creates expected match. Test early in Phase 4 |
| ARUN01 risk score not deterministic | Medium | Verify seeded `approval_events` data produces consistent ~78 score. Test in Phase 4 |
| Demo auth bypass misunderstood by judges | Low | Frame: "Auth handled via Azure AD/MSAL — same infra Sun Life uses. Bypassed for demo to focus on provisioning logic." |

---

## Technologies (Final — No Stale References)

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Next.js (App Router), React 19, TypeScript | Port 3000 — frozen |
| Styling | Tailwind CSS v4 | `@theme inline` syntax |
| Backend | Python 3.11+, FastAPI, uvicorn | Port 8000 |
| LLM | AWS Bedrock — Claude Sonnet 4.6 | Only LLM provider. Only used as LLM |
| Database | SQLite via official MCP server | Schema injected into agent system prompt |
| ITSM | ServiceNow MCP (with mock fallback) | Real RITM tickets |
| Notifications | MS Teams Incoming Webhook + Adaptive Cards | Single channel for demo |
| Voice (stretch) | RetellAI | Voice I/O wrapper around FastAPI |
| Auth | `BYPASS_AUTH=true` | Azure AD/MSAL documented as production path |

**Dead technologies (do NOT use):**
- ~~MongoDB~~ → SQLite MCP
- ~~Supabase~~ → SQLite MCP
- ~~pgvector~~ → Context stuffing
- ~~Ollama~~ → Bedrock only
- ~~Gemini API~~ → Bedrock only
- ~~nomic-embed-text~~ → Context stuffing
- ~~Express / Node.js backend~~ → Python / FastAPI
- ~~better-sqlite3~~ → SQLite MCP server
- ~~RAG / embeddings~~ → Context stuffing

---

*Last updated: 2026-04-29*
*All phases reflect current architecture decisions. No stale references.*
