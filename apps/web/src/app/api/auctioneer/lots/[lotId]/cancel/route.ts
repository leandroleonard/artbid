import { NextResponse } from 'next/server'
import { z } from 'zod'
import { auctioneerLotResponseSchema } from '@/lib/api/contract'
import { requireAuth } from '@/server/auth'
import { backendJson } from '@/server/backend'
import { assertSameOrigin, handleRouteError, parseInput, parseJsonBody, requireIdempotencyKey } from '@/server/http'

const cancelSchema = z.object({ confirmation: z.literal('CANCELAR') })

export async function POST(request: Request, context: { params: Promise<{ lotId: string }> }) {
  try {
    assertSameOrigin(request)
    const { token } = await requireAuth(request, 'auctioneer')
    const { lotId } = parseInput(await context.params, z.object({ lotId: z.string().min(1).max(100) }))
    const body = await parseJsonBody(request, cancelSchema)
    const idempotencyKey = requireIdempotencyKey(request)
    const result = await backendJson(`/v1/auctioneer/lots/${encodeURIComponent(lotId)}/cancel`, auctioneerLotResponseSchema, {
      method: 'POST', token, body, idempotencyKey,
    })
    return NextResponse.json(result)
  } catch (error) {
    return handleRouteError(error)
  }
}
