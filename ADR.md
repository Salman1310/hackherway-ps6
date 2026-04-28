# Architecture Decision Records (ADR)
## PS6: AI-Powered Access Approval — HackHERway | Sun Life

> **Process:** This file must be updated before every local Git checkpoint that introduces a structural change.
> A pre-commit git hook enforces this check (see `.githooks/pre-commit`).
> Status lifecycle: `Proposed → Accepted → Deprecated → Superseded`

---

## ADR Index

| ID | Title | Status | Last Updated |
|----|-------|--------|--------------|
| ADR-001 | Overall System Architecture | Accepted | 2025-04-24 |
| ADR-002 | AI Layer: Conversational Agent Architecture | Accepted | 2025-04-24 |
| ADR-003 | Database: Supabase + pgvector | Accepted | 2025-04-24 |
| ADR-004 | Approval Channel: MS Teams Incoming Webhook | Accepted | 2025-04-24 |
| ADR-005 | External Systems: Mock APIs | Accepted | 2025-04-24 |
| ADR-006 | D1: Adaptive Persona Learning | Accepted | 2025-04-24 |
| ADR-007 | D2: Explainable Anomaly Scoring | Accepted | 2025-04-24 |
| ADR-008 | D3: Cross-Request Privilege Accumulation Detection | Accepted | 2025-04-24 |
| ADR-009 | ADR Enforcement via Git Hook | Accepted | 2025-04-24 |
| ADR-010 | LLM Provider: Gemini 2.0 Flash + Ollama Fallback | Accepted | 2025-04-24 |
| ADR-011 | RAG Architecture: pgvector + nomic-embed-text | Accepted | 2025-04-24 |
| ADR-012 | Agentic Design: 3 Active Capabilities + 1 Proposed | Accepted | 2025-04-24 |
| ADR-013 | Auth: Azure AD / MSAL — Proposed for Production | Deprecated | 2025-04-24 |
| ADR-014 | AWS Production Migration Path | Accepted | 2025-04-24 |
| ADR-015 | Demo Strategy: Single Account + Pre-seeded ACF2 IDs | Accepted | 2025-04-24 |

---

## ADR-001: Overall System Architecture

**Date:** 2025-04-24 | **Status:** Accepted

### Context
Sun Life's access provisioning takes 2–30 days. New employees and team-changers raise individual tickets per system. No central audit trail. Joinee has zero visibility into approval status.

### Decision
A joinee-initiated, AI-agent-driven provisioning system. The joinee drives the flow — not the manager. Identity verified via ACF2 ID against Workday. An AI agent determines the right access template, handles ambiguity conversationally, performs pre-submission privilege checks, and routes approval requests via MS Teams. Joinee has real-time visibility into approval status.

**Architecture layers:**
- **Presentation:** Standalone web app — 3-panel layout (sidebar / chat / template+status panel). Sun Life Ask-inspired design language.
- **Agent:** Conversational AI with tool-calling — 3 active agentic capabilities (A, B, C).
- **Template Engine:** RAG retrieval (pgvector) → AI generation fallback → admin ratification.
- **Core Services:** API Gateway, stateless Orchestrator, Approval Engine with state machine.
- **Approval Notification:** MS Teams Adaptive Cards via Incoming Webhook.
- **Persistence:** Supabase (PostgreSQL + pgvector). Schema designed for AWS RDS drop-in.
- **Provisioning Targets:** Mock APIs for Workday, ServiceNow, Jira, AD/LDAP, SAM.

**Primary flow:**
```
Joinee opens app → enters ACF2 ID → agent fetches Workday context
→ joinee states role → Agent A resolves ambiguity if needed
→ RAG retrieves top 3 matching templates
→ joinee selects + customises (mandatory locked, optional toggleable)
→ Agent B checks privilege accumulation before submission
→ request splits into approval streams → Teams cards sent
→ Manager approves optional access first → provisioning team approves mandatory
→ Orchestrator provisions all systems in parallel on full approval
→ Joinee sees live status via Agent C → everything audit logged
```

### Consequences
- **Positive:** Joinee-driven removes manager bottleneck. AI handles ambiguity static forms can't. Real-time status eliminates follow-up tickets.
- **Negative:** Workday dependency — hard block on failure by design.
- **Production note:** SunLife Ask integration is post-win. Standalone web app is the hackathon deliverable, designed so webhook handoff to SunLife Ask is straightforward.

---

## ADR-002: AI Layer — Conversational Agent Architecture

**Date:** 2025-04-24 | **Status:** Accepted
**Supersedes:** Original "NLP Engine: single LLM API call" framing

