# Architecture Decision Records (ADR)
## PS6: AI-Powered Access Approval — HackHERway | Sun Life

> **Process:** This file must be updated before every Git commit that introduces a structural change.
> Status lifecycle: `Proposed → Accepted → Deprecated → Superseded`

---

## ADR Index

| ID | Title | Status | Last Updated |
|----|-------|--------|--------------|
| ADR-001 | Overall System Architecture | Accepted | 2026-04-26 |
| ADR-002 | AI Layer: Conversational Agent Architecture | Accepted | 2026-04-26 |
| ADR-003 | Database: MongoDB Community Server | Accepted | 2026-04-26 |
| ADR-004 | Approval Channel: MS Teams Incoming Webhook | Accepted | 2025-04-24 |
| ADR-005 | External Systems: ServiceNow MCP + SAM Mock | Accepted | 2026-04-26 |
| ADR-006 | D1: Adaptive Persona Learning | Accepted | 2025-04-24 |
| ADR-007 | D2: Explainable Anomaly Scoring | Accepted | 2025-04-24 |
| ADR-008 | D3: Cross-Request Privilege Accumulation Detection | Accepted | 2025-04-24 |
| ADR-009 | ADR Enforcement via Git Convention | Accepted | 2026-04-26 |
| ADR-010 | LLM Provider: AWS Bedrock Claude Sonnet 4.6 | Accepted | 2026-04-26 |
| ADR-011 | Template Matching: LLM Context Stuffing | Accepted | 2026-04-26 |
| ADR-012 | Agentic Design: 3 Active Capabilities + 1 Proposed | Accepted | 2025-04-24 |
| ADR-013 | Auth: Azure AD / MSAL — Proposed for Production | Deprecated | 2025-04-24 |
| ADR-014 | AWS Production Migration Path | Accepted | 2026-04-26 |
| ADR-015 | Demo Strategy: Single Account + Pre-seeded ACF2 IDs | Accepted | 2025-04-24 |
| ADR-016 | GitHub Workflow Convention | Accepted | 2026-04-26 |

---

## ADR-001: Overall System Architecture

**Date:** 2025-04-24 | **Last updated:** 2026-04-26 | **Status:** Accepted

### Context
Sun Life's access provisioning takes 2–30 days. New employees and team-changers raise individual tickets per system. No central audit trail. Joinee has zero visibility into approval status.

### Decision
A joinee-initiated, AI-agent-driven provisioning system. Identity verified via ACF2 ID against Workday mock. An AI agent determines the right access template, handles ambiguity conversationally, performs pre-submission privilege checks, and routes approval requests via MS Teams. Joinee has real-time visibility into approval status.

**Architecture layers:**
- **Presentation:** Standalone web app — 3-panel layout (sidebar / chat / template+status panel). Sun Life Ask-inspired design language.
- **Agent:** Claude Sonnet 4.6 via AWS Bedrock with tool-calling — 3 active agentic capabilities (A, B, C).
- **Template Engine:** LLM context stuffing — all persona templates injected into system prompt, Claude selects best match.
- **Core Services:** Next.js API routes, stateless Orchestrator, Approval Engine with state machine.
- **Approval Notification:** MS Teams Adaptive Cards via Incoming Webhook.
- **Persistence:** MongoDB Community Server (local). Two primary collections: `users`, `designations`. See ADR-003.
- **ITSM Integration:** ServiceNow MCP raises RITM tickets on approval. See ADR-005.
- **Provisioning Targets:** Workday mock (identity), ServiceNow MCP (tickets), SAM mock (NPE + GitHub Copilot).

**Primary flow:**
```
Joinee opens app → enters ACF2 ID → agent fetches user from MongoDB
→ joinee states role → Agent A resolves ambiguity if needed
→ Claude matches role to designation template (context stuffing)
→ joinee selects + customises (mandatory locked, optional toggleable)
→ Agent B checks privilege accumulation before submission
→ request submitted → ServiceNow MCP raises RITM ticket
→ Teams card sent to approver via Incoming Webhook
→ Approver approves → Orchestrator provisions systems
→ Joinee sees live status via Agent C → everything audit logged in MongoDB
```

