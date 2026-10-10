'use client'
/**
 * Primitivas visuais do tema NOC — a "gramatica" que todas as telas usam:
 * Panel (bloco com cabecalho), StatTile (KPI), StatusDot (estado ao vivo),
 * FilterTabs (filtro por status com contagem), Avatar, PageHeader, Skeleton.
 *
 * Regras: status sempre com icone/ponto + texto (nunca so cor); numeros em
 * mono tabular (`.num`); texto nunca usa a cor da serie do grafico.
 */
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

export type Tone = 'success' | 'warning' | 'destructive' | 'info' | 'primary' | 'muted'

const TONE_TEXT: Record<Tone, string> = {
  success: 'text-success',
  warning: 'text-warning',
  destructive: 'text-destructive',
  info: 'text-info',
  primary: 'text-primary',
  muted: 'text-muted-foreground',
}

const TONE_BG: Record<Tone, string> = {
  success: 'bg-success',
  warning: 'bg-warning',
  destructive: 'bg-destructive',
  info: 'bg-info',
  primary: 'bg-primary',
  muted: 'bg-muted-foreground',
}

export const TONE_SOFT: Record<Tone, string> = {
  success: 'bg-success/[0.12] text-success ring-success/25',
  warning: 'bg-warning/[0.14] text-warning ring-warning/25',
  destructive: 'bg-destructive/[0.13] text-destructive ring-destructive/30',
  info: 'bg-info/[0.12] text-info ring-info/25',
  primary: 'bg-primary/[0.12] text-primary ring-primary/25',
  muted: 'bg-muted text-muted-foreground ring-border',
}

/* ── Cabecalho de pagina ─────────────────────────────────────────────── */

