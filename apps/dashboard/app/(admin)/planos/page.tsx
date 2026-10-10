import { PlanosManager } from '@/components/planos-manager'
import { PageHeader } from '@/components/noc/primitives'

export default function PlanosPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Planos de Internet"
        description="Gerencie os planos apresentados pelo bot aos clientes"
      />
      <PlanosManager />
    </div>
  )
}
