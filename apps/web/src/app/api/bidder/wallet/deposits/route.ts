import { NextResponse } from 'next/server'
import { z } from 'zod'
import { depositResponseSchema } from '@/lib/api/contract'
import { requireAuth } from '@/server/auth'
import { backendJson } from '@/server/backend'
import { assertSameOrigin, handleRouteError, parseJsonBody, requireIdempotencyKey } from '@/server/http'

const depositSchema = z.object({ amountCents: z.number().int().positive().max(100_000_000) })

export async function POST(request: Request) {
  try {
    assertSameOrigin(request)
    const { token } = await requireAuth(request, 'bidder')
    const body = await parseJsonBody(request, depositSchema)
    const idempotencyKey = requireIdempotencyKey(request)
    const result = await backendJson('/v1/me/wallet/deposits', depositResponseSchema, {
      method: 'POST', token, body, idempotencyKey,
    })
    return NextResponse.json(result, { status: 201 })
  } catch (error) {
    return handleRouteError(error)
  }
}
