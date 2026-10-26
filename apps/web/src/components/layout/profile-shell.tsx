'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { ReactNode } from 'react'
import { RoleGate } from '@/components/auth/role-gate'
import type { Role } from '@/lib/api/contract'
import { Icon, type IconName } from '@/components/ui/icon'

const navigation: Record<Role, { href: string; label: string; icon: IconName }[]> = {
  bidder: [
    { href: '/bidder', label: 'Visão geral', icon: 'home' },
    { href: '/bidder/wallet', label: 'Carteira', icon: 'wallet' },
    { href: '/bidder/activity', label: 'Actividade', icon: 'gavel' },
    { href: '/bidder/won', label: 'Lotes ganhos', icon: 'file' },
    { href: '/bidder/settings', label: 'Perfil', icon: 'settings' },
  ],
  auctioneer: [
    { href: '/auctioneer', label: 'Visão geral', icon: 'home' },
    { href: '/auctioneer/catalog', label: 'Pesquisar obras', icon: 'search' },
    { href: '/auctioneer/lots', label: 'Os meus lotes', icon: 'gavel' },
    { href: '/auctioneer/results', label: 'Resultados', icon: 'file' },
  ],
}

export function ProfileShell({ role, children }: { role: Role; children: ReactNode }) {
  const pathname = usePathname()
  return <RoleGate role={role}><div className="profile-shell section"><aside className="profile-sidebar"><p className="kicker">{role === 'bidder' ? 'Licitante' : 'Leiloeiro'}</p><nav aria-label={`Navegação de ${role === 'bidder' ? 'licitante' : 'leiloeiro'}`}>{navigation[role].map((item) => {
    const active = pathname === item.href || (item.href !== `/${role}` && pathname.startsWith(item.href))
    return <Link key={item.href} href={item.href} className={active ? 'active' : ''} aria-current={active ? 'page' : undefined}><Icon name={item.icon}/>{item.label}</Link>
  })}</nav></aside><div className="profile-content">{children}</div></div></RoleGate>
}
