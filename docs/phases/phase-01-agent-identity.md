# Phase 1 - Agent Core + Identity Verification

## What Was Built

| Deliverable | Location | Purpose |
|-------------|----------|---------|
| FastAPI message endpoint | `backend/src/routes/agent.py` | Accepts `POST /api/agent/message` and returns an agent reply |
| Frontend proxy | `frontend/src/app/api/agent/message/route.ts` | Forwards chat requests to FastAPI with no business logic |
| Chat hook integration | `frontend/src/hooks/useChat.ts` | Sends messages, displays replies, and merges session updates |
| Bedrock tool-use support | `backend/src/lib/bedrock.py` | `converse_with_tools()` returns raw Converse responses for the loop |
| Agent tool-use loop | `backend/src/agent/index.py` | Sends user input to Bedrock, executes tool calls, feeds results back, and returns final text |
| `query_db` tool definition | `backend/src/agent/index.py` | Lets Bedrock request read-only SQLite lookups through MCP |
| SQL guard | `backend/src/agent/index.py`, `backend/mcp_server/sqlite_server.py` | Blocks non-SELECT statements before and inside MCP query execution |
| Identity session update | `backend/src/agent/index.py` | Captures verified user rows and returns `acf2_id` plus Workday-style context |
| ACF2 clarification handling | `backend/src/agent/index.py` | Lets Bedrock explain ACF2 naturally without querying the database |
| Plain-text reply cleanup | `backend/src/agent/index.py` | Removes leaked Markdown bold markers from model replies |
| Locked identity guard | `backend/src/agent/index.py` | Prevents a verified session from switching to a different ACF2 ID mid-chat |
| Reset chat control | `frontend/src/contexts/SessionContext.tsx`, `frontend/src/components/layout/ChatPanel.tsx` | Clears session state and restarts the chat intentionally |
| Bedrock-down fallback | `backend/src/agent/index.py` | Tells the user when Bedrock is unavailable instead of returning a static explanation |
| Windows-safe logging | `backend/src/lib/logger.py` | Prevents Unicode log characters from crashing Windows console output |
| Regression tests | `backend/tests/` | Covers logger encoding, ACF2 clarification prompt rules, plain-text cleanup, locked identity, and Bedrock-down fallback |

## Why It Was Built

Phase 1 gives the chat experience its first real backend-owned capability: identity verification.

The previous identity flow was simpler and closer to intent parsing. The current implementation uses Bedrock's native tool-use flow so the model can decide when to call `query_db`, the backend can validate and execute the SQL through the SQLite MCP layer, and the model can then write the final user-facing reply.

This keeps the frontend thin, keeps database access in the backend, and creates the same tool-use pattern future phases can extend for role resolution, privilege checks, risk scoring, request submission, and status tracking.

## How It Works

### Request Flow

```text
User enters message
  -> frontend chat hook
  -> Next.js proxy route
  -> FastAPI /api/agent/message
  -> agent builds Bedrock conversation history
  -> Bedrock either replies directly or requests query_db
  -> backend validates SQL and calls SQLite MCP query_db
  -> tool result is sent back to Bedrock
  -> final reply returns to chat
```

### Bedrock Tool-Use Loop

```text
User message
  -> messages = history + current user message
  -> converse_with_tools(ACF2_SYSTEM_PROMPT, messages, TOOL_SPECS)

If stopReason == "tool_use":
  -> log [BEDROCK] tool_call
  -> validate SELECT-only SQL
  -> log [MCP] SQL
  -> call mcp_server.sqlite_server.query_db(sql)
  -> log row count
  -> capture verified user if a users row is returned
  -> append toolResult
  -> call Bedrock again

If stopReason == "end_turn":
  -> extract final text
  -> include session_update if identity was verified
  -> return response to frontend
```

The loop is capped at 6 iterations. Normal identity verification should take 2 Bedrock calls: one tool request and one final answer.

### Identity Verification

When the user provides an ACF2 ID, Bedrock should call:

```sql
SELECT * FROM users WHERE acf2_id = 'ARUN01'
```

If a row is returned, the agent greets the user by name, mentions team and manager, asks for the user's role, and sends a session update:

```json
{
  "session_update": {
    "acf2_id": "ARUN01",
    "workday_context": {
      "name": "Arun Mehta",
      "team": "Cloud Infrastructure",
      "manager": "Raj Kumar",
      "dept": "Technology",
      "employment_type": "full-time"
    }
  }
}
```

