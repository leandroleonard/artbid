'use client'

import Link from 'next/link'
import { useState, type FormEvent } from 'react'
import { Button, buttonClass } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { EmptyState, ErrorState, LoadingState, PageTitle, Pagination } from '@/components/ui/states'
import { useArtworks } from '@/hooks/use-auctioneer'
import { getErrorMessage } from '@/lib/api/client'

export function ArtworkSearchPage() {
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const artworks = useArtworks(query, page)
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (search.trim().length < 2) return
    setQuery(search.trim()); setPage(1)
  }
  return <main className="page"><PageTitle kicker="Catálogo" title="Pesquisar obras" description="Consulte o Art Institute of Chicago."/><form className="catalog-tools" onSubmit={submit}><label className="search"><Icon name="search"/><input value={search} onChange={(event) => setSearch(event.target.value)} minLength={2} maxLength={100} placeholder="Título, artista ou termo" aria-label="Pesquisar no catálogo do Art Institute of Chicago"/></label><Button type="submit" disabled={search.trim().length < 2}>Pesquisar</Button></form><div className="dashboard-section">{!query ? <EmptyState title="Comece uma pesquisa" message="Indique pelo menos dois caracteres para consultar o catálogo."/> : artworks.isLoading ? <LoadingState label="A pesquisar obras"/> : artworks.isError ? <ErrorState message={getErrorMessage(artworks.error)} onRetry={() => void artworks.refetch()}/> : artworks.data?.data.length ? <><p className="results-line">{artworks.data.pagination.totalItems} resultados para “{query}”</p><div className="art-results">{artworks.data.data.map((artwork) => <article className="art-result" key={artwork.id}><img src={artwork.imageUrl} alt={artwork.imageAlt}/><span><strong>{artwork.title}</strong><small>{artwork.artist} · {artwork.date}</small><em>{artwork.id}</em></span><div className="art-result-actions"><Link className={buttonClass('secondary')} href={`/auctioneer/catalog/${artwork.id}`}>Pré-visualizar</Link><Link className={buttonClass()} href={`/auctioneer/lots/new?artwork=${artwork.id}`}>Seleccionar</Link></div></article>)}</div><Pagination page={page} totalPages={artworks.data.pagination.totalPages} onPage={setPage}/></> : <EmptyState title="Nenhuma obra encontrada" message="Tente outro título, artista ou termo." action={<Button variant="secondary" onClick={() => { setSearch(''); setQuery('') }}>Nova pesquisa</Button>}/>}</div></main>
}
