import type { ReactNode } from 'react'
import { ProfileShell } from '@/components/layout/profile-shell'
export default function BidderLayout({ children }: { children: ReactNode }) { return <ProfileShell role="bidder">{children}</ProfileShell> }
