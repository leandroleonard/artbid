'use client'

import Link from 'next/link'
import { buttonClass } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { ErrorState, LoadingState } from '@/components/ui/states'
import { useArtwork } from '@/hooks/use-auctioneer'
import { getErrorMessage } from '@/lib/api/client'

export function ArtworkPreviewPage({ artworkId }: { artworkId: string }) {
  const artwork = useArtwork(artworkId)
  if (artwork.isLoading) return <main className="page"><LoadingState label="A carregar a obra seleccionada"/></main>
  if (artwork.isError || !artwork.data) return <main className="page"><ErrorState message={getErrorMessage(artwork.error)} onRetry={() => void artwork.refetch()}/></main>
  const data = artwork.data.data
  return <main className="page"><div className="breadcrumb"><Link href="/auctioneer/catalog">Pesquisar obras</Link><span>/</span><span>{data.id}</span></div><div className="artwork-layout"><div className="artwork-preview"><img src={data.imageUrl} alt={data.imageAlt}/></div><aside className="artwork-details"><p className="kicker">Obra seleccionada</p><h1>{data.title}</h1><p className="artist">{data.artist}, {data.date}</p><p>{data.description ?? 'Sem descrição fornecida pela fonte externa.'}</p><dl><div><dt>ID</dt><dd>{data.id}</dd></div><div><dt>Fonte</dt><dd>{data.source}</dd></div><div><dt>Integração</dt><dd>Normalizada</dd></div></dl><Link className={buttonClass()} href={`/auctioneer/lots/new?artwork=${data.id}`}>Configurar leilão <Icon name="arrow"/></Link><p className="form-note"><Icon name="shield"/>Os dados essenciais serão novamente validados ao publicar.</p></aside></div></main>
}