### Consequences
- **Positive:** Joinee-driven removes manager bottleneck. Real ITSM integration via ServiceNow MCP. No vector DB dependency.
- **Negative:** Workday still mocked — hard block on failure by design.
- **Production note:** SunLife Ask integration is post-win. Standalone web app is the hackathon deliverable.

---

## ADR-002: AI Layer — Conversational Agent Architecture

**Date:** 2025-04-24 | **Last updated:** 2026-04-26 | **Status:** Accepted

### Context
Requirements are multi-turn conversation, identity-aware context, tool-calling, ambiguity resolution loops, and post-submission status queries. Single LLM call cannot handle this.

### Decision

**LLM:** Claude Sonnet 4.6 via AWS Bedrock. All agent calls go through Bedrock — no other LLM providers.

**Agent tools:**
```
fetch_user(acf2_id)                             → employee record from MongoDB users collection
retrieve_template(role, team, dept)             → best-match designation from MongoDB (context stuffing)
check_privilege_accumulation(acf2_id, bundle)   → D3 danger check against privilege_edges collection
get_request_status(acf2_id)                     → live approval state from approval_events collection
submit_access_request(bundle)                   → writes to MongoDB, triggers ServiceNow MCP + Teams
```

**Session-level conversation state:**
```json
{
  "acf2_id": "RIYA001",
  "workday_context": { "name", "team", "manager", "dept", "employment_type" },
  "resolved_role": { "role", "seniority", "employment_type" },
  "selected_template": { "id", "name", "mandatory_access", "optional_access" },
  "final_bundle": [],
  "request_id": "uuid"
}
```

**Three active agentic capabilities:**

**Agent A — Ambiguity Resolution Loop**
Triggers when role input is vague. Loops with targeted questions until 4 fields resolved: `role`, `seniority`, `employment_type`, `team` (pre-filled from MongoDB user record). Only proceeds to template retrieval when confidence threshold met.

**Agent B — Pre-Submission Privilege Check (D3 in chat)**
Before final submission, queries `privilege_edges` collection for user's existing permissions and cross-references `dangerous_combinations` collection. If dangerous match found, agent surfaces it conversationally. CRITICAL combinations auto-escalate to security team regardless of joinee response.

**Agent C — Live Status Query Tool**
Post-submission, joinee can ask status at any time. Agent calls `get_request_status()` → returns per-system approval state in plain language from `approval_events` collection.

**Agent D — Template Self-Critique Loop (v2 scope — not built)**
Deferred. Presented to judges as production roadmap item.

### Consequences
- **Positive:** Genuinely agentic. Single LLM provider reduces integration complexity.
- **Negative:** Session state managed carefully. Prompt engineering quality determines reliability.

---

## ADR-003: Database — MongoDB Community Server

**Date:** 2026-04-26 | **Status:** Accepted
**Supersedes:** ADR-003 v1 (Supabase + pgvector, 2025-04-24)

### Context
Original decision used Supabase + pgvector for relational storage and vector similarity search. Decision changed: team uses company laptop for demo, MongoDB is preferred, and pgvector dependency removed (replaced by LLM context stuffing per ADR-011).

### Decision
MongoDB Community Server running locally. MongoDB Compass used as GUI. Connection string: `mongodb://localhost:27017/hackherway`.

**Collections:**

