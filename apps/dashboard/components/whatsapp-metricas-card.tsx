'use client'
import { useState } from 'react'
import { CheckCircle2, Eye, MessageSquare, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useWhatsAppMetricas } from '@/lib/api/queries'
import type { TemplateStats } from '@/lib/api/types'
import { cn } from '@/lib/utils'

/**
 * Painel de métricas de templates WhatsApp — Fase 2.2 do plano de evolução.
 *
 * Mostra tabela por template com taxas de entrega/leitura/falha numa janela
 * temporal selecionável (7/14/30 dias). Dados vêm de whatsapp_message_status,
 * populada pelo envio (INSERT) e pelo webhook Cloud (UPDATE).
 */

const DAYS_OPTIONS = [7, 14, 30] as const

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`
}

function fmt(n: number): string {
  return n.toLocaleString('pt-BR')
}

function rateColor(rate: number, kind: 'good' | 'bad'): string {
  // good (delivery/read): mais alto melhor; bad (failure): mais baixo melhor.
  if (kind === 'good') {
    if (rate >= 0.95) return 'text-success'
    if (rate >= 0.8) return 'text-foreground'
    return 'text-warning'
  }
  // bad: failure rate
  if (rate >= 0.1) return 'text-destructive'
  if (rate >= 0.03) return 'text-warning'
  return 'text-foreground'
}

interface TemplateRowProps {
  item: TemplateStats
}

function TemplateRow({ item }: TemplateRowProps) {
  return (
    <tr className="border-b last:border-0 hover:bg-muted/40">
      <td className="py-2.5 pl-4 pr-2">
        <code className="text-xs font-medium">{item.template_name}</code>
      </td>
      <td className="px-2 py-2.5 text-right tabular-nums">{fmt(item.sent)}</td>
      <td className={cn('px-2 py-2.5 text-right tabular-nums', rateColor(item.delivery_rate, 'good'))}>
        {pct(item.delivery_rate)}
        <span className="ml-1 text-[10px] text-muted-foreground">({fmt(item.delivered)})</span>
      </td>
      <td className={cn('px-2 py-2.5 text-right tabular-nums', rateColor(item.read_rate, 'good'))}>
        {pct(item.read_rate)}
        <span className="ml-1 text-[10px] text-muted-foreground">({fmt(item.read)})</span>
      </td>
      <td className={cn('py-2.5 pl-2 pr-4 text-right tabular-nums', rateColor(item.failure_rate, 'bad'))}>
        {item.failed > 0 ? pct(item.failure_rate) : '—'}
        {item.failed > 0 && (
          <span className="ml-1 text-[10px] text-muted-foreground">({fmt(item.failed)})</span>
        )}
      </td>
    </tr>
  )
}

export function WhatsAppMetricasCard() {
  const [days, setDays] = useState<number>(7)
  const { data, isLoading, isError } = useWhatsAppMetricas(days)

  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              <h3 className="text-sm font-semibold">WhatsApp — Templates (entrega &amp; leitura)</h3>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Status updates do Meta (delivered / read / failed). Atualiza a cada 2 min.
            </p>
          </div>
          <div className="flex gap-1">
            {DAYS_OPTIONS.map((d) => (
              <Button
                key={d}
                type="button"
                variant={days === d ? 'default' : 'outline'}
                size="sm"
                className="h-7 px-2.5 text-xs"
                onClick={() => setDays(d)}
              >
                {d}d
              </Button>
            ))}
          </div>
        </div>

        {isLoading && (
          <div className="text-sm text-muted-foreground">Carregando…</div>
        )}
        {isError && (
          <div className="text-sm text-destructive">Falha ao carregar.</div>
        )}
        {data && data.items.length === 0 && (
          <div className="rounded-md border border-dashed p-4 text-center text-sm text-muted-foreground">
            Sem envios de templates nos últimos {days} dias.
          </div>
        )}

        {data && data.items.length > 0 && (
          <>
            <div className="grid grid-cols-4 gap-3">
              <SummaryStat label="Enviadas" value={fmt(data.total_sent)} icon={MessageSquare} />
              <SummaryStat
                label="Entregues"
                value={
                  data.total_sent > 0
                    ? pct(data.total_delivered / data.total_sent)
                    : '—'
                }
                icon={CheckCircle2}
                tone="success"
              />
              <SummaryStat
                label="Lidas"
                value={
                  data.total_sent > 0
                    ? pct(data.total_read / data.total_sent)
                    : '—'
                }
                icon={Eye}
                tone="info"
              />
              <SummaryStat
                label="Falhas"
                value={fmt(data.total_failed)}
                icon={XCircle}
                tone={data.total_failed > 0 ? 'destructive' : 'muted'}
              />
            </div>

            <div className="overflow-hidden rounded-md border">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-[11px] uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="py-2 pl-4 pr-2 text-left font-medium">Template</th>
                    <th className="px-2 py-2 text-right font-medium">Enviadas</th>
                    <th className="px-2 py-2 text-right font-medium">Entrega</th>
                    <th className="px-2 py-2 text-right font-medium">Leitura</th>
                    <th className="py-2 pl-2 pr-4 text-right font-medium">Falha</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((it) => (
                    <TemplateRow key={it.template_name} item={it} />
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

interface SummaryStatProps {
  label: string
  value: string
  icon: React.ComponentType<{ className?: string }>
  tone?: 'success' | 'info' | 'destructive' | 'muted'
}

const SUMMARY_TONE: Record<NonNullable<SummaryStatProps['tone']>, string> = {
  success: 'bg-success/[0.12] text-success',
  info: 'bg-info/[0.12] text-info',
  destructive: 'bg-destructive/[0.12] text-destructive',
  muted: 'bg-muted text-muted-foreground',
}

function SummaryStat({ label, value, icon: Icon, tone = 'muted' }: SummaryStatProps) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</span>
        <div className={cn('flex h-6 w-6 items-center justify-center rounded-md', SUMMARY_TONE[tone])}>
          <Icon className="h-3 w-3" />
        </div>
      </div>
      <div className="mt-1 text-xl font-semibold tabular-nums">{value}</div>
    </div>
  )
}
