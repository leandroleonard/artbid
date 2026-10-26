import { z } from 'zod'

export const roleSchema = z.enum(['bidder', 'auctioneer'])
export const userSchema = z.object({
  id: z.string(),
  displayName: z.string(),
  email: z.email(),
  role: roleSchema,
  createdAt: z.iso.datetime(),
})
export const authResponseSchema = z.object({
  data: z.object({
    user: userSchema,
    accessToken: z.string().min(1),
    expiresAt: z.iso.datetime(),
    demo: z.boolean(),
  }),
})
export const sessionResponseSchema = authResponseSchema
export const userResponseSchema = z.object({ data: userSchema })

export const paginationSchema = z.object({
  page: z.number().int().positive(),
  pageSize: z.number().int().positive(),
  totalItems: z.number().int().nonnegative(),
  totalPages: z.number().int().nonnegative(),
})

export function dataResponseSchema<T extends z.ZodType>(schema: T) {
  return z.object({ data: schema })
}

export function paginatedResponseSchema<T extends z.ZodType>(schema: T) {
  return z.object({ data: z.array(schema), pagination: paginationSchema })
}

export const lotStatusSchema = z.enum(['scheduled', 'live', 'ended'])
export const privateLotStatusSchema = z.enum(['scheduled', 'live', 'ended', 'cancelled'])
export const lotSchema = z.object({
  id: z.string(),
  number: z.string(),
  title: z.string(),
  artist: z.string(),
  artworkDate: z.string(),
  description: z.string().nullable(),
  imageUrl: z.string(),
  imageAlt: z.string(),
  externalArtworkId: z.string().nullable(),
  status: lotStatusSchema,
  startingBidCents: z.number().int().nonnegative(),
  currentBidCents: z.number().int().nonnegative(),
  minimumIncrementCents: z.number().int().positive(),
  nextMinimumBidCents: z.number().int().nonnegative(),
  startsAt: z.iso.datetime(),
  endsAt: z.iso.datetime(),
  bidCount: z.number().int().nonnegative(),
  createdAt: z.iso.datetime(),
})
export const lotsResponseSchema = paginatedResponseSchema(lotSchema)
export const lotResponseSchema = dataResponseSchema(lotSchema)

export const publicBidSchema = z.object({
  id: z.string(),
  bidderAlias: z.string(),
  amountCents: z.number().int().positive(),
  createdAt: z.iso.datetime(),
})
export const viewerPositionSchema = z.object({
  status: z.enum(['none', 'leading', 'outbid', 'won', 'lost']),
  highestBidCents: z.number().int().nonnegative(),
  committedCents: z.number().int().nonnegative(),
})
export const roomSchema = z.object({
  lot: lotSchema,
  publicBids: z.array(publicBidSchema),
  viewerPosition: viewerPositionSchema.nullable(),
  serverTime: z.iso.datetime(),
})
export const roomResponseSchema = dataResponseSchema(roomSchema)

export const walletSchema = z.object({
  totalCents: z.number().int().nonnegative(),
  committedCents: z.number().int().nonnegative(),
  availableCents: z.number().int().nonnegative(),
  currency: z.literal('BRL'),
  asOf: z.iso.datetime(),
})
export const walletResponseSchema = dataResponseSchema(walletSchema)
export const movementSchema = z.object({
  id: z.string(),
  type: z.enum(['deposit', 'hold', 'release', 'settlement']),
  amountCents: z.number().int(),
  description: z.string(),
  lotId: z.string().nullable(),
  balanceAfterCents: z.number().int().nonnegative(),
  createdAt: z.iso.datetime(),
})
export const movementsResponseSchema = paginatedResponseSchema(movementSchema)
export const depositResponseSchema = dataResponseSchema(z.object({
  movement: movementSchema,
  wallet: walletSchema,
}))

export const bidSchema = z.object({
  id: z.string(),
  lotId: z.string(),
  lotTitle: z.string(),
  amountCents: z.number().int().positive(),
  status: z.enum(['leading', 'outbid', 'won', 'lost']),
  createdAt: z.iso.datetime(),
})
export const bidsResponseSchema = paginatedResponseSchema(bidSchema)
export const bidAcceptedResponseSchema = dataResponseSchema(z.object({
  bid: bidSchema,
  room: z.object({
    currentBidCents: z.number().int().nonnegative(),
    nextMinimumBidCents: z.number().int().nonnegative(),
    endsAt: z.iso.datetime(),
    bidCount: z.number().int().nonnegative(),
  }),
  wallet: walletSchema,
}))

