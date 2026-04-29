import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const acf2_id = searchParams.get('acf2_id');

    const res = await fetch(
      `${BACKEND_URL}/api/conversations?acf2_id=${acf2_id ?? ''}`,
    );

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error('[proxy /api/conversations]', err);
    return NextResponse.json({ conversations: [] });
  }
}
