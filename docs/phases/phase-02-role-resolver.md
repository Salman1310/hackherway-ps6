# Phase 2 - Role Resolver + Template Matching

## Status

Planned. Do not start Phase 2 until Phase 0B normalized schema rework is complete.

Phase 2 depends on these Phase 0B tables:

```text
designations
role_access_items
user_designations
```

## Goal

After identity verification, the user describes their role. The agent resolves the role details, queries the normalized designation catalog, selects the best access template, and returns structured template data that the frontend can render in the right panel.

Phase 2 should not submit access requests. Submission starts in Phase 3.

## What Changes From Phase 1

Phase 1 ends after identity is locked and the agent asks for the user's role.

Phase 2 adds:

- role clarification after identity verification
- designation/template lookup through `query_db`
- structured selected-template response data
- session updates for `resolved_role` and `selected_template`
- optional write to `user_designations` when the role is confidently resolved

## Data Model Assumption

Phase 2 assumes this normalized shape:

```text
designations(id, title, description, team_hint, dept_hint)
role_access_items(id, designation_id, access_item, display_name, system, description, mandatory, owner_team, servicenow_catalog_item_id, sort_order)
user_designations(acf2_id, designation_id, assigned_at, source)
```

Do not rely on `designations.mandatory_items` or `designations.optional_items`. Those JSON columns belong to the Phase 0A schema and should be removed in Phase 0B.

## Matching Strategy

Use Bedrock reasoning plus tool-use queries over SQLite. Do not context-stuff all templates into the system prompt.

The agent should:

1. Use the locked `session.acf2_id` and `session.workday_context`.
2. Ask clarifying questions if role, seniority, employment type, team, or department is unclear.
3. Query `designations` for candidate roles.
4. Query `role_access_items` for the candidate roles.
5. Choose the best match using role text, seniority, employment type, team, department, and available access items.
6. Return structured data for the frontend.

This keeps the prompt smaller and makes access item rows available to Phase 3 without JSON parsing.

## Planned Work

| Task | Owner Module | Notes |
|------|--------------|-------|
| Extend agent state handling | `backend/src/agent/index.py` | Continue after identity instead of returning the Phase 1 placeholder |
| Update tool schema awareness | `backend/src/agent/index.py` | Add `user_designations` and `role_access_items` to tool descriptions |
| Add role-resolution prompt rules | `backend/src/agent/index.py` | Ask focused follow-ups for vague role input |
| Query designation catalog | `query_db` tool | Read `designations` and candidate `role_access_items` rows |
| Add optional write tool path | `execute_db` tool or constrained backend helper | Write confirmed matches to `user_designations` only after confidence threshold is met |
| Extend response model | `backend/src/types.py` | Return structured template data in `session_update` |
| Render backend-selected template | `frontend/src/components/layout/RightPanel.tsx` | Frontend renders data only; no matching logic |
| Add regression tests | `backend/tests/` | Cover direct match, vague role clarification, no-match, and gibberish input |

## Target Flow

```text
ARUN01 verified
  -> user says "I am a backend developer"
  -> agent resolves role details
  -> agent queries designations and role_access_items
  -> agent selects the best template
  -> backend returns selected_template and resolved_role
  -> frontend renders the selected template in the right panel
```

For vague input:

```text
ARUN01 verified
  -> user says "I do backend stuff"
  -> agent asks a focused follow-up
  -> user answers
  -> agent resolves and matches
```

## Confidence Rules

| Confidence | Behavior |
|------------|----------|
| `> 0.95` | Return one selected template |
| `0.70 - 0.95` | Return top 3 candidate templates for user selection |
| `< 0.70` | Return `no_match: true`; do not write `user_designations` |

When confidence is high enough and the user confirms the match, write:

```text
user_designations(acf2_id, designation_id, assigned_at, source='agent_resolved')
```

For SARA03 or any unclear role with low confidence, do not write `user_designations`.

## Structured Response Shape

The backend should update session state with data shaped like:

```json
{
  "resolved_role": {
    "role": "Backend Developer",
    "seniority": "Junior",
    "employment_type": "full-time",
    "team": "Cloud Infrastructure"
  },
  "selected_template": {
    "id": "backend_developer",
    "name": "Backend Developer",
    "confidence": 0.93,
    "reasoning": "The role description maps to backend service development in the Technology department.",
    "mandatory_access": [
      {
        "id": "github_repo_access",
        "name": "GitHub repository access",
        "system": "GitHub",
        "reason": "Required for source code work",
        "mandatory": true
      }
    ],
    "optional_access": []
  }
}
```

The frontend should not calculate confidence or choose templates. It should render the backend response.

## Out Of Scope For Phase 2

- Access request submission
- Mandatory/optional toggling behavior
- Teams approval routing
- ServiceNow RITM creation
- Risk scoring
- Privilege Guard
- Admin ratification dashboard

## How To Test When Built

| Scenario | Expected |
|----------|----------|
| `ARUN01` then `I am a backend developer` | Backend returns a relevant template with confidence and reasoning |
| `ARUN01` then `I do backend stuff` | Agent asks a clarifying question before matching |
| `ARUN01` then gibberish | Agent asks the user to clarify without crashing |
| `SARA03` with a role that has no suitable template | Backend returns `no_match: true` and does not write `user_designations` |
| Existing verified user enters another ACF2 ID | Phase 1 identity lock remains active; Phase 2 does not switch identity |

Verification commands:

```bash
cd backend
python -m unittest discover -s tests
```

If frontend rendering changes:

```bash
cd frontend
npm run lint
npm run build
```

## Decisions Made

- Phase 2 uses tool-query matching over normalized SQLite tables.
- No RAG, embeddings, pgvector, Ollama, Supabase, or context-stuffed template catalog.
- The frontend remains a renderer of backend-selected data.
- `user_designations` is updated only after a confident/confirmed match.
- No-match handling is marked in Phase 2 but admin ratification remains Phase 6.
