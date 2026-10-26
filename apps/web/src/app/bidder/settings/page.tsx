import type { Metadata } from 'next'
import { SettingsPage } from '@/components/bidder/settings-page'
export const metadata: Metadata = { title: 'Definições de perfil' }
export default function Page() { return <SettingsPage/> }
