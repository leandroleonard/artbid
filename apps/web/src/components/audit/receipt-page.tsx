'use client'

import Link from 'next/link'
import { useState } from 'react'
import { Button, buttonClass } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { ErrorState, LoadingState } from '@/components/ui/states'
import { useReceipt } from '@/hooks/use-audit'
import { getErrorMessage } from '@/lib/api/client'
import { formatDateTime, formatMoney } from '@/lib/format'

export function ReceiptPage({ receiptId }: { receiptId: string }) {
  const receipt = useReceipt(receiptId)
  const [copied, setCopied] = useState(false)
  if (receipt.isLoading) return <main className="section page"><LoadingState label="A consultar o comprovativo"/></main>
  if (receipt.isError || !receipt.data) return <main className="section page"><ErrorState title="Comprovativo indisponível" message={getErrorMessage(receipt.error)} onRetry={() => void receipt.refetch()}/></main>
  const data = receipt.data.data
  const copy = async () => {
    try { await navigator.clipboard.writeText(window.location.href); setCopied(true) } catch { setCopied(false) }
  }
  return <main className="receipt-page section"><div className="receipt"><div className="receipt-head"><div className="brand"><span className="brand-mark">A</span><span>ArtBid</span></div><span className={`receipt-status ${data.integrityStatus}`}><Icon name={data.integrityStatus === 'verified' ? 'shield' : 'alert'}/>{data.integrityStatus === 'verified' ? 'Verificado' : data.integrityStatus === 'failed' ? 'Falha de integridade' : 'Verificação indisponível'}</span></div><div className="receipt-title"><p className="kicker">Comprovativo de arremate</p><h1>Uma obra, um registo permanente.</h1><p>Emitido apenas após liquidação.</p></div><div className="receipt-art"><img src={data.imageUrl} alt={data.title}/><div><span>LOTE {data.lotNumber}</span><h2>{data.title}</h2><p>{data.artist}</p><small>Arrematado por</small><strong>{data.winnerAlias}</strong></div></div><div className="receipt-value"><span>Valor final</span><strong>{formatMoney(data.finalAmountCents)}</strong><small>Encerrado em {formatDateTime(data.closedAt)}</small></div><dl className="receipt-data"><div><dt>ID do comprovativo</dt><dd>{data.id}</dd></div><div><dt>ID de verificação</dt><dd>{data.verificationId}</dd></div><div><dt>Liquidação</dt><dd>{formatDateTime(data.settledAt)}</dd></div><div><dt>Integridade</dt><dd>{data.integrityStatus === 'verified' ? 'Verificada' : 'Não confirmada'}</dd></div></dl><div className="receipt-actions"><Link className={buttonClass('secondary')} href={`/audit?lotId=${data.lotId}`}>Auditar histórico</Link><Button onClick={copy}><Icon name="share"/> Copiar ligação</Button></div>{copied && <p className="copy-feedback" role="status">Ligação copiada.</p>}<p className="receipt-note"><Icon name="shield"/> Este comprovativo usa apenas identificadores  pseudónimos.</p></div></main>
}