```
users
  acf2_id          string (unique index)
  name             string
  team             string
  manager          string
  dept             string
  employment_type  string
  request_history  ObjectId[]   ← refs to access_requests

designations
  role             string
  seniority        string
  team             string
  dept             string
  mandatory_access AccessItem[]
  optional_access  AccessItem[]
  ratified_by      string
  ratified_at      Date

access_requests
  _id              ObjectId
  acf2_id          string
  designation_id   ObjectId
  final_bundle     AccessItem[]
  status           enum: pending | approved | rejected | provisioned | partially_provisioned
  submitted_at     Date
  completed_at     Date
  servicenow_ritm  string       ← RITM number from ServiceNow MCP

approval_events
  _id              ObjectId
  request_id       ObjectId
  access_item      string
  approver_type    string
  approver_email   string
  status           enum: pending | approved | rejected | escalated
  decided_at       Date
  escalated_at     Date
  anomaly_score    number
  anomaly_explanation string

approver_routing
  system_name      string
  sensitivity_tier string
  approver_email   string
  approver_team    string

audit_log
  _id              ObjectId
  event_type       string
  actor            string
  target_acf2_id   string
  payload          object
  created_at       Date         ← append-only, never update

privilege_edges
  _id              ObjectId
  acf2_id          string
  permission       string
  system_name      string
  sensitivity_tier string
  granted_at       Date
  revoked_at       Date

dangerous_combinations
  _id              ObjectId
  permission_a     string
  permission_b     string
  severity         enum: HIGH | CRITICAL
  reason           string

bundle_fit_scores
  _id              ObjectId
  designation_id   ObjectId
  access_item      string
  approval_rate    number
  sample_size      number
  proposed_action  enum: add | remove
  surfaced_at      Date
  admin_decision   string

template_drafts
  _id              ObjectId
  generated_role   string
  generated_bundle AccessItem[]
  generation_reasoning string
  status           enum: pending_ratification | approved | rejected
  reviewed_by      string
  reviewed_at      Date
```

**Real-time updates:** MongoDB Change Streams on `approval_events` power the joinee status panel.

**Seeding:** Pre-seed 4 ACF2 users + 8 designation templates + dangerous_combinations + synthetic approval events in Phase 0.

### Consequences
- **Positive:** Flexible schema. No cloud dependency for demo. Compass gives visual data inspection during dev. No pgvector or Ollama required.
- **Negative:** No built-in vector search — mitigated by ADR-011 (context stuffing). Change streams require replica set or standalone with `--replSet` flag for real-time.
- **Production:** MongoDB Atlas or AWS DocumentDB (MongoDB-compatible API). Change streams work natively on both.

---

## ADR-004: Approval Channel — MS Teams Incoming Webhook

**Date:** 2025-04-24 | **Status:** Accepted

### Context
Original ADR considered Azure Bot Framework. High-risk for hackathon timeline. Incoming Webhook achieves the same demo result in 20 minutes of setup.

### Decision
MS Teams Incoming Webhook. Single webhook URL, single channel, all notifications centralised for hackathon.

**Approval flow — Model A (two-step for optional access):**
```
Mandatory access:  submission → provisioning team card → approval → provisioning
Optional access:   submission → manager card → manager approval → provisioning team card → approval → provisioning
```

**Adaptive Card content:** Joinee info, access items, ServiceNow RITM reference, D2 risk score (colour-coded), Approve/Reject buttons (Action.Http → `/api/approve` or `/api/reject`).

**Escalation:** No action in 24 hours → auto-escalate to manager's manager → `audit_log` entry written.

**Production upgrade path:** Replace webhook URL with Azure Bot Framework endpoint for targeted DMs. No approval logic changes required.

### Consequences
- **Positive:** ~20 min setup. Approve/Reject buttons functional. Demonstrates concept completely.
- **Negative:** Channel-level notifications, not individual DMs. Acceptable for demo framing.

---

## ADR-005: External Systems — ServiceNow MCP + SAM Mock

**Date:** 2026-04-26 | **Status:** Accepted
**Supersedes:** ADR-005 v1 (All Mock APIs, 2025-04-24)

### Context
Original decision mocked all external systems. Decision changed: ServiceNow MCP is available and provides real ITSM ticket creation — a strong differentiator for the demo. SAM (Software Asset Management) mock retained for Non-Primary ID and GitHub Copilot access which are harder to demonstrate via real integration.

### Decision

**Workday — still mocked:**
```
GET /mock/workday/employee/:acf2_id → full employee record
```
Hard block on failure: agent responds "I wasn't able to verify your identity. Please contact IT support." Flow stops.

**ServiceNow — real via MCP:**
On access bundle submission, the agent calls ServiceNow MCP to:
- Create RITM (Requested Item) in ServiceNow
- RITM number stored on `access_requests.servicenow_ritm`
- RITM number displayed on Teams Adaptive Card for traceability
- On approve/reject callback: ServiceNow MCP updates RITM status

```
ServiceNow MCP actions used:
  create_request_item(short_description, category, items[]) → ritm_number
  update_request_item(ritm_number, state, comments)         → success
```

