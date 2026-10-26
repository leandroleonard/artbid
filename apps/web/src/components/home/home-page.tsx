'use client'

import Link from 'next/link'
import { buttonClass } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { ErrorState, LoadingState } from '@/components/ui/states'
import { LotCard } from '@/components/lots/lot-card'
import { useLots } from '@/hooks/use-lots'
import type { Lot } from '@/lib/api/contract'

type LotSectionProps = {
  kicker: string
  title: string
  lots?: Lot[]
  isLoading: boolean
  error: Error | null
  retry: () => void
  empty: string
}

function LotSection({ kicker, title, lots, isLoading, error, retry, empty }: LotSectionProps) {
  return <section className="section live-section"><div className="section-heading"><div><p className="kicker">{kicker}</p><h2>{title}</h2></div><Link className={buttonClass('text')} href="/lots">Ver catálogo <Icon name="arrow"/></Link></div>
    {isLoading ? <LoadingState label={`A carregar ${title.toLowerCase()}`}/> : error ? <ErrorState message={error.message} onRetry={retry}/> : lots?.length ? <div className="lot-grid">{lots.map((lot) => <LotCard key={lot.id} lot={lot}/>)}</div> : <div className="inline-state">{empty}</div>}
  </section>
}

export function HomePage() {
  const live = useLots({ status: 'live', pageSize: 3, sort: 'endingSoon' })
  const scheduled = useLots({ status: 'scheduled', pageSize: 3, sort: 'endingSoon' })
  const ended = useLots({ status: 'ended', pageSize: 3, sort: 'recent' })
  const featured = live.data?.data[0] ?? scheduled.data?.data[0]

  return <main>
    <section className="hero section">
      <div className="hero-copy"><p className="kicker">Leilões de arte com procedência e transparência</p><h1>Obras que atravessam o tempo.</h1><p className="lead">Descubra arte com curadoria e participe de leilões ao vivo.</p><div className="button-row"><Link className={buttonClass()} href="/lots">Explorar leilões <Icon name="arrow"/></Link><Link className={buttonClass('text')} href="/audit">Auditoria</Link></div><div className="hero-note"><Icon name="shield"/><span><strong>Histórico verificável</strong><small>Integridade a cada lance</small></span></div></div>
      <div className="hero-art">{featured ? <><Link href={`/lots/${featured.id}`} className="frame"><img src={featured.imageUrl} alt={featured.imageAlt}/></Link><div className="caption"><span>Lote em destaque · {featured.number}</span><strong>{featured.title}</strong><span>{featured.artist}, {featured.artworkDate}</span></div></> : <div className="frame hero-placeholder">{live.isLoading ? <LoadingState label="Sorteando lote"/> : <Icon name="image" size={60}/>}</div>}</div>
    </section>

    <LotSection kicker="Agora em disputa" title="Lotes ao vivo" lots={live.data?.data} isLoading={live.isLoading} error={live.error} retry={() => void live.refetch()} empty="Não existem lotes em curso neste momento. Consulte os próximos leilões."/>
    <section className="trust-band" id="como-funciona"><div className="section trust-grid"><div><p className="kicker">Participar é simples</p><h2>Da descoberta ao arremate, com clareza.</h2></div>{[['01','Crie a sua conta','Conheça as regras antes de participar.'],['02','Adicione saldo','Use seus créditos; Dá o teu lance.'],['03','Acompanhe ao vivo','Receba notificações e consulte o estado oficial de cada lance.']].map(([number,title,description]) => <div className="step" key={number}><span>{number}</span><h3>{title}</h3><p>{description}</p></div>)}</div></section>
    <LotSection kicker="Em breve" title="Próximos leilões" lots={scheduled.data?.data} isLoading={scheduled.isLoading} error={scheduled.error} retry={() => void scheduled.refetch()} empty="Ainda não há novos lotes agendados."/>
    <LotSection kicker="Arquivo" title="Encerrados recentemente" lots={ended.data?.data} isLoading={ended.isLoading} error={ended.error} retry={() => void ended.refetch()} empty="Ainda não existem resultados."/>
    <section className="section audit-callout"><div className="seal"><Icon name="shield" size={30}/></div><div><p className="kicker">Transparência por princípio</p><h2>Cada lance deixa um rasto.</h2><p>A ArtBid apresenta um histórico cronológico e pseudonimizado. Dados pessoas são preservados.</p></div><Link className={buttonClass('secondary')} href="/audit">Ver auditoria</Link></section>
  </main>
}
