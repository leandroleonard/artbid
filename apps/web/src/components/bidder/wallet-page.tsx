'use client'

import Link from 'next/link'
import { useState } from 'react'
import { buttonClass } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { PageTitle } from '@/components/ui/states'
import { BalanceCards, MovementsList } from './wallet-components'

export function WalletPage() {
  const [page, setPage] = useState(1)
  return <main className="page"><PageTitle kicker="Conta" title="Minha carteira" description="Créditos de licitação." action={<Link className={buttonClass()} href="/bidder/wallet/add"><Icon name="plus"/> Adicionar saldo</Link>}/><div className="demo-banner"><Icon name="wallet"/><span></span></div><BalanceCards/><section className="dashboard-section"><div className="section-heading compact"><div><p className="kicker">Movimentações</p><h2>Histórico de movimentos</h2></div></div><MovementsList page={page} onPage={setPage}/></section></main>
}
