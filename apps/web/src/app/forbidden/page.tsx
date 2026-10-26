import Link from 'next/link'
import { buttonClass } from '@/components/ui/button'

export default function ForbiddenPage() {
  return <main className="section page"><section className="access-panel"><p className="kicker">Erro 403</p><h1>Acesso reservado.</h1><p>O seu perfil não tem permissão para consultar esta área.</p><Link href="/" className={buttonClass()}>Voltar ao início</Link></section></main>
}
