import { z } from 'zod'
import { bearerToken, sessionToken, validateToken } from '@/server/auth'
import { backendFetch } from '@/server/backend'
import { BffError, handleRouteError, parseInput } from '@/server/http'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'
export const maxDuration = 300

function eventHeaders() {
  return {
    'Content-Type': 'text/event-stream; charset=utf-8',
    'Cache-Control': 'no-cache, no-store, no-transform',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  }
}

export async function GET(request: Request, context: { params: Promise<{ lotId: string }> }) {
  try {
    const { lotId } = parseInput(await context.params, z.object({ lotId: z.string().min(1).max(100) }))
    const lastEventId = request.headers.get('last-event-id') ?? undefined
    if (lastEventId && lastEventId.length > 128) throw new BffError(400, 'VALIDATION_ERROR', 'Last-Event-ID inválido.')

    const token = bearerToken(request) ?? (await sessionToken())
    if (token) await validateToken(token)
    const upstream = await backendFetch(`/v1/lots/${encodeURIComponent(lotId)}/events`, {
      token: token ?? undefined,
      lastEventId,
      signal: request.signal,
      stream: true,
    })
    if (!upstream.ok || !upstream.body || !upstream.headers.get('content-type')?.includes('text/event-stream')) {
      upstream.body?.cancel().catch(() => undefined)
      throw new BffError(upstream.ok ? 502 : upstream.status, 'SSE_UNAVAILABLE', 'O serviço de eventos está indisponível.', undefined, true)
    }
    return new Response(upstream.body, { status: 200, headers: eventHeaders() })
  } catch (error) {
    return handleRouteError(error)
  }
}
