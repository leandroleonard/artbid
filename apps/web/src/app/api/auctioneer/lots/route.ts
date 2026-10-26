import { NextResponse } from 'next/server'
import { z } from 'zod'
import { auctioneerLotResponseSchema, auctioneerLotsResponseSchema } from '@/lib/api/contract'
import { requireAuth } from '@/server/auth'
import { backendJson } from '@/server/backend'
import { assertSameOrigin, handleRouteError, parseInput, parseJsonBody, requireIdempotencyKey } from '@/server/http'

const querySchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(1).max(50).default(12),
  status: z.enum(['scheduled', 'live', 'ended', 'cancelled']).optional(),
})
const createLotSchema = z.object({
  artworkId: z.string().min(1).max(100),
  title: z.string().trim().min(3).max(160),
  description: z.string().trim().max(2000).optional(),
  startingBidCents: z.number().int().positive().max(Number.MAX_SAFE_INTEGER),
  minimumIncrementCents: z.number().int().positive().max(Number.MAX_SAFE_INTEGER),
  startsAt: z.iso.datetime(),
  endsAt: z.iso.datetime(),
}).refine((value) => new Date(value.endsAt) > new Date(value.startsAt), {
  message: 'O fim deve ser posterior ao início.', path: ['endsAt'],
})

export async function GET(request: Request) {
  try {
    const { token } = await requireAuth(request, 'auctioneer')
    const query = parseInput(Object.fromEntries(new URL(request.url).searchParams), querySchema)
    const result = await backendJson('/v1/auctioneer/lots', auctioneerLotsResponseSchema, { token, query })
    return NextResponse.json(result)
  } catch (error) {
    return handleRouteError(error)
  }
}

export async function POST(request: Request) {
  try {
    assertSameOrigin(request)
    const { token } = await requireAuth(request, 'auctioneer')
    const body = await parseJsonBody(request, createLotSchema)
    const idempotencyKey = requireIdempotencyKey(request)
    const result = await backendJson('/v1/auctioneer/lots', auctioneerLotResponseSchema, {
      method: 'POST', token, body, idempotencyKey,
    })
    return NextResponse.json(result, { status: 201 })
  } catch (error) {
    return handleRouteError(error)
  }
}
