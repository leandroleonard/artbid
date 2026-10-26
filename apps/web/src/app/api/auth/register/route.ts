import { NextResponse } from 'next/server'
import { z } from 'zod'
import { authResponseSchema } from '@/lib/api/contract'
import { setSessionCookie } from '@/server/auth'
import { backendJson } from '@/server/backend'
import { assertSameOrigin, handleRouteError, parseJsonBody } from '@/server/http'

const registerSchema = z.object({
  displayName: z.string().trim().min(2).max(80),
  email: z.email().max(254),
  password: z.string().min(12).max(128),
  role: z.enum(['bidder', 'auctioneer']),
})

export async function POST(request: Request) {
  try {
    assertSameOrigin(request)
    const body = await parseJsonBody(request, registerSchema)
    const result = await backendJson('/v1/auth/register', authResponseSchema, { method: 'POST', body })
    const response = NextResponse.json(result, { status: 201 })
    setSessionCookie(response, result.data.accessToken, result.data.expiresAt)
    return response
  } catch (error) {
    return handleRouteError(error)
  }
}
