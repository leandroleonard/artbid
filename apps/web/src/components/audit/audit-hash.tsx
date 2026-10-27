'use client'

import { useState } from 'react'
import { Icon } from '@/components/ui/icon'
import { formatDateTime } from '@/lib/format'

type Props = {
  hash: string
  label?: string
}

export function AuditHash({ hash, label = 'Hash reportado' }: Props) {
  const [showFull, setShowFull] = useState(false)
  const [copied, setCopied] = useState(false)

  const copyFull = async () => {
    try {
      await navigator.clipboard.writeText(hash)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }

  const copyShort = async () => {
    try {
      await navigator.clipboard.writeText(shortHash(hash))
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }

  const short = showFull ? hash : shortHash(hash)
  return (
    <div className="audit-hash">
      <span className="audit-hash-label">{label}</span>
      <button
        type="button"
        className="audit-hash-toggle"
        onClick={() => setShowFull((v) => !v)}
        aria-label={showFull ? 'Ver hash completo' : 'Ver hash resumido'}
        title={showFull ? 'Ver hash completo' : 'Ver hash resumido'}
      >
        <span className="audit-hash-value">{short}</span>
        <Icon name="external" size={14} />
      </button>
      {showFull && (
        <div className="audit-hash-menu">
          <button
            type="button"
            className="audit-hash-menu-item"
            onClick={copyFull}
            aria-label="Copiar hash completo"
          >
            <Icon name="copy" size={14} /> Copiar hash completo
          </button>
          <button
            type="button"
            className="audit-hash-menu-item"
            onClick={copyShort}
            aria-label="Copiar hash resumido"
          >
            <Icon name="copy" size={14} /> Copiar hash resumido
          </button>
          <button
            type="button"
            className="audit-hash-menu-item audit-hash-close"
            onClick={() => setShowFull(false)}
            aria-label="Fechar"
          >
            <Icon name="close" size={14} /> Fechar
          </button>
        </div>
      )}
      {copied && <span className="audit-hash-copied">Copiado!</span>}
    </div>
  )
}

function shortHash(value: string, parts = 3, length = 4): string {
  if (!value) return ''
  const cleaned = value.trim()
  if (cleaned.length <= parts * length) return cleaned
  const head = cleaned.slice(0, length)
  const body = cleaned.slice(length, cleaned.length - length)
  const tail = cleaned.slice(cleaned.length - length)
  return [head, ...body.split('').fill('', 0).map(() => '...'), tail].join('')
}