**SAM — mocked (NPE + GitHub Copilot):**
```
POST /mock/sam/provision/non-primary-id  → { success, npe_id, expires_at }
POST /mock/sam/provision/github-copilot  → { success, seat_assigned, license_id }
```
These appear as optional access items in relevant designation templates. Agent B (D3) flags NPE requests for intern seniority as HIGH risk.

**AD/LDAP, Jira — mocked:**
```
POST /mock/ad/provision   → { success, user_dn }
POST /mock/jira/provision → { success, project_key }
```

### Consequences
- **Positive:** Real ServiceNow integration is a demo differentiator. Judges see an actual ITSM ticket being raised, not a mock response.
- **Negative:** Requires ServiceNow developer instance (free at developer.servicenow.com). MCP setup needed before Phase 7.
- **Risk:** ServiceNow MCP availability must be verified before Phase 7 starts. Fallback: direct ServiceNow Table REST API (well-documented, same outcome).

---

## ADR-006: D1 — Adaptive Persona Learning

**Date:** 2025-04-24 | **Status:** Accepted

### Decision
Nightly scoring job reads `approval_events`, computes approval rate per access item per designation. Threshold: >80% → propose addition, <20% → propose removal. Proposals written to `bundle_fit_scores` collection, surfaced in Admin Dashboard for ratification — never auto-applied.

Cold-start: 50–100 synthetic approval events seeded per designation in Phase 0.

---

## ADR-007: D2 — Explainable Anomaly Scoring

**Date:** 2025-04-24 | **Status:** Accepted

### Decision
Risk score (0–100) computed on submission via Claude Sonnet 4.6 (Bedrock). Signals: role-baseline deviation, off-hours flag, request velocity, privilege escalation patterns. Score + plain-language explanation injected into Teams Adaptive Card. Colour-coded: Green <40, Amber 40–70, Red >70. JOHN002 pre-scripted to produce ~78.

---

## ADR-008: D3 — Cross-Request Privilege Accumulation Detection

**Date:** 2025-04-24 | **Status:** Accepted

### Decision
Combination-rules check via `dangerous_combinations` MongoDB collection. On each new request, query `privilege_edges` for user's existing permissions, cross-reference collection.

**Initial dangerous combinations:**
```
Prod DB write   + Deploy pipeline write  = CRITICAL (auto-escalate to security)
Prod DB read    + Deploy pipeline write  = HIGH
Any prod access + intern seniority       = HIGH
Finance data    + external API access    = HIGH
NPE (non-primary ID) + intern seniority  = HIGH
```

Agent B surfaces any match conversationally before submission. CRITICAL combinations auto-escalate regardless of joinee response.

---

## ADR-009: ADR Enforcement via Git Convention

**Date:** 2026-04-26 | **Status:** Accepted
**Supersedes:** ADR-009 v1 (Local Git Hook, 2025-04-24)

### Context
Original decision used a `.githooks/pre-commit` hook. Replaced by GitHub-based workflow (ADR-016). Convention enforced by process, not automated hook, to reduce setup friction on company laptop.

### Decision
Every commit that changes `web/`, `agent/`, `api/`, `orchestrator/`, or `schema/` must include an updated `ADR.md` in the same commit. Enforced by convention and code review, not a hook. Violations noted in PR description.

---

## ADR-010: LLM Provider — AWS Bedrock Claude Sonnet 4.6

**Date:** 2026-04-26 | **Status:** Accepted
**Supersedes:** ADR-010 v1 (Gemini 2.0 Flash + Ollama Fallback, 2025-04-24)

### Context
Original plan used Gemini 2.0 Flash (free tier) with Ollama local fallback. Decision changed: team has access to AWS Bedrock via company account. Claude Sonnet 4.6 on Bedrock is significantly more capable, has better tool-calling support, and aligns with company infrastructure. Single provider reduces integration complexity.

### Decision
**Primary and only:** Claude Sonnet 4.6 via AWS Bedrock.

No fallback LLM. If Bedrock is unavailable during demo, graceful error message shown in chat.

**AWS credentials:** Loaded from environment variables. Format matches AWS Option A:
```
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=       ← required for temporary/STS credentials
AWS_REGION=              ← confirm with team (us-east-1 or ap-south-1)
```

