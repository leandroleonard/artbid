import Link from 'next/link'
import type { Lot } from '@/lib/api/contract'
import { formatDateTime, formatMoney } from '@/lib/format'
import { Icon } from '@/components/ui/icon'
import { StatusBadge } from '@/components/ui/states'

export function LotCard({ lot }: { lot: Lot }) {
  return <Link href={`/lots/${lot.id}`} className="lot-card" aria-label={`${lot.title}, ${lot.artist}. Abrir lote`}>
    <div className="lot-image"><img src={lot.imageUrl} alt={lot.imageAlt} loading="lazy"/><StatusBadge status={lot.status}/></div>
    <div className="lot-body">
      <p className="eyebrow">{lot.artist} · {lot.artworkDate}</p>
      <h3>{lot.title}</h3>
      <div className="lot-meta"><div><small>{lot.status === 'scheduled' ? 'Lance inicial' : lot.status === 'ended' ? 'Valor final' : 'Lance actual'}</small><strong>{formatMoney(lot.currentBidCents)}</strong></div><div><small><Icon name="clock" size={14}/> {lot.status === 'ended' ? 'Encerrado' : formatDateTime(lot.endsAt)}</small><span>{lot.bidCount} {lot.bidCount === 1 ? 'lance' : 'lances'}</span></div></div>
      <span className="lot-card-link">Ver lote <Icon name="arrow" size={15}/></span>
    </div>
  </Link>
}
