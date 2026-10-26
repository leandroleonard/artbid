import { z } from 'zod'

export const lotEventSchema = z.object({
  eventId: z.string().min(1),
  lotId: z.string().min(1),
  sequence: z.number().int().nonnegative(),
  occurredAt: z.iso.datetime(),
  type: z.enum(['bid.accepted', 'bid.outbid', 'lot.extended', 'lot.closed', 'lot.cancelled', 'lot.state.changed']),
}).passthrough()
export type LotEvent = z.infer<typeof lotEventSchema>
export type ConnectionStatus = 'connected' | 'reconnecting' | 'unavailable'