### Context
Original architecture treated AI as a one-shot extraction call. Actual requirements are multi-turn conversation, Workday-aware context, tool-calling, ambiguity resolution loops, and post-submission status queries. This requires a genuine agent.

### Decision

**Agent tools:**
```
fetch_workday(acf2_id)                              → employee record
retrieve_templates(role, team, dept)                → top 3 RAG results with scores
check_privilege_accumulation(acf2_id, permissions)  → D3 danger check
get_request_status(acf2_id)                         → live approval state
submit_access_request(bundle)                       → writes to DB, triggers approval flow
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
Triggers when role input is vague. Loops with targeted questions until 4 fields resolved: `role`, `seniority`, `employment_type`, `team` (team pre-filled from Workday). Only proceeds to template retrieval when confidence threshold met.
Example: "I do backend stuff" → "Backend Developer or DevOps?" → "Full-time or contract?" → resolved.

**Agent B — Pre-Submission Privilege Check (D3 in chat)**
Before final submission, queries user's existing privilege graph. If new bundle + existing access creates a dangerous combination, agent surfaces it conversationally with explanation. Joinee must confirm before proceeding. CRITICAL combinations auto-escalate to security regardless of joinee response.

**Agent C — Live Status Query Tool**
Post-submission, joinee can ask "what's the status of my request?" at any time. Agent calls `get_request_status()` → returns per-system approval state in plain language.

**Agent D — Template Self-Critique Loop (v2 scope — not built for hackathon)**
When no template exists: agent generates draft → LLM audits own output against security baselines → submits to admin. Deferred — implementation risk too high for hackathon timeline. Presented to judges as production roadmap item.

### Consequences
- **Positive:** Genuinely agentic — not a form with a chatbot wrapper. Each capability adds demonstrable value.
- **Negative:** Session state must be managed carefully. Prompt engineering quality directly determines reliability.

---

## ADR-003: Database — Supabase + pgvector

**Date:** 2025-04-24 | **Status:** Accepted

### Context
Need persistent storage for templates + embeddings, requests, approvals, audit log, privilege graph, and D1 scoring. Need real-time subscription for the joinee status panel.

### Decision
Supabase free tier with pgvector extension. Schema is plain PostgreSQL — zero Supabase-specific features. Direct drop-in to AWS RDS PostgreSQL in production.

**Full schema:**
```sql
personas            (id, role_name, seniority, team, dept, mandatory_access[], optional_access[], embedding vector(768), ratified_by, ratified_at)
access_requests     (id, acf2_id, persona_id, final_bundle jsonb, status, submitted_at, completed_at)
approval_events     (id, request_id, access_item, approver_type, approver_email, status, decided_at, escalated_at, anomaly_score, anomaly_explanation)
approver_routing    (id, system_name, sensitivity_tier, approver_email, approver_team)
audit_log           (id, event_type, actor, target_acf2_id, payload jsonb, created_at)  -- immutable, append-only
privilege_edges     (id, acf2_id, permission, system_name, sensitivity_tier, granted_at, revoked_at)
bundle_fit_scores   (id, persona_id, access_item, approval_rate, sample_size, proposed_action, surfaced_at, admin_decision)
template_drafts     (id, generated_role, generated_bundle jsonb, generation_reasoning, status, reviewed_by, reviewed_at)
```

Real-time subscriptions on `approval_events` power the joinee status panel without polling.

### Consequences
- **Positive:** pgvector co-located with relational data — no separate vector service. Real-time built-in.
- **Risk:** Free tier cold-start. Warm-up script runs 10 minutes before demo.
- **Production:** AWS RDS PostgreSQL + pgvector extension. See ADR-014.

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

**Adaptive Card content:** Joinee info, access items, D2 risk score (colour-coded), Approve/Reject buttons (Action.Http → `/api/approve` or `/api/reject`).

**Escalation:** No action in 24 hours → auto-escalate to manager's manager → `audit_log` entry written.

**Demo:** All routing table entries point to one webhook URL. See ADR-015.

**Production upgrade path:** Replace webhook URL with Azure Bot Framework endpoint for targeted DMs. No approval logic changes required.

### Consequences
- **Positive:** ~20 min setup. Approve/Reject buttons functional. Demonstrates the concept completely.
- **Negative:** Channel-level notifications, not individual DMs. Framed correctly to judges this is acceptable.

---

## ADR-005: External Systems — Mock APIs

**Date:** 2025-04-24 | **Status:** Accepted

### Decision
All external systems simulated locally.

**Mock endpoints:**
```
GET  /mock/workday/employee/:acf2_id  → full employee record
POST /mock/servicenow/provision       → { success, ticket_id }
POST /mock/jira/provision             → { success, project_key }
POST /mock/ad/provision               → { success, user_dn }
POST /mock/sam/provision              → { success, asset_id }
```

**Workday failure behaviour:** Hard block. Agent responds: "I wasn't able to verify your identity. Please contact IT support." Flow does not continue under any circumstance.

**Pre-seeded ACF2 IDs:** See ADR-015.

---

## ADR-006: D1 — Adaptive Persona Learning

**Date:** 2025-04-24 | **Status:** Accepted

### Decision
Nightly scoring job reads `approval_events`, computes approval rate per access item per persona. Threshold logic: >80% approval rate for an item not in the bundle → propose addition. <20% → propose removal. Proposals surfaced in Admin Dashboard for ratification — never auto-applied.

Cold-start mitigation: 50–100 synthetic approval events seeded per persona in Phase 0.

---

## ADR-007: D2 — Explainable Anomaly Scoring

**Date:** 2025-04-24 | **Status:** Accepted

### Decision
Risk score (0–100) computed on submission. Signals: role-baseline deviation, off-hours flag, request velocity, privilege escalation patterns. Score + LLM-generated plain-language explanation injected into Teams Adaptive Card. Colour-coded: Green <40, Amber 40–70, Red >70. Approver decisions logged against flags for accuracy improvement.

---

## ADR-008: D3 — Cross-Request Privilege Accumulation Detection

**Date:** 2025-04-24 | **Status:** Accepted

### Decision
**v1 (hackathon):** Combination-rules check via `dangerous_combinations` lookup table. On each new request, query `privilege_edges` for user's existing permissions, cross-reference lookup table.

**Initial dangerous combinations:**
```
Prod DB write   + Deploy pipeline write  = CRITICAL (auto-escalate to security)
Prod DB read    + Deploy pipeline write  = HIGH
Any prod access + intern seniority       = HIGH
Finance data    + external API access    = HIGH
```

Agent B surfaces any match conversationally before submission. CRITICAL combinations auto-escalate regardless.

**v2 upgrade path:** Replace lookup table with recursive CTE graph traversal on `privilege_edges`. Documented as future ADR amendment.

---

## ADR-009: ADR Enforcement — Local Git Hook

**Date:** 2025-04-24 | **Status:** Accepted

### Decision
`.githooks/pre-commit` checks if staged changes modify `web/`, `agent/`, `api/`, `orchestrator/`, `schema/`, or `config/`. If yes and `ADR.md` is not staged in the same checkpoint, the commit is blocked with: `Structural change detected. Update ADR.md before committing.`

Override: `git commit --no-verify` (must be noted in the commit message).

**Required in every local working copy:**
```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
```

---

## ADR-010: LLM Provider — Gemini 2.0 Flash + Ollama Fallback

**Date:** 2025-04-24 | **Status:** Accepted

### Context
GPT-4o is paid. Requirements: JSON output mode, multi-turn conversation, tool-calling, large context window for persona catalog injection.

### Decision
**Primary:** Gemini 2.0 Flash (Google AI Studio free tier — 1M tokens/day, 15 req/min). Native JSON output mode. Strong instruction following. Good tool-calling support.

**Fallback:** Ollama local model. Use only if Gemini is unavailable during demo-critical flows. This keeps the fallback local and avoids adding another hosted LLM provider dependency.

**API keys:** Environment variables only. `.env` in `.gitignore`. `.env.example` documents all required keys.

### Consequences
- **Positive:** Gemini JSON mode eliminates parsing bugs. Ollama keeps fallback execution local and removes dependency on another hosted LLM provider.
- **Risk:** 15 req/min Gemini limit is not a concern for the demo. Ollama fallback quality and latency depend on the demo machine, so the local model must be pulled and tested before rehearsal.

---

## ADR-011: RAG Architecture — pgvector + nomic-embed-text

**Date:** 2025-04-24 | **Status:** Accepted

### Decision
**Vector store:** pgvector on Supabase. `personas.embedding` column, `vector(768)`.

**Embedding model:** `nomic-embed-text` (free). 768 dimensions. Runs locally through Ollama.

**Retrieval logic:**
```
query_embedding = embed(role + " " + team + " " + dept)
results = SELECT * FROM personas ORDER BY embedding <=> query_embedding LIMIT 3

