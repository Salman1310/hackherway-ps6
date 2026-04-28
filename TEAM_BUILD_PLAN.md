# Team Build Plan - PS6 AI-Powered Access Approval

> **Purpose:** This document helps the team start building in parallel. It explains what the project is, what the demo must communicate, who owns which parts, and what contracts must be agreed before implementation starts.

---

## 1. Project Summary

Sun Life access provisioning is currently fragmented across ServiceNow, Jira, email, SAM, cloud tools, and manual approvals. A new joinee or role-changer may wait 2-30 days because every access item becomes a separate request, approvers are unclear, and audit history is scattered.

This project builds an AI-powered access approval assistant that lets a joinee initiate access setup through a conversational web app. The system verifies the joinee through Workday/ACF2, understands their role, matches them to a persona-based access template, bundles mandatory and optional access, routes approvals through Teams, provisions mock systems, and records everything in an audit trail.

In short:

```text
Fragmented access tickets -> AI-guided role understanding -> one bundled request -> routed approvals -> auditable provisioning
```

---

## 2. What The Problem Statement Asked For

| Requirement | Our Implementation |
|------------|--------------------|
| Access Inventory | Persona templates for roles such as Backend Developer, QA Engineer, Finance Analyst |
| Access Consolidation | One bundled access request per persona instead of separate tool-by-tool tickets |
| Intelligent Approval Routing | Approval engine routes mandatory and optional access to the correct approvers |
| Audit & Governance | Audit dashboard shows who requested, approved, and received access |

---

## 3. What We Are Adding Beyond The Problem Statement

These are the differentiators that make the project feel intelligent rather than just digital:

| Differentiator | Why It Matters |
|---------------|----------------|
| Conversational ambiguity resolution | The joinee can say "I do backend stuff," and the agent asks clarifying questions before choosing a template |
| RAG-based persona matching | Role/team/department context is matched semantically against persona templates |
| Pre-submission privilege accumulation check | The system warns before granting combinations that create excess privilege |
| Explainable anomaly score | Approvers see why a request may be risky |
| Adaptive persona learning | Admins can improve templates based on approval patterns |
| Template generation for no-match roles | Missing personas can be drafted and sent for admin ratification |

---

## 4. Core Demo Story

The demo should communicate the idea clearly before showing advanced features.

### Moment 1: The System Understands The Joinee

Show:
- Joinee enters ACF2 ID
- Workday mock verifies identity
- Agent asks clarifying questions if role input is vague
- RAG finds the closest persona template

Message to jury:

```text
The system knows who the joinee is and resolves ambiguity before creating an access request.
```

### Moment 2: Fragmented Tickets Become One Smart Bundle

Show:
- Persona template appears in the right panel
- Mandatory access is locked
- Optional access can be selected
- Joinee submits one bundled request

Message to jury:

```text
Instead of four or five separate tickets, the joinee submits one role-based access bundle.
```

### Moment 3: Governance Intelligence Catches Risk

Show one strong governance feature:
- Preferred: D3 privilege accumulation warning in chat
- Backup: D2 anomaly score on Teams card

Message to jury:

```text
The system is not only faster. It is safer and more auditable.
```

---

## 5. Recommended Team Ownership Split

Avoid assigning one person to each sequential phase only. Many phases depend on previous phases, which can block teammates. Instead, assign ownership by subsystem while still using phases as checkpoints.

Before Phase 0 starts, replace the owner labels below with real team member names. Unassigned ownership usually becomes unowned work.

| Owner | Area | Primary Phases | Responsibilities |
|------|------|----------------|------------------|
| Teammate A | Frontend experience | Phase 1, Phase 5, Phase 9, parts of Phase 13 | Three-panel UI, chat shell, template panel, status tracker, admin/audit UI surfaces |
| Teammate B | Agent, identity, and RAG | Phase 2, Phase 3, Phase 4, Phase 10, Phase 11, Phase 14 | ACF2 flow, Workday tool, role resolution, template retrieval, embedding script, D2 explanation, D3 warning, no-match template generation |
| Teammate C | Approval and provisioning backend | Phase 6, Phase 7, Phase 8 | Approval state machine, Teams cards, public callback URL, approve/reject endpoints, orchestrator, mock provisioning |
| Teammate D | Data, seeds, admin intelligence | Phase 0, Phase 12, Phase 13 | Schema, seed data, dangerous combinations, synthetic approval events, D1 scoring, audit dashboard data |

### Owner Name Mapping

Fill this before coding starts:

| Owner Label | Team Member Name | Final Area |
|-------------|------------------|------------|
| Teammate A | Unassigned | Frontend experience |
| Teammate B | Unassigned | Agent, identity, RAG, and embedding script |
| Teammate C | Unassigned | Approval and provisioning backend |
| Teammate D | Unassigned | Data, seeds, admin intelligence |

If the team has only three developers, combine Teammate D with Teammate C for backend/data ownership.

If the team has two developers, use this split:

| Owner | Area |
|------|------|
| Developer 1 | Frontend + user/demo flow |
| Developer 2 | Backend + agent + data + Teams integration |

---

## 6. Build Order

Use this order to keep everyone unblocked:

### Step 1: Lock Shared Contracts

Before anyone builds their phase, agree on these contracts:

```text
Session state shape
API endpoint names
Mock ACF2 users
Persona template JSON shape
Access request payload
Approval event payload
Teams callback URL format
Audit log event shape
```

