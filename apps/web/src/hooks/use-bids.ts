'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/components/auth/auth-provider'
import { apiFetch } from '@/lib/api/client'
import { bidAcceptedResponseSchema, bidsResponseSchema, wonResponseSchema } from '@/lib/api/contract'
import { queryKeys } from '@/lib/api/query-keys'

export function useBidHistory(page = 1, status = 'all') {
  const { token } = useAuth()
  const statusQuery = status === 'all' ? '' : `&status=${encodeURIComponent(status)}`
  return useQuery({
    queryKey: queryKeys.bids(page, status),
    queryFn: () => apiFetch(`/api/bidder/bids?page=${page}&pageSize=20${statusQuery}`, bidsResponseSchema, { token }),
    enabled: Boolean(token),
  })
}

export function useWonLots(page = 1) {
  const { token } = useAuth()
  return useQuery({
    queryKey: queryKeys.won(page),
    queryFn: () => apiFetch(`/api/bidder/won?page=${page}&pageSize=12`, wonResponseSchema, { token }),
    enabled: Boolean(token),
  })
}

export function useCreateBid(lotId: string) {
  const { token } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ amountCents, idempotencyKey }: { amountCents: number; idempotencyKey: string }) => apiFetch('/api/bids', bidAcceptedResponseSchema, {
      method: 'POST', token, body: { lotId, amountCents }, idempotencyKey,
    }),
    onSuccess: () => {
      const invalidations = [
        queryClient.invalidateQueries({ queryKey: queryKeys.room(lotId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.lotsRoot }),
        queryClient.invalidateQueries({ queryKey: queryKeys.wallet }),
        queryClient.invalidateQueries({ queryKey: ['bids'] }),
        queryClient.invalidateQueries({ queryKey: ['movements'] }),
      ]
      return Promise.all(invalidations).then(() => undefined)
    },
  })
}
