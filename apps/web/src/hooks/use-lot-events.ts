'use client'

import { useEffect, useRef, useState } from 'react'
import { useAuth } from '@/components/auth/auth-provider'
import { lotEventSchema, type ConnectionStatus, type LotEvent } from '@/lib/api/events'
import { RecentEventIds, reconnectDelay, SseParser } from '@/lib/sse'

export function useLotEvents(
  lotId: string,
  onEvent: (event: LotEvent) => void,
  onReconnect: () => void,
) {
  const { token } = useAuth()
  const [status, setStatus] = useState<ConnectionStatus>('reconnecting')
  const eventCallback = useRef(onEvent)
  const reconnectCallback = useRef(onReconnect)

  useEffect(() => {
    eventCallback.current = onEvent
    reconnectCallback.current = onReconnect
  }, [onEvent, onReconnect])

  useEffect(() => {
    let disposed = false
    let generation = 0
    let controller: AbortController | null = null
    let retryTimer: ReturnType<typeof setTimeout> | null = null
    let attempts = 0
    let lastEventId = ''
    let lastSequence = 0
    const recent = new RecentEventIds()

    const connect = async () => {
      if (disposed || document.hidden) return
      const currentGeneration = ++generation
      controller = new AbortController()
      setStatus('reconnecting')
      if (attempts > 0) reconnectCallback.current()
      try {
        const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/events`, {
          credentials: 'same-origin',
          cache: 'no-store',
          headers: {
            Accept: 'text/event-stream',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(lastEventId ? { 'Last-Event-ID': lastEventId } : {}),
          },
          signal: controller.signal,
        })
        if (!response.ok || !response.body || !response.headers.get('content-type')?.includes('text/event-stream')) {
          if (response.status === 401) window.dispatchEvent(new CustomEvent('artbid:unauthorized'))
          throw new Error('SSE indisponível')
        }
        if (currentGeneration !== generation) return
        setStatus('connected')
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        const parser = new SseParser()
        while (!disposed && currentGeneration === generation) {
          const { done, value } = await reader.read()
          if (done) break
          const messages = parser.push(decoder.decode(value, { stream: true }))
          for (const message of messages) {
            let payload: unknown
            try { payload = JSON.parse(message.data) } catch { continue }
            const parsed = lotEventSchema.safeParse(payload)
            if (!parsed.success || parsed.data.lotId !== lotId) continue
            const event = parsed.data
            const eventId = event.eventId || message.id
            if (recent.has(eventId)) continue
            recent.add(eventId)
            attempts = 0
            lastEventId = eventId
            if (event.sequence < lastSequence) {
              reconnectCallback.current()
            }
            lastSequence = Math.max(lastSequence, event.sequence)
            eventCallback.current(event)
          }
        }
        throw new Error('Ligação encerrada')
      } catch {
        if (disposed || currentGeneration !== generation) return
        attempts += 1
        setStatus(attempts >= 3 ? 'unavailable' : 'reconnecting')
        retryTimer = setTimeout(connect, reconnectDelay(attempts))
      }
    }

    const onVisibility = () => {
      if (document.hidden) {
        generation += 1
        controller?.abort()
        if (retryTimer) clearTimeout(retryTimer)
        setStatus('reconnecting')
      } else {
        attempts = 0
        reconnectCallback.current()
        void connect()
      }
    }

    void connect()
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      disposed = true
      generation += 1
      controller?.abort()
      if (retryTimer) clearTimeout(retryTimer)
      recent.clear()
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [lotId, token])

  return status
}
