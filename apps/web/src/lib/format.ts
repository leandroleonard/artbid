const brlFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

export function formatMoney(cents: number) {
  if (!Number.isSafeInteger(cents)) return '—'
  return brlFormatter.format(cents / 100)
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat('pt-PT', { dateStyle: 'long' }).format(new Date(value))
}

export function formatDateTime(value: string) {
  return new Intl.DateTimeFormat('pt-PT', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function formatTime(value: string) {
  return new Intl.DateTimeFormat('pt-PT', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(value))
}

export function parseMoneyToCents(value: string): number | null {
  const normalized = value.trim().replace(/\s/g, '').replace(/^R\$/i, '')
  if (!/^(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d{1,2})?$/.test(normalized)) return null
  const [wholePart, fraction = ''] = normalized.replace(/\./g, '').split(',')
  if (!wholePart) return null
  const centsText = `${wholePart}${fraction.padEnd(2, '0')}`
  const cents = Number(centsText)
  return Number.isSafeInteger(cents) ? cents : null
}

export function centsToInput(cents: number) {
  if (!Number.isSafeInteger(cents) || cents < 0) return ''
  const whole = Math.floor(cents / 100).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${whole},${String(cents % 100).padStart(2, '0')}`
}

export function toLocalDateTimeInput(date: Date) {
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}
