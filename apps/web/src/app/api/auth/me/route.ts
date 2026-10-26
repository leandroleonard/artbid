import { NextResponse } from 'next/server'
import { z } from 'zod'
import { userResponseSchema } from '@/lib/api/contract'
import { requireAuth } from '@/server/auth'
import { backendJson } from '@/server/backend'
import { assertSameOrigin, handleRouteError, notIntegrated, parseJsonBody } from '@/server/http'

const profileSchema = z.object({ displayName: z.string().trim().min(2).max(80) })

export async function GET(request: Request) {
  try {
    const { user } = await requireAuth(request)
    return NextResponse.json({ data: user })
  } catch (error) {
    return handleRouteError(error)
  }
}

export async function PATCH(request: Request) {
  try {
    assertSameOrigin(request)
    const { token } = await requireAuth(request)
    const body = await parseJsonBody(request, profileSchema)
    const result = await backendJson('/v1/auth/me', userResponseSchema, { method: 'PATCH', token, body })
    return NextResponse.json(result)
  } catch (error) {
    return handleRouteError(error)
  }
}
