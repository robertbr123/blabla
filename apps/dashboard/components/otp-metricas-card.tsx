'use client'
import { AlertTriangle, CheckCircle2, Cloud, MessageCircle, Send } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { useOtpMetricas } from '@/lib/api/queries'
import { cn } from '@/lib/utils'

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

interface ProviderColumnProps {
  title: string
  icon: React.ComponentType<{ className?: string }>
  tone: 'cloud' | 'evolution'
  success: number
  fallback: number
  error: number
}

const TONE_BG: Record<ProviderColumnProps['tone'], string> = {
  cloud: 'bg-primary/[0.08] text-primary',
  evolution: 'bg-warning/[0.12] text-warning',
}

function ProviderColumn({ title, icon: Icon, tone, success, fallback, error }: ProviderColumnProps) {
  const total = success + fallback + error
  return (
    <div className="flex-1 rounded-lg border bg-card p-4">
      <div className="flex items-center gap-2">
        <div className={cn('flex h-7 w-7 items-center justify-center rounded-md', TONE_BG[tone])}>
          <Icon className="h-3.5 w-3.5" />
        </div>
        <div className="text-sm font-medium">{title}</div>
        <div className="ml-auto text-xs text-muted-foreground" style={{ fontVariantNumeric: 'tabular-nums' }}>
          {fmt(total)} envios
        </div>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground">Sucesso</span>
          <span className="font-semibold tabular-nums">{fmt(success)}</span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground">Fallback</span>
          <span className="font-semibold tabular-nums">{fmt(fallback)}</span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground">Erro</span>
          <span className={cn('font-semibold tabular-nums', error > 0 && 'text-destructive')}>
            {fmt(error)}
          </span>
        </div>
      </div>
    </div>
  )
}

export function OtpMetricasCard() {
  const { data, isLoading, isError } = useOtpMetricas()

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-5">
          <div className="text-sm text-muted-foreground">Carregando métricas de OTP…</div>
        </CardContent>
      </Card>
    )
  }
  if (isError || !data) {
    return (
      <Card>
        <CardContent className="p-5">
          <div className="text-sm text-destructive">Falha ao carregar métricas de OTP.</div>
        </CardContent>
      </Card>
    )
  }

  const noData = data.total === 0
  const fallbackAlert = data.cloud_fallback_rate > 0.05 // >5% chama atenção

  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Send className="h-4 w-4 text-muted-foreground" />
              <h3 className="text-sm font-semibold">OTP — Provedor de envio</h3>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Split Cloud (oficial) vs Evolution (legado). Contadores desde o último restart da API.
            </p>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Total</div>
            <div className="text-2xl font-semibold tabular-nums">{fmt(data.total)}</div>
          </div>
        </div>

        {noData ? (
          <div className="rounded-md border border-dashed p-4 text-center text-sm text-muted-foreground">
            Sem envios registrados ainda nesta instância.
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-3 sm:flex-row">
              <ProviderColumn
                title="Cloud (oficial)"
                icon={Cloud}
                tone="cloud"
                success={data.cloud.success}
                fallback={data.cloud.fallback_to_evolution}
                error={data.cloud.error}
              />
              <ProviderColumn
                title="Evolution (legado)"
                icon={MessageCircle}
                tone="evolution"
                success={data.evolution.success}
                fallback={data.evolution.fallback_to_evolution}
                error={data.evolution.error}
              />
            </div>

            <div className="grid grid-cols-2 gap-3 sm:gap-4">
              <div className="rounded-lg border bg-card p-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                  <span className="text-xs text-muted-foreground">Taxa de sucesso Cloud</span>
                </div>
                <div className="mt-1 text-xl font-semibold tabular-nums">
                  {pct(data.cloud_success_rate)}
                </div>
              </div>
              <div className="rounded-lg border bg-card p-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle
                    className={cn(
                      'h-3.5 w-3.5',
                      fallbackAlert ? 'text-destructive' : 'text-muted-foreground',
                    )}
                  />
                  <span className="text-xs text-muted-foreground">Taxa de fallback Cloud→Evolution</span>
                </div>
                <div
                  className={cn(
                    'mt-1 text-xl font-semibold tabular-nums',
                    fallbackAlert && 'text-destructive',
                  )}
                >
                  {pct(data.cloud_fallback_rate)}
                </div>
                {fallbackAlert && (
                  <p className="mt-1 text-[11px] text-destructive">
                    Acima de 5% — investigar template ou config Cloud.
                  </p>
                )}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
