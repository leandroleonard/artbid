import type { Metadata } from 'next'
import { ArtworkPreviewPage } from '@/components/auctioneer/artwork-preview-page'
export const metadata: Metadata = { title: 'Pré-visualizar obra' }
export default async function Page({ params }: { params: Promise<{ artworkId: string }> }) {
  const { artworkId } = await params
  return <ArtworkPreviewPage artworkId={artworkId}/>
}
