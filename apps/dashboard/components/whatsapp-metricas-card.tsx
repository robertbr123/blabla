'use client'
import { useState } from 'react'
import { AlertTriangle, CheckCircle2, Eye, MessageSquare, XCircle } from 'lucide-react'
import {
  Panel,
  PanelBody,
  PanelHeader,
  SkeletonRows,
  StatTile,
} from '@/components/noc/primitives'
import { useWhatsAppMetricas } from '@/lib/api/queries'
import type { TemplateStats } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { Segmented } from './metricas-dashboard'

/**
 * Painel de métricas de templates WhatsApp — Fase 2.2 do plano de evolução.
 *
 * Mostra tabela por template com taxas de entrega/leitura/falha numa janela
 * temporal selecionável (7/14/30 dias). Dados vêm de whatsapp_message_status,
 * populada pelo envio (INSERT) e pelo webhook Cloud (UPDATE).
 */

const DAYS_OPTIONS: ReadonlyArray<{ value: number; label: string }> = [
  { value: 7, label: '7d' },
  { value: 14, label: '14d' },
  { value: 30, label: '30d' },
]

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`
}

function fmt(n: number): string {
  return n.toLocaleString('pt-BR')
}

type RateLevel = 'good' | 'neutral' | 'warn' | 'bad'

function rateLevel(rate: number, kind: 'good' | 'bad'): RateLevel {
  // good (delivery/read): mais alto melhor; bad (failure): mais baixo melhor.
  if (kind === 'good') {
    if (rate >= 0.95) return 'good'
    if (rate >= 0.8) return 'neutral'
    return 'warn'
  }
  // bad: failure rate
  if (rate >= 0.1) return 'bad'
  if (rate >= 0.03) return 'warn'
  return 'neutral'
}

const LEVEL_TEXT: Record<RateLevel, string> = {
  good: 'text-success',
  neutral: 'text-foreground',
  warn: 'text-warning',
  bad: 'text-destructive',
}

/** Taxa + contagem absoluta. Nível ruim ganha ícone — nunca só a cor. */
function RateCell({
  rate,
  count,
  kind,
  empty = false,
}: {
  rate: number
  count: number
  kind: 'good' | 'bad'
  empty?: boolean
}) {
  if (empty) return <td className="num text-right text-muted-foreground">—</td>
  const level = rateLevel(rate, kind)
  const flagged = level === 'warn' || level === 'bad'
  return (
    <td className="whitespace-nowrap text-right">
      <span className={cn('num inline-flex items-center gap-1', LEVEL_TEXT[level])}>
        {flagged && (
          <>
            <AlertTriangle aria-hidden className="h-3 w-3 shrink-0" />
            <span className="sr-only">{level === 'bad' ? 'Crítico:' : 'Atenção:'}</span>
          </>
        )}
        {pct(rate)}
      </span>
      <span className="num ml-1.5 text-[11px] text-muted-foreground">({fmt(count)})</span>
    </td>
  )
}

interface TemplateRowProps {
  item: TemplateStats
}

function TemplateRow({ item }: TemplateRowProps) {
  return (
    <tr>
      <td>
        <code className="num text-xs font-medium">{item.template_name}</code>
      </td>
      <td className="num text-right">{fmt(item.sent)}</td>
      <RateCell rate={item.delivery_rate} count={item.delivered} kind="good" />
      <RateCell rate={item.read_rate} count={item.read} kind="good" />
      <RateCell
        rate={item.failure_rate}
        count={item.failed}
        kind="bad"
        empty={item.failed <= 0}
      />
    </tr>
  )
}

export function WhatsAppMetricasCard() {
  const [days, setDays] = useState<number>(7)
  const { data, isLoading, isError } = useWhatsAppMetricas(days)

  return (
    <Panel>
      <PanelHeader
        title="WhatsApp — templates"
        icon={MessageSquare}
        actions={
          <Segmented options={DAYS_OPTIONS} value={days} onChange={setDays} ariaLabel="Período" />
        }
      />
      <PanelBody className="space-y-4">
        <p className="text-xs text-muted-foreground">
          Entrega e leitura por template — status updates do Meta (delivered / read / failed).
          Atualiza a cada 2 min.
        </p>

        {isLoading && <SkeletonRows rows={4} className="p-0" />}
        {isError && (
          <div
            role="alert"
            className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/[0.08] p-3 text-sm"
          >
            <AlertTriangle aria-hidden className="h-4 w-4 shrink-0 text-destructive" />
            Falha ao carregar.
          </div>
        )}
        {data && data.items.length === 0 && (
          <div className="rounded-md border border-dashed p-4 text-center text-sm text-muted-foreground">
            Sem envios de templates nos últimos {days} dias.
          </div>
        )}

        {data && data.items.length > 0 && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatTile label="Enviadas" value={fmt(data.total_sent)} icon={MessageSquare} />
            <StatTile
              label="Entregues"
              value={
                data.total_sent > 0
                  ? pct(data.total_delivered / data.total_sent)
                  : '—'
              }
              icon={CheckCircle2}
              tone="success"
            />
            <StatTile
              label="Lidas"
              value={
                data.total_sent > 0
                  ? pct(data.total_read / data.total_sent)
                  : '—'
              }
              icon={Eye}
              tone="info"
            />
            <StatTile
              label="Falhas"
              value={fmt(data.total_failed)}
              icon={XCircle}
              tone={data.total_failed > 0 ? 'destructive' : 'muted'}
            />
          </div>
        )}
      </PanelBody>

      {data && data.items.length > 0 && (
        <div className="overflow-x-auto border-t">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Template</th>
                <th scope="col" className="text-right">Enviadas</th>
                <th scope="col" className="text-right">Entrega</th>
                <th scope="col" className="text-right">Leitura</th>
                <th scope="col" className="text-right">Falha</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((it) => (
                <TemplateRow key={it.template_name} item={it} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
