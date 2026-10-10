'use client'
/**
 * Estado do sistema pro shell (topbar/sidebar) e pro Painel NOC.
 * Fonte: /healthz (db, redis, worker, evolution) — mesmo endpoint que a tela
 * de Configuracoes ja usa. Poll de 30s, uma query compartilhada.
 */
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api/client'
import type { Tone } from './primitives'

interface HealthOut {
  status: string
  checks: Record<string, string>
}

export interface SystemCheck {
  key: string
  label: string
  tone: Tone
  /** Texto curto do estado ("Conectado", "Fora do ar"). */
  state: string
}

const LABELS: Record<string, string> = {
  evolution: 'WhatsApp',
  db: 'Banco',
  redis: 'Fila',
  worker: 'Worker',
  celery: 'Worker',
}

export function useSystemHealth() {
  const q = useQuery<HealthOut>({
    queryKey: ['healthz'],
    queryFn: () => apiFetch<HealthOut>('/healthz'),
    refetchInterval: 30_000,
    retry: 0,
  })
  const checks: SystemCheck[] = Object.entries(q.data?.checks ?? {}).map(([key, raw]) => {
    const ok = raw === 'ok'
    return {
      key,
      label: LABELS[key] ?? key,
      tone: ok ? 'success' : 'destructive',
      state: ok ? (key === 'evolution' ? 'Conectado' : 'OK') : raw || 'Falha',
    }
  })
  // Sem resposta do /healthz = a propria API esta inacessivel.
  const apiDown = q.isError
  const failing = checks.filter((c) => c.tone !== 'success')
  const overall: Tone = apiDown ? 'destructive' : failing.length > 0 ? 'warning' : q.data ? 'success' : 'muted'
  const summary = apiDown
    ? 'API inacessível'
    : failing.length > 0
      ? `${failing.length} ${failing.length === 1 ? 'serviço com falha' : 'serviços com falha'}`
      : q.data
        ? 'Todos os sistemas operacionais'
        : 'Verificando…'
  return { checks, overall, summary, apiDown, isLoading: q.isLoading, updatedAt: q.dataUpdatedAt }
}

/** Relogio da operacao. Renderiza vazio no SSR pra nao dar mismatch de hidratacao. */
export function LiveClock({ className }: { className?: string }) {
  const [now, setNow] = useState<Date | null>(null)
  useEffect(() => {
    setNow(new Date())
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  const time = now
    ? now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '--:--:--'
  const rawDate = now
    ? now.toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: 'short' }).replace(/\./g, '')
    : ''
  // "sex, 09 de out" -> "Sex, 09 de out" (so a primeira letra; `capitalize` do CSS subia o "de").
  const date = rawDate.charAt(0).toUpperCase() + rawDate.slice(1)
  return (
    <time className={className} dateTime={now?.toISOString()} suppressHydrationWarning>
      <span className="num text-sm font-medium text-foreground">{time}</span>
      {date && <span className="ml-2 hidden text-xs text-muted-foreground xl:inline">{date}</span>}
    </time>
  )
}