If no row is returned, the agent hard-blocks the flow and asks the user to double-check the ID or contact the IT Help Desk. It does not update session state.

### ACF2 Clarification

If the user asks what an ACF2 ID is, says they do not know it, or asks where to find it, the system prompt tells Bedrock to answer naturally in its own words, not call `query_db`, avoid example IDs or other people's IDs, and then ask for the ACF2 ID again.

If Bedrock is unavailable, the backend returns an explicit service fallback:

```text
Bedrock is currently unavailable, so I can't generate a live answer right now. Please try again in a moment.
```

### SQL Safety

There are two SELECT-only guards:

1. Agent side: `_mcp_query_db()` rejects any query whose first word is not `SELECT`.
2. MCP side: `sqlite_server.query_db()` performs the same check before touching SQLite.

This keeps Phase 1 identity verification read-only. Write tools are reserved for later phases.

### Locked Identity and Reset

After `session.acf2_id` is set, identity is locked for that chat session. If the user enters another ACF2-looking value, the backend does not call Bedrock or query the database again. It tells the user they are already verified and asks them to reset the chat if they need to start over.

The chat header includes a reset icon button. Reset clears the React session, clears the message history, stops any loading state, and shows the initial welcome message again.

## API Contract

Request:

```json
{
  "content": "Yes my ID is ARUN01",
  "session": {
    "acf2_id": null,
    "workday_context": null,
    "resolved_role": null,
    "selected_template": null,
    "final_bundle": [],
    "request_id": null
  },
  "history": []
}
```

Response for verified identity:

```json
{
  "reply": "Hi Arun, I can see you're joining the Cloud Infrastructure team under Raj Kumar. What will your role be?",
  "session_update": {
    "acf2_id": "ARUN01",
    "workday_context": {
      "name": "Arun Mehta",
      "team": "Cloud Infrastructure",
      "manager": "Raj Kumar",
      "dept": "Technology",
      "employment_type": "full-time"
    }
  }
}
```

Response for unknown identity:

```json
{
  "reply": "I wasn't able to verify your identity with that ACF2 ID. Please double-check or contact the IT Help Desk.",
  "session_update": null
}
```

## How to Test

From `backend/`:

```bash
python scripts/seed_sqlite.py
python -m unittest discover -s tests
uvicorn src.main:app --reload --port 8000
```

From `frontend/`:

```bash
npm run lint
npm run build
npm run dev
```

Manual chat checks:

| Input | Expected |
|-------|----------|
| `ARUN01` | Greets Arun, mentions Cloud Infrastructure and Raj Kumar, asks for role |
| `Yes my ID is ARUN01` | Extracts and verifies ARUN01 from natural language |
| `FAKE99` | Hard-blocks identity verification and does not update session |
| `I don't know what ACF2 ID is` | Bedrock explains ACF2 naturally without sample IDs, does not query DB, asks for the ID again |
| Enter another ACF2 ID after ARUN01 is verified | Keeps the existing identity locked and asks the user to reset the chat |
| Click the reset icon | Clears the session and returns to the initial welcome prompt |

Expected backend logs for verified identity:

```text
[AGENT]   Message received (len=6)
[BEDROCK] Converse call #1 (messages=1)
[BEDROCK] stopReason=tool_use, blocks=1
[BEDROCK] tool_call -> query_db
[MCP]     SQL: SELECT * FROM users WHERE acf2_id = 'ARUN01'
[MCP]     1 row(s) returned
[AGENT]   Identity verified: Arun Mehta (ARUN01) - Cloud Infrastructure
[BEDROCK] Converse call #2 (messages=3)
[BEDROCK] stopReason=end_turn, blocks=1
[AGENT]   Session update: acf2_id=ARUN01
```

## Decisions Made

- The frontend proxy remains business-logic free.
- Bedrock is the only LLM path for normal conversational answers.
- SQLite reads for the agent go through the MCP query tool path, not direct `sqlite3`.
- The MCP function is imported directly instead of launching a separate stdio subprocess for each local demo request.
- Verified identity is captured from the database row, not parsed from Bedrock prose.
- Unknown IDs are hard-blocked.
- ACF2-help questions stay dynamic through Bedrock, but must not include sample IDs or other people's IDs.
- Model replies are normalized to plain text before returning to the chat UI.
- Verified identity is immutable until the user intentionally resets the chat.
- Bedrock outages are disclosed clearly to the user.
