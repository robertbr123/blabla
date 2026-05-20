'use client'

import { useTheme } from 'next-themes'
import { useEffect, useState } from 'react'
import {
  CheckCircle2,
  Clock,
  XCircle,
  PlayCircle,
  Moon,
  Sun,
  TrendingUp,
  Users,
  Wrench,
  MessageSquare,
} from 'lucide-react'

const PREVIEW_TOKENS_LIGHT = {
  '--background': '0 0% 100%',
  '--foreground': '222.2 84% 4.9%',
  '--card': '0 0% 100%',
  '--card-foreground': '222.2 84% 4.9%',
  '--primary': '160 84% 39%',
  '--primary-foreground': '0 0% 100%',
  '--secondary': '210 40% 96%',
  '--secondary-foreground': '222.2 47.4% 11.2%',
  '--muted': '210 40% 96%',
  '--muted-foreground': '215.4 16.3% 46.9%',
  '--accent': '160 84% 96%',
  '--accent-foreground': '160 84% 25%',
  '--destructive': '0 84.2% 60.2%',
  '--destructive-foreground': '0 0% 100%',
  '--success': '160 84% 39%',
  '--warning': '38 92% 50%',
  '--info': '217 91% 60%',
  '--border': '214.3 31.8% 91.4%',
  '--input': '214.3 31.8% 91.4%',
  '--ring': '160 84% 39%',
  '--radius': '0.5rem',
} as const

const PREVIEW_TOKENS_DARK = {
  '--background': '222.2 84% 4.9%',
  '--foreground': '210 40% 98%',
  '--card': '222.2 47% 7%',
  '--card-foreground': '210 40% 98%',
  '--primary': '160 84% 45%',
  '--primary-foreground': '160 84% 8%',
  '--secondary': '217.2 32.6% 17.5%',
  '--secondary-foreground': '210 40% 98%',
  '--muted': '217.2 32.6% 17.5%',
  '--muted-foreground': '215 20.2% 65.1%',
  '--accent': '160 50% 15%',
  '--accent-foreground': '160 84% 70%',
  '--destructive': '0 62.8% 50%',
  '--destructive-foreground': '0 0% 100%',
  '--success': '160 70% 45%',
  '--warning': '38 92% 55%',
  '--info': '217 91% 65%',
  '--border': '217.2 32.6% 17.5%',
  '--input': '217.2 32.6% 17.5%',
  '--ring': '160 84% 45%',
  '--radius': '0.5rem',
} as const

