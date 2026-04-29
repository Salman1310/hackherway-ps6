import { NextResponse } from 'next/server';
import { getDb } from '@/lib/sqlite';
import { converse } from '@/lib/bedrock';
import type { SessionState } from '@/lib/types';

const HARD_BLOCK =
  "I wasn't able to verify your identity with that ACF2 ID. Please double-check and try again, or contact your IT Help Desk if the issue persists.";

type RequestBody = {
  content: string;
  session: SessionState;
  history: { role: string; content: string }[];
};

export async function POST(request: Request) {
  try {
    const { content, session } = (await request.json()) as RequestBody;

    // Phase 2: ACF2 identity verification (first message)
    if (!session.acf2_id) {
      return handleAcf2Verification(content);
    }

    // Phase 3+ placeholder
    return NextResponse.json({
      reply:
        "Great, I've confirmed your identity! Next, I'll identify the right access template based on your role. Give me a moment...",
    });
  } catch (err) {
    console.error('[agent/message]', err);
    return NextResponse.json(
      { reply: 'Something went wrong on my end. Please try again.' },
      { status: 500 },
    );
  }
}

type UserRow = {
  acf2_id: string;
  name: string;
  team: string;
  manager: string;
  dept: string;
  employment_type: string;
};

async function handleAcf2Verification(content: string) {
  const acf2_id = content.trim().toUpperCase();

  // Lookup user in SQLite (fast, local, no network)
  let employee: UserRow | null = null;
  try {
    const db = getDb();
    employee = db.prepare('SELECT * FROM users WHERE acf2_id = ?').get(acf2_id) as UserRow ?? null;
  } catch (dbErr) {
    console.error('[SQLite]', dbErr);
  }

  if (!employee) {
    return NextResponse.json({ reply: HARD_BLOCK });
  }

  // Generate personalised Bedrock greeting
  const systemPrompt = `You are an AI-powered access request assistant for Sun Life Financial.
You are warm, professional, and concise — like a helpful IT colleague.
The user has just verified their identity. Greet them by first name, acknowledge their team,
and tell them you'll guide them through setting up their system access.
Keep it to 2–3 sentences. Do not mention ACF2 IDs or technical details.`;

  const userPrompt = `Verified employee details:
Name: ${employee.name}
Team: ${employee.team}
Manager: ${employee.manager}
Department: ${employee.dept}
Employment Type: ${employee.employment_type}

Please produce the personalised greeting now.`;

  let reply: string;
  try {
    reply = await converse(systemPrompt, [
      { role: 'user', content: [{ text: userPrompt }] },
    ]);
  } catch (bedrockErr) {
    console.error('[Bedrock]', bedrockErr);
    reply = `Welcome, ${employee.name}! I can see you're joining the ${employee.team} team. Let me help you get all the right access set up — this should only take a few minutes.`;
  }

  return NextResponse.json({
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
  });
}
