'use client'

import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/components/auth/auth-provider'
import { apiFetch } from '@/lib/api/client'
import { roomResponseSchema } from '@/lib/api/contract'
import { queryKeys } from '@/lib/api/query-keys'

const configuredInterval = Number(process.env.NEXT_PUBLIC_LOT_POLL_INTERVAL_MS ?? 15_000)
export const lotPollInterval = Number.isFinite(configuredInterval) ? Math.max(5_000, configuredInterval) : 15_000

export function useRoom(lotId: string, pollingFallback: boolean) {
  const { token, user } = useAuth()
  return useQuery({
    queryKey: queryKeys.roomViewer(lotId, user?.id ?? 'visitor'),
    queryFn: () => apiFetch(`/api/lots/${encodeURIComponent(lotId)}/room`, roomResponseSchema, { token }),
    refetchInterval: pollingFallback ? lotPollInterval : false,
    refetchIntervalInBackground: false,
  })
}
