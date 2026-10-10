import type { Metadata } from 'next'
import { NocPanel } from '@/components/noc/noc-panel'

export const metadata: Metadata = { title: 'Painel NOC — BlaBla' }

export default function NocPage() {
  return <NocPanel />
}
