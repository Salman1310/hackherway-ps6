import { NextRequest } from 'next/server';

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const team = body.team ?? 'TEAM';

  return Response.json({
    success: true,
    project_key: team.replace(/\s+/g, '-').toUpperCase().slice(0, 10),
  });
}
