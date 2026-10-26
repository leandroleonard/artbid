'use client'

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/components/auth/auth-provider'
import { apiFetch } from '@/lib/api/client'
import { artworkResponseSchema, artworksResponseSchema, auctioneerLotResponseSchema, auctioneerLotsResponseSchema, auctioneerResultsResponseSchema } from '@/lib/api/contract'
import { queryKeys } from '@/lib/api/query-keys'

export function useArtworks(query: string, page = 1) {
  const { token } = useAuth()
  return useQuery({
    queryKey: queryKeys.artworks(query, page),
    queryFn: () => apiFetch(`/api/auctioneer/artworks?q=${encodeURIComponent(query)}&page=${page}&pageSize=12`, artworksResponseSchema, { token }),
    enabled: Boolean(token) && query.trim().length >= 2,
    placeholderData: keepPreviousData,
  })
}

export function useArtwork(artworkId: string) {
  const { token } = useAuth()
  return useQuery({
    queryKey: queryKeys.artwork(artworkId),
    queryFn: () => apiFetch(`/api/auctioneer/artworks/${encodeURIComponent(artworkId)}`, artworkResponseSchema, { token }),
    enabled: Boolean(token) && Boolean(artworkId),
  })
}

export function useOwnLots(status = 'all', page = 1) {
  const { token } = useAuth()
  return useQuery({
    queryKey: queryKeys.ownLots(status, page),
    queryFn: () => apiFetch(`/api/auctioneer/lots?page=${page}&pageSize=12${status === 'all' ? '' : `&status=${status}`}`, auctioneerLotsResponseSchema, { token }),
    enabled: Boolean(token),
    placeholderData: keepPreviousData,
  })
}

export function useAuctioneerResults(page = 1) {
  const { token } = useAuth()
  return useQuery({
    queryKey: queryKeys.results(page),
    queryFn: () => apiFetch(`/api/auctioneer/results?page=${page}&pageSize=12`, auctioneerResultsResponseSchema, { token }),
    enabled: Boolean(token),
  })
}

export type CreateLotInput = {
  artworkId: string
  title: string
  description?: string
  startingBidCents: number
  minimumIncrementCents: number
  startsAt: string
  endsAt: string
}

export function useCreateLot() {
  const { token } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ input, idempotencyKey }: { input: CreateLotInput; idempotencyKey: string }) => apiFetch('/api/auctioneer/lots', auctioneerLotResponseSchema, {
      method: 'POST', token, body: input, idempotencyKey,
    }),
    onSuccess: () => Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.ownLotsRoot }),
      queryClient.invalidateQueries({ queryKey: queryKeys.lotsRoot }),
      queryClient.invalidateQueries({ queryKey: ['results'] }),
    ]).then(() => undefined),
  })
}

export function useCancelLot() {
  const { token } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ lotId, idempotencyKey }: { lotId: string; idempotencyKey: string }) => apiFetch(`/api/auctioneer/lots/${encodeURIComponent(lotId)}/cancel`, auctioneerLotResponseSchema, {
      method: 'POST', token, body: { confirmation: 'CANCELAR' }, idempotencyKey,
    }),
    onSuccess: () => Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.ownLotsRoot }),
      queryClient.invalidateQueries({ queryKey: queryKeys.lotsRoot }),
      queryClient.invalidateQueries({ queryKey: ['results'] }),
    ]).then(() => undefined),
  })
}
