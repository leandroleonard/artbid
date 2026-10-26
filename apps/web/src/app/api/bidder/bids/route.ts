import { NextResponse } from 'next/server'
import { z } from 'zod'
import { bidsResponseSchema } from '@/lib/api/contract'
import { requireAuth } from '@/server/auth'
import { backendJson } from '@/server/backend'
import { handleRouteError, pageJson, parseInput } from '@/server/http'

const querySchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(1).max(50).default(20),
  status: z.enum(['leading', 'outbid', 'won', 'lost']).optional(),
})

export async function GET(request: Request) {
  try {
    const { token } = await requireAuth(request, 'bidder')
    const query = parseInput(Object.fromEntries(new URL(request.url).searchParams), querySchema)
    
    const result = await backendJson('/v1/me/bids', bidsResponseSchema, { token, query })
    return NextResponse.json(result)
  } catch (error) {
    return handleRouteError(error)
  }
}