export const receiptSchema = z.object({
  id: z.string(),
  lotId: z.string(),
  lotNumber: z.string(),
  title: z.string(),
  artist: z.string(),
  imageUrl: z.string(),
  finalAmountCents: z.number().int().nonnegative(),
  currency: z.literal('BRL'),
  winnerAlias: z.string(),
  closedAt: z.iso.datetime(),
  settledAt: z.iso.datetime(),
  verificationId: z.string(),
  integrityStatus: z.enum(['verified', 'failed', 'unavailable']),
})
export const receiptResponseSchema = dataResponseSchema(receiptSchema)
export const wonLotSchema = z.object({
  lot: lotSchema,
  finalAmountCents: z.number().int().nonnegative(),
  settledAt: z.iso.datetime(),
  receiptId: z.string(),
})
export const wonResponseSchema = paginatedResponseSchema(wonLotSchema)

export const artworkSchema = z.object({
  id: z.string(),
  title: z.string(),
  artist: z.string(),
  date: z.string(),
  description: z.string().nullable(),
  imageUrl: z.string(),
  imageAlt: z.string(),
  source: z.literal('Art Institute of Chicago'),
})
export const artworksResponseSchema = paginatedResponseSchema(artworkSchema)
export const artworkResponseSchema = dataResponseSchema(artworkSchema)

export const auctioneerLotSchema = lotSchema.extend({
  status: privateLotStatusSchema,
  cancelledAt: z.iso.datetime().nullable(),
  cancellationReason: z.string().nullable(),
  finalAmountCents: z.number().int().nonnegative().nullable(),
  revenueCents: z.number().int().nonnegative().nullable(),
  winnerAlias: z.string().nullable(),
})
export const auctioneerLotsResponseSchema = paginatedResponseSchema(auctioneerLotSchema)
export const auctioneerLotResponseSchema = dataResponseSchema(auctioneerLotSchema)
export const auctioneerResultsSchema = z.object({
  summary: z.object({
    totalLots: z.number().int().nonnegative(),
    liveLots: z.number().int().nonnegative(),
    endedLots: z.number().int().nonnegative(),
    totalRevenueCents: z.number().int().nonnegative(),
    currency: z.literal('BRL'),
  }),
  lots: z.array(auctioneerLotSchema),
})
export const auctioneerResultsResponseSchema = z.object({
  data: auctioneerResultsSchema,
  pagination: paginationSchema,
})

export const auditEventSchema = z.object({
  id: z.string(),
  sequence: z.number().int().positive(),
  type: z.string(),
  actorAlias: z.string().nullable(),
  amountCents: z.number().int().nonnegative().nullable(),
  occurredAt: z.iso.datetime(),
  hash: z.string(),
  previousHash: z.string().nullable(),
})
export const auditLogSchema = z.object({
  lotId: z.string(),
  events: z.array(auditEventSchema),
  integrity: z.object({
    status: z.enum(['verified', 'failed', 'unavailable']),
    checkedEventCount: z.number().int().nonnegative(),
    totalEventCount: z.number().int().nonnegative(),
    algorithm: z.string(),
    expectedHash: z.string().nullable(),
    calculatedHash: z.string().nullable(),
    verifiedAt: z.iso.datetime(),
    verificationDataUrl: z.string().nullable(),
  }),
})
export const auditResponseSchema = z.object({ data: auditLogSchema, pagination: paginationSchema })

export const apiErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    fieldErrors: z.record(z.string(), z.array(z.string())).optional(),
    requestId: z.string().optional(),
    retryable: z.boolean().optional(),
  }),
})

export type Role = z.infer<typeof roleSchema>
export type User = z.infer<typeof userSchema>
export type AuthResponse = z.infer<typeof authResponseSchema>
export type Lot = z.infer<typeof lotSchema>
export type LotStatus = z.infer<typeof lotStatusSchema>
export type LotsResponse = z.infer<typeof lotsResponseSchema>
export type Room = z.infer<typeof roomSchema>
export type RoomResponse = z.infer<typeof roomResponseSchema>
export type PublicBid = z.infer<typeof publicBidSchema>
export type Wallet = z.infer<typeof walletSchema>
export type Movement = z.infer<typeof movementSchema>
export type Bid = z.infer<typeof bidSchema>
export type BidAcceptedResponse = z.infer<typeof bidAcceptedResponseSchema>
export type Receipt = z.infer<typeof receiptSchema>
export type WonLot = z.infer<typeof wonLotSchema>
export type Artwork = z.infer<typeof artworkSchema>
export type AuctioneerLot = z.infer<typeof auctioneerLotSchema>
export type AuctioneerResultsResponse = z.infer<typeof auctioneerResultsResponseSchema>
export type AuditLog = z.infer<typeof auditLogSchema>
export type AuditResponse = z.infer<typeof auditResponseSchema>
export type Pagination = z.infer<typeof paginationSchema>
