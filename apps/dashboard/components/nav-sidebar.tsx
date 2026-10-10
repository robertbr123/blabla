'use client'
import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import {
  Activity,
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
  Sparkles,
  ChevronRight,
} from 'lucide-react'
import { useTemChamadoAberto, useTemConversaAguardando } from '@/lib/api/queries'
import { cn } from '@/lib/utils'
import { StatusDot } from './noc/primitives'
import { useSystemHealth } from './noc/system-status'

type Role = 'admin' | 'atendente' | 'tecnico'

interface NavItem {
  href: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  roles?: ReadonlyArray<'admin' | 'atendente'>
  exact?: boolean
}

interface NavGroup {
  /** Identificador estável pro estado de expansão (localStorage). */
  id: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  children: ReadonlyArray<NavItem>
}

type NavEntry = NavItem | NavGroup

function isGroup(e: NavEntry): e is NavGroup {
  return 'children' in e
}

interface NavSection {
  label: string
  items: ReadonlyArray<NavEntry>
}

const SECTIONS: ReadonlyArray<NavSection> = [
  {
    label: 'Monitoramento',
    items: [
      { href: '/noc', label: 'Painel NOC', icon: Activity, roles: ['admin', 'atendente'] },
      { href: '/metricas', label: 'Métricas', icon: BarChart3, roles: ['admin'] },
    ],
  },
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
      {
        // Grupo colapsável: tudo que pertence ao app cliente vai aqui dentro.
        // Abrir/fechar persiste em localStorage; auto-abre quando a rota ativa
        // for de algum filho. Roles filtram filho a filho — se o role nao ve
        // nenhum filho, o grupo inteiro some.
        id: 'app-cliente',
        label: 'App Cliente',
        icon: Smartphone,
        children: [
          { href: '/cliente-app-os', label: 'Chamados', icon: Smartphone, roles: ['admin', 'atendente'] },
          { href: '/promocoes', label: 'Promoções', icon: Megaphone, roles: ['admin'] },
          { href: '/cliente-app-contatos', label: 'Fale conosco', icon: PhoneCall, roles: ['admin'] },
          { href: '/cliente-app-fidelidade', label: 'Fidelidade', icon: Award, roles: ['admin'] },
          { href: '/cliente-app-cards-dia', label: 'Card do dia', icon: Sparkles, roles: ['admin'] },
        ],
      },
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
      { href: '/comunicados', label: 'Comunicados', icon: Megaphone, roles: ['admin'] },
      { href: '/canais', label: 'Canais WhatsApp', icon: Radio, roles: ['admin'] },
      { href: '/config', label: 'Configurações', icon: Settings, roles: ['admin'] },
    ],
  },
]

function itemVisibleForRole(it: NavItem, role: Role): boolean {
  return !it.roles || (role !== 'tecnico' && it.roles.includes(role))
}

function isItemActive(href: string, exact: boolean | undefined, pathname: string): boolean {
  return pathname === href || (!exact && pathname.startsWith(href + '/'))
}

const EXPANDED_STORAGE_KEY = 'nav.expanded'

function NavLink({
  item,
  pathname,
  badge,
}: {
  item: NavItem
  pathname: string
  badge: boolean
}) {
  const Icon = item.icon
  const active = isItemActive(item.href, item.exact, pathname)
  return (
    <Link
      href={item.href}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'group relative flex h-8 items-center gap-2.5 rounded-md px-2.5 text-[13px] transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        active
          ? 'bg-accent font-medium text-accent-foreground'
          : 'text-muted-foreground hover:bg-elevated hover:text-foreground',
      )}
    >
      {active && (
        <span
          aria-hidden
          className="absolute -left-3 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-r-full bg-primary"
        />
      )}
      <Icon className={cn('h-4 w-4 shrink-0', active && 'text-primary')} />
      <span className="flex-1 truncate">{item.label}</span>
      {badge && (
        <>
          <StatusDot tone="destructive" pulse />
          <span className="sr-only">Tem item novo</span>
        </>
      )}
    </Link>
  )
}

function SidebarStatus() {
  const { overall, summary, checks } = useSystemHealth()
  return (
    <div className="border-t px-4 py-3" title={checks.map((c) => `${c.label}: ${c.state}`).join(' · ')}>
      <div className="flex items-center gap-2 text-xs">
        <StatusDot tone={overall} pulse={overall !== 'muted'} />
        <span className="truncate text-muted-foreground">{summary}</span>
      </div>
    </div>
  )
}