**Credentials workflow:**
- Build machine: `.env` with placeholder values (not committed)
- Company laptop: populate `.env` from credentials.txt
- `.env.example` committed to repo documenting all required vars

**SDK:** `@aws-sdk/client-bedrock-runtime` — `InvokeModelCommand` for inference, `ConverseCommand` for multi-turn tool use.

**Model ID:** `anthropic.claude-sonnet-4-5` (confirm exact Bedrock model ID for Sonnet 4.6 before Phase 2).

### Consequences
- **Positive:** Best-in-class tool calling. 200K token context handles all persona templates in one prompt. Company infrastructure — no personal API keys needed. Single provider = simpler error handling.
- **Negative:** No free tier — tokens billed to company AWS account. Confirm account allows Bedrock usage before Phase 2.
- **Risk:** AWS_REGION must match where Bedrock is enabled on the company account. Verify before build.

---

## ADR-011: Template Matching — LLM Context Stuffing

**Date:** 2026-04-26 | **Status:** Accepted
**Supersedes:** ADR-011 v1 (RAG Architecture: pgvector + nomic-embed-text, 2025-04-24)

### Context
Original plan used pgvector on Supabase with nomic-embed-text embeddings via Ollama for semantic template retrieval. Decision changed: MongoDB replaced Supabase (ADR-003), removing pgvector. Ollama dropped alongside Gemini/Groq (ADR-010). With Claude Sonnet 4.6's 200K token context, all 8 persona templates fit comfortably in a single system prompt.

### Decision
All designation templates loaded from MongoDB `designations` collection at agent startup and injected into Claude's system prompt. Claude selects the best-matching template based on resolved role, seniority, team, and dept.

**System prompt injection format:**
```
You have access to the following designation templates:
[1] Backend Developer (Mid, Payments)
    Mandatory: GitHub Enterprise, Jira, AWS Dev, PostgreSQL Dev
    Optional: CyberArk, AWS Prod Read, PagerDuty
    ...
[2] DevOps Engineer (Junior, Cloud Infrastructure)
    ...
[8] Data Analyst (Senior, Finance)
    ...

Given the resolved role details, select the best match. Return:
{
  "match_id": 1,
  "confidence": 0.92,
  "reasoning": "...",
  "no_match": false
}
If no template matches with confidence > 0.70, return no_match: true.
```

**No-match path:** `no_match: true` → Phase 14 template generation flow (Claude drafts template → admin ratification queue).

**Top-3 selection:** If confidence 0.70–0.95, return top 3 with scores. Joinee picks one. If confidence > 0.95, serve directly without selection step.

### Consequences
- **Positive:** Zero infrastructure dependency. No Ollama install. No embedding model. Works offline. Simpler to debug.
- **Negative:** Context window used for templates (minor — 8 templates ≈ 2K tokens, well within 200K limit). Adding more templates requires no code change — just insert into MongoDB.
- **Scalability note:** At ~200+ templates, switch to MongoDB Atlas Vector Search with Titan Embeddings (Bedrock). No agent logic change required — only retrieval layer changes.

---

## ADR-012: Agentic Design — 3 Active + 1 Proposed Capability

**Date:** 2025-04-24 | **Status:** Accepted

| Capability | Status | Phase Built |
|-----------|--------|-------------|
| Agent A: Ambiguity resolution loop | Build | Phase 3 |
| Agent B: D3 privilege check in chat | Build | Phase 11 |
| Agent C: Real-time status query | Build | Phase 9 |
| Agent D: Template self-critique loop | Proposed v2 | Not built |

Agent D deferred. Presented as production roadmap item.

---

## ADR-013: Auth — Azure AD / MSAL (Proposed for Production)

**Date:** 2025-04-24 | **Status:** Deprecated
**Reason:** Not implemented for hackathon. `BYPASS_AUTH=true` permanent in demo. Proposed as production roadmap item.

### Decision
Auth not implemented for the hackathon. `BYPASS_AUTH=true` hardcoded in `.env`. Session context injected at app level.

