import { PlanosManager } from '@/components/planos-manager'

export default function PlanosPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Planos de Internet</h1>
        <p className="text-sm text-muted-foreground">
          Gerencie os planos apresentados pelo bot aos clientes
        </p>
      </div>
      <PlanosManager />
    </div>
  )
}
