import Link from 'next/link'
import { buttonClass } from '@/components/ui/button'

export default function NotFound() {
  return <main className="section page"><section className="access-panel"><p className="kicker">Erro 404</p><h1>Esta obra saiu do catálogo.</h1><p>O endereço não corresponde a uma página ou recurso disponível.</p><Link href="/lots" className={buttonClass()}>Voltar aos leilões</Link></section></main>
}
