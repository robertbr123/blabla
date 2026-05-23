'use client'
import Link from 'next/link'
import Image from 'next/image'
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
  Trophy,
  Package,
  Radio,
  Boxes,
  Gift,
  Smartphone,
  Megaphone,
  PhoneCall,
  Award,
} from 'lucide-react'
import { useTemChamadoAberto, useTemConversaAguardando } from '@/lib/api/queries'
import { cn } from '@/lib/utils'

type Role = 'admin' | 'atendente' | 'tecnico'

interface NavItem {
  href: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  roles?: ReadonlyArray<'admin' | 'atendente'>
  exact?: boolean
}

interface NavSection {
  label: string
  items: ReadonlyArray<NavItem>
}

const SECTIONS: ReadonlyArray<NavSection> = [
  {
    label: 'Atendimento',
    items: [
      { href: '/conversas', label: 'Conversas', icon: MessageSquare, roles: ['admin', 'atendente'] },
      { href: '/leads', label: 'Leads', icon: UserPlus, roles: ['admin', 'atendente'] },
      { href: '/indicacoes', label: 'Indicações', icon: Gift, roles: ['admin', 'atendente'] },
    ],
  },
  {
    label: 'Operação',
    items: [
      { href: '/os', label: 'Ordens de serviço', icon: ClipboardList, roles: ['admin', 'atendente'] },
      { href: '/manutencoes', label: 'Manutenções', icon: CalendarClock, roles: ['admin'] },
      { href: '/clientes-campo', label: 'Clientes (em campo)', icon: Users, roles: ['admin', 'atendente'] },
      { href: '/cliente-app-os', label: 'Chamados app cliente', icon: Smartphone, roles: ['admin', 'atendente'] },
      { href: '/promocoes', label: 'Promoções (app)', icon: Megaphone, roles: ['admin'] },
      { href: '/cliente-app-contatos', label: 'Fale conosco (app)', icon: PhoneCall, roles: ['admin'] },
      { href: '/cliente-app-fidelidade', label: 'Fidelidade (app)', icon: Award, roles: ['admin'] },
      { href: '/tecnicos', label: 'Técnicos', icon: Wrench, roles: ['admin'], exact: true },
      { href: '/tecnicos/ranking', label: 'Ranking', icon: Trophy, roles: ['admin'] },
      { href: '/tecnicos/produtividade', label: 'Comissão', icon: Trophy, roles: ['admin'] },
    ],
  },
  {
    label: 'Cadastros',
    items: [
      { href: '/clientes', label: 'Clientes', icon: Users, roles: ['admin', 'atendente'], exact: true },
      { href: '/planos', label: 'Planos', icon: Package, roles: ['admin'] },
      { href: '/estoque', label: 'Estoque', icon: Boxes, roles: ['admin', 'atendente'] },
    ],
  },
  {
    label: 'Sistema',
    items: [
      { href: '/metricas', label: 'Métricas', icon: BarChart3, roles: ['admin'] },
      { href: '/canais', label: 'Canais WhatsApp', icon: Radio, roles: ['admin'] },
      { href: '/config', label: 'Configurações', icon: Settings, roles: ['admin'] },
    ],
  },
]

export function NavSidebar({ role }: { role: Role }) {
  const pathname = usePathname()
  const { data: temConversaAguardando } = useTemConversaAguardando()
  const { data: temChamadoAberto } = useTemChamadoAberto()

  const badgePorHref: Record<string, boolean> = {
    '/conversas': !!temConversaAguardando,
    '/cliente-app-os': !!temChamadoAberto,
  }

  const visibleSections = SECTIONS.map((s) => ({
    ...s,
    items: s.items.filter((it) => !it.roles || (role !== 'tecnico' && it.roles.includes(role))),
  })).filter((s) => s.items.length > 0)

  return (
    <aside className="flex h-screen w-60 flex-col border-r bg-card">
      <div className="flex h-14 items-center border-b px-5">
        <Link href="/metricas" className="flex items-center" aria-label="BlaBla">
          <Image
            src="/branding/logo_horizontal_light.png"
            alt="BlaBla"
            width={120}
            height={32}
            priority
            className="h-7 w-auto dark:hidden"
          />
          <Image
            src="/branding/logo_horizontal_dark.png"
            alt="BlaBla"
            width={120}
            height={32}
            priority
            className="hidden h-7 w-auto dark:block"
          />
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-5">
        {visibleSections.map((section) => (
          <div key={section.label}>
            <div className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              {section.label}
            </div>
            <div className="space-y-0.5">
              {section.items.map((it) => {
                const Icon = it.icon
                const active = pathname === it.href || (!it.exact && pathname.startsWith(it.href + '/'))
                return (
                  <Link
                    key={it.href}
                    href={it.href}
                    aria-current={active ? 'page' : undefined}
                    className={cn(
                      'group relative flex items-center gap-3 rounded-md px-3 py-1.5 text-sm transition-colors',
                      active
                        ? 'bg-accent text-accent-foreground font-medium'
                        : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground',
                    )}
                  >
                    {active && (
                      <span
                        aria-hidden
                        className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-r-full bg-primary"
                      />
                    )}
                    <span className="relative shrink-0">
                      <Icon className={cn('h-4 w-4', active && 'text-primary')} />
                      {badgePorHref[it.href] && (
                        <span
                          aria-label="Tem item novo"
                          className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-red-500 ring-2 ring-card"
                        />
                      )}
                    </span>
                    <span className="truncate">{it.label}</span>
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  )
}