export function PageHeader({
  title,
  description,
  actions,
  className,
}: {
  title: string
  description?: React.ReactNode
  actions?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-wrap items-end justify-between gap-3', className)}>
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

/* ── Painel ──────────────────────────────────────────────────────────── */

export function Panel({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={cn('flex min-w-0 flex-col rounded-lg border bg-card text-card-foreground', className)}
      {...props}
    >
      {children}
    </section>
  )
}

export function PanelHeader({
  title,
  icon: Icon,
  meta,
  actions,
  className,
}: {
  title: string
  icon?: React.ComponentType<{ className?: string }>
  /** Texto curto ao lado do titulo (contagem, periodo). */
  meta?: React.ReactNode
  actions?: React.ReactNode
  className?: string
}) {
  return (
    <header className={cn('flex h-11 shrink-0 items-center gap-2 border-b px-4', className)}>
      {Icon && <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
      <h2 className="eyebrow truncate text-foreground/80">{title}</h2>
      {meta != null && <span className="num text-xs text-muted-foreground">{meta}</span>}
      {actions && <div className="ml-auto flex items-center gap-1.5">{actions}</div>}
    </header>
  )
}

export function PanelBody({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('min-h-0 flex-1 p-4', className)} {...props} />
}

/* ── Ponto de status ─────────────────────────────────────────────────── */

export function StatusDot({
  tone,
  pulse = false,
  className,
}: {
  tone: Tone
  /** Anel pulsante — reservar pra "ao vivo" ou alerta ativo. */
  pulse?: boolean
  className?: string
}) {
  return (
    <span aria-hidden className={cn('relative inline-flex h-2 w-2 shrink-0', className)}>
      {pulse && (
        <span className={cn('absolute inset-0 rounded-full animate-status-ping', TONE_BG[tone])} />
      )}
      <span className={cn('relative h-2 w-2 rounded-full', TONE_BG[tone])} />
    </span>
  )
}

/** Chip de estado: ponto + rotulo (+ valor). Usado na barra de sistema. */
export function StatusChip({
  tone,
  label,
  value,
  pulse,
  title,
  className,
}: {
  tone: Tone
  label: string
  value?: React.ReactNode
  pulse?: boolean
  title?: string
  className?: string
}) {
  return (
    <span
      title={title}
      className={cn(
        'inline-flex h-7 items-center gap-2 rounded-md border bg-card px-2.5 text-xs',
        className,
      )}
    >
      <StatusDot tone={tone} pulse={pulse} />
      <span className="text-muted-foreground">{label}</span>
      {value != null && <span className="font-medium text-foreground">{value}</span>}
    </span>
  )
}

/* ── KPI ─────────────────────────────────────────────────────────────── */

export function StatTile({
  label,
  value,
  unit,
  hint,
  icon: Icon,
  tone = 'muted',
  alert = false,
  href,
  children,
  className,
}: {
  label: string
  value: React.ReactNode
  unit?: string
  /** Linha de contexto abaixo do numero ("meta 15 min", "vs ontem"). */
  hint?: React.ReactNode
  icon?: React.ComponentType<{ className?: string }>
  tone?: Tone
  /** Destaca o tile inteiro (borda + faixa) — usar so quando exige acao. */
  alert?: boolean
  href?: string
  /** Slot inferior (sparkline, barra de progresso). */
  children?: React.ReactNode
  className?: string
}) {
  const body = (
    <>
      <span
        aria-hidden
        className={cn(
          'absolute inset-y-0 left-0 w-[3px] rounded-l-lg',
          alert ? TONE_BG[tone] : 'bg-transparent',
        )}
      />
      <div className="flex items-center justify-between gap-2">
        <span className="eyebrow truncate">{label}</span>
        {Icon && <Icon className={cn('h-3.5 w-3.5 shrink-0', TONE_TEXT[tone])} />}
      </div>
      <div className="mt-2 flex items-baseline gap-1.5">
        <span className={cn('num text-[28px] font-semibold leading-none', alert && TONE_TEXT[tone])}>
          {value}
        </span>
        {unit && <span className="text-xs text-muted-foreground">{unit}</span>}
      </div>
      {hint && <div className="mt-1.5 truncate text-xs text-muted-foreground">{hint}</div>}
      {children && <div className="mt-3">{children}</div>}
    </>
  )
  const cls = cn(
    'relative block rounded-lg border bg-card p-4 transition-colors',
    alert && tone === 'destructive' && 'border-destructive/40',
    alert && tone === 'warning' && 'border-warning/40',
    href && 'hover:bg-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
    className,
  )
  if (href) {
    return (
      <Link href={href} className={cls}>
        {body}
      </Link>
    )
  }
  return <div className={cls}>{body}</div>
}

/* ── Filtro por status (abas com contagem) ───────────────────────────── */

export interface FilterTab<T extends string> {
  value: T
  label: string
  count?: number | null
  tone?: Tone
}

export function FilterTabs<T extends string>({
  tabs,
  value,
  onChange,
  ariaLabel,
  className,
}: {
  tabs: ReadonlyArray<FilterTab<T>>
  value: T
  onChange: (v: T) => void
  ariaLabel: string
  className?: string
}) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn('inline-flex flex-wrap items-center gap-1 rounded-lg border bg-card p-1', className)}
    >
      {tabs.map((t) => {
        const active = t.value === value
        return (
          <button
            key={t.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(t.value)}
            className={cn(
              'inline-flex h-7 items-center gap-2 rounded-md px-2.5 text-xs font-medium transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              active
                ? 'bg-secondary text-foreground'
                : 'text-muted-foreground hover:bg-elevated hover:text-foreground',
            )}
          >
            {t.tone && <StatusDot tone={t.tone} />}
            {t.label}
            {t.count != null && (
              <span className={cn('num text-[11px]', active ? 'text-foreground' : 'text-muted-foreground')}>
                {t.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

/* ── Avatar de iniciais ──────────────────────────────────────────────── */

export function initials(name: string): string {
  // So letras: um telefone como nome ("(97) 9 8401-4115") nao vira "(8".
  const parts = name
    .replace(/[^\p{L}\s]/gu, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
  if (parts.length === 0) return '#'
  const first = parts[0]?.[0] ?? ''
  const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? '') : ''
  return (first + last).toUpperCase()
}

export function Avatar({
  name,
  size = 'md',
  className,
}: {
  name: string
  size?: 'sm' | 'md'
  className?: string
}) {
  return (
    <span
      aria-hidden
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded-md bg-secondary font-semibold text-secondary-foreground',
        size === 'sm' ? 'h-6 w-6 text-[10px]' : 'h-8 w-8 text-[11px]',
        className,
      )}
    >
      {initials(name)}
    </span>
  )
}

/* ── Skeleton ────────────────────────────────────────────────────────── */

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn('animate-pulse rounded-md bg-muted', className)} />
}

/** Linhas-fantasma pra tabela/lista enquanto carrega. */
export function SkeletonRows({ rows = 6, className }: { rows?: number; className?: string }) {
  return (
    <div role="status" aria-label="Carregando" className={cn('space-y-2 p-4', className)}>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-9 w-full" />
      ))}
    </div>
  )
}

/* ── Tempo ───────────────────────────────────────────────────────────── */

/** "agora", "5min", "3h", "2d" — idade compacta pra colunas densas. */
export function ageShort(iso: string | null | undefined, now: number = Date.now()): string {
  if (!iso) return '—'
  const ms = now - new Date(iso).getTime()
  if (Number.isNaN(ms)) return '—'
  const min = Math.floor(ms / 60_000)
  if (min < 1) return 'agora'
  if (min < 60) return `${min}min`
  const h = Math.floor(min / 60)
  if (h < 48) return `${h}h`
  return `${Math.floor(h / 24)}d`
}

/** Re-renderiza a cada `ms` — pra idades/relogios andarem sem refetch. */
export function useNow(ms = 30_000): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), ms)
    return () => clearInterval(id)
  }, [ms])
  return now
}

/** Idade que se atualiza sozinha; `title` traz a data completa. */
export function Age({ iso, className }: { iso: string | null | undefined; className?: string }) {
  const now = useNow()
  return (
    <span
      className={cn('num text-xs text-muted-foreground', className)}
      title={iso ? new Date(iso).toLocaleString('pt-BR') : undefined}
      suppressHydrationWarning
    >
      {ageShort(iso, now)}
    </span>
  )
}
