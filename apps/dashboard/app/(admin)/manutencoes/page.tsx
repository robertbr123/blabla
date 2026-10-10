import { ManutencaoList } from '@/components/manutencao-list'
import { PageHeader } from '@/components/noc/primitives'

export default function ManutencoesPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Manutenções" />
      <ManutencaoList />
    </div>
  )
}
