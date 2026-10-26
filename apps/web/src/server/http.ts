import { NextResponse } from 'next/server'
import type { z } from 'zod'

export class BffError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly fieldErrors?: Record<string, string[]>,
    public readonly retryable = false,
    public readonly requestId?: string,
  ) {
    super(message)
    this.name = 'BffError'
  }
}

export function dataJson(data: unknown, status = 200) {
  return NextResponse.json({ data }, { status })
}

export function pageJson(data: unknown[], page: number, pageSize: number, totalItems: number) {
  return NextResponse.json({
    data,
    pagination: { page, pageSize, totalItems, totalPages: Math.ceil(totalItems / pageSize) },
  })
}

export function errorJson(error: BffError) {
  return NextResponse.json(
    {
      error: {
        code: error.code,
        message: error.message,
        ...(error.fieldErrors ? { fieldErrors: error.fieldErrors } : {}),
        ...(error.requestId ? { requestId: error.requestId } : {}),
        retryable: error.retryable,
      },
    },
    { status: error.status, headers: { 'Cache-Control': 'no-store' } },
  )
}

export function handleRouteError(error: unknown) {
  if (error instanceof BffError) return errorJson(error)
  return errorJson(new BffError(500, 'INTERNAL_ERROR', 'Não foi possível concluir o pedido.'))
}

export async function parseJsonBody<T>(request: Request, schema: z.ZodType<T>): Promise<T> {
  let body: unknown
  try {
    body = await request.json()
  } catch {
    throw new BffError(400, 'VALIDATION_ERROR', 'O corpo do pedido deve ser JSON válido.')
  }
  const parsed = schema.safeParse(body)
  if (!parsed.success) {
    const fieldErrors: Record<string, string[]> = {}
    for (const issue of parsed.error.issues) {
      const key = issue.path.join('.') || 'body'
      fieldErrors[key] = [...(fieldErrors[key] ?? []), issue.message]
    }
    throw new BffError(422, 'VALIDATION_ERROR', 'Verifique os campos enviados.', fieldErrors)
  }
  return parsed.data
}

export function parseInput<T>(input: unknown, schema: z.ZodType<T>): T {
  const parsed = schema.safeParse(input)
  if (!parsed.success) {
    throw new BffError(422, 'VALIDATION_ERROR', 'Os parâmetros enviados são inválidos.')
  }
  return parsed.data
}

export function assertSameOrigin(request: Request) {
  const origin = request.headers.get('origin')
  if (!origin) return
  const forwardedHost = request.headers.get('x-forwarded-host')
  const host = forwardedHost ?? request.headers.get('host')
  try {
    if (!host || new URL(origin).host !== host) {
      throw new Error('origin mismatch')
    }
  } catch {
    throw new BffError(403, 'FORBIDDEN', 'A origem do pedido não é permitida.')
  }
}

export function requireIdempotencyKey(request: Request) {
  const key = request.headers.get('idempotency-key')
  if (!key || !/^[A-Za-z0-9-]{36,100}$/.test(key)) {
    throw new BffError(400, 'VALIDATION_ERROR', 'É necessária uma chave de idempotência válida.')
  }
  return key
}

export function notIntegrated(): never {
  throw new BffError(
    503,
    'BACKEND_NOT_INTEGRATED',
    'Modo de leitura apenas.',
    undefined,
    false,
  )
}
