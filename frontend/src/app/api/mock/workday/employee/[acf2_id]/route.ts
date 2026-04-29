import { MOCK_EMPLOYEES } from '@/lib/mockData';
import { NextRequest } from 'next/server';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ acf2_id: string }> }
) {
  const { acf2_id } = await params;
  const employee = MOCK_EMPLOYEES[acf2_id.toUpperCase()];

  if (!employee) {
    return Response.json(
      { error: 'Employee not found', acf2_id },
      { status: 404 }
    );
  }

  return Response.json(employee);
}
