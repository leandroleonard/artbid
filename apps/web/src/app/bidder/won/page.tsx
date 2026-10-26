import type { Metadata } from 'next'
import { WonPage } from '@/components/bidder/won-page'
export const metadata: Metadata = { title: 'Lotes ganhos' }
export default function Page() { return <WonPage/> }
