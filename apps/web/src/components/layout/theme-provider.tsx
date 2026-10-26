'use client'

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

type Theme = 'light' | 'dark' | 'system'
type ThemeContextValue = { theme: Theme; cycleTheme: () => void }
const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>('light')
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      const saved = window.localStorage.getItem('artbid-theme')
      setTheme(saved === 'dark' || saved === 'system' || saved === 'light' ? saved : 'light')
      setReady(true)
    })
    return () => window.cancelAnimationFrame(frame)
  }, [])

  useEffect(() => {
    if (!ready) return
    const apply = () => {
      const dark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
      document.documentElement.dataset.theme = dark ? 'dark' : 'light'
    }
    apply()
    window.localStorage.setItem('artbid-theme', theme)
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    media.addEventListener('change', apply)
    return () => media.removeEventListener('change', apply)
  }, [theme, ready])

  const value = useMemo(() => ({
    theme,
    cycleTheme: () => setTheme((current) => current === 'light' ? 'dark' : current === 'dark' ? 'system' : 'light'),
  }), [theme])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme deve ser usado dentro de ThemeProvider')
  return context
}
