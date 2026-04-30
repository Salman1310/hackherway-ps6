# Architecture Decision Records (ADR)
## PS6: AI-Powered Access Approval - HackHERway | Sun Life

> Process: update this file before every commit that introduces a structural change.
> Status lifecycle: `Proposed -> Accepted -> Deprecated -> Superseded`

---

## ADR Index

| ID | Title | Status | Last Updated |
|----|-------|--------|--------------|
| ADR-001 | Overall System Architecture | Accepted | 2026-04-29 |
| ADR-002 | AI Layer: Single Conversational Agent | Accepted | 2026-04-29 |
| ADR-003 | Database: SQLite via MCP | Accepted | 2026-04-29 |
| ADR-004 | Approval Channel: MS Teams Incoming Webhook | Accepted | 2026-04-29 |
| ADR-005 | External Systems: ServiceNow MCP + Mock Provisioning APIs | Accepted | 2026-04-29 |
| ADR-006 | D1: Adaptive Persona Learning | Accepted | 2026-04-29 |
| ADR-007 | D2: Explainable Risk Scoring | Accepted | 2026-04-29 |
| ADR-008 | D3: Cross-Request Privilege Accumulation Detection | Accepted | 2026-04-29 |
| ADR-009 | ADR Enforcement via Git Convention | Accepted | 2026-04-29 |
| ADR-010 | LLM Provider: AWS Bedrock Claude Sonnet 4.6 | Accepted | 2026-04-29 |
| ADR-011 | Template Matching: Tool-Query Over Normalized Role Tables | Accepted | 2026-04-30 |
| ADR-012 | Agentic Design: 4 Capabilities in One Agent | Accepted | 2026-04-29 |
| ADR-013 | Auth: Bypassed for Hackathon, Azure AD for Production | Accepted | 2026-04-29 |
| ADR-014 | Production Migration Path | Accepted | 2026-04-29 |
| ADR-015 | Demo Strategy: Three Pre-Seeded ACF2 IDs | Accepted | 2026-04-29 |
| ADR-016 | GitHub Workflow Convention | Accepted | 2026-04-29 |

---

## ADR-001: Overall System Architecture

**Date:** 2026-04-29 | **Status:** Accepted

### Context
The project needs to demo an AI-powered access approval flow with minimal setup friction on both personal and company laptops. The older plan put business logic in the frontend layer and used MongoDB. That created firewall risk, duplicated frontend/backend responsibilities, and made it too easy for secrets to leak into frontend configuration.

### Decision
Use a two-process application:

```text
User
  <-> Next.js frontend on port 3000
  <-> FastAPI backend on port 8000
      <-> Access Agent
          <-> AWS Bedrock Claude Sonnet 4.6
          <-> SQLite MCP server
          <-> Mock Workday / AD / Jira / SAM APIs
          <-> ServiceNow MCP
      <-> Orchestrator
          <-> SQLite MCP server
          <-> Mock provisioning APIs
          <-> MS Teams Incoming Webhook
```

Key boundaries:

- `frontend/` owns UI only.
- `backend/` owns all business logic, AI calls, database access, approval callbacks, and secrets.
- The frontend never imports AWS SDKs, database drivers, MCP clients, or Teams webhooks.
- FastAPI exposes HTTP endpoints consumed by thin Next.js proxy routes.
- The agent is a Python module, not the FastAPI app itself.
- The orchestrator is a separate Python module, event-driven and non-conversational.

### Consequences
- Lower demo risk: SQLite is local, FastAPI is explicit, and the frontend remains stable.
- Clear secret boundary: AWS, ServiceNow, and Teams credentials live only in `backend/.env`.
- The frontend can be frozen while backend/agent work continues.

---

## ADR-002: AI Layer - Single Conversational Agent

**Date:** 2026-04-29 | **Status:** Accepted

### Decision
Use one Bedrock-backed conversational agent with a tool-use loop. Do not build separate agents for each capability.

Agent tools:

```text
query_db(sql)                                  -> execute SQL through SQLite MCP
check_privilege_accumulation(acf2_id, bundle) -> detect dangerous permission combinations
get_request_status(acf2_id)                   -> read per-item approval state
submit_access_request(bundle)                 -> write request state and trigger downstream flow
```

Session state shape:

```json
{
  "acf2_id": "ARUN01",
  "workday_context": { "name": "", "team": "", "manager": "", "dept": "", "employment_type": "" },
  "resolved_role": { "role": "", "seniority": "", "employment_type": "" },
  "selected_template": null,
  "final_bundle": [],
  "request_id": null
}
```

