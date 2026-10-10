'use client'
import { AlertTriangle, CheckCircle2, Cloud, MessageCircle, Send } from 'lucide-react'
import {
  Panel,
  PanelBody,
  PanelHeader,
  SkeletonRows,
  StatTile,
} from '@/components/noc/primitives'
import { useOtpMetricas } from '@/lib/api/queries'
import { cn } from '@/lib/utils'
import { PANEL_HEADER_WRAP, TILE_LABEL_WRAP } from './responsive'

/**
 * Painel de métricas de OTP — Fase 2.3 do plano de evolução.
 *
 * Mostra split de envio (Cloud oficial vs Evolution legado) com taxas de
 * sucesso e fallback. Os contadores Prometheus são cumulativos desde o último
 * restart da API, então o painel é "vida da instância", não janela temporal.
 */
function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`
}

function fmt(n: number): string {
  return n.toLocaleString('pt-BR')
}

interface ProviderRowProps {
  title: string
  icon: React.ComponentType<{ className?: string }>
  success: number
  fallback: number
  error: number
}

function ProviderRow({ title, icon: Icon, success, fallback, error }: ProviderRowProps) {
  const total = success + fallback + error
  return (
    <tr>
      <td>
        <span className="flex items-center gap-2 whitespace-nowrap font-medium">
          <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          {title}
        </span>
      </td>
      <td className="num text-right">{fmt(total)}</td>
      <td className="num text-right">{fmt(success)}</td>
      <td className="num text-right">{fmt(fallback)}</td>
      <td className="text-right">
        <span
          className={cn(
            'num inline-flex items-center gap-1',
            error > 0 && 'font-medium text-destructive',
          )}
        >
          {error > 0 && (
            <>
              <AlertTriangle aria-hidden className="h-3 w-3 shrink-0" />
              <span className="sr-only">Com erros:</span>
            </>
          )}
          {fmt(error)}
        </span>
      </td>
    </tr>
  )
}

const TITULO = 'OTP — provedor de envio'

export function OtpMetricasCard() {
  const { data, isLoading, isError } = useOtpMetricas()

  if (isLoading) {
    return (
      <Panel>
        <PanelHeader title={TITULO} icon={Send} />
        <SkeletonRows rows={3} />
      </Panel>
    )
  }
  if (isError || !data) {
    return (
      <Panel>
        <PanelHeader title={TITULO} icon={Send} />
        <PanelBody>
          <div
            role="alert"
            className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/[0.08] p-3 text-sm"
          >
            <AlertTriangle aria-hidden className="h-4 w-4 shrink-0 text-destructive" />
            Falha ao carregar métricas de OTP.
          </div>
        </PanelBody>
      </Panel>
    )
  }

  const noData = data.total === 0
  const fallbackAlert = data.cloud_fallback_rate > 0.05 // >5% chama atenção

  return (
    <Panel>
      <PanelHeader
        title={TITULO}
        icon={Send}
        className={PANEL_HEADER_WRAP}
        actions={
          <span className="flex items-baseline gap-1.5 text-xs text-muted-foreground">
            Total
            <span className="num text-sm font-semibold text-foreground">{fmt(data.total)}</span>
          </span>
        }
      />
      <PanelBody className="space-y-4">
        <p className="text-xs text-muted-foreground">
          Split Cloud (oficial) vs Evolution (legado). Contadores desde o último restart da API.
        </p>

        {noData ? (
          <div className="rounded-md border border-dashed p-4 text-center text-sm text-muted-foreground">
            Sem envios registrados ainda nesta instância.
          </div>
        ) : (
          <div className={cn('grid grid-cols-2 gap-3', TILE_LABEL_WRAP)}>
            <StatTile
              label="Taxa de sucesso Cloud"
              value={pct(data.cloud_success_rate)}
              icon={CheckCircle2}
              tone="success"
            />
            <StatTile
              label="Fallback Cloud→Evolution"
              value={pct(data.cloud_fallback_rate)}
              icon={AlertTriangle}
              tone={fallbackAlert ? 'destructive' : 'muted'}
              alert={fallbackAlert}
              hint={
                fallbackAlert
                  ? 'Acima de 5% — investigar template ou config Cloud.'
                  : undefined
              }
            />
          </div>
        )}
      </PanelBody>

      {!noData && (
        <div className="overflow-x-auto border-t">
          <table className="data-table min-w-[460px]">
            <thead>
              <tr>
                <th scope="col">Provedor</th>
                <th scope="col" className="text-right">Envios</th>
                <th scope="col" className="text-right">Sucesso</th>
                <th scope="col" className="text-right">Fallback</th>
                <th scope="col" className="text-right">Erro</th>
              </tr>
            </thead>
            <tbody>
              <ProviderRow
                title="Cloud (oficial)"
                icon={Cloud}
                success={data.cloud.success}
                fallback={data.cloud.fallback_to_evolution}
                error={data.cloud.error}
              />
              <ProviderRow
                title="Evolution (legado)"
                icon={MessageCircle}
                success={data.evolution.success}
                fallback={data.evolution.fallback_to_evolution}
                error={data.evolution.error}
              />
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
