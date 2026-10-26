'use client'

import { useEffect, useRef, type ReactNode } from 'react'
import { Icon } from './icon'

export function Dialog({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return <dialog ref={ref} className="dialog" aria-labelledby="dialog-title" onCancel={(event) => { event.preventDefault(); onClose() }} onClick={(event) => { if (event.target === ref.current) onClose() }}>
    <div className="dialog-inner">
      <button className="modal-close" onClick={onClose} aria-label="Fechar"><Icon name="close"/></button>
      <h2 id="dialog-title">{title}</h2>
      {children}
    </div>
  </dialog>
}
