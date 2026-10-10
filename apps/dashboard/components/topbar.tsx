'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Menu } from 'lucide-react'
import { useMetricas } from '@/lib/api/queries'
import { Button } from '@/components/ui/button'
import { NavSidebar } from './nav-sidebar'
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

/** Abaixo de `lg` a sidebar some do layout e abre como gaveta por aqui. */
function MobileNav({ role }: { role: string }) {
  const [open, setOpen] = useState(false)
  const pathname = usePathname()
  // Navegou -> fecha.
  useEffect(() => setOpen(false), [pathname])
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])
  if (role !== 'admin' && role !== 'atendente') return null
  return (
    <div className="lg:hidden">
      <Button
        variant="ghost"
        size="icon"
        aria-label="Abrir menu"
        aria-expanded={open}
        onClick={() => setOpen(true)}
      >
        <Menu />
      </Button>
      {open && (
        <div className="fixed inset-0 z-50 flex" role="dialog" aria-modal="true" aria-label="Menu">
          <NavSidebar role={role} className="flex" />
          <button
            type="button"
            aria-label="Fechar menu"
            className="flex-1 bg-background/70 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
        </div>
      )}
    </div>
  )
}

export function Topbar({ email, name, role }: TopbarProps) {
  return (
    <header className="sticky top-0 z-30 flex h-12 shrink-0 items-center gap-3 border-b bg-background/85 px-3 backdrop-blur sm:px-5">
      <MobileNav role={role} />
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