### Demo Framing
> "Authentication is handled via Azure AD and Microsoft Authenticator — the same infrastructure Sun Life already uses. For the demo we've bypassed it to keep focus on the provisioning logic."

---

## ADR-014: AWS Production Migration Path

**Date:** 2025-04-24 | **Last updated:** 2026-04-26 | **Status:** Accepted

### Decision
All Orchestrator functions stateless from day 1. State lives in DB only.

**Migration map:**
```
MongoDB local             → AWS DocumentDB (MongoDB-compatible)
                             OR MongoDB Atlas M0 free → paid tier
MongoDB Change Streams    → DocumentDB Change Streams (compatible)
Next.js API routes        → API Gateway + Lambda (stateless already)
Local cron job (D1)       → AWS EventBridge + Lambda
Teams Incoming Webhook    → Azure Bot Framework (targeted DMs)
ServiceNow MCP            → ServiceNow production instance (same MCP, different URL)
SAM mock                  → Real SAM REST API
Workday mock              → Real Workday API (or Sun Life internal wrapper)
AWS Bedrock (same)        → No change — already production AWS
Auth bypass               → Azure AD + MSAL
SunLife Ask               → Webhook handoff to agent endpoint
```

**Stateless function contract:**
```json
Input:  { "request_id", "access_item", "target_system", "acf2_id", "bundle_metadata" }
Output: { "success", "system_reference_id", "error_message?" }
```

---

## ADR-015: Demo Strategy — Single Account + Pre-seeded ACF2 IDs

**Date:** 2025-04-24 | **Status:** Accepted

### Decision
Single Teams account. All routing table entries point to one webhook URL.

**Pre-seeded ACF2 IDs in MongoDB `users` collection:**
```
RIYA001  → Backend Developer, Payments, Full-time         → happy path
JOHN002  → Junior DevOps, Cloud Infrastructure, Full-time → D2 anomaly score ~78
PRIYA003 → Data Analyst, Finance, Contract                → D3 privilege warning fires
SAM004   → Unknown role                                   → no-match → draft + admin ratification
```

**Demo sequence (5 minutes):**
1. RIYA001 → full happy path → ServiceNow RITM created → Teams card → approve → provisioning → live status
2. JOHN002 → Teams card arrives red-flagged → show D2 explanation
3. PRIYA003 → Agent B surfaces privilege warning in chat before submission
4. SAM004 (if time) → template generated, admin ratification in dashboard

**Judge framing:** "In production, each approver receives their card via DM. For the demo, all notifications are centralised to demonstrate card content and approval mechanics."

---

## ADR-016: GitHub Workflow Convention

**Date:** 2026-04-26 | **Status:** Accepted

### Context
Team of 2, building on personal machine, deploying to company laptop for demo. Need a clean handoff mechanism and audit trail of what was built per phase.

### Decision
**Repo:** `Salman1310/hackherway-ps6` (private)

**Branch convention:**
```
main                    ← always stable, phase-complete code only
phase/01-ui-shell       ← feature branch per phase
phase/02-identity
phase/03-agent-a
...
```

**Commit convention:**
```
feat(phase-01): description of what was built
fix(phase-02): description of fix
docs(adr): update ADR-003 for MongoDB decision
```

**Phase completion checklist before merging to main:**
1. Phase exit criteria pass (from PHASES.md)
2. ADR.md updated if any structural decision changed
3. `.env.example` updated if any new env var added
4. Commit message references phase number

**Company laptop setup (clone and run):**
```bash
git clone https://<PAT>@github.com/Salman1310/hackherway-ps6.git
cd hackherway-ps6/web
npm install
cp .env.example .env
# populate .env from credentials.txt
npm run dev
```

**Files never committed:**
```
.env
credentials.txt
token.txt
*.token
node_modules/
.next/
```

### Consequences
- **Positive:** Clean audit trail. Company laptop always gets stable code from main. ADR.md in repo = single source of truth for all decisions.
- **Negative:** Manual convention, not automated hook. Relies on discipline.

---

*Last updated: 2026-04-26*
*Phase 1 complete. ADRs updated: 001, 002, 003, 005, 009, 010, 011, 014. ADR-016 added.*
*Next: Phase 2 — Identity verification (ACF2 input → MongoDB user fetch → session populate).*
