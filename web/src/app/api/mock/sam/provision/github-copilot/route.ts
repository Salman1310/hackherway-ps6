import { NextRequest } from 'next/server';

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const acf2_id = body.acf2_id ?? 'UNKNOWN';

  return Response.json({
    success: true,
    seat_assigned: true,
    license_id: `COPILOT-${acf2_id}-${Date.now()}`,
  });
}
