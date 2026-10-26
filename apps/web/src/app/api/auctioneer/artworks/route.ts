import { NextResponse } from 'next/server'
import { z } from 'zod'
import { artworksResponseSchema } from '@/lib/api/contract'
import { requireAuth } from '@/server/auth'
import { backendJson } from '@/server/backend'
import { handleRouteError, parseInput } from '@/server/http'

const querySchema = z.object({
  q: z.string().trim().min(2).max(100),
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(1).max(24).default(12),
})

export async function GET(request: Request) {
  try {
    const { token } = await requireAuth(request, 'auctioneer')
    const query = parseInput(Object.fromEntries(new URL(request.url).searchParams), querySchema)
    
    const result = await backendJson('/v1/auctioneer/artworks', artworksResponseSchema, { token, query })
    return NextResponse.json(result)
  } catch (error) {
    return handleRouteError(error)
  }
}
