'use client'

import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/client'
import { lotsResponseSchema, type LotStatus } from '@/lib/api/contract'
import { queryKeys } from '@/lib/api/query-keys'

export type LotFilters = { q?: string; status?: LotStatus; sort?: string; page?: number; pageSize?: number }

export function useLots(filters: LotFilters = {}) {
  const query = new URLSearchParams()
  query.set('page', String(filters.page ?? 1))
  query.set('pageSize', String(filters.pageSize ?? 12))
  query.set('sort', filters.sort ?? 'endingSoon')
  if (filters.q) query.set('q', filters.q)
  if (filters.status) query.set('status', filters.status)
  return useQuery({
    queryKey: queryKeys.lots(filters),
    queryFn: () => apiFetch(`/api/lots?${query}`, lotsResponseSchema),
    placeholderData: keepPreviousData,
  })
}
