"""
Access Agent — HackHERway PS6
Phase 1: Identity Verification via Bedrock tool-use loop

Flow:
  User message → Bedrock (tool-use) → query_db → SQLite MCP → result → Bedrock → reply

The agent uses Bedrock's Converse API with tool definitions.
Bedrock generates SQL, the agent routes it through the SQLite MCP server,
and the result is fed back to Bedrock until it produces a final text reply.
"""

import json
from typing import List, Optional

from ..lib.bedrock import converse_with_tools
from ..lib.logger import agent as log_agent, bedrock as log_bedrock, mcp as log_mcp, error as log_error
from ..types import SessionState, ChatMessage

# ── Tool definitions (Bedrock toolSpec format) ────────────────────────────────

TOOL_SPECS = [
    {
        "toolSpec": {
            "name": "query_db",
            "description": (
                "Execute a SELECT query against the hackherway SQLite database. "
                "Use this to look up employee records, designations, approval history, "
                "privilege edges, dangerous combinations, etc.\n\n"
                "Key tables:\n"
                "  users(acf2_id, name, team, manager, dept, employment_type)\n"
                "  designations(id, title, mandatory_items JSON, optional_items JSON)\n"
                "  privilege_edges(acf2_id, access_item, granted_by, granted_at)\n"
                "  dangerous_combinations(id, item_a, item_b, severity, reason)\n"
                "  approval_events(id, acf2_id, access_item, status, approved_at, off_hours)\n\n"
                "ACF2 IDs are always UPPERCASE (e.g. ARUN01, NEHA02, SARA03)."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": (
                                "A valid SQL SELECT statement. "
                                "Embed literal values directly — no ? placeholders.\n"
                                "Example: SELECT * FROM users WHERE acf2_id = 'ARUN01'"
                            ),
                        }
                    },
                    "required": ["sql"],
                }
            },
        }
    }
]

# ── System prompt ─────────────────────────────────────────────────────────────

ACF2_SYSTEM_PROMPT = """\
You are an AI access request assistant for Sun Life Financial.
You are warm, professional, and concise — like a helpful IT colleague.

## Your current goal
Verify the employee's identity using their ACF2 ID before proceeding.

## What is an ACF2 ID?
ACF2 is Sun Life's identity and access management system.
Every employee has a unique ACF2 ID — letters followed by numbers (e.g. ARUN01, NEHA02).
Employees can find it in: their welcome email from HR, their employee badge,
or by calling the IT Help Desk.

## How to verify identity
When the user provides something that looks like an ACF2 ID:
1. Call query_db with: SELECT * FROM users WHERE acf2_id = 'THE_ID_UPPERCASED'
2. If a row is returned → greet them by first name, mention their team and manager,
   then ask: "What will your role be?" (to resolve their designation in the next step)
3. If no rows returned → tell them you could not verify that ID and suggest
   they double-check or contact the IT Help Desk. Do NOT guess or make up data.

## Tone rules
- Max 2–3 sentences per reply.
- Never reveal raw SQL or database details to the user.
- Never invent employee data — only use what the database returns.
- If the message has nothing to do with access requests, gently redirect.
"""

FALLBACK_REPLY = (
    "I wasn't able to process that request. Please try again or contact the IT Help Desk."
)

HARD_BLOCK = (
    "I wasn't able to verify your identity with that ACF2 ID. "
    "Please double-check and try again, or contact your IT Help Desk if the issue persists."
)

MAX_TOOL_ITERATIONS = 6  # safety cap on tool-use loop


# ── Public entry point ────────────────────────────────────────────────────────

def handle_agent_message(
    content: str, session: SessionState, history: List[ChatMessage]
) -> dict:
    if not session.acf2_id:
        return _handle_acf2_phase(content, history)

    # Phase 3+ placeholder — extended in future phases
    return {
        "reply": (
            "Identity confirmed! Next I'll identify the right access template for your role "
            "— give me just a moment."
        )
    }


# ── ACF2 phase ────────────────────────────────────────────────────────────────

def _build_bedrock_history(history: List[ChatMessage]) -> List[dict]:
    """Convert chat history to Bedrock message format. Skip leading bot messages."""
    found_user = False
    filtered = []
    for msg in history:
        if msg.role == "user":
            found_user = True
        if found_user:
            filtered.append(msg)
    return [
        {
            "role": "assistant" if m.role == "bot" else "user",
            "content": [{"text": m.content}],
        }
        for m in filtered
    ]


