# Build Phases — PS6: AI-Powered Access Approval
## HackHERway | Sun Life

> **Principle:** Every phase ends with something demoable or testable. No phase ends with half-built infrastructure.
> Every local Git checkpoint is a phase checkpoint. ADR.md must be updated on any checkpoint that changes structure.
> Run `git config core.hooksPath .githooks` in every local working copy to activate the pre-commit hook.

---

## Phase Map (Quick Reference)

```
Phase 0   → Foundation: repo, schema, seeds, mock APIs, local git hook
Phase 1   → UI Shell: 3-panel layout, Sun Life theming, hardcoded content
Phase 2   → Identity: ACF2 input, Workday mock fetch, hard block on failure
Phase 3   → Agent A: Ambiguity resolution loop
Phase 4   → RAG: Template retrieval, top 3 results, similarity thresholds
Phase 5   → Template UI: mandatory/optional display, customisation, submission
Phase 6   → Approval Engine: state machine, routing table, 24hr escalation
Phase 7   → Teams: Incoming Webhook, Adaptive Cards, Approve/Reject callbacks
Phase 8   → Orchestrator: parallel provisioning, partial failure handling
Phase 9   → Agent C: Real-time status query in chat
Phase 10  → D2: Anomaly scoring + explainability on Teams card
Phase 11  → Agent B: D3 privilege check surfaced in chat
Phase 12  → D1: Adaptive persona learning, nightly job, admin proposals
Phase 13  → Admin Dashboard + Audit Panel
Phase 14  → Template Generation: no-match flow, admin ratification queue
Phase 15  → Polish + Demo Prep
```

---

## Phase 0 — Foundation

**Goal:** Everything set up. Everyone can open the local repo, migrate, and hit a mock API. Zero features, zero ambiguity.
**Local Git checkpoint:** Repo is initialised locally, hook is active, DB is running.

| Task | ADR | Notes |
|------|-----|-------|
| Initialise local Git repo | — | Keep the hackathon build local first. Use `main`, `dev`, and feature branches only if the team wants branch isolation |
| Local collaboration strategy documented in README | — | Describe who owns each phase and how code is shared/merged locally |
| Create `.githooks/pre-commit` ADR enforcement hook | ADR-009 | `chmod +x`, README documents setup step |
| Supabase project created, pgvector extension enabled | ADR-003 | |
| Run all schema migrations (all 8 tables) | ADR-003 | |
| Seed approver routing table | ADR-004 | All entries point to single webhook URL for demo |
| Seed 5–8 persona templates | ADR-001 | Backend Dev, DevOps, Data Analyst, Finance Analyst, Intern, Manager, Auditor, Contractor |
| Seed 50–100 synthetic approval events per persona | ADR-006, ADR-007 | D1 and D2 need baseline data |
| Seed `dangerous_combinations` lookup table | ADR-008 | 4 initial entries |
| Mock APIs running: Workday, ServiceNow, Jira, AD/LDAP, SAM | ADR-005 | Pre-seed 4 ACF2 IDs (ADR-015) |
| Folder structure committed | — | `web/`, `agent/`, `api/`, `mock-apis/`, `schema/`, `orchestrator/`, `.githooks/` |
| `.env.example` with all required keys documented | ADR-010 | Gemini API key, Supabase URL/key, Teams webhook URL, `PUBLIC_BASE_URL` for Teams callbacks |
| `BYPASS_AUTH=true` flag wired into app shell | ADR-013 | Hardcoded session context for dev |

**Exit criteria:** Open local repo → `npm install` → `npm run dev` → mock Workday responds to `GET /mock/workday/employee/RIYA001`.

---

## Phase 1 — UI Shell

**Goal:** Full 3-panel layout renders with hardcoded placeholder content. No logic.
**Local Git checkpoint:** UI is reviewable by all team members. Hardcoded data only.

| Task | ADR | Notes |
|------|-----|-------|
| 3-panel layout: left sidebar + center chat + right panel | — | Sun Life Ask-inspired |
| Left sidebar: app name/logo, "New Request" button, request history placeholder | — | |
| Center chat panel: bot avatar, message bubbles (bot left, user right), timestamps | — | |
| Bottom-anchored input: "Type your message..." placeholder, dark circular send button | — | |
| Right panel: split into top (template cards) and bottom (request status tracker) | — | Empty skeleton for now |
| Sun Life theming: gold/yellow primary accent, diagonal background texture, clean sans-serif | — | See screenshot reference |
| Hardcoded welcome message renders: "Hi! I'm here to help set up your system access. Let's get started. What's your ACF2 ID?" | — | |
| Conversation state management wired (session-level) | ADR-002 | Empty state object, ready for population |
| Mobile-responsive layout (basic) | — | Judges may view on various screens |

