'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  MessageSquare,
  ClipboardList,
  Users,
  UserPlus,
  Wrench,
  Settings,
  CalendarClock,
  BarChart3,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavItem {
  href: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  roles?: ReadonlyArray<'admin' | 'atendente'>
}

const ITEMS: ReadonlyArray<NavItem> = [
  { href: '/metricas', label: 'Métricas', icon: BarChart3, roles: ['admin'] },
  { href: '/conversas', label: 'Conversas', icon: MessageSquare, roles: ['admin', 'atendente'] },
  { href: '/os', label: 'Ordens de serviço', icon: ClipboardList, roles: ['admin', 'atendente'] },
  { href: '/leads', label: 'Leads', icon: UserPlus, roles: ['admin', 'atendente'] },
  { href: '/clientes', label: 'Clientes', icon: Users, roles: ['admin', 'atendente'] },
  { href: '/tecnicos', label: 'Técnicos', icon: Wrench, roles: ['admin'] },
  { href: '/manutencoes', label: 'Manutenções', icon: CalendarClock, roles: ['admin'] },
  { href: '/config', label: 'Configurações', icon: Settings, roles: ['admin'] },
]

export function NavSidebar({ role }: { role: 'admin' | 'atendente' | 'tecnico' }) {
  const pathname = usePathname()
  const items = ITEMS.filter((it) => !it.roles || (role !== 'tecnico' && it.roles.includes(role)))

  return (
    <aside className="flex h-screen w-60 flex-col border-r bg-card">
      <div className="flex h-14 items-center border-b px-6">
        <Link href="/metricas" className="font-semibold">
          Ondeline
        </Link>
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {items.map((it) => {
          const Icon = it.icon
          const active = pathname === it.href || pathname.startsWith(it.href + '/')
          return (
            <Link
              key={it.href}
              href={it.href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                active
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground',
              )}
            >
              <Icon className="h-4 w-4" />
              {it.label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
