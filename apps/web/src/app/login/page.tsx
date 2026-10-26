import type { Metadata } from 'next'
import { Suspense } from 'react'
import { LoginPage } from '@/components/auth/login-page'
import { LoadingState } from '@/components/ui/states'
export const metadata: Metadata = { title: 'Iniciar sessão' }
export default function Page() { return <Suspense fallback={<main className="section page"><LoadingState/></main>}><LoginPage/></Suspense> }
