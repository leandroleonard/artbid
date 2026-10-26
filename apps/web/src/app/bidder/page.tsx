import type { Metadata } from 'next'
import { BidderDashboard } from '@/components/bidder/bidder-dashboard'
export const metadata: Metadata = { title: 'Painel' }
export default function Page() { return <BidderDashboard/> }
