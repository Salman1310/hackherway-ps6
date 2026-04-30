"""
Access Agent - HackHERway PS6
Phase 1: Identity verification via Bedrock tool-use loop.

Flow:
  User message -> Bedrock tool-use -> query_db -> SQLite MCP -> result -> Bedrock -> reply
"""

import json
import re
import time
from typing import List, Optional

from ..lib.bedrock import converse_with_tools
from ..lib.logger import agent as log_agent, bedrock as log_bedrock, mcp as log_mcp, error as log_error
from ..types import SessionState, ChatMessage


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
                "  user_designations(acf2_id, designation_id, assigned_at, source)\n"
                "  designations(id, title, description, team_hint, dept_hint)\n"
                "  role_access_items(id, designation_id, access_item, display_name, "
                "system, description, mandatory, owner_team, servicenow_catalog_item_id, sort_order)\n"
                "  privilege_edges(acf2_id, access_item, granted_by, granted_at)\n"
                "  dangerous_combinations(id, access_item_a, access_item_b, severity, reason)\n"
                "  approval_events(id, acf2_id, access_item, status, submitted_at, resolved_at, off_hours)\n\n"
                "ACF2 IDs are always uppercase letters followed by numbers."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": (
                                "A valid SQL SELECT statement. Embed literal values directly; "
                                "do not use placeholders. Query the users table by acf2_id when "
                                "verifying identity."
                            ),
                        }
                    },
                    "required": ["sql"],
                }
            },
        }
    }
]


ACF2_SYSTEM_PROMPT = """\
You are an AI access request assistant for Sun Life Financial.
You are warm, professional, and concise, like a helpful IT colleague.

## Your current goal
Verify the employee's identity using their ACF2 ID before proceeding.

## What is an ACF2 ID?
ACF2 is Sun Life's identity and access management system.
Every employee has a unique ACF2 ID made from letters followed by numbers.
Employees can find it in their welcome email from HR, their employee badge, or by calling the IT Help Desk.

## How to verify identity
When the user provides something that looks like an ACF2 ID:
1. Call query_db with a SELECT from users where acf2_id equals the user's uppercased ID.
2. If a row is returned, greet them by first name, mention their team and manager, then ask: "What will your role be?"
3. If no rows are returned, tell them you could not verify that ID and suggest they double-check or contact the IT Help Desk. Do not guess or make up data.

## ACF2 clarification
If the user asks what an ACF2 ID is, says they do not know their ACF2 ID, or asks where to find it, answer naturally in your own words using the definition above.
Do not include example IDs or any other person's ACF2 ID.
Do not call query_db for clarification questions.
After answering, ask for their ACF2 ID again.

## Tone rules
- Max 2-3 sentences per reply.
- Use plain text only. Do not use Markdown, bold text, asterisks, or code formatting.
- Never reveal raw SQL or database details to the user.
- Never invent employee data; only use what the database returns.
- If the message has nothing to do with access requests, gently redirect.
"""

ROLE_SYSTEM_PROMPT = """\
You are an AI access request assistant for Sun Life Financial.
You are warm, professional, concise, and careful with access data.

## Current goal
The employee is already verified. Resolve their role and select the best access template.

## Data access rules
Use query_db to query normalized SQLite tables:
- designations(id, title, description, team_hint, dept_hint)
- role_access_items(id, designation_id, access_item, display_name, system, description, mandatory, owner_team, servicenow_catalog_item_id, sort_order)
- user_designations(acf2_id, designation_id, assigned_at, source)

Do not context-stuff the full template catalog into your answer or prompt. Query only the rows you need.
Do not use legacy JSON template columns.

## Matching behavior
1. Use the verified employee context supplied in the user message.
2. If the role request is vague, ask one focused clarifying question and do not query the database.
3. If the role request is clear, query designations for likely candidates using title, description, team_hint, or dept_hint.
4. Query role_access_items for the selected designation_id and order by mandatory DESC, sort_order ASC.
5. Explain the selected template in plain professional language.
6. If there is no suitable template, say that the role could not be matched yet and that an admin review is needed.

## Tone rules
- Max 2-3 sentences per reply.
- Use plain text only. Do not use Markdown, bold text, asterisks, or code formatting.
- Never reveal raw SQL or database details to the user.
- Never invent access items; only use rows returned by query_db.
"""

FALLBACK_REPLY = (
    "Bedrock is currently unavailable, so I can't generate a live answer right now. "
    "Please try again in a moment."
)

HARD_BLOCK = (
    "I wasn't able to verify your identity with that ACF2 ID. "
    "Please double-check and try again, or contact your IT Help Desk if the issue persists."
)

MAX_TOOL_ITERATIONS = 6
ACF2_PATTERN = re.compile(r"\b[A-Z]{2,8}\d{2,6}\b", re.IGNORECASE)


