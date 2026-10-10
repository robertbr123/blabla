import { FormManutencao } from '@/components/form-manutencao'
import { PageHeader } from '@/components/noc/primitives'

export default function NovaManutencaoPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Nova manutenção" />
      <FormManutencao />
    </div>
  )
}
