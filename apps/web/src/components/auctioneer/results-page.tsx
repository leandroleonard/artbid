'use client'

import { useState } from 'react'
import { EmptyState, ErrorState, LoadingState, PageTitle, Pagination, StatusBadge } from '@/components/ui/states'
import { useAuctioneerResults } from '@/hooks/use-auctioneer'
import { getErrorMessage } from '@/lib/api/client'
import { formatDateTime, formatMoney } from '@/lib/format'

export function ResultsPage() {
  const [page, setPage] = useState(1)
  const results = useAuctioneerResults(page)
  return <main className="page"><PageTitle kicker="Histórico" title="Resultados e receitas" description="Somente valores finais."/>{results.isLoading ? <LoadingState/> : results.isError || !results.data ? <ErrorState message={getErrorMessage(results.error)} onRetry={() => void results.refetch()}/> : <><div className="dashboard-grid"><div className="metric-card primary"><span>Receita total liquidada</span><strong>{formatMoney(results.data.data.summary.totalRevenueCents)}</strong><small>Sem cálculo no browser</small></div><div className="metric-card"><span>Lotes encerrados</span><strong>{results.data.data.summary.endedLots}</strong><small>Histórico próprio</small></div><div className="metric-card"><span>Total de lotes</span><strong>{results.data.data.summary.totalLots}</strong><small>{results.data.data.summary.liveLots} actualmente em curso</small></div></div><section className="dashboard-section">{results.data.data.lots.length ? <><div className="data-table-wrap"><table className="data-table"><thead><tr><th>Lote</th><th>Estado</th><th>Valor final</th><th>Receita</th><th>Vencedor</th><th>Fim</th></tr></thead><tbody>{results.data.data.lots.map((lot) => <tr key={lot.id}><td><strong>{lot.title}</strong><small>Lote {lot.number}</small></td><td><StatusBadge status={lot.status}/></td><td className="numeric">{lot.finalAmountCents === null ? '—' : formatMoney(lot.finalAmountCents)}</td><td className="numeric">{lot.revenueCents === null ? '—' : formatMoney(lot.revenueCents)}</td><td>{lot.winnerAlias ?? '—'}</td><td>{formatDateTime(lot.endsAt)}</td></tr>)}</tbody></table></div><Pagination page={page} totalPages={results.data.pagination.totalPages} onPage={setPage}/></> : <EmptyState title="Ainda sem resultados" message="Os resultados aparecem depois do encerramento e da liquidação oficial."/>}</section></>}</main>
}
