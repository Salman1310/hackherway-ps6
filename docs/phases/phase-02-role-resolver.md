# Phase 2 - Role Resolver + Template Matching

## Status

Done.

Phase 2 is built on top of the Phase 0B normalized schema. It resolves a verified user's role, queries the normalized designation catalog, returns a selected access template, and renders that template in the frontend right panel.

Phase 2 does not submit access requests. Submission starts in Phase 3.

## Goal

After identity verification, the user describes their role. The agent asks for clarification when needed, queries `designations` and `role_access_items`, selects the best access template, updates session state, and lets the frontend render the result.

## What Was Built

| Deliverable | Location | Notes |
|-------------|----------|-------|
| Role phase handler | `backend/src/agent/index.py` | Continues after `session.acf2_id` is set |
| Role resolver prompt | `backend/src/agent/index.py` | Uses normalized schema and forbids full catalog context stuffing |
| Tool-query matching loop | `backend/src/agent/index.py` | Lets Bedrock query `designations` and `role_access_items` through `query_db` |
| Selected template shaping | `backend/src/agent/index.py` | Builds `resolved_role`, `selected_template`, and mandatory `final_bundle` |
| Role mapping write | `backend/src/agent/index.py` | Upserts confident matches into `user_designations` through MCP `execute_db` |
| Frontend type contract | `frontend/src/lib/types.ts` | Adds Phase 2 fields for confidence, reasoning, owner team, and catalog IDs |
| Right-panel renderer | `frontend/src/components/layout/RightPanel.tsx` | Renders backend-selected template only; no Phase 3 toggles or submit |
| Regression tests | `backend/tests/test_phase2_role_resolver.py` | Covers prompt rules, direct match, vague input, and no-match response |

## How It Works

```text
User is verified in Phase 1
  -> user describes role
  -> backend calls Bedrock with Phase 2 role prompt
  -> Bedrock uses query_db for candidate designations
  -> Bedrock uses query_db for role_access_items
  -> backend captures returned rows
  -> backend shapes selected_template
  -> backend upserts user_designations for confident matches
  -> frontend renders selected_template in the right panel
```

The frontend does not choose templates, compute confidence, call Bedrock, or query SQLite. It only renders the structured data returned by the backend.

## Structured Session Update

```json
{
  "resolved_role": {
    "role": "Backend Developer",
    "designation_id": "backend_developer",
    "seniority": "Not specified",
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
    "reasoning": "I matched your role to Backend Developer.",
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
  },
  "final_bundle": []
}
```

For Phase 2, `final_bundle` is initialized to mandatory access only. Optional selection and submission are Phase 3.

## Behavior

| Scenario | Expected |
|----------|----------|
| Existing verified user enters another ACF2 ID | Identity remains locked; user is asked to reset chat |
| Clear role input | Agent queries templates and returns a selected template |
| Vague role input | Agent asks one focused clarification question and does not update template state |
| No suitable match | Agent says the role could not be matched yet; no template update is returned |
| Bedrock outage | Backend returns explicit Bedrock-unavailable message |

## Out Of Scope For Phase 2

- Access request submission
- Mandatory/optional toggling behavior
- Teams approval routing
- ServiceNow RITM creation
- Risk scoring
- Privilege Guard
- Admin ratification dashboard

## How To Verify

Backend:

```bash
cd backend
python -m unittest discover -s tests
python -m compileall src mcp_server scripts tests
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Seed:

```bash
cd backend
python scripts/seed_sqlite.py
```

## Decisions Made

- Phase 2 uses Bedrock reasoning plus tool-use queries over normalized SQLite tables.
- No RAG, embeddings, pgvector, Ollama, Supabase, or context-stuffed template catalog.
- The frontend remains a renderer of backend-selected data.
- `user_designations` is updated only when a selected template was built from returned role/access rows.
- No-match/admin ratification remains Phase 6.
