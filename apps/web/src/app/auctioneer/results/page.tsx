import type { Metadata } from 'next'
import { ResultsPage } from '@/components/auctioneer/results-page'

export const metadata: Metadata = { title: 'Resultados e receitas' }
export const instant = false

export default function Page() {
  return <ResultsPage />
}
