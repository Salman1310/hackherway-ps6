# Phase 3 - Template UI + Submission Flow

## Status

Done.

## Goal

After role resolution, the agent negotiates optional access items with the user, confirms the final bundle, and submits the access request to the database. The right panel already renders the selected template from Phase 2. Phase 3 adds the conversational submission loop.

## What Was Built

| Deliverable | Location | Notes |
|-------------|----------|-------|
| `SUBMISSION_TOOL_SPECS` | `backend/src/agent/index.py` | query_db + execute_db available to Bedrock during submission phase |
| `_build_submission_prompt()` | `backend/src/agent/index.py` | Dynamic system prompt with employee context, template name, mandatory items, optional items, pre-generated request_id, and INSERT SQL template |
| `_handle_submission_phase()` | `backend/src/agent/index.py` | Tool-use loop for optional negotiation and submission; detects execute_db success; returns session_update with final_bundle and request_id |
| Routing update | `backend/src/agent/index.py` | `handle_agent_message()` routes to submission phase when `session.selected_template` is set |
| `execute_db` routing | `backend/src/agent/index.py` | `_execute_tool()` now handles both `query_db` and `execute_db` tool names |
| Phase 3 tests | `backend/tests/test_agent_submission.py` | 9 tests: routing, submission detection, prompt content, Bedrock fallback |

## How It Works

### Routing

```
handle_agent_message()
  ├── no acf2_id          → _handle_acf2_phase()     [Phase 1]
  ├── acf2_id + ACF2 msg  → identity lock reply
  ├── selected_template   → _handle_submission_phase() [Phase 3]
  └── else                → _handle_role_phase()      [Phase 2]
```

### Submission Loop

1. `request_id = uuid.uuid4()` and `current_ts = int(time.time())` generated at call start.
2. `_build_submission_prompt()` builds system prompt including the exact INSERT SQL with the pre-generated request_id.
3. Bedrock tool-use loop runs with `SUBMISSION_TOOL_SPECS` (query_db + execute_db).
4. On each `execute_db` call: if SQL targets `access_requests` table and contains the pre-generated request_id, and the MCP result is `{"success": true}`, `request_submitted = True`.
5. On `end_turn` with `request_submitted == True`: returns `session_update` with `final_bundle` (mandatory access items from selected_template) and `request_id`.
6. On `end_turn` with `request_submitted == False`: returns reply only (still negotiating or no submission yet).

### Conversation Flow (demo path)

```
User: "I want to submit my access request"
Agent: lists optional items, asks which to include
User: "Add pagerduty"
Agent: confirms final bundle, asks "Ready to submit?"
User: "Yes"
Agent: calls execute_db → INSERT INTO access_requests
Agent: "Your request has been submitted. Approvals will be routed shortly."
→ session_update: { final_bundle: [...mandatory items...], request_id: "uuid" }
```

### access_requests Record

```sql
INSERT INTO access_requests
  (id, acf2_id, designation_id, final_bundle, status, created_at)
VALUES
  ('<uuid>', 'ARUN01', 'devops_cloud_engineer', '[...]', 'pending', <unix_ts>)
```

`final_bundle` stored as JSON array of access_item IDs (mandatory + chosen optional).

## How To Test

```bash
cd backend
python -m unittest discover -s tests
```

Manual verification:
1. Run `python scripts/seed_sqlite.py`
2. Start backend: `uvicorn src.main:app --reload --port 8000`
3. ARUN01 → identity verified → role resolved → template in right panel
4. Send "I want to submit my request" → agent lists optional items
5. Confirm and submit → request_id returned
6. Verify DB: `SELECT * FROM access_requests WHERE acf2_id = 'ARUN01'`

## Decisions Made

- **Submission via chat only**: frozen frontend has no submit button; all interaction goes through `POST /api/agent/message`.
- **request_id pre-generated in Python**: UUID created before Bedrock loop so detection is reliable (search for exact UUID in execute_db SQL).
- **final_bundle in session_update**: returns mandatory items from selected_template; DB record may have additional optional items chosen in conversation.
- **execute_db not exposed in Phase 1/2 tool specs**: only available in `SUBMISSION_TOOL_SPECS` to limit write surface during earlier phases.
- **No new FastAPI routes**: Phase 3 is entirely agent-side; frontend proxy unchanged.
