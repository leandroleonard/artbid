import type { Metadata } from 'next'
import { Suspense } from 'react'
import { CreateLotPage } from '@/components/auctioneer/create-lot-page'
import { LoadingState } from '@/components/ui/states'
export const metadata: Metadata = { title: 'Criar novo lote' }
export default function Page() { return <Suspense fallback={<main className="section page"><LoadingState/></main>}><CreateLotPage/></Suspense> }
