'use client'
import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
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
  Sparkles,
  ChevronRight,
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
      { href: '/metricas', label: 'Métricas', icon: BarChart3, roles: ['admin'] },
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

export function NavSidebar({ role }: { role: Role }) {
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
              {section.items.map((entry) => {
                if (isGroup(entry)) {
                  const Icon = entry.icon
                  const isOpen = !!expanded[entry.id]
                  const childActive = entry.children.some((c) =>
                    isItemActive(c.href, c.exact, pathname),
                  )
                  // Badge no pai (so quando fechado): se algum filho tem badge ativo,
                  // mostra um pontinho no icone do pai pra nao perder o sinal.
                  const groupBadge =
                    !isOpen && entry.children.some((c) => badgePorHref[c.href])

                  return (
                    <div key={entry.id}>
                      <button
                        type="button"
                        onClick={() => toggleGroup(entry.id)}
                        aria-expanded={isOpen}
                        aria-controls={`navgroup-${entry.id}`}
                        className={cn(
                          'group relative flex w-full items-center gap-3 rounded-md px-3 py-1.5 text-sm transition-colors',
                          childActive
                            ? 'text-foreground font-medium'
                            : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground',
                        )}
                      >
                        <span className="relative shrink-0">
                          <Icon className={cn('h-4 w-4', childActive && 'text-primary')} />
                          {groupBadge && (
                            <span
                              aria-label="Tem item novo"
                              className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-red-500 ring-2 ring-card"
                            />
                          )}
                        </span>
                        <span className="flex-1 truncate text-left">{entry.label}</span>
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
                          className="ml-4 mt-0.5 space-y-0.5 border-l border-border/50 pl-2"
                        >
                          {entry.children.map((it) => {
                            const ChildIcon = it.icon
                            const active = isItemActive(it.href, it.exact, pathname)
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
                                  <ChildIcon
                                    className={cn('h-4 w-4', active && 'text-primary')}
                                  />
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
                      )}
                    </div>
                  )
                }

                // Item simples (não grupo).
                const Icon = entry.icon
                const active = isItemActive(entry.href, entry.exact, pathname)
                return (
                  <Link
                    key={entry.href}
                    href={entry.href}
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
                      {badgePorHref[entry.href] && (
                        <span
                          aria-label="Tem item novo"
                          className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-red-500 ring-2 ring-card"
                        />
                      )}
                    </span>
                    <span className="truncate">{entry.label}</span>
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