similarity > 0.95 → exact match, serve directly
similarity > 0.70 → present top 3 to joinee
else              → no match, trigger template generation flow
```

**No-match template generation flow:**
1. LLM generates draft template
2. Written to `template_drafts` with status `pending_ratification`
3. Joinee informed request is on hold pending admin ratification
4. Admin approves/edits/rejects in Admin Dashboard
5. On approval: template embedded and written to `personas`

### Consequences
- **Positive:** No separate vector service. Semantic matching handles natural language variance. Ollama keeps embedding generation local and avoids hosted inference latency during the demo.
- **Risk:** Demo machine must have Ollama installed and the `nomic-embed-text` model pulled before Phase 4 rehearsal.

---

## ADR-012: Agentic Design — 3 Active + 1 Proposed Capability

**Date:** 2025-04-24 | **Status:** Accepted

| Capability | Status | Phase Built |
|-----------|--------|-------------|
| Agent A: Ambiguity resolution loop | Build | Phase 4 |
| Agent B: D3 privilege check in chat | Build | Phase 12 |
| Agent C: Real-time status query | Build | Phase 10 |
| Agent D: Template self-critique loop | Proposed v2 | Not built |

Agent D deferred: multi-step LLM-reviews-own-output loop is high effort, high demo risk. Presented as production roadmap item with documented design.

---

## ADR-013: Auth — Azure AD / MSAL (Proposed for Production)

**Date:** 2025-04-24 | **Status:** Deprecated
**Reason:** Not implemented for hackathon. `BYPASS_AUTH=true` permanent. Proposed as production roadmap item.

### Decision
Auth is **not implemented** for the hackathon. Judges' time is better spent seeing the agent, RAG, Teams flow, and D1/D2/D3 in action — not a login screen. `BYPASS_AUTH=true` is permanent in the demo `.env`. Hardcoded session context injected at app level for all phases.

### Production Proposal
When this system moves to beta:
- **Azure AD + Microsoft Authenticator** — same infrastructure Sun Life already uses org-wide
- **MSAL JS** (`@azure/msal-browser`) — Microsoft login popup, returns name, email, session token
- **Low integration cost** — already in the Microsoft ecosystem via Teams. Same Azure AD tenant serves both auth and Teams webhook

### Demo Framing
> "Authentication is handled via Azure AD and Microsoft Authenticator — the same infrastructure Sun Life already uses. Integration is straightforward given we're already in the Microsoft ecosystem for Teams. For the demo we've bypassed it to keep focus on the provisioning logic."

### Consequences
- **Positive:** Full build time spent on features that matter for the demo.
- **Production note:** Route guards, token passing, and role-based access are straightforward additions on top of the existing app structure.

---

## ADR-014: AWS Production Migration Path

**Date:** 2025-04-24 | **Status:** Accepted

### Decision
All Orchestrator functions stateless from day 1. State lives in DB only.

**Migration map:**
```
Supabase PostgreSQL   → AWS RDS PostgreSQL         (schema identical)
Supabase pgvector     → RDS pgvector extension      (same queries)
Supabase real-time    → API Gateway WebSocket + Lambda
Supabase cron jobs    → AWS EventBridge + Lambda
Orchestrator          → Lambda functions            (stateless already)
Logs/files            → S3
Auth                  → Azure AD stays              (org standard)
Mock APIs             → Real ServiceNow, Jira, AD/LDAP, SAM integrations
SunLife Ask           → Webhook handoff to agent endpoint
```

**Stateless function contract (all Orchestrator calls must follow):**
```json
Input:  { "request_id", "access_item", "target_system", "acf2_id", "bundle_metadata" }
Output: { "success", "system_reference_id", "error_message?" }
```

---

## ADR-015: Demo Strategy — Single Account + Pre-seeded ACF2 IDs

**Date:** 2025-04-24 | **Status:** Accepted

### Decision
Single Teams account. All routing table entries point to one webhook URL.

**Pre-seeded ACF2 IDs:**
```
RIYA001  → Backend Developer, Payments, Full-time        → happy path
JOHN002  → Junior DevOps, Cloud Infrastructure, Full-time → D2 anomaly triggers (score 78/100 pre-scripted)
PRIYA003 → Data Analyst, Finance, Contract               → D3 privilege combo triggers via Agent B
SAM004   → Role with no existing template                → template generation + admin ratification flow
```

**Demo sequence (5 minutes):**
1. RIYA001 → full happy path → Teams card → approve → provisioning → live status update
2. JOHN002 → anomaly card arrives red-flagged → show D2 explanation
3. PRIYA003 → Agent B surfaces privilege warning in chat before submission
4. SAM004 (if time) → new template generated, admin ratification in dashboard

**Judge framing for single account:** "In production, each approver receives their card via DM. For the demo, all notifications are centralised to demonstrate card content and approval mechanics."

**Money moments to rehearse:** Teams card arriving live + Agent B's privilege warning in chat.

---

*Last updated: 2025-04-24 — Planning phase complete. All decisions locked. Auth removed from scope (ADR-013 Deprecated).*
*Next update: Phase 0 checkpoint — local repo structure and schema confirmed.*
