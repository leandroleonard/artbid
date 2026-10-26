'use client'

import Link from 'next/link'
import { useRef, useState } from 'react'
import { Button, buttonClass } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Icon } from '@/components/ui/icon'
import { EmptyState, ErrorState, LoadingState, PageTitle, Pagination, StatusBadge } from '@/components/ui/states'
import { useCancelLot, useOwnLots } from '@/hooks/use-auctioneer'
import { getErrorMessage } from '@/lib/api/client'
import type { AuctioneerLot } from '@/lib/api/contract'
import { formatMoney } from '@/lib/format'

const tabs = [{ value: 'all', label: 'Todos' }, { value: 'scheduled', label: 'Agendados' }, { value: 'live', label: 'Ao vivo' }, { value: 'ended', label: 'Encerrados' }, { value: 'cancelled', label: 'Cancelados' }]

export function ManageLotsPage() {
  const [status, setStatus] = useState('all')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<AuctioneerLot | null>(null)
  const [confirmation, setConfirmation] = useState('')
  const [feedback, setFeedback] = useState<{ type: 'error' | 'success'; text: string } | null>(null)
  const idempotencyKey = useRef<string | null>(null)
  const lots = useOwnLots(status, page)
  const cancel = useCancelLot()

  const openCancel = (lot: AuctioneerLot) => {
    setSelected(lot); setConfirmation(''); setFeedback(null); idempotencyKey.current = crypto.randomUUID()
  }
  const close = () => { if (!cancel.isPending) { setSelected(null); setConfirmation(''); idempotencyKey.current = null } }
  const confirmCancel = async () => {
    if (!selected || confirmation !== 'CANCELAR' || !idempotencyKey.current) return
    setFeedback(null)
    try {
      const response = await cancel.mutateAsync({ lotId: selected.id, idempotencyKey: idempotencyKey.current })
      setFeedback({ type: 'success', text: `Cancelamento confirmato. Lote: ${response.data.number}.` })
      setSelected(null)
    } catch (error) { setFeedback({ type: 'error', text: getErrorMessage(error) }) }
  }

  return <main className="page"><PageTitle kicker="Gestão" title="Os meus lotes" description="Apenas lotes da sua conta. " action={<Link className={buttonClass()} href="/auctioneer/catalog"><Icon name="plus"/> Novo lote</Link>}/><div className="tabs" role="group" aria-label="Estado dos lotes">{tabs.map((tab) => <button key={tab.value} className={status === tab.value ? 'active' : ''} aria-pressed={status === tab.value} onClick={() => { setStatus(tab.value); setPage(1) }}>{tab.label}</button>)}</div>{feedback && (feedback.type === 'success' || !selected) && <div className={`form-${feedback.type}`} role={feedback.type === 'error' ? 'alert' : 'status'}>{feedback.text}</div>}<div className="dashboard-section">{lots.isLoading ? <LoadingState/> : lots.isError ? <ErrorState message={getErrorMessage(lots.error)} onRetry={() => void lots.refetch()}/> : lots.data?.data.length ? <><div className="data-table-wrap"><table className="data-table"><thead><tr><th>Obra</th><th>Estado</th><th>Valor actual</th><th>Lances</th><th>Acções</th></tr></thead><tbody>{lots.data.data.map((lot) => <tr key={lot.id}><td><div className="table-art"><img src={lot.imageUrl} alt=""/><span><strong>{lot.title}</strong><small>Lote {lot.number}</small></span></div></td><td><StatusBadge status={lot.status}/></td><td className="numeric">{formatMoney(lot.currentBidCents)}</td><td>{lot.bidCount}</td><td><div className="room-tools">{lot.status !== 'cancelled' && <Link href={`/lots/${lot.id}`}>Ver</Link>}{lot.status !== 'ended' && lot.status !== 'cancelled' && (lot.bidCount === 0 ? <Button variant="text" onClick={() => openCancel(lot)}><Icon name="trash"/> Cancelar</Button> : <span className="field-help" title="Lotes com lances não podem ser cancelados">Não cancelável</span>)}</div></td></tr>)}</tbody></table></div><Pagination page={page} totalPages={lots.data.pagination.totalPages} onPage={setPage}/></> : <EmptyState title="Nenhum lote neste estado" message="Altere o filtro ou pesquise uma obra para criar um lote." action={<Link className={buttonClass()} href="/auctioneer/catalog">Criar lote</Link>}/>}</div>
    <Dialog open={Boolean(selected)} onClose={close} title="Cancelar lote?"><p>Esta acção só será aplicada se o lote é seu, não tem lances e pode ser cancelado.</p>{selected && <p><strong>Lote {selected.number} · {selected.title}</strong></p>}<label className="field">Escreva CANCELAR para confirmar<input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} autoComplete="off"/></label>{feedback?.type === 'error' && <div className="form-error" role="alert">{feedback.text}</div>}<div className="dialog-actions"><Button variant="secondary" onClick={close} disabled={cancel.isPending}>Manter lote</Button><Button variant="danger" onClick={() => void confirmCancel()} disabled={confirmation !== 'CANCELAR' || cancel.isPending}>{cancel.isPending ? 'A confirmar…' : 'Cancelar lote'}</Button></div></Dialog>
  </main>
}
