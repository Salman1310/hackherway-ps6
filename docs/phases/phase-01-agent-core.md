# Phase 1 — Agent Core + Identity Verification

## What Was Built

| Deliverable | Location | Purpose |
|-------------|----------|---------|
| Bedrock tool-use support | `backend/src/lib/bedrock.py` | `converse_with_tools()` — returns raw response for loop |
| Agent rewrite (tool-use loop) | `backend/src/agent/index.py` | Full rewrite: Bedrock → tool_use → MCP → loop → reply |
| SQL guard (agent-side) | `backend/src/agent/index.py` | Blocks non-SELECT before MCP call |
| Proper error logging | `backend/src/routes/agent.py` | Replaced `print()` with `log_error()` |

## Why It Was Built

Phase 0 left the agent using a JSON intent-classification approach (Bedrock returns JSON, agent parses, acts). This worked but was brittle (JSON parse failures, no tool-use, no DB querying).

Phase 1 replaces this with Bedrock's native **tool-use** (function calling) flow:
- Agent defines a `query_db` tool with schema
- Bedrock decides when to call it (e.g. when it sees an ACF2 ID)
- Agent executes, routes through MCP, feeds result back
- Bedrock generates the final human reply

This is more robust, more observable, and sets up the foundation for Phase 2 (Role Resolver) and Phase 4 (Risk Scorer) which need the same tool-use loop with more tools.

## How It Works

### Bedrock Tool-Use Loop

```
User message
    │
    ▼
messages = history + [user message]
    │
    ▼ (loop, max 6 iterations)
converse_with_tools(ACF2_SYSTEM_PROMPT, messages, TOOL_SPECS)
    │
    ├─ stopReason == "end_turn"  ──→ extract text → return reply
    │
    └─ stopReason == "tool_use"  ──→ for each toolUse block:
           │                            • log [BEDROCK] tool_call → query_db
           │                            • validate SQL (SELECT only)
           │                            • log [MCP] SQL: ...
           │                            • call mcp_server.sqlite_server.query_db(sql)
           │                            • log [MCP] N row(s) returned
           │                            • if users row returned → capture verified_user
           │
           └─ append tool_result messages → loop
```

### Identity Capture

When `query_db` returns a row containing `acf2_id` and `name`, the agent captures it as `verified_user`. On `end_turn`, if `verified_user` is set, the response includes a `session_update` dict:

```json
{
  "reply": "Hi Arun! ...",
  "session_update": {
    "acf2_id": "ARUN01",
    "workday_context": {
      "name": "Arun Mehta",
      "team": "Cloud Infrastructure",
      "manager": "Raj Kumar",
      "dept": "Technology",
      "employment_type": "Full-time"
    }
  }
}
```

The frontend stores this in session state. Subsequent messages see `session.acf2_id` set and skip to Phase 3+.

### SQL Guard

Two layers block dangerous SQL:

1. **Agent-side** (`_mcp_query_db`): checks `first_word != "SELECT"` before calling MCP. Logs `[ERROR]` and returns error JSON.
2. **MCP-side** (`sqlite_server.query_db`): same check — belt-and-suspenders.

### Tool Spec

```python
TOOL_SPECS = [{
    "toolSpec": {
        "name": "query_db",
        "description": "Execute a SELECT query against the hackherway SQLite database...",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {"sql": {"type": "string"}},
                "required": ["sql"]
            }
        }
    }
}]
```

## How to Test

### Exit Criteria

| Test | Input | Expected |
|------|-------|---------|
| Happy path | `ARUN01` | Greet "Arun", mention Cloud Infrastructure + Raj Kumar, ask about role |
| Hard block | `FAKE99` | "I wasn't able to verify..." + IT Help Desk message |
| Natural language | `"Yes my ID is ARUN01"` | Agent extracts, queries, greets by name |
| Backend logs | Any verified ID | `[BEDROCK] tool_call → query_db`, `[MCP] SQL: SELECT...`, `[MCP] 1 row(s) returned` |

### Log output (ARUN01)

```
[AGENT]   Message received (len=6)
[BEDROCK] Converse call #1 (messages=1)
[BEDROCK] stopReason=tool_use, blocks=1
[BEDROCK] tool_call → query_db
[MCP]     SQL: SELECT * FROM users WHERE acf2_id = 'ARUN01'
[MCP]     1 row(s) returned
[AGENT]   Identity verified: Arun Mehta (ARUN01) — Cloud Infrastructure
[BEDROCK] Converse call #2 (messages=3)
[BEDROCK] stopReason=end_turn, blocks=1
[AGENT]   Session update: acf2_id=ARUN01
```

### Log output (FAKE99)

```
[AGENT]   Message received (len=6)
[BEDROCK] Converse call #1 (messages=1)
[BEDROCK] stopReason=tool_use, blocks=1
[BEDROCK] tool_call → query_db
[MCP]     SQL: SELECT * FROM users WHERE acf2_id = 'FAKE99'
[MCP]     0 row(s) returned
[BEDROCK] Converse call #2 (messages=3)
[BEDROCK] stopReason=end_turn, blocks=1
```

## Decisions Made

- **Import MCP tool function directly** — `from mcp_server.sqlite_server import query_db` — rather than spawning a subprocess via the MCP stdio client. Rationale: same validation logic, same SQLite path, observable via [MCP] logs. MCP stdio protocol adds subprocess overhead without benefit for a hackathon demo running all services locally.
- **`verified_user` captured in loop, not parsed from LLM text** — more reliable than parsing Bedrock's prose response. The DB row is the source of truth.
- **Max 6 iterations** — identity verification needs 2 Bedrock calls (tool_use + end_turn). 6 gives 3× headroom for future tools added to the same phase.
- **temperature=0.3 for tool-use calls** — lower temperature means the LLM is more deterministic when generating SQL and deciding to call tools. The original `converse()` keeps 0.7 for prose.
