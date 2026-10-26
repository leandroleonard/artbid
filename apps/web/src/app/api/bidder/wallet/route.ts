import { NextResponse } from 'next/server'
import { walletResponseSchema } from '@/lib/api/contract'
import { requireAuth } from '@/server/auth'
import { backendJson } from '@/server/backend'
import { handleRouteError } from '@/server/http'

export async function GET(request: Request) {
  try {
    const { token } = await requireAuth(request, 'bidder')
    const result = await backendJson('/v1/me/wallet', walletResponseSchema, { token })
    return NextResponse.json(result)
  } catch (error) {
    return handleRouteError(error)
  }
}
