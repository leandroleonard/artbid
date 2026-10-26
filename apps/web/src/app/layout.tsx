import type { Metadata, Viewport } from 'next'
import type { ReactNode } from 'react'
import './globals.css'
import { Providers } from '@/components/providers'
import { Header } from '@/components/layout/header'
import { Footer } from '@/components/layout/footer'

export const metadata: Metadata = {
  title: { default: 'ArtBid — Leilões de arte', template: '%s · ArtBid' },
  description: 'Explore obras de arte em leilões exclusivos.',
}

export const viewport: Viewport = {
  width: 'device-width', initialScale: 1, themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#F6F1E7' },
    { media: '(prefers-color-scheme: dark)', color: '#29231E' },
  ]
}

const themeScript = `(function(){try{var t=localStorage.getItem('artbid-theme')||'light';var d=t==='dark'||(t==='system'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.dataset.theme=d?'dark':'light'}catch(e){document.documentElement.dataset.theme='light'}})()`

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="pt" data-scroll-behavior="smooth" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{ __html: themeScript }} /></head><body><Providers><a className="skip-link" href="#main-content">Saltar para o conteúdo</a><Header /><div id="main-content">{children}</div><Footer /></Providers></body></html>
}
