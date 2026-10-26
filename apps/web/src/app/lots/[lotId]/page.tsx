import type { Metadata } from 'next'
import { AuctionRoom } from '@/components/room/auction-room'

export const metadata: Metadata = { title: 'Sala do leilão' }

export default async function LotPage({ params }: { params: Promise<{ lotId: string }> }) {
  const { lotId } = await params
  return <AuctionRoom lotId={lotId}/>
}