**Exit criteria:** Open app → see 3-panel layout → see welcome message → input field accepts text → nothing happens yet (no backend).

---

## Phase 2 — Identity Verification

**Goal:** Joinee enters ACF2 ID → Workday fetch → identity confirmed in chat → session populated.
**Local Git checkpoint:** First real agent-to-backend call working.

| Task | ADR | Notes |
|------|-----|-------|
| ACF2 ID input handler: captures first user message as ACF2 ID | ADR-002 | |
| Agent calls `fetch_workday(acf2_id)` tool | ADR-002, ADR-005 | |
| Workday mock responds with employee record | ADR-005 | |
| Agent confirms identity in chat: "Hi Riya, I can see you're joining the Payments Backend team under Anjali Singh. What will your role be?" | — | |
| Session state populated: `acf2_id`, `workday_context` | ADR-002 | |
| Hard block on Workday failure: agent responds with IT support message, flow stops | ADR-005 | |
| Hard block on unrecognised ACF2 ID: same message, same stop | ADR-005 | |
| Loading state shown in chat while Workday fetch is in progress | — | Prevents user confusion on latency |

**Exit criteria:** Enter `RIYA001` → see "Hi Riya..." confirmation. Enter `FAKE999` → see IT support block message.

---

## Phase 3 — Agent A: Ambiguity Resolution

**Goal:** Agent asks targeted questions until role is fully resolved. Does not proceed to template retrieval until confidence threshold met.
**Local Git checkpoint:** Vague inputs are handled. Specific inputs pass through cleanly.

| Task | ADR | Notes |
|------|-----|-------|
| System prompt engineering: role extraction with confidence threshold | ADR-002 | LLM must return structured confidence assessment |
| Ambiguity detection: if `role`, `seniority`, or `employment_type` missing → ask | ADR-002 | `team` pre-filled from Workday |
| Multi-turn loop: agent continues asking until all 4 fields resolved | ADR-002 | |
| Confidence threshold defined: all 4 fields present + role maps to recognisable category | ADR-002 | |
| Resolved state written to `session.resolved_role` | ADR-002 | |
| Test case 1: "I do backend stuff" → should ask 2 clarifying questions → resolve | — | |
| Test case 2: "Junior Backend Developer, full-time" → should resolve in one turn | — | |
| Test case 3: Gibberish input → agent asks again gracefully, does not crash | — | |

**Exit criteria:** All 3 test cases pass. Resolved role correctly populated in session state before RAG call.

---

## Phase 4 — RAG Template Retrieval

**Goal:** Resolved role → top 3 matching templates retrieved with similarity scores and reasoning. No-match case handled.
**Local Git checkpoint:** Template retrieval working against seeded personas.

| Task | ADR | Notes |
|------|-----|-------|
| `nomic-embed-text` integration wired through local Ollama | ADR-011 | Model must be pulled and tested before this phase starts |
| All seeded persona templates embedded and stored in `personas.embedding` | ADR-011 | Teammate B owns embedding script; Teammate D owns seed data |
| `retrieve_templates()` tool: takes resolved role → cosine similarity query → top 3 | ADR-011 | |
| Exact match detection: similarity > 0.95 → serve directly, skip selection step | ADR-011 | |
| Top 3 result format: template name, match score %, plain-language reasoning | — | e.g. "92% match — Backend Developer with payments team context" |
| No-match path: similarity < 0.70 for all → flag for Phase 14 template generation flow | ADR-011 | For now: "I couldn't find an exact match. Using closest available." |
| Results passed to Phase 5 UI — agent does NOT render template in chat | ADR-002 | Template renders in right panel only |

**Exit criteria:** `RIYA001` (Backend Dev, Payments) → top result is "Backend Developer — Payments" at >85% similarity. `SAM004` (unknown role) → no-match path triggered.

---

## Phase 5 — Template UI + Customisation

**Goal:** Joinee sees template in right panel. Can toggle optional access. Submits final customised bundle.
**Local Git checkpoint:** Full template display and customisation working. First complete user-facing flow.

