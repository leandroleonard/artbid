import type { z } from 'zod'
import { apiErrorSchema } from '@/lib/api/contract'
import { apiBaseUrl, apiTimeoutMs } from './env'
import { BffError } from './http'

type BackendOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  token?: string
  body?: unknown
  query?: Record<string, string | number | undefined>
  idempotencyKey?: string
  lastEventId?: string
  signal?: AbortSignal
  stream?: boolean
}

function backendUrl(path: string, query?: BackendOptions['query']) {
  if (!/^\/v1\/[A-Za-z0-9_/{}/?&=.-]*$/.test(path) || path.includes('..')) {
    throw new BffError(500, 'INVALID_BACKEND_PATH', 'Destino inválido.')
  }
  let base: string
  try {
    base = apiBaseUrl()
  } catch {
    throw new BffError(503, 'BACKEND_NOT_INTEGRATED', 'Modo de leitura apenas.', undefined, true)
  }
  const url = new URL(`${base}${path}`)
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined) url.searchParams.set(key, String(value))
  }
  return url
}

export async function backendFetch(path: string, options: BackendOptions = {}) {
  const controller = new AbortController()
  const timeout = options.stream ? undefined : setTimeout(() => controller.abort(), apiTimeoutMs())
  const abortFromParent = () => controller.abort(options.signal?.reason)
  options.signal?.addEventListener('abort', abortFromParent, { once: true })

  try {
    return await fetch(backendUrl(path, options.query), {
      method: options.method ?? 'GET',
      headers: {
        Accept: options.stream ? 'text/event-stream' : 'application/json',
        ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
        ...(options.idempotencyKey ? { 'Idempotency-Key': options.idempotencyKey } : {}),
        ...(options.lastEventId ? { 'Last-Event-ID': options.lastEventId } : {}),
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: 'no-store',
      signal: controller.signal,
    })
  } catch (error) {
    if (controller.signal.aborted && !options.signal?.aborted) {
      throw new BffError(504, 'UPSTREAM_TIMEOUT', 'O pedido excedeu o tempo limite.', undefined, true)
    }
    if (options.signal?.aborted) throw error
    throw new BffError(503, 'BACKEND_UNAVAILABLE', 'Sistem temporariamente indisponível.', undefined, true)
  } finally {
    if (timeout) clearTimeout(timeout)
    if (!options.stream) options.signal?.removeEventListener('abort', abortFromParent)
  }
}

export async function backendJson<T>(
  path: string,
  schema: z.ZodType<T>,
  options: BackendOptions = {},
): Promise<T> {
  const response = await backendFetch(path, options)
  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      throw new BffError(502, 'UPSTREAM_INVALID_RESPONSE', 'Resposta inválida.')
    }
  }

  if (!response.ok) {
    const parsedError = apiErrorSchema.safeParse(payload)
    if (parsedError.success) {
      const error = parsedError.data.error
      throw new BffError(response.status, error.code, error.message, error.fieldErrors, error.retryable, error.requestId)
    }
    throw new BffError(response.status, 'UPSTREAM_ERROR', 'Não foi possível concluir o pedido.')
  }

  const parsed = schema.safeParse(payload)
  if (!parsed.success) {
    throw new BffError(502, 'UPSTREAM_INVALID_RESPONSE', 'Resposta inválida.')
  }
  return parsed.data
}
