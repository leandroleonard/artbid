import type { Metadata } from 'next'
import { ManageLotsPage } from '@/components/auctioneer/manage-lots-page'
export const metadata: Metadata = { title: 'Os meus lotes' }
export default function Page() { return <ManageLotsPage/> }
