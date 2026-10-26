import { NextResponse } from 'next/server'
import { z } from 'zod'
import { auditResponseSchema } from '@/lib/api/contract'
import { backendJson } from '@/server/backend'
import { handleRouteError, parseInput } from '@/server/http'

const querySchema = z.object({
  lotId: z.string().min(1).max(100),
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(1).max(50).default(20),
})

export async function GET(request: Request) {
  try {
    const query = parseInput(Object.fromEntries(new URL(request.url).searchParams), querySchema)
    const result = await backendJson('/v1/audit', auditResponseSchema, { query })
    return NextResponse.json(result)
  } catch (error) {
    return handleRouteError(error)
  }
}
