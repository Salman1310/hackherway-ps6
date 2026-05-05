import { NextRequest } from 'next/server';

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const acf2_id = body.acf2_id ?? 'UNKNOWN';

  return Response.json({
    success: true,
    user_dn: `CN=${acf2_id},OU=Users,DC=sunlife,DC=com`,
  });
}
