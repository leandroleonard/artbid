import type { Metadata } from 'next'
import { ArtworkSearchPage } from '@/components/auctioneer/artwork-search-page'
export const metadata: Metadata = { title: 'Pesquisar obras' }
export default function Page() { return <ArtworkSearchPage/> }
