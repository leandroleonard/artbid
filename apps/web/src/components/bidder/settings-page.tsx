'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { z } from 'zod'
import { useAuth } from '@/components/auth/auth-provider'
import { Button } from '@/components/ui/button'
import { PageTitle } from '@/components/ui/states'
import { apiFetch, getErrorMessage } from '@/lib/api/client'
import { userResponseSchema } from '@/lib/api/contract'

const schema = z.object({ displayName: z.string().trim().min(2, 'Indique pelo menos 2 caracteres.').max(80) })
type Values = z.infer<typeof schema>

export function SettingsPage() {
  const { user, token, setUser } = useAuth()
  const [feedback, setFeedback] = useState<{ type: 'error' | 'success'; text: string } | null>(null)
  const { register, handleSubmit, formState: { errors } } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { displayName: user?.displayName ?? '' } })
  const mutation = useMutation({
    mutationFn: (values: Values) => apiFetch('/api/auth/me', userResponseSchema, { method: 'PATCH', token, body: values }),
    onSuccess: (response) => { setUser(response.data); setFeedback({ type: 'success', text: 'Perfil actualizado.' }) },
    onError: (error) => setFeedback({ type: 'error', text: getErrorMessage(error) }),
  })
  return <main className="page"><PageTitle kicker="Definições" title="Perfil básico" description="Apenas o nome de apresentação pode ser alterado nesta versão."/><div className="form-card"><form onSubmit={handleSubmit((values) => { setFeedback(null); mutation.mutate(values) })} noValidate><div className="form-grid"><label className="field">Nome de apresentação<input maxLength={80} aria-invalid={Boolean(errors.displayName)} {...register('displayName')}/>{errors.displayName && <small className="field-error">{errors.displayName.message}</small>}</label><label className="field">Email<input value={user?.email ?? ''} disabled/><small className="field-help">A alteração de email não está disponível.</small></label><label className="field">Perfil funcional<input value={user?.role === 'bidder' ? 'Licitante' : 'Leiloeiro'} disabled/></label></div>{feedback && <div className={`form-${feedback.type}`} role={feedback.type === 'error' ? 'alert' : 'status'}>{feedback.text}</div>}<div className="form-actions"><span/><Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'A guardar…' : 'Guardar alterações'}</Button></div></form></div></main>
}
