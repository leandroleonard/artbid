import type { Metadata } from 'next'
import { ReceiptPage } from '@/components/audit/receipt-page'
export const metadata: Metadata = { title: 'Comprovativo' }
export default async function Page({ params }: { params: Promise<{ receiptId: string }> }) {
  const { receiptId } = await params
  return <ReceiptPage receiptId={receiptId}/>
}
