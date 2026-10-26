import type { Metadata } from 'next'
import { WalletPage } from '@/components/bidder/wallet-page'
export const metadata: Metadata = { title: 'Carteira' }
export default function Page() { return <WalletPage/> }
