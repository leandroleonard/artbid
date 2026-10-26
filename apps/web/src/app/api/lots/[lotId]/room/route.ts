import { NextResponse } from 'next/server'
import { z } from 'zod'
import { roomResponseSchema } from '@/lib/api/contract'
import { optionalAuth } from '@/server/auth'
import { backendJson } from '@/server/backend'
import { handleRouteError, parseInput } from '@/server/http'

export async function GET(request: Request, context: { params: Promise<{ lotId: string }> }) {
  try {
    const { lotId } = parseInput(await context.params, z.object({ lotId: z.string().min(1).max(100) }))
    const auth = await optionalAuth(request)
    const result = await backendJson(`/v1/lots/${encodeURIComponent(lotId)}/room`, roomResponseSchema, { token: auth?.token })
    return NextResponse.json(result)
  } catch (error) {
    return handleRouteError(error)
  }
}
