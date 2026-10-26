'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/components/auth/auth-provider'
import { apiFetch } from '@/lib/api/client'
import { depositResponseSchema, movementsResponseSchema, walletResponseSchema } from '@/lib/api/contract'
import { queryKeys } from '@/lib/api/query-keys'

export function useWallet(enabled = true) {
  const { token } = useAuth()
  return useQuery({
    queryKey: queryKeys.wallet,
    queryFn: () => apiFetch('/api/bidder/wallet', walletResponseSchema, { token }),
    enabled: Boolean(token) && enabled,
  })
}

export function useMovements(page = 1) {
  const { token } = useAuth()
  return useQuery({
    queryKey: queryKeys.movements(page),
    queryFn: () => apiFetch(`/api/bidder/movements?page=${page}&pageSize=20`, movementsResponseSchema, { token }),
    enabled: Boolean(token),
  })
}

export function useDeposit() {
  const { token } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ amountCents, idempotencyKey }: { amountCents: number; idempotencyKey: string }) => apiFetch('/api/bidder/wallet/deposits', depositResponseSchema, {
      method: 'POST', token, body: { amountCents }, idempotencyKey,
    }),
    onSuccess: () => Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.wallet }),
      queryClient.invalidateQueries({ queryKey: ['movements'] }),
    ]).then(() => undefined),
  })
}
