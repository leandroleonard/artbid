import type { ReactNode } from 'react'
import { ProfileShell } from '@/components/layout/profile-shell'
export default function AuctioneerLayout({ children }: { children: ReactNode }) { return <ProfileShell role="auctioneer">{children}</ProfileShell> }
