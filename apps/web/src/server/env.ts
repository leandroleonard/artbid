
export function apiTimeoutMs() {
  const value = Number(process.env.API_TIMEOUT_MS ?? 10_000)
  return Number.isFinite(value) && value >= 1_000 ? Math.min(value, 60_000) : 10_000
}

export function apiBaseUrl() {
  const value = process.env.API_BASE_URL
  if (!value) {
    throw new Error('API_BASE_URL não configurada.')
  }
  const url = new URL(value)
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
    throw new Error('API_BASE_URL inválida.')
  }
  return url.origin.replace(/\/$/, '')
}
