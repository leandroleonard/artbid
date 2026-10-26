import type { Metadata } from 'next'
import { AddFundsPage } from '@/components/bidder/add-funds-page'
export const metadata: Metadata = { title: 'Adicionar saldo' }
export default function Page() { return <AddFundsPage/> }
