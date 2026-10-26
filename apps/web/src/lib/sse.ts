export type SseMessage = { id: string; event: string; data: string }

export class SseParser {
  private buffer = ''

  push(chunk: string): SseMessage[] {
    this.buffer += chunk.replace(/\r\n/g, '\n')
    const messages: SseMessage[] = []
    let boundary = this.buffer.indexOf('\n\n')
    while (boundary >= 0) {
      const block = this.buffer.slice(0, boundary)
      this.buffer = this.buffer.slice(boundary + 2)
      const message = this.parseBlock(block)
      if (message) messages.push(message)
      boundary = this.buffer.indexOf('\n\n')
    }
    return messages
  }

  private parseBlock(block: string): SseMessage | null {
    let id = ''
    let event = 'message'
    const data: string[] = []
    for (const line of block.split('\n')) {
      if (!line || line.startsWith(':')) continue
      const separator = line.indexOf(':')
      const field = separator < 0 ? line : line.slice(0, separator)
      const value = separator < 0 ? '' : line.slice(separator + 1).replace(/^ /, '')
      if (field === 'id') id = value
      if (field === 'event') event = value
      if (field === 'data') data.push(value)
    }
    return data.length ? { id, event, data: data.join('\n') } : null
  }
}

export class RecentEventIds {
  private ids = new Set<string>()
  private order: string[] = []

  constructor(private readonly limit = 500) {}

  has(id: string) {
    return this.ids.has(id)
  }

  add(id: string) {
    if (!id || this.ids.has(id)) return
    this.ids.add(id)
    this.order.push(id)
    if (this.order.length > this.limit) {
      const oldest = this.order.shift()
      if (oldest) this.ids.delete(oldest)
    }
  }

  clear() {
    this.ids.clear()
    this.order = []
  }
}

export function reconnectDelay(attempt: number) {
  const exponential = Math.min(30_000, 1_000 * 2 ** Math.max(0, attempt - 1))
  return Math.round(exponential * (0.8 + Math.random() * 0.4))
}
