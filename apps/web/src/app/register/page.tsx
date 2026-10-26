import type { Metadata } from 'next'
import { RegisterPage } from '@/components/auth/register-page'
export const metadata: Metadata = { title: 'Criar conta' }
export default function Page() { return <RegisterPage/> }
