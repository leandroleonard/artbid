'use client'

import Link from 'next/link'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '@/components/auth/auth-provider'
import { Button, buttonClass } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { ErrorState, LoadingState, StatusBadge } from '@/components/ui/states'
import { useCreateBid } from '@/hooks/use-bids'
import { useLotEvents } from '@/hooks/use-lot-events'
import { useRoom } from '@/hooks/use-room'
import { useWallet } from '@/hooks/use-wallet'
import { getErrorMessage } from '@/lib/api/client'
import type { Lot, Room } from '@/lib/api/contract'
import type { ConnectionStatus, LotEvent } from '@/lib/api/events'
import { queryKeys } from '@/lib/api/query-keys'
import { centsToInput, formatMoney, formatTime, parseMoneyToCents } from '@/lib/format'

function ConnectionBadge({ status }: { status: ConnectionStatus }) {
  const content = status === 'connected' ? ['Ligado', 'wifi'] as const : status === 'reconnecting' ? ['A reconectar', 'refresh'] as const : ['Ligação indisponível · polling', 'wifiOff'] as const
  return <span className={`connection ${status}`} role="status"><Icon name={content[1]} size={14} />{content[0]}</span>
}

function Countdown({ endsAt, status }: { endsAt: string; status: Lot['status'] }) {
  const [now, setNow] = useState<number | null>(null)
  useEffect(() => {
    const update = () => setNow(Date.now())
    update()
    const timer = setInterval(update, 1000)
    return () => clearInterval(timer)
  }, [endsAt])
  const remaining = now === null ? null : Math.max(0, new Date(endsAt).getTime() - now)
  const text = remaining === null ? '— : — : —' : `${String(Math.floor(remaining / 3_600_000)).padStart(2, '0')} : ${String(Math.floor((remaining % 3_600_000) / 60_000)).padStart(2, '0')} : ${String(Math.floor((remaining % 60_000) / 1000)).padStart(2, '0')}`
  return <div className={`countdown ${remaining !== null && remaining < 120_000 && status === 'live' ? 'urgent' : ''}`}><span><Icon name="clock" /> {status === 'scheduled' ? 'Início previsto' : status === 'ended' ? 'Leilão encerrado' : 'Encerra em'}</span><strong>{status === 'ended' ? 'Encerrado' : text}</strong><small>{remaining === 0 && status === 'live' ? 'A aguardar confirmação de encerramento.' : ''}</small></div>
}

type BidFormProps = { lot: Lot; position: Room['viewerPosition'] }
type BidFormValues = { amount: string }

