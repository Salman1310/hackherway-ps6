import { NextRequest } from 'next/server';

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const acf2_id = body.acf2_id ?? 'UNKNOWN';

  return Response.json({
    success: true,
    npe_id: `NPE-${acf2_id}-${Date.now()}`,
    expires_at: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString(),
  });
}
