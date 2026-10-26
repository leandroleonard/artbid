'use client'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { EmptyState, ErrorState, LoadingState, PageTitle, Pagination } from '@/components/ui/states'
import { useAudit } from '@/hooks/use-audit'
import { useLots } from '@/hooks/use-lots'
import { getErrorMessage } from '@/lib/api/client'
import { formatDateTime, formatMoney, formatTime } from '@/lib/format'

export function AuditPage() {
  const searchParams = useSearchParams()
  const [selectedLotId, setLotId] = useState(searchParams.get('lotId') ?? '')
  const [page, setPage] = useState(1)
  const lots = useLots({ pageSize: 50, sort: 'recent' })
  const lotId = selectedLotId || lots.data?.data[0]?.id || ''
  const audit = useAudit(lotId, page)

  const exportData = () => {
    if (!audit.data) return
    const url = URL.createObjectURL(new Blob([JSON.stringify(audit.data, null, 2)], { type: 'application/json' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `artbid-auditoria-${lotId}.json`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const integrity = audit.data?.data.integrity
  return <main className="section page audit-page"><PageTitle kicker="Verificação" title="Auditoria de leilões" description="Consulte eventos cronológicos e pseudonimizados."/>
    <div className="audit-toolbar"><label className="field">Lote a auditar<select className="input" value={lotId} onChange={(event) => { setLotId(event.target.value); setPage(1) }} disabled={lots.isLoading}><option value="">Seleccione um lote</option>{lots.data?.data.map((lot) => <option key={lot.id} value={lot.id}>Lote {lot.number} · {lot.title}</option>)}</select></label><Button variant="secondary" onClick={exportData} disabled={!audit.data}><Icon name="file"/> Exportar dados</Button></div>
    {lots.isError && <ErrorState message={getErrorMessage(lots.error)} onRetry={() => void lots.refetch()}/>} 
    {!lotId && !lots.isLoading ? <EmptyState title="Seleccione um lote" message="Escolha um lote para consultar a sua cadeia de eventos."/> : audit.isLoading ? <LoadingState label="A consultar a auditoria"/> : audit.isError ? <ErrorState message={getErrorMessage(audit.error)} onRetry={() => void audit.refetch()}/> : audit.data && integrity ? <>
      <div className={`integrity-card ${integrity.status}`}><div className={`seal ${integrity.status}`}><Icon name={integrity.status === 'verified' ? 'shield' : 'alert'} size={28}/></div><div><span>Estado de integridade reportado</span><h2>{integrity.status === 'verified' ? 'Histórico íntegro' : integrity.status === 'failed' ? 'Falha de integridade' : 'Verificação indisponível'}</h2><p>{integrity.status === 'verified' ? '' : integrity.status === 'failed' ? 'Divergência encontrada. Não trate este histórico como verificado.' : 'Verificação em curso.'}</p></div><dl><div><dt>Eventos verificados</dt><dd>{integrity.checkedEventCount} de {integrity.totalEventCount}</dd></div><div><dt>Última verificação</dt><dd>{formatDateTime(integrity.verifiedAt)}</dd></div></dl></div>
      <div className="audit-layout"><div className="timeline"><div className="section-heading compact"><div><p className="kicker">Cadeia de eventos</p><h2>Histórico integral</h2></div><Link href={`/lots/${lotId}`}>Voltar ao lote</Link></div>{audit.data.data.events.length ? audit.data.data.events.map((event) => <div className="event" key={event.id}><span className="event-no">{event.sequence}</span><div><span className="audit-event-type">{event.type}</span><strong>{event.actorAlias ?? 'Sistema'}</strong><small>{formatTime(event.occurredAt)}</small></div><strong>{event.amountCents === null ? '—' : formatMoney(event.amountCents)}</strong><div className="hash"><small>Hash reportado</small><code>{event.hash}</code><small>{event.previousHash ? 'Referencia evento anterior' : 'Evento inicial'}</small></div></div>) : <p className="audit-empty-events">Não existem eventos nesta página.</p>}<Pagination page={page} totalPages={audit.data.pagination.totalPages} onPage={setPage}/></div>
      <aside className="verify-panel"><p className="kicker">Checkpoint final</p><div><small>Código</small><code>{integrity.expectedHash ?? 'Não disponibilizado'}</code></div><div><small>Código apresentado</small><code>{integrity.calculatedHash ?? 'Não disponibilizado'}</code></div><p className={integrity.status === 'verified' ? '' : 'limitation'}><Icon name={integrity.status === 'verified' ? 'check' : 'alert'}/> {integrity.status === 'verified' ? 'Correspondência confirmada' : 'Sem confirmação'}</p><hr/><h3>Como funciona?</h3><p>O comparação entre a cadeia de resultados e apresentação dos dados.</p><p className="limitation">Reportado: {integrity.algorithm}. A protecção do checkpoint é indispensável.</p></aside></div>
    </> : null}
  </main>
}
