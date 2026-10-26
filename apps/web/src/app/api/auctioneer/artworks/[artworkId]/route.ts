import { NextResponse } from 'next/server'
import { z } from 'zod'
import { artworkResponseSchema } from '@/lib/api/contract'
import { requireAuth } from '@/server/auth'
import { backendJson } from '@/server/backend'
import { handleRouteError, parseInput } from '@/server/http'

export async function GET(request: Request, context: { params: Promise<{ artworkId: string }> }) {
  try {
    const { token } = await requireAuth(request, 'auctioneer')
    const { artworkId } = parseInput(await context.params, z.object({ artworkId: z.string().min(1).max(100) }))

    const result = await backendJson(`/v1/auctioneer/artworks/${encodeURIComponent(artworkId)}`, artworkResponseSchema, { token })
    return NextResponse.json(result)
  } catch (error) {
    return handleRouteError(error)
  }
}
