'use client'

import { useState, type FormEvent } from 'react'
import { LotCard } from './lot-card'
import { useLots } from '@/hooks/use-lots'
import type { LotStatus } from '@/lib/api/contract'
import { Button } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { EmptyState, ErrorState, LoadingState, PageTitle, Pagination } from '@/components/ui/states'
import { getErrorMessage } from '@/lib/api/client'

const tabs: { label: string; value?: LotStatus }[] = [
  { label: 'Todos' }, { label: 'Ao vivo', value: 'live' }, { label: 'Agendados', value: 'scheduled' }, { label: 'Encerrados', value: 'ended' },
]

export function CatalogPage() {
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<LotStatus | undefined>()
  const [sort, setSort] = useState('endingSoon')
  const [page, setPage] = useState(1)
  const lots = useLots({ q: query || undefined, status, sort, page, pageSize: 12 })

  const submitSearch = (event: FormEvent) => {
    event.preventDefault()
    setQuery(search.trim())
    setPage(1)
  }
  const clear = () => {
    setSearch(''); setQuery(''); setStatus(undefined); setSort('endingSoon'); setPage(1)
  }

  return <main className="section page"><PageTitle kicker="Catálogo de leilões" title="Descubra obras singulares" description="Explore lotes seleccionados e acompanhe as disputas através do estado."/>
    <form className="catalog-tools" onSubmit={submitSearch}><label className="search"><Icon name="search"/><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Pesquisar por obra ou artista" aria-label="Pesquisar por obra ou artista" maxLength={100}/></label><Button type="submit" variant="secondary">Pesquisar</Button><select aria-label="Ordenar lotes" value={sort} onChange={(event) => { setSort(event.target.value); setPage(1) }}><option value="endingSoon">Fim mais próximo</option><option value="recent">Mais recentes</option><option value="highestBid">Maior valor actual</option></select></form>
    <div className="tabs" role="group" aria-label="Filtrar por estado">{tabs.map((tab) => <button key={tab.label} className={status === tab.value ? 'active' : ''} aria-pressed={status === tab.value} onClick={() => { setStatus(tab.value); setPage(1) }}>{tab.label}</button>)}</div>
    <div className="results-line"><span>{lots.data ? `${lots.data.pagination.totalItems} ${lots.data.pagination.totalItems === 1 ? 'lote encontrado' : 'lotes encontrados'}` : 'A consultar o catálogo'}</span>{(query || status) && <button onClick={clear}>Limpar filtros</button>}</div>
    {lots.isLoading ? <LoadingState label="A carregar o catálogo"/> : lots.isError ? <ErrorState message={getErrorMessage(lots.error)} onRetry={() => void lots.refetch()}/> : lots.data?.data.length ? <><div className="lot-grid catalog">{lots.data.data.map((lot) => <LotCard key={lot.id} lot={lot}/>)}</div><Pagination page={page} totalPages={lots.data.pagination.totalPages} onPage={setPage}/></> : <EmptyState title="Nenhuma obra encontrada" message="Tente remover filtros ou pesquisar por outro termo." action={<Button variant="secondary" onClick={clear}>Limpar filtros</Button>}/>} 
  </main>
}
