import { NextResponse } from 'next/server'
import { z } from 'zod'
import { lotsResponseSchema } from '@/lib/api/contract'
import { backendJson } from '@/server/backend'
import { handleRouteError, parseInput } from '@/server/http'

const querySchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(1).max(50).default(12),
  q: z.string().trim().max(100).optional(),
  status: z.enum(['scheduled', 'live', 'ended']).optional(),
  sort: z.enum(['endingSoon', 'recent', 'highestBid']).default('endingSoon'),
})

export async function GET(request: Request) {
  try {
    const query = parseInput(Object.fromEntries(new URL(request.url).searchParams), querySchema)
    const result = await backendJson('/v1/lots', lotsResponseSchema, { query })
    return NextResponse.json(result)

  } catch (error) {
    return handleRouteError(error)
  }
}
