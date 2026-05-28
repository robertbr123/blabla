import { MetricasDashboard } from '@/components/metricas-dashboard'
import { OtpMetricasCard } from '@/components/otp-metricas-card'
import { WhatsAppMetricasCard } from '@/components/whatsapp-metricas-card'

export default function MetricasPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Métricas</h1>
        <p className="text-sm text-muted-foreground">Painel operacional</p>
      </div>
      <MetricasDashboard />
      <WhatsAppMetricasCard />
      <OtpMetricasCard />
    </div>
  )
}