| Task | ADR | Notes |
|------|-----|-------|
| Right panel top section: renders template card from RAG results | — | |
| If top 3 served: joinee sees 3 cards with match % — clicks one to expand | — | |
| If exact match: single template expanded immediately | — | |
| Template card displays: platform name, icon, access type, reason it's included | — | |
| Mandatory access items: auto-checked, greyed out, tooltip "Required for this role" | ADR-001 | Cannot be unchecked |
| Optional access items: unchecked by default, toggleable by joinee | ADR-001 | |
| "Confirm & Submit" button: active only after joinee acknowledges mandatory items | — | Checkbox: "I confirm the mandatory access above is correct for my role" |
| Final bundle (mandatory + selected optional) written to `access_requests` table on submit | ADR-003 | Status: `pending` |
| Chat confirms submission: "Got it. Your request has been submitted. I'm sending it to the relevant approvers now." | — | |

**Exit criteria:** Select template → toggle optional items → submit → `access_requests` row created in Supabase with correct bundle.

---

## Phase 6 — Approval Engine + Routing Table

**Goal:** Submitted request correctly splits into approval streams and routes to the right approvers. 24hr escalation timer active.
**Local Git checkpoint:** State machine working. Correct streams created per submission.

| Task | ADR | Notes |
|------|-----|-------|
| Approval state machine implemented: `pending_manager → pending_team → approved / rejected` | ADR-004 | Optional items start at `pending_manager`. Mandatory start at `pending_team` |
| Request splits into per-access-item approval events on submission | ADR-004 | One row in `approval_events` per access item |
| Approver routing: each access item queries `approver_routing` table to get approver | ADR-004 | All entries point to demo webhook URL |
| 24hr escalation cron job: checks `approval_events` for overdue items → escalates | ADR-004 | Escalation event written to `audit_log` |
| Escalation target: manager's manager (sourced from Workday context in session) | ADR-004 | |
| All approval state changes written to `audit_log` | ADR-003 | |

**Exit criteria:** Submit request → `approval_events` table has correct rows per access item → correct approval stream per item type (manager-first for optional, team-direct for mandatory).

---

## Phase 7 — MS Teams Adaptive Cards

**Goal:** Approver receives card in Teams. Clicking Approve/Reject updates approval state via callback.
**Local Git checkpoint:** End-to-end approval loop working via Teams.

| Task | ADR | Notes |
|------|-----|-------|
| Teams Incoming Webhook configured, URL in `.env` | ADR-004 | Test channel set up |
| Public HTTPS callback URL configured | ADR-004 | Use ngrok or equivalent. Set `PUBLIC_BASE_URL` so Teams buttons can call back to local demo API |
| Adaptive Card template built: joinee info, access items, Approve/Reject buttons | ADR-004 | Placeholder for D2 score (added in Phase 10) |
| `POST /api/approve?request_id=&item=` endpoint live | ADR-004 | Updates `approval_events` status |
| `POST /api/reject?request_id=&item=` endpoint live | ADR-004 | Same |
| Adaptive Card button URLs use `PUBLIC_BASE_URL` | ADR-004 | Teams cannot call `localhost`; button actions must point to public `/api/approve` and `/api/reject` URLs |
| Approval Engine sends Teams card when approval stream is created | ADR-004 | |
| On manager approval of optional item → provisioning team card automatically sent | ADR-004 | Model A second step |
| Test full loop: submit → card in Teams → click approve → `approval_events` row updates | — | |

**Exit criteria:** Submit RIYA001 request → see card in Teams → click Approve through public callback URL → `approval_events.status` changes to `approved`.

---

## Phase 8 — Orchestrator + Mock Provisioning

**Goal:** On full approval of an access item, mock system is provisioned. Partial failures handled. All outcomes logged.
**Local Git checkpoint:** First fully provisioned access item, end-to-end.

| Task | ADR | Notes |
|------|-----|-------|
| Orchestrator triggers on `approval_events.status = approved` | ADR-001 | Event-driven, not polled |
| Each provisioning call is stateless: takes request context, calls mock API, returns result | ADR-014 | Lambda-ready contract |
| All mock API calls fire in parallel for same-stream approved items | ADR-001 | |
| Partial failure handling: if one mock fails, others complete, failure logged | ADR-001 | No silent failures |
| Provisioning result written to `audit_log` per system | ADR-003 | |
| `access_requests.status` updated: `provisioned`, `partially_provisioned`, or `failed` | ADR-003 | |
| `privilege_edges` table updated with newly granted access | ADR-008 | Required for D3 in Phase 11 |

