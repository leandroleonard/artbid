import { NextResponse } from 'next/server'
import { z } from 'zod'
import { bidAcceptedResponseSchema } from '@/lib/api/contract'
import { requireAuth } from '@/server/auth'
import { backendJson } from '@/server/backend'
import { assertSameOrigin, handleRouteError, parseJsonBody, requireIdempotencyKey } from '@/server/http'

const createBidSchema = z.object({
  lotId: z.string().min(1).max(100),
  amountCents: z.number().int().positive().max(Number.MAX_SAFE_INTEGER),
})

export async function POST(request: Request) {
  try {
    assertSameOrigin(request)
    const { token, user } = await requireAuth(request, 'bidder')
    if (user.role === 'auctioneer') throw new Error('unreachable')
    const body = await parseJsonBody(request, createBidSchema)
    const idempotencyKey = requireIdempotencyKey(request)
    const result = await backendJson('/v1/bids', bidAcceptedResponseSchema, {
      method: 'POST', token, body, idempotencyKey,
    })
    return NextResponse.json(result, { status: 201 })
  } catch (error) {
    return handleRouteError(error)
  }
}
