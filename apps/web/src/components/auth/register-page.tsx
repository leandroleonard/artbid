'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from './auth-provider'
import { Button } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { getErrorMessage } from '@/lib/api/client'

const registerSchema = z.object({
  displayName: z.string().trim().min(2, 'Indique pelo menos 2 caracteres.').max(80),
  email: z.email('Indique um email válido.'),
  password: z.string().min(12, 'Use pelo menos 12 caracteres.').max(128),
  confirmPassword: z.string(),
  role: z.enum(['bidder', 'auctioneer']),
}).refine((values) => values.password === values.confirmPassword, { path: ['confirmPassword'], message: 'As palavras-passe não coincidem.' })
type RegisterValues = z.infer<typeof registerSchema>

export function RegisterPage() {
  const { register: registerAccount } = useAuth()
  const router = useRouter()
  const [serverError, setServerError] = useState('')
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterValues>({ resolver: zodResolver(registerSchema), defaultValues: { displayName: '', email: '', password: '', confirmPassword: '', role: 'bidder' } })
  const submit = handleSubmit(async (values) => {
    setServerError('')
    try {
      const user = await registerAccount({ displayName: values.displayName, email: values.email, password: values.password, role: values.role })
      router.push(user.role === 'bidder' ? '/bidder' : '/auctioneer')
    } catch (error) { setServerError(getErrorMessage(error)) }
  })

  return <main className="auth-page"><div className="auth-art"><img src="/images/art-salon.jpg" alt="Salão clássico"/><div className="auth-art-caption"><p className="kicker">Duas funções, dois painéis</p><h2>Escolha como participar.</h2></div></div><div className="auth-form-wrap"><div className="auth-form"><p className="kicker">Nova conta</p><h1>Criar conta</h1><p className="page-subtitle">Registe-se como licitante ou leiloeiro. </p><form onSubmit={submit} noValidate><label className="field">Nome de apresentação<input autoComplete="name" maxLength={80} aria-invalid={Boolean(errors.displayName)} {...register('displayName')}/>{errors.displayName && <small className="field-error">{errors.displayName.message}</small>}</label><label className="field">Email<input type="email" autoComplete="email" aria-invalid={Boolean(errors.email)} {...register('email')}/>{errors.email && <small className="field-error">{errors.email.message}</small>}</label><fieldset className="field"><legend>Perfil funcional</legend><div className="role-options"><label className="role-option"><input type="radio" value="bidder" {...register('role')}/><span><strong>Licitante</strong></span></label><label className="role-option"><input type="radio" value="auctioneer" {...register('role')}/><span><strong>Leiloeiro</strong><small>Importação, criação e gestão de lotes.</small></span></label></div></fieldset><label className="field">Palavra-passe<input type="password" autoComplete="new-password" aria-invalid={Boolean(errors.password)} {...register('password')}/><small className="field-help">Mínimo de 12 caracteres.</small>{errors.password && <small className="field-error">{errors.password.message}</small>}</label><label className="field">Confirmar palavra-passe<input type="password" autoComplete="new-password" aria-invalid={Boolean(errors.confirmPassword)} {...register('confirmPassword')}/>{errors.confirmPassword && <small className="field-error">{errors.confirmPassword.message}</small>}</label>{serverError && <div className="form-error" role="alert">{serverError}</div>}<Button type="submit" className="full" disabled={isSubmitting} aria-busy={isSubmitting}>{isSubmitting ? 'A criar…' : 'Criar conta'} <Icon name="arrow"/></Button></form><p className="auth-switch">Já tem conta? <Link href="/login">Iniciar sessão</Link></p></div></div></main>
}
