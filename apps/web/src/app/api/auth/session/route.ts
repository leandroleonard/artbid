import { NextResponse } from 'next/server'
import { clearSessionCookie, sessionExpiry, sessionToken, validateToken } from '@/server/auth'
import { BffError, handleRouteError } from '@/server/http'

export async function GET() {
  try {
    const [token, expiresAt] = await Promise.all([sessionToken(), sessionExpiry()])
    if (!token || !expiresAt || new Date(expiresAt).getTime() <= Date.now()) {
      throw new BffError(401, 'UNAUTHENTICATED', 'Não existe uma sessão activa.')
    }
    const user = await validateToken(token)
    return NextResponse.json({ data: { user, accessToken: token, expiresAt } })
  } catch (error) {
    const response = handleRouteError(error)
    clearSessionCookie(response)
    return response
  }
}