**Exit criteria:** Approve all items for RIYA001 → all mock APIs called → `audit_log` shows provisioning entries → `privilege_edges` populated.

---

## Phase 9 — Agent C: Real-Time Status in Chat + Right Panel

**Goal:** Joinee sees live approval status without refreshing. Can also ask agent for status in conversation.
**Local Git checkpoint:** Real-time status visible. Agent responds to status queries conversationally.

| Task | ADR | Notes |
|------|-----|-------|
| Supabase real-time subscription on `approval_events` for current `request_id` | ADR-003 | |
| Right panel bottom section: live status tracker per access item (Pending / Approved ✓ / Rejected ✗) | ADR-001 | Updates without page refresh |
| `get_request_status()` tool implemented | ADR-002 | Queries `approval_events` |
| Agent responds to "what's the status?" conversationally | ADR-002 | "CyberArk approved. AWS still pending with the Cloud team." |
| Status query available at any time post-submission | ADR-002 | Not just immediately after |

**Exit criteria:** Approve one item in Teams → right panel updates within 2 seconds without refresh. Ask "what's my status?" → agent responds with current per-item state.

---

## Phase 10 — D2: Anomaly Scoring + Explainability

**Goal:** Teams card shows risk score with plain-language explanation. High-risk requests visually flagged.
**Local Git checkpoint:** All Teams cards now include D2 data. Score is deterministic for demo ACF2 IDs.

| Task | ADR | Notes |
|------|-----|-------|
| Risk scoring function: queries `approval_events` history, computes 0–100 per request | ADR-007 | |
| Signals implemented: role-baseline deviation, off-hours flag, velocity, escalation pattern | ADR-007 | |
| LLM call generates one-sentence plain-language explanation | ADR-007 | |
| Score + explanation injected into Adaptive Card template | ADR-007 | |
| Colour coding on card: Green <40, Amber 40–70, Red >70 | ADR-007 | |
| JOHN002 pre-scripted to produce score of ~78 (seeded data ensures this) | ADR-015 | |
| Approver decision logged against anomaly flag in `approval_events` | ADR-007 | |

**Exit criteria:** Submit JOHN002 request → Teams card shows score ~78, amber/red, with explanation sentence.

---

## Phase 11 — Agent B: D3 Privilege Check in Chat

**Goal:** Agent catches dangerous access accumulation before submission and surfaces it conversationally.
**Local Git checkpoint:** PRIYA003 scenario triggers Agent B warning in chat.

| Task | ADR | Notes |
|------|-----|-------|
| `check_privilege_accumulation()` tool queries `privilege_edges` for user + cross-references `dangerous_combinations` | ADR-008 | |
| Tool called by agent before `submit_access_request()` — not after | ADR-002 | |
| If match found: agent explains in chat, asks joinee to confirm before proceeding | ADR-008 | |
| CRITICAL match: agent warns, auto-escalates to security team regardless of joinee response | ADR-008 | |
| PRIYA003 pre-seeded with existing `privilege_edges` data that triggers HIGH combination | ADR-015 | |
| D3 flag written to `audit_log` on trigger | ADR-003 | |

**Exit criteria:** Submit PRIYA003 request → agent surfaces privilege warning in chat before submission screen appears. CRITICAL combo → auto-escalation fires.

---

## Phase 12 — D1: Adaptive Persona Learning

**Goal:** Dashboard shows proposed bundle changes. Admin can ratify or reject. Nightly job runs cleanly.
**Local Git checkpoint:** At least one proposal visible in Admin Dashboard from seeded data.

| Task | ADR | Notes |
|------|-----|-------|
| Nightly scoring job implemented (Supabase cron) | ADR-006 | EventBridge-compatible for AWS |
| Computes approval rate per access item per persona from `approval_events` | ADR-006 | |
| Threshold logic: >80% → propose addition, <20% → propose removal | ADR-006 | |
| Proposals written to `bundle_fit_scores` with `proposed_action` | ADR-006 | |
| Admin Dashboard surfaces proposals: "Add Redis to Backend Developer bundle (87% approval rate)" | ADR-006 | |
| Admin confirm/reject flow: updates `personas` table on confirm | ADR-006 | Re-embeds persona on change |
| Admin decision written to `audit_log` | ADR-003 | |

**Exit criteria:** Seeded approval events produce at least 2 visible proposals in Admin Dashboard. Admin can approve one and see persona table updated.

---

## Phase 13 — Admin Dashboard + Audit Panel

