'use client'
import { useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock,
  Download,
  MessageSquare,
  Star,
  TrendingUp,
  UserPlus,
  Users,
  Wrench,
} from 'lucide-react'
import {
  Panel,
  PanelBody,
  PanelHeader,
  Skeleton,
  StatTile,
} from '@/components/noc/primitives'
import { Button } from '@/components/ui/button'
import {
  downloadTimeseriesCsv,
  useMetricas,
  useRankingTecnicos,
  useTimeseries,
} from '@/lib/api/queries'
import type { RankingTecnicoOut, TimeseriesPontoOut } from '@/lib/api/types'
import { cn } from '@/lib/utils'

/* ── Controle segmentado (período) ───────────────────────────────────── */

export function Segmented<T extends string | number>({
  options,
  value,
  onChange,
  ariaLabel,
  className,
}: {
  options: ReadonlyArray<{ value: T; label: string }>
  value: T
  onChange: (v: T) => void
  ariaLabel: string
  className?: string
}) {
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={cn('inline-flex items-center gap-0.5 rounded-md border bg-background p-0.5', className)}
    >
      {options.map((o) => {
        const active = o.value === value
        return (
          <button
            key={String(o.value)}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(o.value)}
            className={cn(
              'num inline-flex h-6 items-center rounded px-2 text-xs font-medium transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              active
                ? 'bg-secondary text-foreground'
                : 'text-muted-foreground hover:bg-elevated hover:text-foreground',
            )}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

const PERIODOS: ReadonlyArray<{ value: number; label: string }> = [
  { value: 7, label: '7d' },
  { value: 30, label: '30d' },
  { value: 90, label: '90d' },
  { value: 180, label: '180d' },
]

/* ── Formatação ──────────────────────────────────────────────────────── */

function fmtNum(n: number): string {
  return n.toLocaleString('pt-BR')
}

function fmtDia(iso: string): string {
  const [, m, d] = iso.split('-')
  return `${d}/${m}`
}

function fmtDiaCompleto(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

/** Rótulo curto do eixo Y (cabe na margem esquerda). */
function fmtEixo(v: number): string {
  if (v >= 1_000_000) {
    return `${(v / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}M`
  }
  if (v >= 1_000) {
    return `${(v / 1_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}k`
  }
  return String(v)
}

/** Teto "redondo" do eixo Y, sempre par pra a linha do meio ser inteira. */
function niceMax(v: number): number {
  if (v <= 2) return 2
  const pow = 10 ** Math.floor(Math.log10(v))
  for (const f of [1, 2, 4, 6, 8, 10]) {
    if (f * pow >= v) return Math.max(2, f * pow)
  }
  return 10 * pow
}

/* ── Tendência diária: pequenos múltiplos ────────────────────────────── */

type SerieKey = 'msgs' | 'os_concluidas' | 'leads_novos'

interface Serie {
  key: SerieKey
  label: string
  /** Classe do quadradinho de legenda. */
  swatch: string
  /** Cor da marca no SVG (var do tema, validada nos dois modos). */
  color: string
}

// Uma série por gráfico, cada uma com a própria escala Y — num eixo só o
// volume de mensagens achata OS e leads.
const SERIES: ReadonlyArray<Serie> = [
  { key: 'msgs', label: 'Mensagens', swatch: 'bg-chart-1', color: 'var(--chart-1)' },
  { key: 'os_concluidas', label: 'OS concluídas', swatch: 'bg-chart-2', color: 'var(--chart-2)' },
  { key: 'leads_novos', label: 'Leads novos', swatch: 'bg-chart-3', color: 'var(--chart-3)' },
]

const PAD_L = 44
const PAD_R = 16
const PAD_T = 8
const PLOT_H = 90
const X_AXIS_H = 22
const GRID = 'hsl(var(--chart-grid))'

function xPos(i: number, n: number, width: number): number {
  const innerW = Math.max(0, width - PAD_L - PAD_R)
  if (n <= 1) return PAD_L + innerW / 2
  return PAD_L + (i * innerW) / (n - 1)
}

function MiniChart({
  data,
  serie,
  width,
  hoverIdx,
  showXAxis,
}: {
  data: TimeseriesPontoOut[]
  serie: Serie
  width: number
  hoverIdx: number | null
  showXAxis: boolean
}) {
  const n = data.length
  const height = PAD_T + PLOT_H + (showXAxis ? X_AXIS_H : 4)
  const y0 = PAD_T + PLOT_H
  const max = niceMax(Math.max(0, ...data.map((p) => p[serie.key])))
  const yAt = (v: number) => y0 - (v / max) * PLOT_H
  const xAt = (i: number) => xPos(i, n, width)

  const line = data
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${xAt(i).toFixed(1)},${yAt(p[serie.key]).toFixed(1)}`)
    .join(' ')
  const area = `${line} L${xAt(n - 1).toFixed(1)},${y0} L${xAt(0).toFixed(1)},${y0} Z`

  const ticks = [0, max / 2, max]
  // ~6 marcas no eixo X; a última sempre aparece, sem encostar na penúltima.
  const every = Math.max(1, Math.ceil(n / 6))
  const hoverPoint = hoverIdx !== null ? data[hoverIdx] : undefined

  return (
    <svg
      aria-hidden
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
      className="block"
    >
      {ticks.map((t) => (
        <g key={t}>
          <line x1={PAD_L} x2={width - PAD_R} y1={yAt(t)} y2={yAt(t)} stroke={GRID} strokeWidth={1} />
          <text
            x={PAD_L - 8}
            y={yAt(t)}
            textAnchor="end"
            dominantBaseline="middle"
            fontSize={10}
            className="num fill-muted-foreground"
          >
            {fmtEixo(t)}
          </text>
        </g>
      ))}

      {n > 1 ? (
        <>
          <path d={area} fill={serie.color} fillOpacity={0.1} stroke="none" />
          <path
            d={line}
            fill="none"
            stroke={serie.color}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        </>
      ) : (
        <circle cx={xAt(0)} cy={yAt(data[0]?.[serie.key] ?? 0)} r={4} fill={serie.color} />
      )}

      {hoverIdx !== null && hoverPoint && (
        <>
          <line
            x1={xAt(hoverIdx)}
            x2={xAt(hoverIdx)}
            y1={PAD_T}
            y2={y0}
            stroke="hsl(var(--muted-foreground))"
            strokeOpacity={0.6}
            strokeWidth={1}
          />
          <circle
            cx={xAt(hoverIdx)}
            cy={yAt(hoverPoint[serie.key])}
            r={4}
            fill={serie.color}
            stroke="hsl(var(--card))"
            strokeWidth={2}
          />
        </>
      )}

      {showXAxis &&
        data.map((p, i) => {
          const last = i === n - 1
          const regular = i % every === 0 && n - 1 - i >= every * 0.6
          if (!last && !regular) return null
          return (
            <text
              key={p.dia}
              x={xAt(i)}
              y={y0 + 15}
              textAnchor={last && n > 1 ? 'end' : i === 0 && n > 1 ? 'start' : 'middle'}
              fontSize={10}
              className="num fill-muted-foreground"
            >
              {fmtDia(p.dia)}
            </text>
          )
        })}
    </svg>
  )
}

interface HoverState {
  i: number
  /** Y do ponteiro dentro do gráfico; null quando veio do teclado. */
  y: number | null
}

/** Espera `data` não vazio (o estado vazio é tratado por quem chama). */
function TrendChart({ data }: { data: TimeseriesPontoOut[] }) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)
  const [hover, setHover] = useState<HoverState | null>(null)
  const n = data.length

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    setWidth(Math.round(el.clientWidth))
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry) setWidth(Math.round(entry.contentRect.width))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const hoverIdx = hover && hover.i >= 0 && hover.i < n ? hover.i : null
  const hoverPoint = hoverIdx !== null ? data[hoverIdx] : undefined

  function handlePointer(e: React.PointerEvent<HTMLDivElement>) {
    if (width === 0) return
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const innerW = Math.max(1, width - PAD_L - PAD_R)
    const raw = n > 1 ? Math.round(((x - PAD_L) / innerW) * (n - 1)) : 0
    const i = Math.min(n - 1, Math.max(0, raw))
    setHover({ i, y: e.clientY - rect.top })
  }

  function handleKey(e: React.KeyboardEvent<HTMLDivElement>) {
    let next: number | null = null
    const cur = hoverIdx ?? n - 1
    if (e.key === 'ArrowLeft') next = hoverIdx === null ? n - 1 : Math.max(0, cur - 1)
    else if (e.key === 'ArrowRight') next = hoverIdx === null ? n - 1 : Math.min(n - 1, cur + 1)
    else if (e.key === 'Home') next = 0
    else if (e.key === 'End') next = n - 1
    else if (e.key === 'Escape') {
      setHover(null)
      return
    }
    if (next === null) return
    e.preventDefault()
    setHover({ i: next, y: null })
  }

  const tipX = hoverIdx !== null ? xPos(hoverIdx, n, width) : 0
  const tipFlip = tipX > width / 2
  const tipY = Math.max(64, hover?.y ?? 64)

  return (
    <div
      ref={wrapRef}
      role="group"
      aria-roledescription="gráfico interativo"
      aria-label="Tendência diária de mensagens, OS concluídas e leads novos. Use as setas esquerda e direita para percorrer os dias."
      tabIndex={0}
      onPointerMove={handlePointer}
      onPointerDown={handlePointer}
      onPointerLeave={() => setHover(null)}
      onFocus={() => setHover((h) => h ?? { i: n - 1, y: null })}
      onBlur={() => setHover(null)}
      onKeyDown={handleKey}
      className="relative w-full min-w-0 cursor-crosshair rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-4 focus-visible:ring-offset-card"
    >
      <div className="space-y-3">
        {SERIES.map((s, idx) => {
          const total = data.reduce((acc, p) => acc + p[s.key], 0)
          const ultimo = data[n - 1]?.[s.key] ?? 0
          return (
            <div key={s.key}>
              <div className="mb-1 flex flex-wrap items-center gap-x-4 gap-y-0.5 text-xs">
                <span className="flex items-center gap-2 font-medium">
                  <span aria-hidden className={cn('h-2.5 w-2.5 shrink-0 rounded-sm', s.swatch)} />
                  {s.label}
                </span>
                <span className="ml-auto flex items-baseline gap-1.5 text-muted-foreground">
                  Total
                  <span className="num text-[13px] font-semibold text-foreground">{fmtNum(total)}</span>
                </span>
                <span className="flex items-baseline gap-1.5 text-muted-foreground">
                  Último dia
                  <span className="num text-[13px] font-semibold text-foreground">{fmtNum(ultimo)}</span>
                </span>
              </div>
              {width > 0 ? (
                <MiniChart
                  data={data}
                  serie={s}
                  width={width}
                  hoverIdx={hoverIdx}
                  showXAxis={idx === SERIES.length - 1}
                />
              ) : (
                <div
                  aria-hidden
                  style={{ height: PAD_T + PLOT_H + (idx === SERIES.length - 1 ? X_AXIS_H : 4) }}
                />
              )}
            </div>
          )
        })}
      </div>

      {/* Leitura do dia em foco — tooltip visual + anúncio pra leitor de tela */}
      {hoverPoint && width > 0 && (
        <div
          aria-hidden
          className="pointer-events-none absolute z-10 min-w-[168px] rounded-md border bg-popover px-3 py-2 text-popover-foreground shadow-lg"
          style={{
            left: tipX,
            top: tipY,
            transform: `translate(${tipFlip ? 'calc(-100% - 12px)' : '12px'}, -50%)`,
          }}
        >
          <div className="num text-[11px] text-muted-foreground">{fmtDiaCompleto(hoverPoint.dia)}</div>
          <div className="mt-1.5 space-y-1">
            {SERIES.map((s) => (
              <div key={s.key} className="flex items-center gap-2 text-xs">
                <span className={cn('h-0.5 w-3 shrink-0 rounded-full', s.swatch)} />
                <span className="text-muted-foreground">{s.label}</span>
                <span className="num ml-auto pl-3 font-semibold">{fmtNum(hoverPoint[s.key])}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      <span className="sr-only" aria-live="polite">
        {hoverPoint
          ? `${fmtDiaCompleto(hoverPoint.dia)}: ${SERIES.map(
              (s) => `${s.label} ${fmtNum(hoverPoint[s.key])}`,
            ).join(', ')}`
          : ''}
      </span>
    </div>
  )
}

/* ── OS por técnico: barras horizontais ──────────────────────────────── */

function BarChartTecnicos({ ranking }: { ranking: RankingTecnicoOut[] }) {
  const items = ranking
    .filter((t) => t.os_concluidas > 0)
    .slice(0, 10)
    .map((t) => ({
      id: t.tecnico_id,
      nomeCompleto: t.nome,
      nome: t.nome.split(' ').slice(0, 2).join(' '),
      os: t.os_concluidas,
      csat: t.csat_avg,
    }))

  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">Sem OS concluídas no mês.</p>
  }

  const max = Math.max(...items.map((t) => t.os))
  const cols = 'grid grid-cols-[7rem_minmax(0,1fr)_3.5rem] items-center gap-3 sm:grid-cols-[9rem_minmax(0,1fr)_3.5rem]'
  return (
    <div>
      <div className={cn(cols, 'px-2 pb-1.5')}>
        <span className="eyebrow text-right">Técnico</span>
        <span className="eyebrow">OS concluídas</span>
        <span className="eyebrow text-right">CSAT</span>
      </div>
      <ul>
        {items.map((t) => (
          <li
            key={t.id}
            title={`${t.nomeCompleto}: ${fmtNum(t.os)} OS concluídas${
              t.csat !== null ? ` · CSAT ${t.csat.toFixed(1)}` : ''
            }`}
            className={cn(cols, 'rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-elevated')}
          >
            <span className="truncate text-right text-muted-foreground">{t.nome}</span>
            <span className="flex min-w-0 items-center gap-2">
              {/* Barra ancorada na base (esquerda reta); só a ponta do dado arredonda. */}
              <span
                aria-hidden
                className="h-4 min-w-[2px] shrink-0 rounded-r"
                style={{
                  width: `calc((100% - 3rem) * ${(t.os / max).toFixed(4)})`,
                  backgroundColor: 'var(--chart-3)',
                }}
              />
              <span className="num text-xs font-medium">{fmtNum(t.os)}</span>
            </span>
            <span className="flex items-center justify-end gap-1 text-xs text-muted-foreground">
              {t.csat !== null ? (
                <>
                  <Star aria-hidden className="h-3 w-3" />
                  <span className="num text-foreground">{t.csat.toFixed(1)}</span>
                </>
              ) : (
                '—'
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/* ── Dashboard ───────────────────────────────────────────────────────── */

const KPI_GRID = 'grid grid-cols-2 gap-3 lg:grid-cols-4 min-[1800px]:grid-cols-7'

export function MetricasDashboard() {
  const [days, setDays] = useState<number>(30)
  const [exporting, setExporting] = useState(false)
  const { data: m, isLoading, error } = useMetricas()
  const { data: ts, isLoading: tsLoading } = useTimeseries(days)
  const mesAtual = new Date().toISOString().slice(0, 7)
  const { data: ranking, isLoading: rankLoading } = useRankingTecnicos(mesAtual)
  const [anoMes, mesMes] = mesAtual.split('-')
  const pontos = ts?.pontos ?? []

  async function handleExport() {
    setExporting(true)
    try {
      await downloadTimeseriesCsv(days)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* KPIs */}
      {isLoading && (
        <div role="status" aria-label="Carregando indicadores" className={KPI_GRID}>
          {Array.from({ length: 7 }, (_, i) => (
            <Skeleton key={i} className="h-[92px] rounded-lg" />
          ))}
        </div>
      )}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/[0.08] p-4"
        >
          <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
          <div className="min-w-0">
            <p className="text-sm font-medium">Não foi possível carregar os indicadores</p>
            <p className="mt-0.5 break-words text-xs text-muted-foreground">
              {error instanceof Error ? error.message : 'Erro'}
            </p>
          </div>
        </div>
      )}
      {m && (
        <div className={KPI_GRID}>
          <StatTile
            label="Conversas aguardando"
            value={fmtNum(m.conversas_aguardando)}
            icon={Clock}
            tone={m.conversas_aguardando > 0 ? 'warning' : 'muted'}
            alert={m.conversas_aguardando > 0}
          />
          <StatTile
            label="Conversas em humano"
            value={fmtNum(m.conversas_humano)}
            icon={MessageSquare}
            tone="info"
          />
          <StatTile label="Mensagens 24h" value={fmtNum(m.msgs_24h)} icon={BarChart3} tone="info" />
          <StatTile label="OS abertas" value={fmtNum(m.os_abertas)} icon={Wrench} tone="muted" />
          <StatTile
            label="OS concluídas 24h"
            value={fmtNum(m.os_concluidas_24h)}
            icon={CheckCircle2}
            tone="success"
          />
          <StatTile
            label="CSAT médio (30d)"
            value={
              m.csat_avg_30d !== null
                ? m.csat_avg_30d.toLocaleString('pt-BR', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })
                : '—'
            }
            icon={Star}
            tone="primary"
          />
          <StatTile
            label="Leads novos (7d)"
            value={fmtNum(m.leads_novos_7d)}
            icon={UserPlus}
            tone="primary"
          />
        </div>
      )}

      {/* Tendência diária */}
      <Panel>
        <PanelHeader
          title="Tendência diária"
          icon={TrendingUp}
          actions={
            <>
              <Segmented options={PERIODOS} value={days} onChange={setDays} ariaLabel="Período" />
              <Button
                size="sm"
                variant="outline"
                onClick={() => void handleExport()}
                disabled={exporting || tsLoading}
                className="h-7 gap-1.5 px-2.5 text-xs"
                title="Exportar série em CSV"
              >
                <Download className="h-3.5 w-3.5" />
                {exporting ? 'Exportando…' : 'CSV'}
              </Button>
            </>
          }
        />
        <PanelBody>
          <p className="mb-4 text-xs text-muted-foreground">
            Mensagens, OS concluídas e leads novos por dia — cada série na própria escala.
          </p>
          {tsLoading ? (
            <div role="status" aria-label="Carregando série" className="space-y-3">
              <Skeleton className="h-[120px] w-full" />
              <Skeleton className="h-[120px] w-full" />
              <Skeleton className="h-[138px] w-full" />
            </div>
          ) : pontos.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sem dados no período.</p>
          ) : (
            <TrendChart key={days} data={pontos} />
          )}
        </PanelBody>
      </Panel>

      {/* Distribuição por técnico */}
      <Panel>
        <PanelHeader title="OS por técnico" icon={Users} meta={`${mesMes}/${anoMes}`} />
        <PanelBody>
          <p className="mb-3 text-xs text-muted-foreground">
            Top 10 técnicos com mais OS concluídas no mês atual.
          </p>
          {rankLoading ? (
            <div role="status" aria-label="Carregando ranking" className="space-y-2">
              {Array.from({ length: 5 }, (_, i) => (
                <Skeleton key={i} className="h-7 w-full" />
              ))}
            </div>
          ) : (
            <BarChartTecnicos ranking={ranking ?? []} />
          )}
        </PanelBody>
      </Panel>
    </div>
  )
}
