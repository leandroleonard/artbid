import type { Metadata } from 'next'
import type { ReactNode } from 'react'
export const metadata: Metadata = { title: 'Acesso negado' }
export default function ForbiddenLayout({ children }: { children: ReactNode }) { return children }
