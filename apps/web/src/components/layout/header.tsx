'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useState } from 'react'
import { useAuth } from '@/components/auth/auth-provider'
import { Button, buttonClass } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { getErrorMessage } from '@/lib/api/client'
import { useTheme } from './theme-provider'

export function Header() {
    const pathname = usePathname()
    const router = useRouter()
    const { user, logout } = useAuth()
    const { theme, cycleTheme } = useTheme()
    const [open, setOpen] = useState(false)
    const [logoutError, setLogoutError] = useState('')
    const accountHref = user?.role === 'auctioneer' ? '/auctioneer' : '/bidder'
    const ThemeIcon = theme === 'dark' ? 'moon' : theme === 'system' ? 'monitor' : 'sun'

    const signOut = async () => {
        try {
            await logout()
            router.push('/')
        } catch (error) {
            setLogoutError(getErrorMessage(error))
        }
    }

    return <header className="header">
        <div className="header-inner">
            <Link className="brand" href="/" aria-label="ArtBid, início" onClick={() => setOpen(false)}><span className="brand-mark">A</span><span>ArtBid</span></Link>
            <nav className={open ? 'nav open' : 'nav'} aria-label="Navegação principal">
                <Link className={pathname.startsWith('/lots') ? 'active' : ''} href="/lots" onClick={() => setOpen(false)}>Leilões</Link>
                <Link href="/#como-funciona" onClick={() => setOpen(false)}>Como funciona</Link>
                <Link className={pathname.startsWith('/audit') ? 'active' : ''} href="/audit" onClick={() => setOpen(false)}>Auditoria</Link>
                <span className="nav-rule" />
                {user && <Link className={pathname.startsWith(accountHref) ? 'active' : ''} href={accountHref} onClick={() => setOpen(false)}>{user.role === 'bidder' ? 'Área do licitante' : 'Área do leiloeiro'}</Link>}
            </nav>
            <div className="header-actions">
                <button className="icon-button" onClick={cycleTheme} aria-label={`Tema actual: ${theme}. Alterar tema`} title={`Tema: ${theme}`}><Icon name={ThemeIcon} /></button>
                {user ? <div className="user-menu"><Link href={accountHref} className="user-name" title={user.displayName}><Icon name="user" /><span>{user.displayName}</span></Link><Button variant="text" className="logout-button" onClick={signOut} aria-label="Terminar sessão"><Icon name="logout" /></Button></div> : <Link className={buttonClass('primary', 'header-login')} href="/login">Entrar</Link>}
                <button className="menu-button" onClick={() => setOpen(!open)} aria-expanded={open} aria-label={open ? 'Fechar menu' : 'Abrir menu'}><Icon name={open ? 'close' : 'menu'} /></button>
            </div>
        </div>
        {logoutError && <p className="nav-error" role="alert">{logoutError}. A sessão local foi limpa.</p>}
    </header>
}
