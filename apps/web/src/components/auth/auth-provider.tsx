'use client'

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { z } from 'zod'
import { apiFetch } from '@/lib/api/client'
import { authResponseSchema, sessionResponseSchema, type User } from '@/lib/api/contract'

type LoginInput = { email: string; password: string }
type RegisterInput = LoginInput & { displayName: string; role: 'bidder' | 'auctioneer' }
type AuthContextValue = {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (input: LoginInput) => Promise<User>
  register: (input: RegisterInput) => Promise<User>
  logout: () => Promise<void>
  setUser: (user: User) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)
const logoutSchema = z.object({ data: z.object({ revoked: z.boolean() }) })
const configSchema = z.object({ data: z.object({ demo: z.boolean() }) })

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [expiresAt, setExpiresAt] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const queryClient = useQueryClient()

  const resetAuth = useCallback(() => {
    setUser(null)
    setToken(null)
    setExpiresAt(null)
  }, [])

  const clearPrivateCache = useCallback(() => {
    for (const root of ['wallet', 'movements', 'bids', 'won', 'artworks', 'artwork', 'ownLots', 'results']) {
      queryClient.removeQueries({ queryKey: [root] })
    }
    void queryClient.resetQueries({ queryKey: ['room'] })
  }, [queryClient])

  const clearSession = useCallback(() => {
    resetAuth()
    clearPrivateCache()
  }, [clearPrivateCache, resetAuth])

  useEffect(() => {
    const controller = new AbortController()
    apiFetch('/api/auth/session', sessionResponseSchema, { signal: controller.signal, timeoutMs: 8_000 })
      .then((response) => {
        setUser(response.data.user)
        setToken(response.data.accessToken)
        setExpiresAt(response.data.expiresAt)
      })
      .catch(() => resetAuth())
      .finally(() => setIsLoading(false))
    return () => controller.abort()
  }, [resetAuth])

  useEffect(() => {
    const unauthorized = () => clearSession()
    window.addEventListener('artbid:unauthorized', unauthorized)
    return () => window.removeEventListener('artbid:unauthorized', unauthorized)
  }, [clearSession])

  useEffect(() => {
    if (!expiresAt) return
    const delay = new Date(expiresAt).getTime() - Date.now()
    const timer = setTimeout(clearSession, Math.max(0, delay))
    return () => clearTimeout(timer)
  }, [expiresAt, clearSession])

  const applyAuth = useCallback((response: z.infer<typeof authResponseSchema>) => {
    clearPrivateCache()
    setUser(response.data.user)
    setToken(response.data.accessToken)
    setExpiresAt(response.data.expiresAt)
    return response.data.user
  }, [clearPrivateCache])

  const login = useCallback(async (input: LoginInput) => {
    const response = await apiFetch('/api/auth/login', authResponseSchema, { method: 'POST', body: input })
    return applyAuth(response)
  }, [applyAuth])

  const register = useCallback(async (input: RegisterInput) => {
    const response = await apiFetch('/api/auth/register', authResponseSchema, { method: 'POST', body: input })
    return applyAuth(response)
  }, [applyAuth])

  const logout = useCallback(async () => {
    try {
      await apiFetch('/api/auth/logout', logoutSchema, { method: 'POST', token })
    } finally {
      clearSession()
    }
  }, [token, clearSession])

  const value = useMemo(() => ({ user, token, isLoading, login, register, logout, setUser }), [user, token, isLoading, login, register, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth deve ser usado dentro de AuthProvider')
  return context
}
