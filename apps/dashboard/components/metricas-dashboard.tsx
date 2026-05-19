'use client'
import { useState } from 'react'
import {
  BarChart3,
  CheckCircle2,
  Clock,
  Download,
  MessageSquare,
  Star,
  UserPlus,
  Wrench,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  downloadTimeseriesCsv,
  useMetricas,
  useRankingTecnicos,
  useTimeseries,
} from '@/lib/api/queries'
import type {
  MetricasOut,
  RankingTecnicoOut,
  TimeseriesPontoOut,
} from '@/lib/api/types'

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

const PERIODOS: { label: string; days: number }[] = [
  { label: '7d', days: 7 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
  { label: '180d', days: 180 },
]

function fmtDia(iso: string): string {
  const [, m, d] = iso.split('-')
  return `${d}/${m}`
}

// Cores das series — fixas pra ler sem CSS var.
const SERIES: { key: keyof Pick<TimeseriesPontoOut, 'msgs' | 'os_concluidas' | 'leads_novos'>; label: string; color: string }[] = [
  { key: 'msgs', label: 'Mensagens', color: '#3b82f6' },
  { key: 'os_concluidas', label: 'OS', color: '#10b981' },
  { key: 'leads_novos', label: 'Leads', color: '#f59e0b' },
]

// Multilinha SVG com eixos minimalistas.
function LineChartSimple({ data }: { data: TimeseriesPontoOut[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground">Sem dados.</p>
  }
  const W = 800
  const H = 260
  const PAD_L = 36
  const PAD_R = 12
  const PAD_T = 12
  const PAD_B = 28
  const innerW = W - PAD_L - PAD_R
  const innerH = H - PAD_T - PAD_B

  const maxVal = Math.max(
    1,
    ...data.flatMap((p) => SERIES.map((s) => p[s.key] as number)),
  )
  const xStep = data.length > 1 ? innerW / (data.length - 1) : innerW
  const xAt = (i: number) => PAD_L + i * xStep
  const yAt = (v: number) => PAD_T + innerH - (v / maxVal) * innerH

  // Grade horizontal: 4 linhas de referencia.
  const gridYs = [0, 0.25, 0.5, 0.75, 1].map((f) => ({
    y: PAD_T + innerH - f * innerH,
    label: Math.round(maxVal * f),
  }))

  // Labels do eixo X: mostrar ~6 marcas distribuidas.
  const xTickEvery = Math.max(1, Math.ceil(data.length / 6))

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* grid */}
        {gridYs.map((g, idx) => (
          <g key={idx}>
            <line
              x1={PAD_L}
              x2={W - PAD_R}
              y1={g.y}
              y2={g.y}
              stroke="currentColor"
              strokeOpacity={0.1}
            />
            <text
              x={PAD_L - 6}
              y={g.y}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-muted-foreground"
              fontSize={10}
            >
              {g.label}
            </text>
          </g>
        ))}

        {/* x labels */}
        {data.map((p, i) =>
          i % xTickEvery === 0 || i === data.length - 1 ? (
            <text
              key={i}
              x={xAt(i)}
              y={H - 8}
              textAnchor="middle"
              className="fill-muted-foreground"
              fontSize={10}
            >
              {fmtDia(p.dia)}
            </text>
          ) : null,
        )}

        {/* linhas */}
        {SERIES.map((s) => {
          const points = data
            .map((p, i) => `${xAt(i)},${yAt(p[s.key] as number)}`)
            .join(' ')
          return (
            <g key={s.key}>
              <polyline
                points={points}
                fill="none"
                stroke={s.color}
                strokeWidth={2}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            </g>
          )
        })}
      </svg>

      {/* legenda */}
      <div className="mt-2 flex flex-wrap gap-4">
        {SERIES.map((s) => (
          <div key={s.key} className="flex items-center gap-2 text-xs">
            <span
              className="inline-block h-3 w-3 rounded-sm"
              style={{ backgroundColor: s.color }}
            />
            <span className="text-muted-foreground">{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function BarChartTecnicos({ ranking }: { ranking: RankingTecnicoOut[] }) {
  const items = ranking
    .filter((t) => t.os_concluidas > 0)
    .slice(0, 10)
    .map((t) => ({
      nome: t.nome.split(' ').slice(0, 2).join(' '),
      os: t.os_concluidas,
      csat: t.csat_avg,
    }))

  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">Sem OS concluídas no mês.</p>
  }

  const max = Math.max(...items.map((t) => t.os))
  return (
    <div className="space-y-2">
      {items.map((t, i) => {
        const pct = (t.os / max) * 100
        return (
          <div key={i} className="flex items-center gap-3 text-sm">
            <div className="w-32 truncate text-right text-muted-foreground">
              {t.nome}
            </div>
            <div className="relative h-6 flex-1 overflow-hidden rounded bg-muted/40">
              <div
                className="absolute inset-y-0 left-0 flex items-center justify-end pr-2 text-xs font-medium text-white"
                style={{ width: `${pct}%`, backgroundColor: '#10b981' }}
              >
                {t.os}
              </div>
            </div>
            <div className="w-16 text-right text-xs text-muted-foreground">
              {t.csat !== null ? `⭐ ${t.csat.toFixed(1)}` : '—'}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function MetricasDashboard() {
  const [days, setDays] = useState<number>(30)
  const [exporting, setExporting] = useState(false)
  const { data, isLoading, error } = useMetricas()
  const { data: ts, isLoading: tsLoading } = useTimeseries(days)
  const mesAtual = new Date().toISOString().slice(0, 7)
  const { data: ranking, isLoading: rankLoading } = useRankingTecnicos(mesAtual)

  async function handleExport() {
    setExporting(true)
    try {
      await downloadTimeseriesCsv(days)
    } finally {
      setExporting(false)
    }
  }

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando…</p>
  if (error) {
    return (
      <p className="text-sm text-destructive">
        {error instanceof Error ? error.message : 'Erro'}
      </p>
    )
  }
  if (!data) return null

  const m: MetricasOut = data

  return (
    <div className="space-y-6">
      {/* KPIs estáticos */}
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

      {/* Tendência diária */}
      <Card>
        <CardContent className="space-y-4 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">Tendência diária</h2>
              <p className="text-xs text-muted-foreground">
                Mensagens, OS concluídas e leads novos por dia.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {PERIODOS.map((p) => (
                <Button
                  key={p.days}
                  size="sm"
                  variant={days === p.days ? 'default' : 'outline'}
                  onClick={() => setDays(p.days)}
                >
                  {p.label}
                </Button>
              ))}
              <Button
                size="sm"
                variant="outline"
                onClick={() => void handleExport()}
                disabled={exporting || tsLoading}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                {exporting ? 'Exportando…' : 'CSV'}
              </Button>
            </div>
          </div>
          {tsLoading ? (
            <p className="text-sm text-muted-foreground">Carregando série…</p>
          ) : (
            <LineChartSimple data={ts?.pontos ?? []} />
          )}
        </CardContent>
      </Card>

      {/* Distribuição por técnico */}
      <Card>
        <CardContent className="space-y-4 p-6">
          <div>
            <h2 className="text-lg font-semibold">
              OS por técnico — {mesAtual}
            </h2>
            <p className="text-xs text-muted-foreground">
              Top 10 técnicos com mais OS concluídas no mês atual.
            </p>
          </div>
          {rankLoading ? (
            <p className="text-sm text-muted-foreground">Carregando ranking…</p>
          ) : (
            <BarChartTecnicos ranking={ranking ?? []} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
