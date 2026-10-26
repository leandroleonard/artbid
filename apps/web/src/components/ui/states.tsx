import type { ReactNode } from 'react'
import { Icon } from './icon'
import { Button } from './button'
import type { LotStatus } from '@/lib/api/contract'

export function LoadingState({ label = 'A carregar dados' }: { label?: string }) {
  return <div className="state-panel loading-state" role="status" aria-live="polite"><span className="spinner" aria-hidden="true"/><p>{label}</p><div className="skeleton-lines" aria-hidden="true"><i/><i/><i/></div></div>
}

export function ErrorState({ title = 'Não foi possível carregar', message, onRetry }: { title?: string; message: string; onRetry?: () => void }) {
  return <div className="state-panel error-state" role="alert"><Icon name="alert" size={28}/><h2>{title}</h2><p>{message}</p>{onRetry && <Button variant="secondary" onClick={onRetry}><Icon name="refresh"/> Tentar novamente</Button>}</div>
}

export function EmptyState({ title, message, action }: { title: string; message: string; action?: ReactNode }) {
  return <div className="state-panel empty"><Icon name="search" size={30}/><h2>{title}</h2><p>{message}</p>{action}</div>
}

const statusLabels: Record<LotStatus | 'cancelled', string> = {
  scheduled: 'Agendado', live: 'Ao vivo', ended: 'Encerrado', cancelled: 'Cancelado',
}

export function StatusBadge({ status }: { status: LotStatus | 'cancelled' }) {
  return <span className={`status status-${status}`}>{status === 'live' && <i aria-hidden="true"/>}{statusLabels[status]}</span>
}

export function Pagination({ page, totalPages, onPage }: { page: number; totalPages: number; onPage: (page: number) => void }) {
  if (totalPages <= 1) return null
  return <nav className="pagination" aria-label="Paginação"><Button variant="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}><Icon name="chevronLeft"/> Anterior</Button><span>Página {page} de {totalPages}</span><Button variant="secondary" disabled={page >= totalPages} onClick={() => onPage(page + 1)}>Seguinte <Icon name="chevronRight"/></Button></nav>
}

export function PageTitle({ kicker, title, description, action }: { kicker: string; title: string; description: string; action?: ReactNode }) {
  return <div className={`page-title ${action ? 'row' : ''}`}><div><p className="kicker">{kicker}</p><h1>{title}</h1><p>{description}</p></div>{action}</div>
}
