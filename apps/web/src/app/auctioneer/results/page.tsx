import type { Metadata } from 'next'
import { ResultsPage } from '@/components/auctioneer/results-page'
export const metadata: Metadata = { title: 'Resultados e receitas' }
export default function Page() { return <ResultsPage/> }
