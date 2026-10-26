import type { Metadata } from 'next'
import { Suspense } from 'react'
import { AuditPage } from '@/components/audit/audit-page'
import { LoadingState } from '@/components/ui/states'
export const metadata: Metadata = { title: 'Auditoria' }
export default function Page() { return <Suspense fallback={<main className="section page"><LoadingState/></main>}><AuditPage/></Suspense> }
