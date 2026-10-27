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

const registerSchema = z
  .object({
    displayName: z.string().trim().min(2, 'Indique pelo menos 2 caracteres.').max(80),
    email: z.email('Indique um email válido.'),
    password: z.string().min(12, 'Use pelo menos 12 caracteres.').max(128),
    confirmPassword: z.string(),
  })
  .refine((values) => values.password === values.confirmPassword, {
    path: ['confirmPassword'],
    message: 'As palavras-passe não coincidem.',
  })

type RegisterValues = z.infer<typeof registerSchema>

export function RegisterPage() {
  const { register: registerAccount } = useAuth()
  const router = useRouter()
  const [serverError, setServerError] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      displayName: '',
      email: '',
      password: '',
      confirmPassword: '',
    },
  })

  const submit = handleSubmit(async (values) => {
    setServerError('')

    try {
      await registerAccount({
        displayName: values.displayName,
        email: values.email,
        password: values.password,
        role: 'bidder',
      })

      router.push('/bidder')
    } catch (error) {
      setServerError(getErrorMessage(error))
    }
  })

  return (
    <main className="auth-page">
      <div className="auth-art">
        <img src="/images/art-salon.jpg" alt="Salão clássico" />
        <div className="auth-art-caption">
          <h2>Registe-se como licitante.</h2>
          <p>Esta conta dá acesso ao painel de licitação e ao histórico de participação.</p>
        </div>
      </div>

      <div className="auth-form-wrap">
        <div className="auth-form">
          <Link className="brand" href="/" aria-label="ArtBid, início"><span className="brand-mark" style={{fontSize: 56, width: 64, height: 64, marginBottom: 25}}>A</span></Link>
          <p className="kicker">Nova conta</p>
          <h1>Criar conta</h1>
          <p className="page-subtitle">
            Registe-se como licitante para participar em lotes, gerir lances e acompanhar o
            estado das suas compras.
          </p>

          <form onSubmit={submit} noValidate>
            <label className="field">
              Nome de apresentação
              <input
                autoComplete="name"
                maxLength={80}
                aria-invalid={Boolean(errors.displayName)}
                {...register('displayName')}
              />
              {errors.displayName && (
                <small className="field-error">{errors.displayName.message}</small>
              )}
            </label>

            <label className="field">
              Email
              <input
                type="email"
                autoComplete="email"
                aria-invalid={Boolean(errors.email)}
                {...register('email')}
              />
              {errors.email && <small className="field-error">{errors.email.message}</small>}
            </label>

            <label className="field">
              Palavra-passe
              <input
                type="password"
                autoComplete="new-password"
                aria-invalid={Boolean(errors.password)}
                {...register('password')}
              />
              <small className="field-help">Mínimo de 12 caracteres.</small>
              {errors.password && <small className="field-error">{errors.password.message}</small>}
            </label>

            <label className="field">
              Confirmar palavra-passe
              <input
                type="password"
                autoComplete="new-password"
                aria-invalid={Boolean(errors.confirmPassword)}
                {...register('confirmPassword')}
              />
              {errors.confirmPassword && (
                <small className="field-error">{errors.confirmPassword.message}</small>
              )}
            </label>

            {serverError && (
              <div className="form-error" role="alert">
                {serverError}
              </div>
            )}

            <Button type="submit" className="full" disabled={isSubmitting} aria-busy={isSubmitting}>
              {isSubmitting ? 'A criar…' : 'Criar conta'}
              <Icon name="arrow" />
            </Button>
          </form>

          <p className="auth-switch">
            Já tem conta? <Link href="/login">Iniciar sessão</Link>
          </p>
        </div>
      </div>
    </main>
  )
}

