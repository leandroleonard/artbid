import { NextResponse } from 'next/server'
import { z } from 'zod'
import { backendJson } from '@/server/backend'
import { bearerToken, clearSessionCookie, sessionToken } from '@/server/auth'
import { assertSameOrigin, handleRouteError } from '@/server/http'

const logoutSchema = z.object({ data: z.object({ revoked: z.boolean() }) })

export async function POST(request: Request) {
  let response: NextResponse
  try {
    assertSameOrigin(request)
    const token = bearerToken(request) ?? (await sessionToken())
    if (!token) {
      response = NextResponse.json({ data: { revoked: Boolean(token) } })
    } else {
      const result = await backendJson('/v1/auth/logout', logoutSchema, { method: 'POST', token })
      response = NextResponse.json(result)
    }
  } catch (error) {
    response = handleRouteError(error)
  }
  clearSessionCookie(response)
  return response
}
