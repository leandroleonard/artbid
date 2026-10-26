'use client'

import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button, buttonClass } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { PageTitle } from '@/components/ui/states'
import { useDeposit, useWallet } from '@/hooks/use-wallet'
import { getErrorMessage } from '@/lib/api/client'
import { centsToInput, formatMoney, parseMoneyToCents } from '@/lib/format'

const schema = z.object({ amount: z.string().min(1, 'Indique um valor.') }).superRefine((value, context) => {
  const cents = parseMoneyToCents(value.amount)
  if (cents === null || cents <= 0) context.addIssue({ code: 'custom', path: ['amount'], message: 'Indique um valor positivo válido.' })
  else if (cents > 100_000_000) context.addIssue({ code: 'custom', path: ['amount'], message: 'O valor excede o limite proposto.' })
})
type Values = z.infer<typeof schema>

export function AddFundsPage() {
  const wallet = useWallet()
  const deposit = useDeposit()
  const key = useRef<string | null>(null)
  const [feedback, setFeedback] = useState<{ type: 'error' | 'success'; text: string } | null>(null)
  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { amount: '5.000,00' } })
  const amount = watch('amount')
  useEffect(() => { key.current = null }, [amount])
  const submit = handleSubmit(async (values) => {
    const amountCents = parseMoneyToCents(values.amount)
    if (amountCents === null) return
    key.current ??= crypto.randomUUID()
    setFeedback(null)
    try {
      const response = await deposit.mutateAsync({ amountCents, idempotencyKey: key.current })
      setFeedback({ type: 'success', text: `Depósito confirmado. Novo saldo disponível: ${formatMoney(response.data.wallet.availableCents)}.` })
      key.current = null
    } catch (error) { setFeedback({ type: 'error', text: getErrorMessage(error) }) }
  })
  return <main className="page"><PageTitle kicker="Depósito" title="Adicionar créditos" description=""/><div className="form-card"><form onSubmit={submit} noValidate><label className="field">Valor do depósito<div className="money-input"><span>R$</span><input inputMode="decimal" aria-invalid={Boolean(errors.amount)} {...register('amount')}/></div>{errors.amount && <small className="field-error">{errors.amount.message}</small>}</label><div className="quick">{[100_000, 500_000, 1_000_000].map((value) => <button type="button" key={value} onClick={() => reset({ amount: centsToInput(value) })}>{formatMoney(value)}</button>)}</div>{wallet.data && <div className="modal-summary"><span>Saldo disponível actual</span><strong>{formatMoney(wallet.data.data.availableCents)}</strong></div>}{feedback && <div className={`form-${feedback.type}`} role={feedback.type === 'error' ? 'alert' : 'status'}>{feedback.text}</div>}<div className="form-actions"><Link href="/bidder/wallet" className={buttonClass('secondary')}>Voltar à carteira</Link><Button type="submit" disabled={deposit.isPending} aria-busy={deposit.isPending}>{deposit.isPending ? 'A aguardar confirmação…' : 'Confirmar depósito'}</Button></div></form></div></main>
}