### Consequences
- One agent is easier to demo and reason about than a multi-agent system.
- Capability boundaries still stay clear through tools and prompt instructions.
- SQL generation must be guarded by backend validation before reaching MCP.

---

## ADR-003: Database - SQLite via MCP

**Date:** 2026-04-29 | **Status:** Accepted
**Supersedes:** MongoDB Atlas / MongoDB Community Server decisions.

### Context
MongoDB Atlas introduced firewall and setup uncertainty. A local database is enough for the hackathon demo, and the agent already needs SQL-aware tool calls.

### Decision
Use SQLite as the hackathon database and access it through the official SQLite MCP server. Application code must not call `sqlite3` directly for feature flows; direct SQLite is permitted only for local seed/setup scripts.

Current Phase 0A tables:

```text
users
designations                 # Phase 0A JSON-template shape
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

Target Phase 0B role/access tables before Phase 2:

```text
users
user_designations
designations                 # id/title/description only
role_access_items            # one access item per row
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

Current demo users:

```text
ARUN01  -> Arun Mehta, Cloud Infrastructure, Technology, full-time
NEHA02  -> Neha Kapoor, Finance Analytics, Finance, contract
SARA03  -> Sara Chen, TBD, TBD, full-time
```

### Consequences
- No network database dependency during the demo.
- Each laptop seeds its own `hackherway.db`.
- Production can later migrate to AWS-managed storage or a corporate database without changing the UI contract.

---

## ADR-004: Approval Channel - MS Teams Incoming Webhook

**Date:** 2026-04-29 | **Status:** Accepted

### Decision
Use a single MS Teams Incoming Webhook for the hackathon approval channel. The webhook URL is a secret and belongs only in `backend/.env` as `TEAMS_WEBHOOK_URL`.

Teams cards include joinee info, requested access, ServiceNow RITM, risk score, explanation, and approve/reject actions that call backend endpoints.

### Consequences
- Fast setup for demo.
- Channel-level notifications are acceptable for judging.
- Production can replace this with Azure Bot Framework targeted DMs without changing frontend behavior.

---

## ADR-005: External Systems - ServiceNow MCP + Mock Provisioning APIs

**Date:** 2026-04-29 | **Status:** Accepted

### Decision
Use ServiceNow MCP for real RITM creation when available. Keep Workday, AD/LDAP, Jira, and SAM as mocks for hackathon reliability.

Mock APIs:

```text
GET  /mock/workday/employee/{acf2_id}
POST /mock/ad/provision
POST /mock/jira/provision
POST /mock/sam/provision/non-primary-id
POST /mock/sam/provision/github-copilot
```

Fallback: if ServiceNow MCP is unavailable, use a mock RITM path so the demo flow continues.

---

## ADR-006: D1 - Adaptive Persona Learning

**Date:** 2026-04-29 | **Status:** Accepted

### Decision
Compute approval-rate suggestions from approval history and write proposals to `bundle_fit_scores` or a later equivalent table. Never auto-change templates. Admin ratification is required.

---

## ADR-007: D2 - Explainable Risk Scoring

**Date:** 2026-04-29 | **Status:** Accepted

### Decision
On submission, compute a 0-100 risk score with a short explanation. Signals include role-baseline deviation, off-hours requests, request velocity, and privilege escalation patterns.

ARUN01 is the scripted risk-scoring demo user and should produce an amber/red score around 78 once Phase 4 seed data is complete.

---

## ADR-008: D3 - Cross-Request Privilege Accumulation Detection

**Date:** 2026-04-29 | **Status:** Accepted

### Decision
Before submission, compare the requested bundle against existing permissions in `privilege_edges` and dangerous pairs in `dangerous_combinations`.

Initial dangerous combinations:

```text
Prod DB write + Deploy pipeline write = CRITICAL
Prod DB read + Deploy pipeline write = HIGH
Any prod access + intern seniority = HIGH
Finance data + external API access = HIGH
NPE + intern seniority = HIGH
```

NEHA02 is the scripted Privilege Guard demo user.

---

## ADR-009: ADR Enforcement via Git Convention

**Date:** 2026-04-29 | **Status:** Accepted

### Decision
Every commit that changes architecture or ownership boundaries in `frontend/`, `backend/`, `orchestrator/`, `mock-apis/`, or database schema must include an ADR update when the decision changes.

