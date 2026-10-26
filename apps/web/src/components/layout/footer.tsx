import Link from 'next/link'

export function Footer() {
    return (
        <footer>
            <div className="section footer-inner">
                <div>
                    <Link href="/" className="brand">
                        <span className="brand-mark">A</span>
                        <span>ArtBid</span>
                    </Link>
                    <p>Arte, procedência e confiança em cada lance.</p>
                </div>
                <div>
                    <strong>Explorar</strong>
                    <Link href="/lots">Leilões</Link>
                    <Link href="/audit">Auditoria</Link>
                </div>
                <div>
                    <strong>Conta</strong>
                    <Link href="/bidder">Área do cliente</Link>
                    {/* <Link href="/auctioneer"> Admin</Link> */}
                </div>
                <small>© 2026 ArtBid · Direitos reservados</small>
            </div>
        </footer>
    );
}
