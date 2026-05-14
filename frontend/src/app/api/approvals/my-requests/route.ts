import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';

export async function GET(req: NextRequest) {
  const acf2Id = req.nextUrl.searchParams.get('acf2_id');
  if (!acf2Id) return NextResponse.json({ error: 'acf2_id required' }, { status: 400 });

  const res = await fetch(`${BACKEND_URL}/api/approvals/my-requests?acf2_id=${encodeURIComponent(acf2Id)}`);
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