export default function DesignPreviewPage() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  const isDark = mounted && resolvedTheme === 'dark'
  const tokens = isDark ? PREVIEW_TOKENS_DARK : PREVIEW_TOKENS_LIGHT

  return (
    <div
      style={tokens as React.CSSProperties}
      className="min-h-screen bg-[hsl(var(--background))] text-[hsl(var(--foreground))] font-sans"
    >
      <div className="mx-auto max-w-6xl px-6 py-10 space-y-12">
        <header className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
              Fase 1 · Design System Preview
            </p>
            <h1 className="text-3xl font-bold mt-1">BlaBla Dashboard</h1>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mt-2">
              Tokens escopados nesta página. Nenhum componente real foi modificado.
            </p>
          </div>
          <button
            onClick={() => setTheme(isDark ? 'light' : 'dark')}
            className="inline-flex items-center gap-2 rounded-md border border-[hsl(var(--border))] px-3 py-2 text-sm hover:bg-[hsl(var(--accent))] hover:text-[hsl(var(--accent-foreground))] transition-colors"
          >
            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {isDark ? 'Light' : 'Dark'}
          </button>
        </header>

        {/* COLORS */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Paleta semântica</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { name: 'Primary', token: '--primary', fg: '--primary-foreground', note: 'Verde BlaBla · CTA/ativo' },
              { name: 'Success', token: '--success', fg: '--primary-foreground', note: 'Status positivo' },
              { name: 'Warning', token: '--warning', fg: '--primary-foreground', note: 'Atenção' },
              { name: 'Info', token: '--info', fg: '--primary-foreground', note: 'Informativo' },
              { name: 'Destructive', token: '--destructive', fg: '--destructive-foreground', note: 'Erro/perigo' },
              { name: 'Foreground', token: '--foreground', fg: '--background', note: 'Texto principal' },
              { name: 'Muted', token: '--muted-foreground', fg: '--background', note: 'Texto secundário' },
              { name: 'Border', token: '--border', fg: '--foreground', note: 'Divisores' },
            ].map((c) => (
              <div
                key={c.token}
                className="rounded-lg border border-[hsl(var(--border))] overflow-hidden"
              >
                <div
                  className="h-16 flex items-end p-2 text-xs font-medium"
                  style={{
                    background: `hsl(var(${c.token}))`,
                    color: `hsl(var(${c.fg}))`,
                  }}
                >
                  {c.name}
                </div>
                <div className="p-2 bg-[hsl(var(--card))] text-[10px] text-[hsl(var(--muted-foreground))]">
                  <code>{c.token}</code>
                  <div className="mt-0.5">{c.note}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* TYPOGRAPHY */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Escala tipográfica · Inter</h2>
          <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] divide-y divide-[hsl(var(--border))]">
            {[
              { label: 'display · 30/36 · 700', cls: 'text-3xl font-bold leading-9', sample: 'Métricas operacionais' },
              { label: 'h1 · 24/32 · 600', cls: 'text-2xl font-semibold leading-8', sample: 'Ordens de serviço' },
              { label: 'h2 · 18/28 · 600', cls: 'text-lg font-semibold leading-7', sample: 'Aberto · 24 OS' },
              { label: 'h3 · 14/20 · 600', cls: 'text-sm font-semibold leading-5', sample: 'STATUS' },
              { label: 'body · 14/20 · 400', cls: 'text-sm leading-5', sample: 'Técnico João Silva concluiu a OS #1247 às 14:32.' },
              { label: 'small · 12/16 · 400', cls: 'text-xs leading-4', sample: 'Atualizado há 2 minutos' },
              { label: 'tabular · numbers', cls: 'text-sm font-mono tabular-nums', sample: 'R$ 12.480,00  ·  1.247 chamadas  ·  98,4%' },
            ].map((t) => (
              <div key={t.label} className="flex items-center gap-6 px-4 py-3">
                <span className="w-44 shrink-0 text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                  {t.label}
                </span>
                <span className={t.cls} style={t.label.startsWith('tabular') ? { fontVariantNumeric: 'tabular-nums' } : undefined}>
                  {t.sample}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* BUTTONS */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Botões</h2>
          <div className="flex flex-wrap gap-3">
            <button className="rounded-md bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] px-4 py-2 text-sm font-medium hover:opacity-90 transition-opacity focus:outline-none focus:ring-2 focus:ring-[hsl(var(--ring))] focus:ring-offset-2 focus:ring-offset-[hsl(var(--background))]">
              Abrir OS
            </button>
            <button className="rounded-md bg-[hsl(var(--secondary))] text-[hsl(var(--secondary-foreground))] px-4 py-2 text-sm font-medium hover:bg-[hsl(var(--accent))] transition-colors">
              Secundário
            </button>
            <button className="rounded-md border border-[hsl(var(--border))] px-4 py-2 text-sm font-medium hover:bg-[hsl(var(--accent))] hover:text-[hsl(var(--accent-foreground))] transition-colors">
              Outline
            </button>
            <button className="rounded-md px-4 py-2 text-sm font-medium hover:bg-[hsl(var(--accent))] hover:text-[hsl(var(--accent-foreground))] transition-colors">
              Ghost
            </button>
            <button className="rounded-md bg-[hsl(var(--destructive))] text-[hsl(var(--destructive-foreground))] px-4 py-2 text-sm font-medium hover:opacity-90 transition-opacity">
              Cancelar OS
            </button>
          </div>
        </section>

        {/* STATUS PILLS — icon + text, never color-only */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Status pills · Ordem de Serviço</h2>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Sempre ícone + texto. Cor sozinha não comunica (a11y · WCAG).
          </p>
          <div className="flex flex-wrap gap-3">
            <StatusPill icon={Clock} label="Aberto" tone="info" />
            <StatusPill icon={PlayCircle} label="Em andamento" tone="warning" />
            <StatusPill icon={CheckCircle2} label="Concluída" tone="success" />
            <StatusPill icon={XCircle} label="Cancelada" tone="destructive" />
          </div>
        </section>

        {/* KPI CARDS */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">KPI cards</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard icon={Wrench} label="OS abertas" value="24" delta="+3" deltaTone="warning" />
            <KpiCard icon={CheckCircle2} label="Concluídas hoje" value="18" delta="+12%" deltaTone="success" />
            <KpiCard icon={Users} label="Clientes ativos" value="1.247" delta="+8" deltaTone="success" />
            <KpiCard icon={MessageSquare} label="Conversas SLA" value="92,4%" delta="-1,2%" deltaTone="destructive" />
          </div>
        </section>

        {/* TABLE */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Tabela · tabular nums + row hover</h2>
          <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] text-xs uppercase tracking-wider">
                <tr>
                  <th className="text-left px-4 py-2 font-semibold">OS</th>
                  <th className="text-left px-4 py-2 font-semibold">Cliente</th>
                  <th className="text-left px-4 py-2 font-semibold">Técnico</th>
                  <th className="text-left px-4 py-2 font-semibold">Status</th>
                  <th className="text-right px-4 py-2 font-semibold" style={{ fontVariantNumeric: 'tabular-nums' }}>Valor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[hsl(var(--border))]">
                {[
                  { id: '1247', cliente: 'Maria Silva', tecnico: 'João S.', status: 'andamento', valor: 'R$ 180,00' },
                  { id: '1246', cliente: 'Carlos Souza', tecnico: 'Ana P.', status: 'concluida', valor: 'R$ 240,00' },
                  { id: '1245', cliente: 'ACME Telecom', tecnico: '—', status: 'aberto', valor: 'R$ 0,00' },
                  { id: '1244', cliente: 'João Pereira', tecnico: 'Pedro L.', status: 'cancelada', valor: 'R$ 0,00' },
                ].map((row) => (
                  <tr key={row.id} className="hover:bg-[hsl(var(--accent))] hover:text-[hsl(var(--accent-foreground))] transition-colors">
                    <td className="px-4 py-3 font-mono text-xs" style={{ fontVariantNumeric: 'tabular-nums' }}>#{row.id}</td>
                    <td className="px-4 py-3">{row.cliente}</td>
                    <td className="px-4 py-3 text-[hsl(var(--muted-foreground))]">{row.tecnico}</td>
                    <td className="px-4 py-3">
                      {row.status === 'aberto' && <StatusPill icon={Clock} label="Aberto" tone="info" size="sm" />}
                      {row.status === 'andamento' && <StatusPill icon={PlayCircle} label="Em andamento" tone="warning" size="sm" />}
                      {row.status === 'concluida' && <StatusPill icon={CheckCircle2} label="Concluída" tone="success" size="sm" />}
                      {row.status === 'cancelada' && <StatusPill icon={XCircle} label="Cancelada" tone="destructive" size="sm" />}
                    </td>
                    <td className="px-4 py-3 text-right" style={{ fontVariantNumeric: 'tabular-nums' }}>{row.valor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <footer className="pt-8 border-t border-[hsl(var(--border))] flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
          <TrendingUp className="h-3.5 w-3.5" />
          Aprovado? Próximo passo é promover esses tokens para <code className="px-1 rounded bg-[hsl(var(--muted))]">app/globals.css</code>.
        </footer>
      </div>
    </div>
  )
}

type Tone = 'success' | 'warning' | 'info' | 'destructive' | 'muted'

function toneStyles(tone: Tone): { bg: string; fg: string; ring: string } {
  switch (tone) {
    case 'success':
      return { bg: 'hsl(var(--success) / 0.12)', fg: 'hsl(var(--success))', ring: 'hsl(var(--success) / 0.3)' }
    case 'warning':
      return { bg: 'hsl(var(--warning) / 0.15)', fg: 'hsl(var(--warning))', ring: 'hsl(var(--warning) / 0.3)' }
    case 'info':
      return { bg: 'hsl(var(--info) / 0.12)', fg: 'hsl(var(--info))', ring: 'hsl(var(--info) / 0.3)' }
    case 'destructive':
      return { bg: 'hsl(var(--destructive) / 0.12)', fg: 'hsl(var(--destructive))', ring: 'hsl(var(--destructive) / 0.3)' }
    case 'muted':
      return { bg: 'hsl(var(--muted))', fg: 'hsl(var(--muted-foreground))', ring: 'hsl(var(--border))' }
  }
}

function StatusPill({
  icon: Icon,
  label,
  tone,
  size = 'md',
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  tone: Tone
  size?: 'sm' | 'md'
}) {
  const s = toneStyles(tone)
  const padding = size === 'sm' ? 'px-2 py-0.5 text-xs gap-1' : 'px-2.5 py-1 text-sm gap-1.5'
  const iconSize = size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5'
  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ring-1 ring-inset ${padding}`}
      style={{ background: s.bg, color: s.fg, ['--tw-ring-color' as string]: s.ring }}
    >
      <Icon className={iconSize} />
      {label}
    </span>
  )
}

function KpiCard({
  icon: Icon,
  label,
  value,
  delta,
  deltaTone,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  delta: string
  deltaTone: Tone
}) {
  const s = toneStyles(deltaTone)
  return (
    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider text-[hsl(var(--muted-foreground))]">{label}</span>
        <Icon className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
      </div>
      <div className="mt-3 text-2xl font-semibold" style={{ fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </div>
      <div className="mt-1 text-xs font-medium" style={{ color: s.fg, fontVariantNumeric: 'tabular-nums' }}>
        {delta} vs ontem
      </div>
    </div>
  )
}
