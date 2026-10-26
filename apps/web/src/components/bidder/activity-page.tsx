'use client'

import Link from 'next/link'
import { useState } from 'react'
import { EmptyState, ErrorState, LoadingState, PageTitle, Pagination } from '@/components/ui/states'
import { useBidHistory } from '@/hooks/use-bids'
import { getErrorMessage } from '@/lib/api/client'
import { formatDateTime, formatMoney } from '@/lib/format'

const statusLabels = { leading: 'A liderar', outbid: 'Ultrapassado', won: 'Ganho', lost: 'Não arrematado' }

export function ActivityPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('all')
  const bids = useBidHistory(page, status)
  return <main className="page"><PageTitle kicker="Actividade" title="Histórico de lances" description="Acompanhe lances aceites, mudanças de liderança e resultados oficiais."/><div className="catalog-tools"><label className="field">Filtrar por posição<select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }}><option value="all">Todos os estados</option><option value="leading">A liderar</option><option value="outbid">Ultrapassados</option><option value="won">Ganhos</option><option value="lost">Não arrematados</option></select></label></div>{bids.isLoading ? <LoadingState/> : bids.isError ? <ErrorState message={getErrorMessage(bids.error)} onRetry={() => void bids.refetch()}/> : bids.data?.data.length ? <><div className="data-table-wrap"><table className="data-table"><thead><tr><th>Obra</th><th>Meu lance</th><th>Estado</th><th>Data</th><th><span className="sr-only">Abrir</span></th></tr></thead><tbody>{bids.data.data.map((bid) => <tr key={bid.id}><td><strong>{bid.lotTitle}</strong><small>{bid.lotId}</small></td><td className="numeric">{formatMoney(bid.amountCents)}</td><td>{statusLabels[bid.status]}</td><td>{formatDateTime(bid.createdAt)}</td><td><Link href={`/lots/${bid.lotId}`}>Abrir lote</Link></td></tr>)}</tbody></table></div><Pagination page={page} totalPages={bids.data.pagination.totalPages} onPage={setPage}/></> : <EmptyState title="Nenhum lance neste filtro" message="Altere o filtro ou explore os leilões disponíveis." action={<Link href="/lots">Explorar lotes</Link>}/>}</main>
}