def handle_agent_message(
    content: str, session: SessionState, history: List[ChatMessage]
) -> dict:
    if not session.acf2_id:
        return _handle_acf2_phase(content, history)

    if _contains_acf2_id(content):
        name = (
            session.workday_context.name
            if session.workday_context and session.workday_context.name
            else "this user"
        )
        return {
            "reply": (
                f"You're already verified as {name}. To use a different ID, "
                "reset the chat and start again."
            )
        }

    return _handle_role_phase(content, session, history)


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

        if stop_reason == "end_turn":
            reply_text = ""
            for block in content_blocks:
                if "text" in block:
                    reply_text = block["text"]
                    break

            result: dict = {"reply": _clean_reply(reply_text or FALLBACK_REPLY)}
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

        if stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": content_blocks})

            tool_results = []
            for block in content_blocks:
                if "toolUse" not in block:
                    continue

                tool_name = block["toolUse"]["name"]
                tool_input = block["toolUse"]["input"]
                tool_use_id = block["toolUse"]["toolUseId"]

                log_bedrock(f"tool_call -> {tool_name}")

                result_text = _execute_tool(tool_name, tool_input)

                if tool_name == "query_db" and verified_user is None:
                    try:
                        rows = json.loads(result_text)
                        if isinstance(rows, list) and len(rows) > 0:
                            first = rows[0]
                            if "acf2_id" in first and "name" in first:
                                verified_user = first
                                log_agent(
                                    f"Identity verified: {first['name']} "
                                    f"({first['acf2_id']}) - {first.get('team', '')}"
                                )
                    except Exception:
                        pass

                tool_results.append({
                    "toolResult": {
                        "toolUseId": tool_use_id,
                        "content": [{"text": result_text}],
                    }
                })

            messages.append({"role": "user", "content": tool_results})
            continue

        log_error(f"Unexpected stopReason: {stop_reason}")
        break

    return {"reply": FALLBACK_REPLY}


def _handle_role_phase(
    content: str, session: SessionState, history: List[ChatMessage]
) -> dict:
    log_agent(f"Role message received (len={len(content)})")

    workday = session.workday_context
    employee_context = {
        "acf2_id": session.acf2_id,
        "name": workday.name if workday else "",
        "team": workday.team if workday else "",
        "manager": workday.manager if workday else "",
        "dept": workday.dept if workday else "",
        "employment_type": workday.employment_type if workday else "",
    }

    messages = _build_bedrock_history(history)
    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "text": (
                        "Verified employee context:\n"
                        f"{json.dumps(employee_context, ensure_ascii=True)}\n\n"
                        f"Role request:\n{content}"
                    )
                }
            ],
        }
    )

    candidate_designations: list[dict] = []
    role_access_rows: list[dict] = []

    for iteration in range(MAX_TOOL_ITERATIONS):
        log_bedrock(f"Role converse call #{iteration + 1} (messages={len(messages)})")

        try:
            response = converse_with_tools(
                ROLE_SYSTEM_PROMPT, messages, TOOL_SPECS, max_tokens=768
            )
        except Exception as exc:
            log_error(f"Bedrock role call failed: {exc}")
            return {"reply": FALLBACK_REPLY}

        stop_reason = response.get("stopReason", "")
        output_msg = response.get("output", {}).get("message", {})
        content_blocks = output_msg.get("content", [])

        log_bedrock(f"role stopReason={stop_reason}, blocks={len(content_blocks)}")

        if stop_reason == "end_turn":
            reply_text = ""
            for block in content_blocks:
                if "text" in block:
                    reply_text = block["text"]
                    break

            result: dict = {"reply": _clean_reply(reply_text or FALLBACK_REPLY)}
            if candidate_designations and role_access_rows:
                selected_template = _build_selected_template(
                    candidate_designations[0], role_access_rows, result["reply"]
                )
                resolved_role = _build_resolved_role(
                    selected_template, employee_context
                )
                final_bundle = selected_template["mandatory_access"]
                result["session_update"] = {
                    "resolved_role": resolved_role,
                    "selected_template": selected_template,
                    "final_bundle": final_bundle,
                }
                _record_user_designation(
                    session.acf2_id or "",
                    selected_template["id"],
                    "agent_resolved",
                )
                log_agent(
                    f"Role resolved: {session.acf2_id} -> {selected_template['id']}"
                )
            return result

        if stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": content_blocks})

            tool_results = []
            for block in content_blocks:
                if "toolUse" not in block:
                    continue

                tool_name = block["toolUse"]["name"]
                tool_input = block["toolUse"]["input"]
                tool_use_id = block["toolUse"]["toolUseId"]

                log_bedrock(f"role tool_call -> {tool_name}")
                result_text = _execute_tool(tool_name, tool_input)
                _capture_role_rows(
                    tool_input.get("sql", ""),
                    result_text,
                    candidate_designations,
                    role_access_rows,
                )

                tool_results.append(
                    {
                        "toolResult": {
                            "toolUseId": tool_use_id,
                            "content": [{"text": result_text}],
                        }
                    }
                )

            messages.append({"role": "user", "content": tool_results})
            continue

        log_error(f"Unexpected role stopReason: {stop_reason}")
        break

    return {"reply": FALLBACK_REPLY}


