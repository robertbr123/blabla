'use client'
import Link from 'next/link'
import { useMetricas } from '@/lib/api/queries'
import { Breadcrumb } from './breadcrumb'
import { StatusChip } from './noc/primitives'
import { LiveClock, useSystemHealth } from './noc/system-status'
import { ThemeToggle } from './theme-toggle'
import { UserMenu } from './user-menu'

interface TopbarProps {
  email: string
  name: string
  role: string
}

/** Sinais sempre visiveis: fila aguardando humano + conexao do WhatsApp. */
function LiveSignals() {
  const { data: m } = useMetricas()
  const { checks, apiDown } = useSystemHealth()
  const wa = checks.find((c) => c.key === 'evolution')
  const fila = m?.conversas_aguardando ?? null
  return (
    <div className="hidden items-center gap-2 md:flex">
      {fila !== null && (
        <Link href="/conversas" className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <StatusChip
            tone={fila > 0 ? 'warning' : 'success'}
            pulse={fila > 0}
            label="Fila"
            value={<span className="num">{fila}</span>}
            title={fila > 0 ? `${fila} conversa(s) aguardando atendente` : 'Nenhuma conversa aguardando'}
          />
        </Link>
      )}
      {apiDown ? (
        <StatusChip tone="destructive" pulse label="API" value="Inacessível" />
      ) : (
        wa && <StatusChip tone={wa.tone} pulse={wa.tone !== 'success'} label={wa.label} value={wa.state} />
      )}
    </div>
  )
}

export function Topbar({ email, name, role }: TopbarProps) {
  return (
    <header className="sticky top-0 z-30 flex h-12 shrink-0 items-center gap-4 border-b bg-background/85 px-5 backdrop-blur">
      <div className="min-w-0 flex-1">
        <Breadcrumb />
      </div>
      <LiveSignals />
      <LiveClock className="hidden items-baseline sm:flex" />
      <div className="flex items-center gap-1 border-l pl-3">
        <ThemeToggle />
        <UserMenu email={email} name={name} role={role} />
      </div>
    </header>
  )
}
