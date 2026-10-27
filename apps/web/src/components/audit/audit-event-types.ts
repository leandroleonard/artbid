export const auditEventTypes: Record<string, string> = {
  'bid.accepted': 'Lance aceite',
  'bid.outbid': 'Perdeu o lance',
  'lot.created': 'Lote criado',
  'lot.extended': 'Prazo prorrogado',
  'lot.closed': 'Lote encerrado',
  'lot.cancelled': 'Lote cancelado',
  'lot.settled': 'Lote liquidado',
  'lot.state.changed': 'Alteração de estado',
} as const
