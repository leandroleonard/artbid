'use client'

import Link from 'next/link'
import { useAuth } from '@/components/auth/auth-provider'
import { buttonClass } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { EmptyState, ErrorState, LoadingState, PageTitle } from '@/components/ui/states'
import { useBidHistory, useWonLots } from '@/hooks/use-bids'
import { getErrorMessage } from '@/lib/api/client'
import { formatDateTime, formatMoney } from '@/lib/format'
import { BalanceCards } from './wallet-components'

export function BidderDashboard() {
  const { user } = useAuth()
  const bids = useBidHistory()
  const won = useWonLots()
  return <main className="page"><PageTitle kicker="Área do licitante" title={`Olá, ${user?.displayName ?? 'licitante'}`} description="Consulte saldo, posição e actividade." action={<Link className={buttonClass()} href="/bidder/wallet/add"><Icon name="plus"/> Adicionar saldo</Link>}/>
    <BalanceCards/>
    <section className="dashboard-section"><div className="quick-links"><Link href="/bidder/activity" className="quick-link"><span><strong>Actividade de lances</strong><small>{bids.data ? `${bids.data.pagination.totalItems} lances no histórico` : 'Consultar posição e resultados'}</small></span><Icon name="arrow"/></Link><Link href="/bidder/won" className="quick-link"><span><strong>Lotes ganhos</strong><small>{won.data ? `${won.data.pagination.totalItems} comprovativos disponíveis` : 'Consultar arremates'}</small></span><Icon name="arrow"/></Link><Link href="/lots" className="quick-link"><span><strong>Explorar leilões</strong><small>Descobrir lotes em curso e agendados</small></span><Icon name="arrow"/></Link></div></section>
    <section className="dashboard-section"><div className="section-heading compact"><div><p className="kicker">Actividade recente</p><h2>Os meus últimos lances</h2></div><Link className={buttonClass('text')} href="/bidder/activity">Ver todos <Icon name="arrow"/></Link></div>{bids.isLoading ? <LoadingState/> : bids.isError ? <ErrorState message={getErrorMessage(bids.error)} onRetry={() => void bids.refetch()}/> : bids.data?.data.length ? <div className="activity-list">{bids.data.data.slice(0, 4).map((bid) => <Link href={`/lots/${bid.lotId}`} className="activity-row" key={bid.id}><span><strong>{bid.lotTitle}</strong><small>Lote {bid.lotId}</small></span><span className="amount">{formatMoney(bid.amountCents)}</span><small>{formatDateTime(bid.createdAt)}</small></Link>)}</div> : <EmptyState title="Ainda sem lances" message="Explore o catálogo para encontrar o primeiro lote." action={<Link href="/lots" className={buttonClass()}>Explorar lotes</Link>}/>}</section>
  </main>
}
