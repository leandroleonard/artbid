import { NextResponse } from 'next/server'
import { authResponseSchema } from '@/lib/api/contract'
import {
  clearSessionCookie,
  sessionExpiry,
  sessionToken,
  validateToken,
} from '@/server/auth'
import { BffError, handleRouteError } from '@/server/http'

export async function GET() {
  try {
    const [token, expiresAt] = await Promise.all([
      sessionToken(),
      sessionExpiry(),
    ])

    const expiryTime = expiresAt ? Date.parse(expiresAt) : NaN

    if (
      !token ||
      !expiresAt ||
      !Number.isFinite(expiryTime) ||
      expiryTime <= Date.now()
    ) {
      throw new BffError(
        401,
        'UNAUTHENTICATED',
        'Não existe uma sessão activa.',
      )
    }

    const user = await validateToken(token)

    const payload = authResponseSchema.parse({
      data: {
        user,
        accessToken: token,
        expiresAt,
        demo: false,
      },
    })

    return NextResponse.json(payload, {
      headers: {
        'Cache-Control': 'no-store',
      },
    })
  } catch (error) {
    const response = handleRouteError(error)

    if (error instanceof BffError && error.status === 401) {
      clearSessionCookie(response)
    }

    return response
  }
}