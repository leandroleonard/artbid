'use client'

import Link from 'next/link'
import type { ReactNode } from 'react'
import type { Role } from '@/lib/api/contract'
import { buttonClass } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { LoadingState } from '@/components/ui/states'
import { useAuth } from './auth-provider'

export function RoleGate({ role, children }: { role: Role; children: ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <main className="section page"><LoadingState label="A validar a sessão"/></main>
  if (!user) return <main className="section page"><section className="access-panel"><Icon name="shield" size={34}/><p className="kicker">Área reservada</p><h1>Inicie sessão para continuar</h1><p>Esta área contém dados privados e requer uma sessão de {role === 'bidder' ? 'licitante' : 'leiloeiro'}.</p><Link className={buttonClass()} href="/login">Iniciar sessão</Link></section></main>
  if (user.role !== role) return <main className="section page"><section className="access-panel"><Icon name="alert" size={34}/><p className="kicker">Acesso negado</p><h1>Este painel pertence a outro perfil</h1><Link className={buttonClass()} href={user.role === 'bidder' ? '/bidder' : '/auctioneer'}>Abrir o meu painel</Link></section></main>
  return children
}
