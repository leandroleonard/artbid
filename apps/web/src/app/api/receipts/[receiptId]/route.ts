import { NextResponse } from 'next/server'
import { z } from 'zod'
import { receiptResponseSchema } from '@/lib/api/contract'
import { backendJson } from '@/server/backend'
import { handleRouteError, parseInput } from '@/server/http'

export async function GET(_request: Request, context: { params: Promise<{ receiptId: string }> }) {
  try {
    const { receiptId } = parseInput(await context.params, z.object({ receiptId: z.string().min(1).max(100) }))
      const result = await backendJson(`/v1/receipts/${encodeURIComponent(receiptId)}`, receiptResponseSchema)
      return NextResponse.json(result)
  } catch (error) {
    return handleRouteError(error)
  }
}
