'use client'

import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/client'
import { auditResponseSchema, receiptResponseSchema } from '@/lib/api/contract'
import { queryKeys } from '@/lib/api/query-keys'

export function useAudit(lotId: string, page = 1) {
  return useQuery({
    queryKey: queryKeys.audit(lotId, page),
    queryFn: () => apiFetch(`/api/audit?lotId=${encodeURIComponent(lotId)}&page=${page}&pageSize=20`, auditResponseSchema),
    enabled: Boolean(lotId),
  })
}

export function useReceipt(receiptId: string) {
  return useQuery({
    queryKey: queryKeys.receipt(receiptId),
    queryFn: () => apiFetch(`/api/receipts/${encodeURIComponent(receiptId)}`, receiptResponseSchema),
    enabled: Boolean(receiptId),
  })
}
