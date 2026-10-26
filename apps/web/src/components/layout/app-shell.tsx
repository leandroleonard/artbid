'use client'

import { usePathname } from 'next/navigation'
import type { ReactNode } from 'react'

import { Footer } from './footer'
import { Header } from './header'

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const hideGlobalChrome = pathname === '/login' || pathname === '/register'

  return (
    <>
      {!hideGlobalChrome && <Header />}
      <div id="main-content">{children}</div>
      {!hideGlobalChrome && <Footer />}
    </>
  )
}
