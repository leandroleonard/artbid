import { cookies } from 'next/headers'
import type { NextResponse } from 'next/server'
import { userResponseSchema, type Role, type User } from '@/lib/api/contract'
import { backendJson } from './backend'
import { BffError } from './http'

const cookiePrefix = process.env.NODE_ENV === 'production' ? '__Host-' : ''
export const SESSION_COOKIE = `${cookiePrefix}artbid_session`
export const SESSION_EXPIRY_COOKIE = `${cookiePrefix}artbid_session_expiry`

export function bearerToken(request: Request) {
  const header = request.headers.get('authorization')
  if (!header) return null
  const match = /^Bearer\s+([^\s]+)$/i.exec(header)
  if (!match?.[1]) throw new BffError(401, 'UNAUTHENTICATED', 'Não tem permissão para esta operação.')
  return match[1]
}

export async function validateToken(token: string): Promise<User> {
  const response = await backendJson('/v1/auth/me', userResponseSchema, { token })
  return response.data
}

export async function requireAuth(request: Request, role?: Role) {
  const token = bearerToken(request)
  if (!token) throw new BffError(401, 'UNAUTHENTICATED', 'Inicie sessão para continuar.')
  const user = await validateToken(token)
  if (role && user.role !== role) {
    throw new BffError(403, 'FORBIDDEN', 'O seu perfil não permite esta operação.')
  }
  return { token, user }
}

export async function optionalAuth(request: Request) {
  const token = bearerToken(request)
  if (!token) return null
  return { token, user: await validateToken(token) }
}

export async function sessionToken() {
  const store = await cookies()
  return store.get(SESSION_COOKIE)?.value ?? null
}

export async function sessionExpiry() {
  const store = await cookies()
  return store.get(SESSION_EXPIRY_COOKIE)?.value ?? null
}

export function setSessionCookie(response: NextResponse, token: string, expiresAt: string) {
  const maxAge = Math.max(1, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000))
  const options = {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax' as const,
    path: '/',
    maxAge,
  }
  response.cookies.set(SESSION_COOKIE, token, options)
  response.cookies.set(SESSION_EXPIRY_COOKIE, expiresAt, options)
}

export function clearSessionCookie(response: NextResponse) {
  const options = {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax' as const,
    path: '/',
    maxAge: 0,
  }
  response.cookies.set(SESSION_COOKIE, '', options)
  response.cookies.set(SESSION_EXPIRY_COOKIE, '', options)
}
