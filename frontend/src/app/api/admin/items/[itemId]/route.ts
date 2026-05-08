import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';

export async function PUT(request: Request, { params }: { params: Promise<{ itemId: string }> }) {
  const { itemId } = await params;
  try {
    const body = await request.json();
    const res = await fetch(`${BACKEND_URL}/api/admin/items/${itemId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Backend unreachable' }, { status: 502 });
  }
}

export async function DELETE(_request: Request, { params }: { params: Promise<{ itemId: string }> }) {
  const { itemId } = await params;
  try {
    const res = await fetch(`${BACKEND_URL}/api/admin/items/${itemId}`, {
      method: 'DELETE',
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Backend unreachable' }, { status: 502 });
  }
}
