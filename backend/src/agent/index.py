import json
import re
from typing import List

from ..lib.bedrock import converse
from ..lib.sqlite import get_db
from ..types import SessionState, ChatMessage

HARD_BLOCK = (
    "I wasn't able to verify your identity with that ACF2 ID. "
    "Please double-check and try again, or contact your IT Help Desk if the issue persists."
)

INTENT_SYSTEM_PROMPT = """You are an AI access request assistant for Sun Life Financial.
Your current goal is to collect the user's ACF2 ID to verify their identity.

ACF2 is Sun Life's identity and access management system. Every employee has a unique ACF2 ID
(e.g. RIYA001, JOHN002). Employees can find it in their:
- Welcome email from HR
- Employee badge
- By contacting IT Help Desk

Analyse the user's message and respond ONLY with valid JSON — no extra text, no markdown.

If the message contains something that looks like an ACF2 ID (letters + numbers):
{ "intent": "provide_acf2", "acf2_id": "EXTRACTED_ID_UPPERCASE" }

If the user doesn't know what ACF2 ID means:
{ "intent": "explain", "message": "your warm 2-sentence explanation" }

If the user says they can't find or don't have their ACF2 ID:
{ "intent": "help_find", "message": "your 2-sentence guidance on how to locate it" }

If the message is unrelated or unclear:
{ "intent": "redirect", "message": "your gentle 1-sentence redirect back to providing the ACF2 ID" }"""

GREETING_SYSTEM_PROMPT = """You are an AI access request assistant for Sun Life Financial.
You are warm, professional, and concise — like a helpful IT colleague.
The user's identity has just been verified. Greet them by first name, acknowledge their team,
and tell them you will guide them through setting up system access.
Keep it to 2-3 sentences. Do not mention ACF2 IDs or technical details."""

ACF2_PATTERN = re.compile(r"\b([A-Z]{2,8}\d{2,6})\b", re.IGNORECASE)


# ── Public entry point ────────────────────────────────────────────────────────

def handle_agent_message(
    content: str, session: SessionState, history: List[ChatMessage]
) -> dict:
    if not session.acf2_id:
        return _handle_acf2_phase(content, history)

    # Phase 3+ placeholder — extended in future phases
    return {
        "reply": "Great, identity confirmed! Next I'll identify the right access template for your role — give me just a moment."
    }


# ── ACF2 phase ────────────────────────────────────────────────────────────────

def _build_bedrock_history(history: List[ChatMessage]) -> List[dict]:
    """Skip leading bot messages — Bedrock requires first message = user."""
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
    bedrock_history = _build_bedrock_history(history)
    messages = bedrock_history + [{"role": "user", "content": [{"text": content}]}]

    # Step 1: Classify intent via Bedrock
    intent_result: dict
    try:
        raw = converse(INTENT_SYSTEM_PROMPT, messages, max_tokens=256)
        cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
        intent_result = json.loads(cleaned)
    except Exception:
        # Fallback: regex ACF2 pattern match
        match = ACF2_PATTERN.search(content)
        if match:
            intent_result = {"intent": "provide_acf2", "acf2_id": match.group(1).upper()}
        else:
            intent_result = {
                "intent": "redirect",
                "message": (
                    "I didn't quite catch that. Could you share your ACF2 ID? "
                    "You'll find it in your welcome email from HR."
                ),
            }

    # Step 2: Act on intent
    if intent_result.get("intent") == "provide_acf2" and intent_result.get("acf2_id"):
        return _verify_and_greet(
            intent_result["acf2_id"].upper(), content, bedrock_history
        )

    return {
        "reply": intent_result.get(
            "message",
            "Could you share your ACF2 ID? You'll find it in your welcome email from HR.",
        )
    }


# ── Verification + greeting ───────────────────────────────────────────────────

def _verify_and_greet(
    acf2_id: str, user_content: str, bedrock_history: List[dict]
) -> dict:
    db = get_db()
    row = db.execute(
        "SELECT * FROM users WHERE acf2_id = ?", (acf2_id,)
    ).fetchone()

    if not row:
        return {"reply": HARD_BLOCK}

    emp = dict(row)

    # Generate personalised greeting
    greeting_messages = (
        bedrock_history
        + [
            {"role": "user", "content": [{"text": user_content}]},
            {
                "role": "assistant",
                "content": [
                    {
                        "text": (
                            f"Identity verified. Employee: {emp['name']}, "
                            f"Team: {emp['team']}, Manager: {emp['manager']}, "
                            f"Dept: {emp['dept']}, Type: {emp['employment_type']}."
                        )
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "text": "Please greet this employee and let them know you will help with access setup."
                    }
                ],
            },
        ]
    )

    try:
        reply = converse(GREETING_SYSTEM_PROMPT, greeting_messages, max_tokens=256)
    except Exception:
        reply = (
            f"Welcome, {emp['name']}! I can see you're joining the {emp['team']} team. "
            "Let me help you get all the right access set up — this should only take a few minutes."
        )

    return {
        "reply": reply,
        "session_update": {
            "acf2_id": acf2_id,
            "workday_context": {
                "name": emp["name"],
                "team": emp["team"],
                "manager": emp["manager"],
                "dept": emp["dept"],
                "employment_type": emp["employment_type"],
            },
        },
    }
