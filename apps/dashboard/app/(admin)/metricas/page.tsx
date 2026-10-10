import { MetricasDashboard } from '@/components/metricas-dashboard'
import { PageHeader } from '@/components/noc/primitives'
import { OtpMetricasCard } from '@/components/otp-metricas-card'
import { WhatsAppMetricasCard } from '@/components/whatsapp-metricas-card'

export default function MetricasPage() {
  return (
    <div className="space-y-4">
      <PageHeader title="Métricas" description="Painel operacional" />
      <MetricasDashboard />
      <div className="grid items-start gap-4 2xl:grid-cols-2">
        <WhatsAppMetricasCard />
        <OtpMetricasCard />
      </div>
    </div>
  )
}
