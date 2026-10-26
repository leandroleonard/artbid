'use client'

import Link from 'next/link'
import { useState } from 'react'
import { buttonClass } from '@/components/ui/button'
import { EmptyState, ErrorState, LoadingState, PageTitle, Pagination } from '@/components/ui/states'
import { useWonLots } from '@/hooks/use-bids'
import { getErrorMessage } from '@/lib/api/client'
import { formatDateTime, formatMoney } from '@/lib/format'

export function WonPage() {
  const [page, setPage] = useState(1)
  const won = useWonLots(page)
  return <main className="page"><PageTitle kicker="Arremates" title="Lotes ganhos" description="Resultados e comprovativos emitidos depois da liquidação."/>{won.isLoading ? <LoadingState/> : won.isError ? <ErrorState message={getErrorMessage(won.error)} onRetry={() => void won.refetch()}/> : won.data?.data.length ? <><div className="lot-grid catalog">{won.data.data.map((item) => <article className="lot-card" key={item.receiptId}><div className="lot-image"><img src={item.lot.imageUrl} alt={item.lot.imageAlt}/></div><div className="lot-body"><p className="eyebrow">Lote {item.lot.number} · {item.lot.artist}</p><h3>{item.lot.title}</h3><div className="lot-meta"><div><small>Valor final</small><strong>{formatMoney(item.finalAmountCents)}</strong></div><div><small>Liquidado</small><span>{formatDateTime(item.settledAt)}</span></div></div><Link href={`/receipts/${item.receiptId}`} className="lot-card-link">Abrir comprovativo →</Link></div></article>)}</div><Pagination page={page} totalPages={won.data.pagination.totalPages} onPage={setPage}/></> : <EmptyState title="Ainda sem lotes ganhos" message="Quando um arremate e a liquidação forem confirmados, o comprovativo ficará disponível aqui." action={<Link className={buttonClass()} href="/lots">Explorar leilões</Link>}/>}</main>
}
