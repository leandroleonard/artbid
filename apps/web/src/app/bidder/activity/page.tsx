import type { Metadata } from 'next'
import { ActivityPage } from '@/components/bidder/activity-page'
export const metadata: Metadata = { title: 'Actividade de lances' }
export default function Page() { return <ActivityPage/> }
