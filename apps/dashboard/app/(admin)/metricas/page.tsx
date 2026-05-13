import { MetricasDashboard } from '@/components/metricas-dashboard'

export default function MetricasPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Métricas</h1>
        <p className="text-sm text-muted-foreground">Painel operacional</p>
      </div>
      <MetricasDashboard />
    </div>
  )
}