function BidForm({ lot, position }: BidFormProps) {
  const { user } = useAuth()
  const mutation = useCreateBid(lot.id)
  const wallet = useWallet(user?.role === 'bidder')
  const queryClient = useQueryClient()
  const idempotencyKey = useRef<string | null>(null)
  const [feedback, setFeedback] = useState<{ type: 'error' | 'success'; text: string } | null>(null)
  const schema = useMemo(() => z.object({ amount: z.string().min(1, 'Indique o valor do lance.') }).superRefine((value, context) => {
    const cents = parseMoneyToCents(value.amount)
    if (cents === null || cents <= 0) {
      context.addIssue({ code: 'custom', path: ['amount'], message: 'Use um valor válido, por exemplo 18.900,00.' })
    } else if (cents < lot.nextMinimumBidCents) {
      context.addIssue({ code: 'custom', path: ['amount'], message: `O mínimo actual é ${formatMoney(lot.nextMinimumBidCents)}.` })
    }
  }), [lot.nextMinimumBidCents])
  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<BidFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { amount: centsToInput(lot.nextMinimumBidCents) },
  })
  const amount = watch('amount')

  useEffect(() => {
    idempotencyKey.current = null
  }, [amount])
  useEffect(() => {
    reset({ amount: centsToInput(lot.nextMinimumBidCents) })
  }, [lot.nextMinimumBidCents, reset])

  if (!user) return <div className="room-notice"><p>Inicie sessão com um perfil de licitante para apresentar um lance.</p><Link className={buttonClass('primary', 'full')} href={`/login?next=/lots/${lot.id}`}>Entrar para licitar</Link></div>
  if (user.role === 'auctioneer') return <div className="room-notice">O perfil de leiloeiro pode acompanhar a sala.</div>
  if (lot.status !== 'live') return <div className="room-notice">{lot.status === 'scheduled' ? 'A licitação ainda não está aberta.' : 'Este lote está encerrado.'}</div>
  if (position?.status === 'leading') return <div className="winning"><Icon name="check" /><span><strong>Está a liderar este lote</strong><small>Não pode ultrapassar o próprio lance. {formatMoney(position.committedCents)} comprometidos.</small></span></div>

  const submit = handleSubmit(async (values) => {
    const amountCents = parseMoneyToCents(values.amount)
    if (amountCents === null) return
    idempotencyKey.current ??= crypto.randomUUID()
    setFeedback(null)
    try {
      const response = await mutation.mutateAsync({ amountCents, idempotencyKey: idempotencyKey.current })
      setFeedback({ type: 'success', text: `Lance de ${formatMoney(response.data.bid.amountCents)} confirmado.` })
      idempotencyKey.current = null
      reset({ amount: centsToInput(response.data.room.nextMinimumBidCents) })
    } catch (error) {
      setFeedback({ type: 'error', text: getErrorMessage(error) })
      await queryClient.invalidateQueries({ queryKey: queryKeys.room(lot.id) })
    }
  })

  const quickValues = [lot.nextMinimumBidCents, lot.nextMinimumBidCents + lot.minimumIncrementCents, lot.nextMinimumBidCents + lot.minimumIncrementCents * 4]
  return <form className="bid-form" onSubmit={submit} noValidate>
    {wallet.data && <div className="field-help">Disponível: <strong>{formatMoney(wallet.data.data.availableCents)}</strong> · Comprometido: {formatMoney(wallet.data.data.committedCents)}</div>}
    <label className="field"><span>Seu próximo lance <small>Mínimo: {formatMoney(lot.nextMinimumBidCents)}</small></span><div className="money-input"><span>R$</span><input inputMode="decimal" autoComplete="off" aria-label="Valor do lance" aria-invalid={Boolean(errors.amount)} aria-describedby={errors.amount ? 'bid-error' : undefined} {...register('amount')} /></div>{errors.amount && <small className="field-error" id="bid-error">{errors.amount.message}</small>}</label>
    <div className="quick" aria-label="Valores rápidos">{quickValues.map((value, index) => <button type="button" key={value} onClick={() => reset({ amount: centsToInput(value) })}>{index === 0 ? 'Mínimo' : `+ ${formatMoney(value - lot.nextMinimumBidCents)}`}</button>)}</div>
    <Button type="submit" className="full" disabled={mutation.isPending} aria-busy={mutation.isPending}>{mutation.isPending ? 'A aguardar confirmação…' : 'Confirmar lance'}</Button>
    {feedback && <div className={`form-${feedback.type}`} role={feedback.type === 'error' ? 'alert' : 'status'}>{feedback.text}</div>}
  </form>
}

