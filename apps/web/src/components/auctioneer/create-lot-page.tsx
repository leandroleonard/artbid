'use client'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button, buttonClass } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { EmptyState, ErrorState, LoadingState, PageTitle } from '@/components/ui/states'
import { useArtwork, useCreateLot, type CreateLotInput } from '@/hooks/use-auctioneer'
import { getErrorMessage } from '@/lib/api/client'
import type { AuctioneerLot } from '@/lib/api/contract'
import { formatDateTime, formatMoney, parseMoneyToCents, toLocalDateTimeInput } from '@/lib/format'

const formSchema = z.object({
  title: z.string().trim().min(3, 'Indique um título com pelo menos 3 caracteres.').max(160),
  description: z.string().trim().max(2000, 'Máximo de 2000 caracteres.'),
  startingBid: z.string().min(1, 'Indique o lance inicial.'),
  minimumIncrement: z.string().min(1, 'Indique o incremento mínimo.'),
  startsAt: z.string().min(1, 'Indique o início.'),
  endsAt: z.string().min(1, 'Indique o fim.'),
}).superRefine((values, context) => {
  const startingBid = parseMoneyToCents(values.startingBid)
  const increment = parseMoneyToCents(values.minimumIncrement)
  if (startingBid === null || startingBid <= 0) context.addIssue({ code: 'custom', path: ['startingBid'], message: 'Indique um valor positivo válido.' })
  if (increment === null || increment <= 0) context.addIssue({ code: 'custom', path: ['minimumIncrement'], message: 'Indique um valor positivo válido.' })
  const start = new Date(values.startsAt)
  const end = new Date(values.endsAt)
  if (Number.isNaN(start.getTime())) context.addIssue({ code: 'custom', path: ['startsAt'], message: 'Data de início inválida.' })
  if (Number.isNaN(end.getTime())) context.addIssue({ code: 'custom', path: ['endsAt'], message: 'Data de fim inválida.' })
  if (!Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime()) && end <= start) context.addIssue({ code: 'custom', path: ['endsAt'], message: 'O fim deve ser posterior ao início.' })
})
type Values = z.infer<typeof formSchema>