This lets the frontend use mock responses while backend pieces are still being built.

### Step 2: Build Phase 0 Foundation Together

Everyone should participate in Phase 0 because it defines the shared ground:

- Local repo structure
- `.env.example`
- Database schema
- Seed users
- Mock APIs
- Persona templates
- Dangerous privilege combinations

Embedding ownership is split intentionally:

| Work | Owner | Output |
|------|-------|--------|
| Seed persona rows and access bundles | Teammate D | Seed SQL or seed script with persona metadata and access lists |
| Generate embeddings for seeded personas | Teammate B | Ollama-based `nomic-embed-text` script that writes vectors into `personas.embedding` |
| Verify pgvector retrieval works | Teammate B + Teammate D | `RIYA001` returns Backend Developer template as top match |

### Step 3: Parallel Build By Ownership

After Phase 0:

- Frontend owner builds UI using mocked JSON
- Agent/RAG owner builds identity and template retrieval
- Backend owner builds approval events and Teams callbacks
- Data owner validates seeds, audit log, and admin queries

### Step 4: Integrate In Thin Vertical Slices

Do not wait until every phase is complete. Integrate one small path at a time:

```text
RIYA001 identity lookup -> template display
Template submit -> approval_events rows
approval_events rows -> Teams card
Teams approve -> status panel update
PRIYA003 request -> D3 warning
JOHN002 request -> D2 score
```

---

## 7. Shared Contracts

### 7.1 Session State

```json
{
  "acf2_id": "RIYA001",
  "workday_context": {
    "name": "Riya Sharma",
    "team": "Payments Backend",
    "manager": "Anjali Singh",
    "dept": "Digital Engineering",
    "employment_type": "Full-time"
  },
  "resolved_role": {
    "role": "Backend Developer",
    "seniority": "Mid",
    "employment_type": "Full-time",
    "team": "Payments Backend"
  },
  "selected_template": {
    "id": "persona_backend_payments",
    "name": "Backend Developer - Payments",
    "mandatory_access": [],
    "optional_access": []
  },
  "final_bundle": [],
  "request_id": "uuid"
}
```

### 7.2 Mock ACF2 Users

| ACF2 ID | Demo Purpose |
--------|--------------|
| RIYA001 | Happy path: backend developer access bundle |
| JOHN002 | D2 anomaly score scenario |
| PRIYA003 | D3 privilege accumulation warning |
| SAM004 | No matching persona template scenario |

### 7.3 API Endpoints

```text
GET  /mock/workday/employee/:acf2_id
POST /api/agent/message
POST /api/templates/retrieve
POST /api/access-requests
GET  /api/access-requests/:request_id/status
POST /api/approve?request_id=&item=
POST /api/reject?request_id=&item=
POST /mock/servicenow/provision
POST /mock/jira/provision
POST /mock/ad/provision
POST /mock/sam/provision
```

### 7.4 Environment Variables

```env
BYPASS_AUTH=true
GEMINI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
SUPABASE_URL=
SUPABASE_ANON_KEY=
TEAMS_WEBHOOK_URL=
PUBLIC_BASE_URL=
```

`PUBLIC_BASE_URL` must point to ngrok or an equivalent public HTTPS tunnel during the Teams demo.

---

## 8. Local Collaboration Workflow

Because the project is local-first, keep the workflow simple:

1. Start from one agreed local baseline repo.
2. Each teammate works in their owned area using either a local feature branch or a copied working folder.
3. Commit at every phase checkpoint.
4. Before merging a teammate's work, run the exit criteria for that phase.
5. Update `ADR.md` when a structural decision changes.
6. Update `PHASES.md` when a phase is completed, cut, or moved.

Suggested branch names if the team wants branch isolation:

```text
feature/ui-shell
feature/identity-agent-rag
feature/approval-teams
feature/schema-audit-admin
```

Suggested commit style:

```text
feat(ui): add three-panel shell
feat(agent): add ACF2 identity lookup
feat(approval): create approval event state machine
feat(data): seed persona templates
docs(adr): record Teams callback URL decision
```

---

## 9. Cut Line If Time Runs Short

Protect the core demo first.

### Must Have

```text
ACF2 lookup
Persona template match
Bundled access request
Teams approval card
Approve/reject callback
Status/audit visibility
```

### Should Have

```text
D3 privilege accumulation warning
D2 anomaly score
```

### Cuttable

```text
D1 adaptive persona learning
SAM004 no-match template generation
Full routing table editor
Full admin ratification workflow
```

These cuttable items are still valuable, but they are not required to explain the core solution.

---

## 10. Demo Rehearsal Checklist

- [ ] `RIYA001` happy path works from ACF2 entry to Teams approval
- [ ] Teams card arrives live
- [ ] Teams approve button calls public `PUBLIC_BASE_URL`
- [ ] Status panel updates after approval
- [ ] `PRIYA003` triggers D3 privilege warning
- [ ] `JOHN002` shows D2 anomaly score if D2 is included
- [ ] Supabase is warmed up before demo
- [ ] Ollama model is pulled and tested locally
- [ ] Gemini API key is valid
- [ ] Teams channel is cleared before final demo
- [ ] Backup recording exists

---

## 11. One-Line Pitch

```text
We are turning access provisioning from scattered manual tickets into an AI-guided, persona-based, approval-routed, and fully auditable workflow.
```
