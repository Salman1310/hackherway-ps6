import { converse } from '../lib/bedrock';
import { getDb } from '../lib/sqlite';
import type { SessionState, ChatMessage, AgentResponse, WorkdayContext } from '../types';

const HARD_BLOCK =
  "I wasn't able to verify your identity with that ACF2 ID. Please double-check and try again, or contact your IT Help Desk if the issue persists.";

// ─── System prompts ───────────────────────────────────────────────────────────

const INTENT_SYSTEM_PROMPT = `You are an AI access request assistant for Sun Life Financial.
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
{ "intent": "redirect", "message": "your gentle 1-sentence redirect back to providing the ACF2 ID" }`;

const GREETING_SYSTEM_PROMPT = `You are an AI access request assistant for Sun Life Financial.
You are warm, professional, and concise — like a helpful IT colleague.
The user's identity has just been verified. Greet them by first name, acknowledge their team,
and tell them you will guide them through setting up system access.
Keep it to 2–3 sentences. Do not mention ACF2 IDs or technical details.`;

// ─── ACF2 pattern fallback ────────────────────────────────────────────────────

const ACF2_PATTERN = /\b([A-Z]{2,8}\d{2,6})\b/i;

// ─── Main entry point ─────────────────────────────────────────────────────────

export async function handleAgentMessage(
  content: string,
  session: SessionState,
  history: ChatMessage[],
): Promise<AgentResponse> {
  if (!session.acf2_id) {
    return handleAcf2Phase(content, history);
  }

  // Phase 3+ placeholder — extended in future phases
  return {
    reply:
      "Great, identity confirmed! Next I'll identify the right access template for your role — give me just a moment.",
  };
}

// ─── Phase 2: ACF2 extraction ─────────────────────────────────────────────────

async function handleAcf2Phase(
  content: string,
  history: ChatMessage[],
): Promise<AgentResponse> {
  // Build Bedrock message history — skip leading bot messages (welcome msg)
  // Bedrock requires the first message to be from 'user'
  const filtered = history.filter(
    (m, i) => m.role === 'user' || history.slice(0, i).some((h) => h.role === 'user'),
  );
  const bedrockHistory = filtered.map((m) => ({
    role: (m.role === 'bot' ? 'assistant' : 'user') as 'user' | 'assistant',
    content: [{ text: m.content }],
  }));

  // ── Step 1: Understand intent ──────────────────────────────────────────────
  let intentResult: { intent: string; acf2_id?: string; message?: string };

  try {
    const intentMessages = [
      ...bedrockHistory,
      { role: 'user' as const, content: [{ text: content }] },
    ];
    const raw = await converse(INTENT_SYSTEM_PROMPT, intentMessages, 256);

    // Strip markdown code fences if model wraps JSON in them
    const cleaned = raw.replace(/```json\n?|\n?```/g, '').trim();
    intentResult = JSON.parse(cleaned);
  } catch {
    // Bedrock or JSON parse failed — fallback to regex pattern match
    const match = content.match(ACF2_PATTERN);
    if (match) {
      intentResult = { intent: 'provide_acf2', acf2_id: match[1].toUpperCase() };
    } else {
      intentResult = {
        intent: 'redirect',
        message:
          "I didn't quite catch that. Could you share your ACF2 ID? You can find it in your welcome email or on your employee badge.",
      };
    }
  }

  // ── Step 2: Act on intent ──────────────────────────────────────────────────
  if (intentResult.intent === 'provide_acf2' && intentResult.acf2_id) {
    return verifyAndGreet(intentResult.acf2_id.toUpperCase(), content, bedrockHistory);
  }

  // Non-ACF2 intents: return the message from Bedrock directly
  return {
    reply:
      intentResult.message ??
      "Could you share your ACF2 ID? You'll find it in your welcome email from HR.",
  };
}

// ─── ACF2 verification + greeting ────────────────────────────────────────────

async function verifyAndGreet(
  acf2_id: string,
  userContent: string,
  bedrockHistory: { role: 'user' | 'assistant'; content: { text: string }[] }[],
): Promise<AgentResponse> {
  // Lookup in SQLite
  const db = getDb();
  const employee = db
    .prepare('SELECT * FROM users WHERE acf2_id = ?')
    .get(acf2_id) as (WorkdayContext & { acf2_id: string }) | undefined;

  if (!employee) {
    return { reply: HARD_BLOCK };
  }

  // Generate personalised greeting via Bedrock
  const greetingMessages = [
    ...bedrockHistory,
    { role: 'user' as const, content: [{ text: userContent }] },
    {
      role: 'assistant' as const,
      content: [
        {
          text: `Identity verified. Employee details: Name: ${employee.name}, Team: ${employee.team}, Manager: ${employee.manager}, Dept: ${employee.dept}, Type: ${employee.employment_type}.`,
        },
      ],
    },
    {
      role: 'user' as const,
      content: [{ text: 'Please greet this employee and let them know you will help with access setup.' }],
    },
  ];

  let reply: string;
  try {
    reply = await converse(GREETING_SYSTEM_PROMPT, greetingMessages, 256);
  } catch {
    // Graceful fallback — flow never breaks on Bedrock error
    reply = `Welcome, ${employee.name}! I can see you're joining the ${employee.team} team. Let me help you get all the right access set up — this should only take a few minutes.`;
  }

  return {
    reply,
    session_update: {
      acf2_id,
      workday_context: {
        name: employee.name,
        team: employee.team,
        manager: employee.manager,
        dept: employee.dept,
        employment_type: employee.employment_type,
      },
    },
  };
}