def _handle_acf2_phase(content: str, history: List[ChatMessage]) -> dict:
    log_agent(f"Message received (len={len(content)})")

    messages = _build_bedrock_history(history)
    messages.append({"role": "user", "content": [{"text": content}]})

    verified_user: Optional[dict] = None

    for iteration in range(MAX_TOOL_ITERATIONS):
        log_bedrock(f"Converse call #{iteration + 1} (messages={len(messages)})")

        try:
            response = converse_with_tools(
                ACF2_SYSTEM_PROMPT, messages, TOOL_SPECS, max_tokens=512
            )
        except Exception as exc:
            log_error(f"Bedrock call failed: {exc}")
            return {"reply": FALLBACK_REPLY}

        stop_reason = response.get("stopReason", "")
        output_msg = response.get("output", {}).get("message", {})
        content_blocks = output_msg.get("content", [])

        log_bedrock(f"stopReason={stop_reason}, blocks={len(content_blocks)}")

        # ── Final text reply ──────────────────────────────────────────────────
        if stop_reason == "end_turn":
            reply_text = ""
            for block in content_blocks:
                if "text" in block:
                    reply_text = block["text"]
                    break

            result: dict = {"reply": reply_text or FALLBACK_REPLY}
            if verified_user:
                result["session_update"] = {
                    "acf2_id": verified_user["acf2_id"],
                    "workday_context": {
                        "name": verified_user["name"],
                        "team": verified_user["team"],
                        "manager": verified_user["manager"],
                        "dept": verified_user["dept"],
                        "employment_type": verified_user["employment_type"],
                    },
                }
                log_agent(f"Session update: acf2_id={verified_user['acf2_id']}")
            return result

        # ── Tool use ──────────────────────────────────────────────────────────
        if stop_reason == "tool_use":
            # Append assistant's tool-use message to history
            messages.append({"role": "assistant", "content": content_blocks})

            tool_results = []
            for block in content_blocks:
                if "toolUse" not in block:
                    continue

                tool_name = block["toolUse"]["name"]
                tool_input = block["toolUse"]["input"]
                tool_use_id = block["toolUse"]["toolUseId"]

                log_bedrock(f"tool_call → {tool_name}")

                result_text = _execute_tool(tool_name, tool_input)

                # Capture verified user from first successful users query
                if tool_name == "query_db" and verified_user is None:
                    try:
                        rows = json.loads(result_text)
                        if isinstance(rows, list) and len(rows) > 0:
                            first = rows[0]
                            if "acf2_id" in first and "name" in first:
                                verified_user = first
                                log_agent(
                                    f"Identity verified: {first['name']} "
                                    f"({first['acf2_id']}) — {first.get('team', '')}"
                                )
                    except Exception:
                        pass

                tool_results.append({
                    "toolResult": {
                        "toolUseId": tool_use_id,
                        "content": [{"text": result_text}],
                    }
                })

            # Append tool results as a user message (Bedrock protocol)
            messages.append({"role": "user", "content": tool_results})
            continue

        # Unexpected stop reason (e.g. max_tokens, guardrails)
        log_error(f"Unexpected stopReason: {stop_reason}")
        break

    return {"reply": FALLBACK_REPLY}


# ── Tool execution ────────────────────────────────────────────────────────────

def _execute_tool(name: str, tool_input: dict) -> str:
    """Route Bedrock tool-use requests to the appropriate MCP server tool."""
    if name == "query_db":
        return _mcp_query_db(tool_input.get("sql", ""))

    log_error(f"Unknown tool requested: {name}")
    return json.dumps({"error": f"Unknown tool: {name}"})


def _mcp_query_db(sql: str) -> str:
    """
    Validate and execute a SELECT query via the SQLite MCP server.

    Blocks non-SELECT statements before they reach the MCP layer.
    Logs every query and result count for observability.
    """
    sql = sql.strip()

    # Agent-side SQL guard (belt-and-suspenders — MCP server also validates)
    first_word = sql.split()[0].upper() if sql else ""
    if first_word != "SELECT":
        log_error(f"Blocked non-SELECT SQL from agent: {sql[:80]}")
        return json.dumps({"error": "Only SELECT statements are permitted via query_db"})

    log_mcp(f"SQL: {sql}")

    try:
        # Call through MCP server tool (no direct sqlite3 in agent code)
        from mcp_server.sqlite_server import query_db as mcp_query_db
        result = mcp_query_db(sql)
    except Exception as exc:
        log_error(f"MCP query_db failed: {exc}")
        return json.dumps({"error": str(exc)})

    # Log row count for observability
    try:
        parsed = json.loads(result)
        row_count = len(parsed) if isinstance(parsed, list) else "?"
        log_mcp(f"{row_count} row(s) returned")
    except Exception:
        log_mcp("Result received (unparseable)")

    return result
