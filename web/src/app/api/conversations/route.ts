import { NextResponse } from 'next/server';
import { getDb } from '@/lib/sqlite';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const acf2_id = searchParams.get('acf2_id')?.toUpperCase();

  if (!acf2_id) {
    return NextResponse.json({ error: 'acf2_id required' }, { status: 400 });
  }

  try {
    const db = getDb();
    const conversations = db
      .prepare(
        `SELECT id, acf2_id, created_at, updated_at
         FROM conversations
         WHERE acf2_id = ?
         ORDER BY updated_at DESC
         LIMIT 20`,
      )
      .all(acf2_id) as {
      id: string;
      acf2_id: string;
      created_at: number;
      updated_at: number;
    }[];

    return NextResponse.json({ conversations });
  } catch (err) {
    console.error('[conversations GET]', err);
    return NextResponse.json({ conversations: [] });
  }
}