export function NavSidebar({
  role,
  className,
}: {
  role: Role
  /** Layout passa `hidden lg:flex`; a gaveta mobile passa `flex`. */
  className?: string
}) {
  const pathname = usePathname()
  const { data: temConversaAguardando } = useTemConversaAguardando()
  const { data: temChamadoAberto } = useTemChamadoAberto()

  const badgePorHref: Record<string, boolean> = {
    '/conversas': !!temConversaAguardando,
    '/cliente-app-os': !!temChamadoAberto,
  }

  // Estado de expansão por grupo. SSR-safe: começa vazio e carrega do
  // localStorage apos hidratar, evitando mismatch de hidratacao do Next.
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    try {
      const raw = localStorage.getItem(EXPANDED_STORAGE_KEY)
      if (raw) setExpanded(JSON.parse(raw))
    } catch {
      // localStorage indisponivel ou JSON invalido — segue com {}
    }
    setHydrated(true)
  }, [])

  // Auto-abre o grupo quando a rota ativa for de algum filho (evita
  // sensacao de "item ativo sumiu" quando o grupo esta fechado).
  useEffect(() => {
    if (!hydrated) return
    setExpanded((prev) => {
      const next = { ...prev }
      let changed = false
      for (const section of SECTIONS) {
        for (const entry of section.items) {
          if (!isGroup(entry)) continue
          const hasActiveChild = entry.children.some((c) =>
            isItemActive(c.href, c.exact, pathname),
          )
          if (hasActiveChild && !next[entry.id]) {
            next[entry.id] = true
            changed = true
          }
        }
      }
      return changed ? next : prev
    })
  }, [pathname, hydrated])

  // Persiste a expansao.
  useEffect(() => {
    if (!hydrated) return
    try {
      localStorage.setItem(EXPANDED_STORAGE_KEY, JSON.stringify(expanded))
    } catch {
      // ignora (quota / private mode)
    }
  }, [expanded, hydrated])

  function toggleGroup(id: string) {
    setExpanded((p) => ({ ...p, [id]: !p[id] }))
  }

  // Filtra sections + entries por role. Grupos sem filhos visiveis somem.
  const visibleSections = SECTIONS.map((s) => {
    const items: NavEntry[] = []
    for (const entry of s.items) {
      if (isGroup(entry)) {
        const visibleChildren = entry.children.filter((c) => itemVisibleForRole(c, role))
        if (visibleChildren.length > 0) {
          items.push({ ...entry, children: visibleChildren })
        }
      } else if (itemVisibleForRole(entry, role)) {
        items.push(entry)
      }
    }
    return { ...s, items }
  }).filter((s) => s.items.length > 0)

  return (
    <aside className={cn('sticky top-0 h-screen w-60 shrink-0 flex-col border-r bg-sidebar', className ?? 'flex')}>
      <div className="flex h-12 items-center border-b px-4">
        <Link href="/noc" className="flex items-center" aria-label="BlaBla — Painel NOC">
          <Image
            src="/branding/logo_horizontal_light.png"
            alt="BlaBla"
            width={120}
            height={32}
            priority
            className="h-6 w-auto dark:hidden"
          />
          <Image
            src="/branding/logo_horizontal_dark.png"
            alt="BlaBla"
            width={120}
            height={32}
            priority
            className="hidden h-6 w-auto dark:block"
          />
        </Link>
      </div>

      <nav aria-label="Principal" className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
        {visibleSections.map((section) => (
          <div key={section.label}>
            <div className="eyebrow mb-1.5 px-2.5">{section.label}</div>
            <div className="space-y-0.5">
              {section.items.map((entry) => {
                if (!isGroup(entry)) {
                  return (
                    <NavLink
                      key={entry.href}
                      item={entry}
                      pathname={pathname}
                      badge={!!badgePorHref[entry.href]}
                    />
                  )
                }
                const Icon = entry.icon
                const isOpen = !!expanded[entry.id]
                const childActive = entry.children.some((c) =>
                  isItemActive(c.href, c.exact, pathname),
                )
                // Badge no pai (so quando fechado): se algum filho tem badge ativo,
                // mostra o ponto no pai pra nao perder o sinal.
                const groupBadge = !isOpen && entry.children.some((c) => badgePorHref[c.href])
                return (
                  <div key={entry.id}>
                    <button
                      type="button"
                      onClick={() => toggleGroup(entry.id)}
                      aria-expanded={isOpen}
                      aria-controls={`navgroup-${entry.id}`}
                      className={cn(
                        'flex h-8 w-full items-center gap-2.5 rounded-md px-2.5 text-[13px] transition-colors',
                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                        childActive
                          ? 'font-medium text-foreground'
                          : 'text-muted-foreground hover:bg-elevated hover:text-foreground',
                      )}
                    >
                      <Icon className={cn('h-4 w-4 shrink-0', childActive && 'text-primary')} />
                      <span className="flex-1 truncate text-left">{entry.label}</span>
                      {groupBadge && (
                        <>
                          <StatusDot tone="destructive" pulse />
                          <span className="sr-only">Tem item novo</span>
                        </>
                      )}
                      <ChevronRight
                        aria-hidden
                        className={cn(
                          'h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform duration-150',
                          isOpen && 'rotate-90',
                        )}
                      />
                    </button>
                    {isOpen && (
                      <div
                        id={`navgroup-${entry.id}`}
                        className="ml-[18px] mt-0.5 space-y-0.5 border-l pl-3"
                      >
                        {entry.children.map((it) => (
                          <NavLink
                            key={it.href}
                            item={it}
                            pathname={pathname}
                            badge={!!badgePorHref[it.href]}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      <SidebarStatus />
    </aside>
  )
}