export function CreateLotPage() {
  const searchParams = useSearchParams()
  const artworkId = searchParams.get('artwork') ?? ''
  const artwork = useArtwork(artworkId)
  const createLot = useCreateLot()
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [created, setCreated] = useState<AuctioneerLot | null>(null)
  const [serverError, setServerError] = useState('')
  const idempotencyKey = useRef<string | null>(null)
  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<Values>({
    resolver: zodResolver(formSchema),
    defaultValues: { title: '', description: '', startingBid: '8.000,00', minimumIncrement: '500,00', startsAt: '', endsAt: '' },
  })
  const values = watch()

  useEffect(() => {
    if (!artwork.data) return
    const data = artwork.data.data
    const start = new Date(Date.now() + 24 * 3_600_000)
    const end = new Date(Date.now() + 3 * 24 * 3_600_000)
    reset({ title: `${data.title} — ${data.artist}`.slice(0, 160), description: data.description ?? '', startingBid: '8.000,00', minimumIncrement: '500,00', startsAt: toLocalDateTimeInput(start), endsAt: toLocalDateTimeInput(end) })
  }, [artwork.data, reset])

  if (!artworkId) return <main className="page"><EmptyState title="Seleccione primeiro uma obra" message="A criação de um lote começa pela pesquisa no catálogo." action={<Link className={buttonClass()} href="/auctioneer/catalog">Pesquisar obras</Link>}/></main>
  if (artwork.isLoading) return <main className="page"><LoadingState label="A consolidar os dados da obra"/></main>
  if (artwork.isError || !artwork.data) return <main className="page"><ErrorState message={getErrorMessage(artwork.error)} onRetry={() => void artwork.refetch()}/></main>
  const artworkData = artwork.data.data

  const publish = async (form: Values) => {
    const startingBidCents = parseMoneyToCents(form.startingBid)
    const minimumIncrementCents = parseMoneyToCents(form.minimumIncrement)
    if (startingBidCents === null || minimumIncrementCents === null) return
    const input: CreateLotInput = {
      artworkId,
      title: form.title,
      ...(form.description ? { description: form.description } : {}),
      startingBidCents,
      minimumIncrementCents,
      startsAt: new Date(form.startsAt).toISOString(),
      endsAt: new Date(form.endsAt).toISOString(),
    }
    idempotencyKey.current ??= crypto.randomUUID()
    setServerError('')
    try {
      const response = await createLot.mutateAsync({ input, idempotencyKey: idempotencyKey.current })
      setCreated(response.data)
      idempotencyKey.current = null
    } catch (error) { setServerError(getErrorMessage(error)) }
  }

  return <main className="page create-page"><PageTitle kicker="Área do leiloeiro" title="Criar novo lote" description="Reveja a obra, configure as condições e publique."/><div className="steps">{['Rever obra', 'Configurar leilão', 'Rever e publicar'].map((label, index) => <div key={label} className={step >= index + 1 ? 'active' : ''}><span>{index + 1}</span><label>{label}</label></div>)}</div>
    <div className="create-shell"><div className="create-main">
      {created ? <div className="form-success" role="status"><h2>Lote publicado</h2><p>Lote {created.number}.</p><Link className={buttonClass()} href="/auctioneer/lots">Gerir os meus lotes</Link></div> : <>
        <div className="create-review"><img src={artworkData.imageUrl} alt={artworkData.imageAlt}/><div><p className="kicker">Dados importados</p><h2>{artworkData.title}</h2><p>{artworkData.artist} · {artworkData.date}</p><p>ID: {artworkData.id}</p></div></div>
        {step === 1 && <><h2>Confirme a obra seleccionada</h2><div className="form-actions"><Link className={buttonClass('secondary')} href="/auctioneer/catalog">Escolher outra obra</Link><Button onClick={() => setStep(2)}>Configurar leilão <Icon name="arrow"/></Button></div></>}
        {step > 1 && <form onSubmit={step === 2 ? handleSubmit(() => { idempotencyKey.current = null; setServerError(''); setStep(3) }) : handleSubmit(publish)} noValidate>
          {step === 2 && <><h2>Configure o leilão</h2><p>Valores convertidos para cêntimos.</p><div className="form-grid"><label className="field wide">Título do lote<input maxLength={160} aria-invalid={Boolean(errors.title)} {...register('title')}/>{errors.title && <small className="field-error">{errors.title.message}</small>}</label><label className="field wide">Descrição editorial<textarea maxLength={2000} aria-invalid={Boolean(errors.description)} {...register('description')}/>{errors.description && <small className="field-error">{errors.description.message}</small>}</label><label className="field">Lance inicial (R$)<input inputMode="decimal" aria-invalid={Boolean(errors.startingBid)} {...register('startingBid')}/>{errors.startingBid && <small className="field-error">{errors.startingBid.message}</small>}</label><label className="field">Incremento mínimo (R$)<input inputMode="decimal" aria-invalid={Boolean(errors.minimumIncrement)} {...register('minimumIncrement')}/>{errors.minimumIncrement && <small className="field-error">{errors.minimumIncrement.message}</small>}</label><label className="field">Início<input type="datetime-local" aria-invalid={Boolean(errors.startsAt)} {...register('startsAt')}/>{errors.startsAt && <small className="field-error">{errors.startsAt.message}</small>}</label><label className="field">Fim<input type="datetime-local" aria-invalid={Boolean(errors.endsAt)} {...register('endsAt')}/>{errors.endsAt && <small className="field-error">{errors.endsAt.message}</small>}</label></div></>}
          {step === 3 && <><h2>Revisão final</h2><p>Confirme os dados antes do pedido.</p><dl className="receipt-data"><div><dt>Título</dt><dd>{values.title}</dd></div><div><dt>Lance inicial</dt><dd>{formatMoney(parseMoneyToCents(values.startingBid) ?? 0)}</dd></div><div><dt>Incremento mínimo</dt><dd>{formatMoney(parseMoneyToCents(values.minimumIncrement) ?? 0)}</dd></div><div><dt>Janela</dt><dd>{new Date(values.startsAt).toString() === 'Invalid Date' ? '—' : `${formatDateTime(new Date(values.startsAt).toISOString())} — ${formatDateTime(new Date(values.endsAt).toISOString())}`}</dd></div></dl>{serverError && <div className="form-error" role="alert">{serverError}</div>}</>}
          <div className="form-actions"><Button variant="secondary" onClick={() => { setStep(step === 3 ? 2 : 1); idempotencyKey.current = null }}>Voltar</Button>{step === 2 ? <Button type="submit">Rever configuração <Icon name="arrow"/></Button> : <Button type="submit" disabled={createLot.isPending} aria-busy={createLot.isPending}>{createLot.isPending ? 'A aguardar publicação…' : 'Publicar lote'}</Button>}</div>
        </form>}
      </>}
    </div><aside className="help-card"><p className="kicker">Boas práticas</p><h3>Antes de publicar</h3><ul><li>Confira a atribuição da obra.</li><li>Use datas futuras e um intervalo válido.</li></ul></aside></div>
  </main>
}
