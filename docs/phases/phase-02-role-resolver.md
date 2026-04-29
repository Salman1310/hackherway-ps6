# Phase 02 - Role Resolver + Template Matching

## Status

Planned next phase for the current FastAPI + SQLite MCP architecture.

## Goal

After identity verification, the user describes their role. The agent resolves role details, selects the best access template from seeded designation data, and returns structured data that the frontend can render in the right panel.

## Planned Work

| Task | Owner Module | Notes |
|---|---|---|
| Extend agent state machine | `backend/src/agent/index.py` | Move from identity-only flow to role resolution |
| Add designation seed data | `backend/scripts/seed_sqlite.py` or dedicated seed module | Include 5-8 role templates |
| Add SQLite MCP query tool | `backend/src/lib` / MCP wrapper | Agent should read templates and request state through MCP |
| Inject templates into prompt | `backend/src/agent/index.py` | Context stuffing, no vector search |
| Return structured match payload | `backend/src/routes/agent.py` response model | Include template, confidence, reasoning, and top-3 options when needed |
| Render template panel | `frontend/src/components/layout/RightPanel.tsx` | Only consume backend response data; no matching logic in frontend |

## Target Flow

```text
ARUN01 verified
  -> user says "backend developer" or similar
  -> agent asks targeted follow-up questions if needed
  -> role, seniority, and employment type are resolved
  -> agent compares against all designation templates in context
  -> backend returns selected_template / top_matches
  -> frontend renders template choices
```

## Matching Rules

| Confidence | Behavior |
|---|---|
| `> 0.95` | Serve one expanded template |
| `0.70 - 0.95` | Return top 3 choices |
| `< 0.70` | Mark `no_match: true`; Phase 6 will create a draft template |

## How To Test When Built

| Scenario | Expected |
|---|---|
| `ARUN01` then `I am a backend developer` | Backend Developer or nearest Cloud/Technology template selected |
| vague role such as `I do backend stuff` | Agent asks clarifying questions |
| nonsense input | Agent re-prompts without crashing |
| no matching role for `SARA03` | `no_match: true` returned |

## Decisions Made

- Template matching stays in the backend agent.
- The frontend renders data only.
- No MongoDB, Supabase, pgvector, or embeddings are part of this phase.