This is enforced by review discipline, not by a local Git hook.

---

## ADR-010: LLM Provider - AWS Bedrock Claude Sonnet 4.6

**Date:** 2026-04-29 | **Status:** Accepted

### Decision
AWS Bedrock is the only LLM provider. Use Claude Sonnet 4.6 through Bedrock Converse/tool-use APIs. Do not add Gemini, Groq, Ollama, or local model fallbacks.

Required backend env vars:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN
AWS_REGION
BEDROCK_MODEL_ID
```

If Bedrock fails during the demo, the backend should return a graceful user-facing message or a narrow deterministic fallback where already implemented.

---

## ADR-011: Template Matching - Tool-Query Over Normalized Role Tables

**Date:** 2026-04-30 | **Status:** Accepted

**Supersedes:** Previous ADR-011 context-stuffing decision.

### Decision
Phase 2 will use Bedrock reasoning with tool-use queries over normalized SQLite role/access tables. Do not inject the full designation catalog into the system prompt.

The target schema is:

```text
designations(id, title, description, team_hint, dept_hint)
role_access_items(id, designation_id, access_item, display_name, system, description, mandatory, owner_team, servicenow_catalog_item_id, sort_order)
user_designations(acf2_id, designation_id, assigned_at, source)
```

The agent should query candidate designations and their access items through `query_db`, reason over those results, and return structured selected-template data to the frontend.

Do not build RAG/vector search for the hackathon.

Match behavior:

```text
confidence > 0.95       -> serve direct match
0.70 <= confidence <= .95 -> return top 3 for user selection
confidence < 0.70       -> no-match flow and template draft
```

### Consequences
- Keeps the system prompt smaller and less brittle than full context stuffing.
- Makes mandatory and optional access rows queryable for Phase 3.
- Gives each access item a place to store owner teams and ServiceNow catalog IDs.
- Requires Phase 0B schema rework before Phase 2 implementation starts.

---

## ADR-012: Agentic Design - 4 Capabilities in One Agent

**Date:** 2026-04-29 | **Status:** Accepted

| Capability | Status | Phase |
|------------|--------|-------|
| Role Resolver | Build | Phase 2 |
| Risk Scorer | Build | Phase 4 |
| Privilege Guard | Build | Phase 4 |
| Status Tracker | Build | Phase 6 |

---

## ADR-013: Auth - Bypassed for Hackathon, Azure AD for Production

**Date:** 2026-04-29 | **Status:** Accepted

### Decision
Do not implement Azure AD/MSAL during the hackathon. Use `BYPASS_AUTH=true` for demo/dev. Present Azure AD/MSAL as the production authentication path.

---

## ADR-014: Production Migration Path

**Date:** 2026-04-29 | **Status:** Accepted

### Decision
Keep backend functions stateless and database-backed so migration is straightforward:

```text
FastAPI routes          -> API Gateway + Lambda or container service
SQLite                  -> AWS-managed relational DB or approved corporate DB
SQLite MCP              -> production DB access layer
Local cron              -> EventBridge + Lambda
Teams Incoming Webhook  -> Azure Bot Framework targeted DMs
ServiceNow MCP          -> production ServiceNow instance
Mock Workday/SAM/etc.   -> real enterprise APIs
Auth bypass             -> Azure AD + MSAL
```

---

## ADR-015: Demo Strategy - Three Pre-Seeded ACF2 IDs

**Date:** 2026-04-29 | **Status:** Accepted

### Decision
Use three demo IDs consistently across code, setup docs, and phase docs:

```text
ARUN01 -> happy path + Risk Scorer score around 78
NEHA02 -> Privilege Guard warning / escalation scenario
SARA03 -> no-match template generation + admin ratification
```

Demo sequence:

1. ARUN01: identity, role, template, submit, ServiceNow RITM, Teams card, approve, provision, status.
2. NEHA02: same start, then Privilege Guard blocks or escalates before submission.
3. SARA03: no matching template, draft is generated for admin review.

---

## ADR-016: GitHub Workflow Convention

**Date:** 2026-04-29 | **Status:** Accepted

### Decision
Private repo: `Salman1310/hackherway-ps6`.

Branch convention:

```text
main
phase/00-foundation
phase/01-agent-identity
phase/02-role-resolver
...
```

Commit convention:

```text
feat(phase-01): add agent identity verification
fix(phase-02): handle vague role input
docs(adr): update SQLite MCP decision
```

Files never committed:

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

---

*Last updated: 2026-04-29*
