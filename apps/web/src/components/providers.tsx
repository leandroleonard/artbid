'use client'

import { useState, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ApiError } from '@/lib/api/client'
import { AuthProvider } from './auth/auth-provider'
import { ThemeProvider } from './layout/theme-provider'

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 10_000,
        retry: (count, error) => count < 2 && (!(error instanceof ApiError) || error.retryable),
        refetchOnWindowFocus: false,
      },
      mutations: { retry: false },
    },
  }))
  return <QueryClientProvider client={queryClient}><ThemeProvider><AuthProvider>{children}</AuthProvider></ThemeProvider></QueryClientProvider>
}
