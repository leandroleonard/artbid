import { NextResponse } from 'next/server'
import { z } from 'zod'
import { lotResponseSchema } from '@/lib/api/contract'
import { backendJson } from '@/server/backend'
import { handleRouteError, parseInput } from '@/server/http'

export async function GET(_request: Request, context: { params: Promise<{ lotId: string }> }) {
  try {
    const { lotId } = parseInput(await context.params, z.object({ lotId: z.string().min(1).max(100) }))
    const result = await backendJson(`/v1/lots/${encodeURIComponent(lotId)}`, lotResponseSchema)
    return NextResponse.json(result)
  } catch (error) {
    return handleRouteError(error)
  }
}
