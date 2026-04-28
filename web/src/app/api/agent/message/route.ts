import { NextResponse } from 'next/server';
import clientPromise from '@/lib/mongodb';
import { converse } from '@/lib/bedrock';
import { MOCK_EMPLOYEES } from '@/lib/mockData';
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

async function handleAcf2Verification(content: string) {
  const acf2_id = content.trim().toUpperCase();

  // 1. Try MongoDB Atlas
  let employee: Record<string, string> | null = null;
  try {
    const client = await clientPromise;
    const db = client.db('hackherway');
    const doc = await db.collection('users').findOne({ acf2_id });
    if (doc) {
      // Strip MongoDB _id before using
      const { _id: _, ...rest } = doc as Record<string, unknown> & { _id: unknown };
      employee = rest as Record<string, string>;
    }
  } catch (dbErr) {
    console.warn('[MongoDB] Unavailable, falling back to mock data:', dbErr);
  }

  // 2. Fall back to mock data when DB is unavailable or BYPASS_AUTH is set
  if (!employee && process.env.BYPASS_AUTH === 'true') {
    const mock = MOCK_EMPLOYEES[acf2_id];
    if (mock) employee = mock as unknown as Record<string, string>;
  }

  if (!employee) {
    return NextResponse.json({ reply: HARD_BLOCK });
  }

  // 3. Generate personalised Bedrock greeting
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
    // Graceful fallback — no Bedrock dependency for demo
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
