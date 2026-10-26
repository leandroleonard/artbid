import type { ReactNode } from 'react'

export type IconName = 'search' | 'moon' | 'sun' | 'monitor' | 'arrow' | 'clock' | 'check' | 'shield' | 'wallet' | 'menu' | 'share' | 'close' | 'plus' | 'user' | 'gavel' | 'logout' | 'alert' | 'wifi' | 'wifiOff' | 'refresh' | 'chevronLeft' | 'chevronRight' | 'external' | 'trash' | 'settings' | 'home' | 'file' | 'image'

const paths: Record<IconName, ReactNode> = {
  search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
  moon: <path d="M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z"/>,
  sun: <><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41"/></>,
  monitor: <><rect x="3" y="4" width="18" height="12" rx="1"/><path d="M8 20h8M12 16v4"/></>,
  arrow: <><path d="M5 12h14"/><path d="m14 7 5 5-5 5"/></>,
  clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  check: <path d="m5 12 4 4L19 6"/>,
  shield: <><path d="M12 3 5 6v5c0 4.5 3 8 7 10 4-2 7-5.5 7-10V6l-7-3Z"/><path d="m9 12 2 2 4-4"/></>,
  wallet: <><path d="M4 6h14a2 2 0 0 1 2 2v10H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h12"/><path d="M16 11h4v4h-4a2 2 0 0 1 0-4Z"/></>,
  menu: <path d="M4 7h16M4 12h16M4 17h16"/>,
  share: <><circle cx="18" cy="5" r="2"/><circle cx="6" cy="12" r="2"/><circle cx="18" cy="19" r="2"/><path d="m8 11 8-5M8 13l8 5"/></>,
  close: <path d="m6 6 12 12M18 6 6 18"/>,
  plus: <path d="M12 5v14M5 12h14"/>,
  user: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
  gavel: <><path d="m14 4 6 6M11 7l6 6M4 20h10M3 17l8-8 4 4-8 8Z"/></>,
  logout: <><path d="M10 5H5v14h5M14 8l4 4-4 4M8 12h10"/></>,
  alert: <><path d="M12 3 2 21h20L12 3Z"/><path d="M12 9v5M12 18h.01"/></>,
  wifi: <><path d="M5 12a10 10 0 0 1 14 0M8 15a6 6 0 0 1 8 0M11 18a2 2 0 0 1 2 0"/><path d="M2 9a14 14 0 0 1 20 0"/></>,
  wifiOff: <><path d="m3 3 18 18M5 12a10 10 0 0 1 4-2M15 10a10 10 0 0 1 4 2M8 15a6 6 0 0 1 7-1M11 18a2 2 0 0 1 2 0"/></>,
  refresh: <><path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.1 8a7 7 0 0 1 11.8-1L20 12M4 12l2.1 5a7 7 0 0 0 11.8-1"/></>,
  chevronLeft: <path d="m15 18-6-6 6-6"/>,
  chevronRight: <path d="m9 18 6-6-6-6"/>,
  external: <><path d="M14 4h6v6M20 4l-9 9"/><path d="M18 13v7H4V6h7"/></>,
  trash: <><path d="M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 11v6M14 11v6"/></>,
  settings: <><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1A8 8 0 0 0 15 6l-.3-2.6h-4L10.4 6A8 8 0 0 0 9 7.1l-2.4-1-2 3.4 2 1.5a7 7 0 0 0 0 2l-2 1.5 2 3.4 2.4-1A8 8 0 0 0 10.4 18l.3 2.6h4L15 18a8 8 0 0 0 1.5-1.1l2.4 1 2-3.4-2-1.5a7 7 0 0 0 .1-1Z"/></>,
  home: <><path d="m3 11 9-8 9 8"/><path d="M5 10v11h14V10M9 21v-7h6v7"/></>,
  file: <><path d="M6 2h8l4 4v16H6Z"/><path d="M14 2v5h5M9 12h6M9 16h6"/></>,
  image: <><rect x="3" y="4" width="18" height="16" rx="1"/><circle cx="9" cy="9" r="2"/><path d="m3 17 5-5 4 4 3-3 6 6"/></>,
}

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>
}
