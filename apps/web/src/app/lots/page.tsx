import type { Metadata } from 'next'
import { CatalogPage } from '@/components/lots/catalog-page'
export const metadata: Metadata = { title: 'Catálogo de leilões' }
export default function LotsPage() { return <CatalogPage/> }
