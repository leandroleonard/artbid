import type { Metadata } from 'next'
import { AuctioneerDashboard } from '@/components/auctioneer/auctioneer-dashboard'
export const metadata: Metadata = { title: 'Admin' }
export default function Page() { return <AuctioneerDashboard/> }
