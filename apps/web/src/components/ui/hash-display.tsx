
'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Icon } from '@/components/ui/icon'

type HashDisplayProps = {
  value: string | null | undefined
  label?: string
  visibleChars?: number
}

export function HashDisplay({
  value,
  label = 'Hash',
  visibleChars = 12,
}: HashDisplayProps) {
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)

  if (!value) {
    return <code className="hash-empty">Não disponibilizado</code>
  }

  const displayValue = expanded
    ? value
    : value.length > visibleChars * 2
      ? `${value.slice(0, visibleChars)}…${value.slice(-visibleChars)}`
      : value

  const copyHash = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="hash-display" style={{flexDirection: 'row'}}>
      <code
        className="hash-value"
        title={value}
      >
        {displayValue}
      </code>

      <div className="hash-actions">
        <button
          type="button"
          className="hash-action"
          onClick={() => setExpanded((current) => !current)}
          aria-expanded={expanded}
          aria-label={expanded ? 'Ocultar hash completo' : 'Mostrar hash completo'}
          title={expanded ? 'Ocultar hash' : 'Mostrar hash completo'}
        >
          <Icon name={expanded ? 'close' : 'plus'} size={15} />
        </button>

        <button
          type="button"
          className="hash-action"
          onClick={copyHash}
          aria-label={`Copiar ${label}`}
          title={copied ? 'Copiado!' : `Copiar ${label}`}
        >
          <Icon name={copied ? 'check' : 'file'} size={15} />
        </button>
      </div>
    </div>
  )
}