**Goal:** Compliance view complete. All access visible. All events traceable. Admin can manage routing table.
**Local Git checkpoint:** Dashboard usable for demo walkthrough.

| Task | ADR | Notes |
|------|-----|-------|
| Audit Dashboard: who has what access, when granted, who approved, any D2/D3 flags | ADR-001 | Read-only view from `audit_log` + `approval_events` |
| Filter by: ACF2 ID, system, date range, flag status | — | |
| D1 proposal queue: proposals from Phase 12 surfaced with approve/reject actions | ADR-006 | |
| Template ratification queue: drafts from Phase 14 (builds on this phase) | ADR-011 | Placeholder section for now |
| Admin routing table editor: view and update approver assignments | ADR-004 | |
| All admin actions written to `audit_log` with actor identity | ADR-003 | |

**Exit criteria:** Full audit trail for RIYA001's provisioned request visible in dashboard, end-to-end.

---

## Phase 14 — Template Generation: No-Match Flow

**Goal:** When no template exists, agent generates a draft and routes it for admin ratification. Joinee is informed and request is held.
**Local Git checkpoint:** SAM004 scenario (no template) flows cleanly to admin queue.

| Task | ADR | Notes |
|------|-----|-------|
| No-match path activated when RAG similarity < 0.70 for all results | ADR-011 | |
| LLM generates draft template: role + team + dept as context | ADR-011 | |
| Draft written to `template_drafts` with `pending_ratification` status | ADR-011 | |
| Agent informs joinee: "No template exists for your role yet. I've created a draft for admin review. Your request is on hold." | — | |
| Admin sees draft in ratification queue (Phase 13 dashboard placeholder now active) | ADR-011 | Can edit, approve, or reject |
| On admin approval: template embedded via nomic-embed-text, written to `personas` | ADR-011 | |
| Joinee notified (chat or email) when template ratified and request can proceed | — | |

**Exit criteria:** Enter SAM004 → trigger no-match → draft appears in admin queue → admin approves → persona table updated with new embedded template.

---

## Phase 15 — Polish + Demo Prep

**Goal:** 5-minute demo runs clean start to finish. No crashes. Backup recording exists.
**Local Git checkpoint:** Final checkpoint. ADR.md final review included.

| Task | Notes |
|------|-------|
| Supabase warm-up script | Hits DB 10 minutes before demo to prevent cold start |
| Error handling: LLM API failure → graceful chat message, not crash | |
| Error handling: Workday failure → graceful block message, not crash | |
| Error handling: Teams webhook failure → approval state still updated in DB, UI still reflects it | |
| Demo data fully seeded and verified: RIYA001, JOHN002, PRIYA003, SAM004 | |
| Demo script written: 5-minute walkthrough with timing notes for each "money moment" | |
| Teams channel cleared of test cards before demo | |
| All 4 team members rehearse their role in the demo at least once | |
| Screen recording backup made of complete flow | |
| Final ADR.md reviewed — all phases and decisions documented | ADR — final checkpoint |
| README updated with setup instructions for judges/reviewers | |

**Exit criteria:** Full demo rehearsal completes in under 5 minutes with no errors. Backup recording saved.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Teams webhook setup fails | Low (simple) | High | Test in Phase 7 with plenty of buffer. Incoming webhook is 20 min max. |
| Gemini API rate limit during demo | Very Low | High | Ollama fallback configured and tested locally before rehearsal. Rate limit (15/min) not reachable in a 5-min demo. |
| Supabase cold start during demo | Low | High | Warm-up script. Run 10 min before. |
| Ollama embedding model not ready before demo | Medium | Medium | Pull and test `nomic-embed-text` locally before Phase 4 starts. Keep a precomputed seed embedding backup for rehearsal. |
| Agent D3 check (Phase 11) produces false positives | Medium | Medium | `dangerous_combinations` table carefully seeded. Test all 4 ACF2 IDs before Phase 15 demo rehearsal. |
| Demo auth bypass is misunderstood as unfinished scope | Low | Medium | ADR-013 clearly states auth is out of hackathon scope. In the demo, frame Azure AD/MSAL as the production path, not pending build work. |
| D1 nightly job produces no proposals | Low (seeded data) | Medium | Verify seeded approval events produce proposals by running job manually in Phase 12. |
| SAM004 no-match flow too slow for demo | Low | Low | Template generation is async. Joinee is told to wait. Not blocking. |

---

*Planning phase complete. Auth removed from scope. Build starts at Phase 0.*
