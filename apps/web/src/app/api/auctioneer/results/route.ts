import { NextResponse } from 'next/server'
import { z } from 'zod'
import { auctioneerResultsResponseSchema } from '@/lib/api/contract'
import { requireAuth } from '@/server/auth'
import { backendJson } from '@/server/backend'
import { handleRouteError, parseInput } from '@/server/http'

const querySchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(1).max(50).default(12),
})

export async function GET(request: Request) {
  try {
    const { token } = await requireAuth(request, 'auctioneer')
    const query = parseInput(Object.fromEntries(new URL(request.url).searchParams), querySchema)
    const result = await backendJson('/v1/auctioneer/results', auctioneerResultsResponseSchema, { token, query })
    return NextResponse.json(result)
  } catch (error) {
    return handleRouteError(error)
  }
}
