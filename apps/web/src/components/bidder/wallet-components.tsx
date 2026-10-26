'use client'

import { useMovements, useWallet } from '@/hooks/use-wallet'
import { formatDateTime, formatMoney } from '@/lib/format'
import { getErrorMessage } from '@/lib/api/client'
import { EmptyState, ErrorState, LoadingState, Pagination } from '@/components/ui/states'

export function BalanceCards() {
  const wallet = useWallet()
  if (wallet.isLoading) return <LoadingState label="A consultar o saldo"/>
  if (wallet.isError || !wallet.data) return <ErrorState message={getErrorMessage(wallet.error)} onRetry={() => void wallet.refetch()}/>
  const data = wallet.data.data
  return <><div className="balance-grid"><div className="balance primary"><span>Saldo total</span><strong>{formatMoney(data.totalCents)}</strong><small>Créditos</small></div><div className="balance"><span>Comprometido</span><strong>{formatMoney(data.committedCents)}</strong><small>Reservado em lances líderes</small></div><div className="balance"><span>Disponível</span><strong>{formatMoney(data.availableCents)}</strong><small>Para novos lances</small></div></div><p className="field-help">Estado oficial em {formatDateTime(data.asOf)}. Nenhuma alteração optimista é aplicada no browser.</p></>
}

export function MovementsList({ page = 1, onPage, compact = false }: { page?: number; onPage?: (page: number) => void; compact?: boolean }) {
  const movements = useMovements(page)
  if (movements.isLoading) return <LoadingState label="A carregar movimentos"/>
  if (movements.isError) return <ErrorState message={getErrorMessage(movements.error)} onRetry={() => void movements.refetch()}/>
  if (!movements.data?.data.length) return <EmptyState title="Sem movimentos" message="Os depósitos, reservas e libertações confirmados aparecerão aqui."/>
  const items = compact ? movements.data.data.slice(0, 5) : movements.data.data
  const labels = { deposit: 'Depósito', hold: 'Saldo comprometido', release: 'Saldo libertado', settlement: 'Liquidação' }
  return <><div className="activity-list">{items.map((movement) => <div className="activity-row" key={movement.id}><span><strong>{labels[movement.type]}</strong><small>{movement.description}</small></span><span className={`amount ${movement.amountCents > 0 ? 'positive' : 'negative'}`}>{movement.amountCents > 0 ? '+' : '−'} {formatMoney(Math.abs(movement.amountCents))}</span><small>{formatDateTime(movement.createdAt)}</small></div>)}</div>{!compact && onPage && <Pagination page={page} totalPages={movements.data.pagination.totalPages} onPage={onPage}/>}</>
}