def _capture_role_rows(
    sql: str,
    result_text: str,
    candidate_designations: list[dict],
    role_access_rows: list[dict],
) -> None:
    try:
        rows = json.loads(result_text)
    except Exception:
        return

    if not isinstance(rows, list):
        return

    lowered_sql = (sql or "").lower()
    if "from designations" in lowered_sql:
        for row in rows:
            if isinstance(row, dict) and "id" in row and "title" in row:
                candidate_designations.append(row)
    elif "from role_access_items" in lowered_sql:
        for row in rows:
            if isinstance(row, dict) and "access_item" in row:
                role_access_rows.append(row)


def _build_selected_template(
    designation: dict, access_rows: list[dict], reasoning: str
) -> dict:
    mandatory_access = []
    optional_access = []
    designation_id = designation["id"]
    scoped_rows = [
        row
        for row in access_rows
        if not row.get("designation_id") or row.get("designation_id") == designation_id
    ]
    for row in sorted(
        scoped_rows,
        key=lambda r: (r.get("mandatory") != 1, r.get("sort_order") or 0),
    ):
        item = _format_access_item(row)
        if item["mandatory"]:
            mandatory_access.append(item)
        else:
            optional_access.append(item)

    return {
        "id": designation["id"],
        "name": designation["title"],
        "description": designation.get("description", ""),
        "confidence": 0.96,
        "reasoning": reasoning,
        "mandatory_access": mandatory_access,
        "optional_access": optional_access,
    }


def _format_access_item(row: dict) -> dict:
    return {
        "id": row.get("access_item") or row.get("id"),
        "name": row.get("display_name") or row.get("access_item") or row.get("id"),
        "system": row.get("system") or "",
        "reason": row.get("description") or "",
        "mandatory": bool(row.get("mandatory")),
        "owner_team": row.get("owner_team") or "",
        "servicenow_catalog_item_id": row.get("servicenow_catalog_item_id") or "",
        "sort_order": row.get("sort_order") or 0,
    }


def _build_resolved_role(selected_template: dict, employee_context: dict) -> dict:
    return {
        "role": selected_template["name"],
        "designation_id": selected_template["id"],
        "seniority": "Not specified",
        "employment_type": employee_context.get("employment_type") or "",
        "team": employee_context.get("team") or "",
        "dept": employee_context.get("dept") or "",
        "confidence": selected_template["confidence"],
    }


def _record_user_designation(acf2_id: str, designation_id: str, source: str) -> None:
    if not acf2_id or not designation_id:
        return

    safe_acf2 = _sql_literal(acf2_id)
    safe_designation = _sql_literal(designation_id)
    safe_source = _sql_literal(source)
    assigned_at = int(time.time())
    sql = (
        "INSERT INTO user_designations (acf2_id, designation_id, assigned_at, source) "
        f"VALUES ({safe_acf2}, {safe_designation}, {assigned_at}, {safe_source}) "
        "ON CONFLICT(acf2_id) DO UPDATE SET "
        "designation_id=excluded.designation_id, "
        "assigned_at=excluded.assigned_at, "
        "source=excluded.source"
    )
    result = _mcp_execute_db(sql)
    log_mcp(f"user_designations upsert result: {result}")


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

    first_word = sql.split()[0].upper() if sql else ""
    if first_word != "SELECT":
        log_error(f"Blocked non-SELECT SQL from agent: {sql[:80]}")
        return json.dumps({"error": "Only SELECT statements are permitted via query_db"})

    log_mcp(f"SQL: {sql}")

    try:
        from mcp_server.sqlite_server import query_db as mcp_query_db
        result = mcp_query_db(sql)
    except Exception as exc:
        log_error(f"MCP query_db failed: {exc}")
        return json.dumps({"error": str(exc)})

    try:
        parsed = json.loads(result)
        row_count = len(parsed) if isinstance(parsed, list) else "?"
        log_mcp(f"{row_count} row(s) returned")
    except Exception:
        log_mcp("Result received (unparseable)")

    return result


def _mcp_execute_db(sql: str) -> str:
    """Execute a constrained write through the SQLite MCP server."""
    sql = sql.strip()
    first_word = sql.split()[0].upper() if sql else ""
    if first_word not in {"INSERT", "UPDATE"}:
        log_error(f"Blocked unsupported write SQL from agent: {sql[:80]}")
        return json.dumps({"error": "Only INSERT and UPDATE statements are permitted"})

    log_mcp(f"WRITE SQL: {sql}")

    try:
        from mcp_server.sqlite_server import execute_db as mcp_execute_db

        return mcp_execute_db(sql)
    except Exception as exc:
        log_error(f"MCP execute_db failed: {exc}")
        return json.dumps({"error": str(exc)})


def _sql_literal(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _contains_acf2_id(content: str) -> bool:
    return bool(ACF2_PATTERN.search(content or ""))


def _clean_reply(reply: str) -> str:
    """Keep model replies plain text for the chat UI."""
    return re.sub(r"\*\*(.*?)\*\*", r"\1", reply or "").strip()