export function AuctionRoom({ lotId }: { lotId: string }) {
  const queryClient = useQueryClient()
  const [notice, setNotice] = useState('')
  const onEvent = (event: LotEvent) => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.room(lotId) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.lotsRoot })
    if (event.type === 'bid.accepted') setNotice('Novo lance registado. A sincronizar o estado oficial.')
    if (event.type === 'bid.outbid') {
      setNotice('A sua posição mudou. A consultar o estado oficial.')
      void queryClient.invalidateQueries({ queryKey: queryKeys.wallet })
      void queryClient.invalidateQueries({ queryKey: ['bids'] })
    }
    if (event.type === 'lot.extended') setNotice('O prazo foi prolongado. A sincronizar o novo fim oficial.')
    if (event.type === 'lot.closed') setNotice('O lote foi encerrado. A consultar o resultado.')
    if (event.type === 'lot.cancelled') setNotice('O lote foi cancelado.')
  }
  const onReconnect = () => void queryClient.invalidateQueries({ queryKey: queryKeys.room(lotId) })
  const connection = useLotEvents(lotId, onEvent, onReconnect)
  const room = useRoom(lotId, connection === 'unavailable')

  if (room.isLoading) return <main className="section page"><LoadingState label="A abrir a sala do leilão" /></main>
  if (room.isError || !room.data) return <main className="section page"><ErrorState title="Não foi possível abrir o lote" message={getErrorMessage(room.error)} onRetry={() => void room.refetch()} /></main>
  const data = room.data.data
  const { lot, publicBids, viewerPosition } = data

  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setNotice('Ligação copiada.')
    } catch {
      setNotice('Não foi possível copiar automaticamente.')
    }
  }

  return <main className="section lot-page">
    <div className="breadcrumb"><Link href="/lots">Leilões</Link><span>/</span><span>Lote {lot.number}</span></div>
    <div className="lot-layout">
      <div className="art-column"><div className="main-art"><img src={lot.imageUrl} alt={lot.imageAlt} /></div><div className="provenance"><p className="kicker">Sobre a obra</p><h2>{lot.title}</h2><p>{lot.description ?? 'Ainda não foi disponibilizada uma descrição editorial.'}</p><dl><div><dt>Artista</dt><dd>{lot.artist}</dd></div><div><dt>Período</dt><dd>{lot.artworkDate}</dd></div><div><dt>Identificador</dt><dd>{lot.externalArtworkId ?? 'Não indicado'}</dd></div></dl></div></div>
      <aside className="bid-panel" aria-label="Estado e licitação do lote">
        <div className="bid-top"><StatusBadge status={lot.status} /><div className="room-tools"><ConnectionBadge status={connection} /><button onClick={share} aria-label="Copiar ligação do lote"><Icon name="share" /></button></div></div>
        <p className="lot-id">LOTE {lot.number}</p><h1>{lot.title}</h1><p className="artist">{lot.artist}, {lot.artworkDate}</p>
        <Countdown endsAt={lot.status === 'scheduled' ? lot.startsAt : lot.endsAt} status={lot.status} />
        <div className="current-bid"><span>{lot.status === 'scheduled' ? 'Lance inicial' : lot.status === 'ended' ? 'Valor final' : 'Lance actual'}</span><strong>{formatMoney(lot.currentBidCents)}</strong><small>{lot.bidCount} {lot.bidCount === 1 ? 'lance' : 'lances'} · próximo mínimo {formatMoney(lot.nextMinimumBidCents)}</small></div>
        {viewerPosition && viewerPosition.status !== 'none' && viewerPosition.status !== 'leading' && <div className={`viewer-position ${viewerPosition.status}`}><Icon name={viewerPosition.status === 'won' ? 'check' : 'gavel'} /><span><strong>{viewerPosition.status === 'outbid' ? 'O seu lance foi ultrapassado' : viewerPosition.status === 'won' ? 'Lote ganho' : 'Participação encerrada'}</strong><small>{viewerPosition.highestBidCents ? `O seu maior lance: ${formatMoney(viewerPosition.highestBidCents)}` : 'Consulte a sua actividade para mais detalhes.'}</small></span></div>}
        {notice && <div className="room-notice" role="status">{notice}</div>}
        <BidForm key={`${lot.id}-${lot.status}`} lot={lot} position={viewerPosition} />
        <div className="history"><div className="history-head"><h3>Histórico de lances</h3><Link href={`/audit?lotId=${lot.id}`}>Auditar histórico</Link></div><div className="bid-history-list">{publicBids.length ? publicBids.map((bid, index) => <div className="history-row" key={bid.id}><span className={index === 0 ? 'leader' : ''}>{index === 0 ? 'Líder' : 'Lance'}</span><span>{bid.bidderAlias}</span><strong>{formatMoney(bid.amountCents)}</strong><small>{formatTime(bid.createdAt)}</small></div>) : <p className="field-help">Ainda não existem lances neste lote.</p>}</div></div>
      </aside>
    </div>
  </main>
}
