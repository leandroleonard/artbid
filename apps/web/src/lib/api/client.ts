'use client'

import type { z } from 'zod'
import { apiErrorSchema } from './contract'

type ApiOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  token?: string | null
  idempotencyKey?: string
  signal?: AbortSignal
  timeoutMs?: number
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
    public readonly fieldErrors?: Record<string, string[]>,
    public readonly requestId?: string,
    public readonly retryable = false,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiFetch<T>(
  path: string,
  schema: z.ZodType<T>,
  options: ApiOptions = {},
): Promise<T> {
  if (!/^\/api\/(?!\/)/.test(path) || path.includes('://')) {
    throw new ApiError('Ocorreu um erro interno.', 500, 'INVALID_API_DESTINATION')
  }

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort('timeout'), options.timeoutMs ?? 12_000)
  const abortFromParent = () => controller.abort(options.signal?.reason)
  options.signal?.addEventListener('abort', abortFromParent, { once: true })

  try {
    const response = await fetch(path, {
      method: options.method ?? 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: {
        Accept: 'application/json',
        ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
        ...(options.idempotencyKey ? { 'Idempotency-Key': options.idempotencyKey } : {}),
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
    })

    const text = await response.text()
    let payload: unknown = null
    if (text) {
      try {
        payload = JSON.parse(text)
      } catch {
        throw new ApiError('Resposta inválida.', 502, 'UPSTREAM_INVALID_RESPONSE')
      }
    }

    if (!response.ok) {
      const parsedError = apiErrorSchema.safeParse(payload)
      if (parsedError.success) {
        const error = parsedError.data.error
        if (response.status === 401 && typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('artbid:unauthorized'))
        }
        throw new ApiError(error.message, response.status, error.code, error.fieldErrors, error.requestId, error.retryable)
      }
      throw new ApiError('Não foi possível concluir o pedido.', response.status, 'REQUEST_FAILED')
    }

    const parsed = schema.safeParse(payload)
    if (!parsed.success) {
      throw new ApiError('Resposta inválida.', 502, 'UPSTREAM_INVALID_RESPONSE')
    }
    return parsed.data
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (controller.signal.aborted) {
      throw new ApiError('O pedido excedeu o tempo limite ou foi cancelado.', 504, 'UPSTREAM_TIMEOUT', undefined, undefined, true)
    }
    throw new ApiError('Falha de rede ao contactar a aplicação.', 503, 'NETWORK_ERROR', undefined, undefined, true)
  } finally {
    clearTimeout(timeout)
    options.signal?.removeEventListener('abort', abortFromParent)
  }
}

export function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Ocorreu um erro inesperado.'
}
