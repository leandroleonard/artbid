'use client'

import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { useAuth } from './auth-provider'
import { Button } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'
import { getErrorMessage } from '@/lib/api/client'

const loginSchema = z.object({
  email: z.email('Indique um email válido.'),
  password: z.string().min(8, 'A palavra-passe deve ter pelo menos 8 caracteres.').max(128),
})

type LoginValues = z.infer<typeof loginSchema>

export function LoginPage() {
  const { login } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const [serverError, setServerError] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  })

  const finish = (role: 'bidder' | 'auctioneer') => {
    const next = searchParams.get('next')
    const safeNext = next?.startsWith('/') && !next.startsWith('//') ? next : null

    router.push(safeNext ?? (role === 'bidder' ? '/bidder' : '/auctioneer'))
  }

  const submit = handleSubmit(async (values) => {
    setServerError('')

    try {
      const user = await login(values)
      finish(user.role)
    } catch (error) {
      setServerError(getErrorMessage(error))
    }
  })

  return (
    <main className="auth-page">
      <div className="auth-art">
        <img src="/images/art-hero.jpg" alt="Obra clássica em moldura" />
        <div className="auth-art-caption">
          <p className="kicker">Casa de leilões digital</p>
          <h2>Participe com clareza.</h2>
          {/* <p>Estado oficial e histórico pseudonimizado.</p> */}
        </div>
      </div>

      <div className="auth-form-wrap">
        <div className="auth-form">
          <p className="kicker">Bem-vindo de volta</p>
          <h1>Iniciar sessão</h1>
          <p className="page-subtitle">Aceda à área correspondente ao seu perfil.</p>

          <form onSubmit={submit} noValidate>
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
                autoComplete="current-password"
                aria-invalid={Boolean(errors.password)}
                {...register('password')}
              />
              {errors.password && <small className="field-error">{errors.password.message}</small>}
            </label>

            {serverError && (
              <div className="form-error" role="alert">
                {serverError}
              </div>
            )}

            <Button type="submit" className="full" disabled={isSubmitting} aria-busy={isSubmitting}>
              {isSubmitting ? 'A validar…' : 'Iniciar sessão'}
              <Icon name="arrow" />
            </Button>
          </form>

          <p className="auth-switch">
            Ainda não tem conta? <Link href="/register">Criar conta</Link>
          </p>
        </div>
      </div>
    </main>
  )
}

