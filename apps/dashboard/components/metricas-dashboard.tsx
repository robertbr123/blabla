'use client'
import {
  BarChart3,
  CheckCircle2,
  Clock,
  MessageSquare,
  Star,
  UserPlus,
  Wrench,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { useMetricas } from '@/lib/api/queries'
import type { MetricasOut } from '@/lib/api/types'

interface KpiProps {
  label: string
  value: string | number
  icon: React.ComponentType<{ className?: string }>
}

function Kpi({ label, value, icon: Icon }: KpiProps) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-6">
        <div>
          <div className="text-xs uppercase text-muted-foreground">{label}</div>
          <div className="mt-2 text-3xl font-semibold">{value}</div>
        </div>
        <Icon className="h-8 w-8 text-muted-foreground/40" />
      </CardContent>
    </Card>
  )
}

export function MetricasDashboard() {
  const { data, isLoading, error } = useMetricas()

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando…</p>
  if (error) {
    return <p className="text-sm text-destructive">{error instanceof Error ? error.message : 'Erro'}</p>
  }
  if (!data) return null

  const m: MetricasOut = data
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <Kpi label="Conversas aguardando" value={m.conversas_aguardando} icon={Clock} />
      <Kpi label="Conversas em humano" value={m.conversas_humano} icon={MessageSquare} />
      <Kpi label="Mensagens 24h" value={m.msgs_24h} icon={BarChart3} />
      <Kpi label="OS abertas" value={m.os_abertas} icon={Wrench} />
      <Kpi label="OS concluídas 24h" value={m.os_concluidas_24h} icon={CheckCircle2} />
      <Kpi
        label="CSAT médio (30d)"
        value={m.csat_avg_30d !== null ? m.csat_avg_30d.toFixed(2) : '—'}
        icon={Star}
      />
      <Kpi label="Leads novos (7d)" value={m.leads_novos_7d} icon={UserPlus} />
    </div>
  )
}
