'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronRight, Home } from 'lucide-react'

const LABELS: Record<string, string> = {
  metricas: 'Métricas',
  conversas: 'Conversas',
  os: 'Ordens de serviço',
  leads: 'Leads',
  indicacoes: 'Indicações',
  clientes: 'Clientes',
  'clientes-campo': 'Clientes em campo',
  tecnicos: 'Técnicos',
  ranking: 'Ranking',
  produtividade: 'Comissão',
  manutencoes: 'Manutenções',
  planos: 'Planos',
  estoque: 'Estoque',
  canais: 'Canais WhatsApp',
  config: 'Configurações',
}

function labelize(seg: string): string {
  if (LABELS[seg]) return LABELS[seg]
  // ID numérico/UUID — chamar de "Detalhe"
  if (/^[0-9a-f-]{8,}$/i.test(seg) || /^\d+$/.test(seg)) return 'Detalhe'
  return seg.charAt(0).toUpperCase() + seg.slice(1)
}

export function Breadcrumb() {
  const pathname = usePathname()
  const segments = pathname.split('/').filter(Boolean)

  if (segments.length === 0) return null

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm text-muted-foreground min-w-0">
      <Link
        href="/metricas"
        aria-label="Início"
        className="flex items-center hover:text-foreground transition-colors shrink-0"
      >
        <Home className="h-3.5 w-3.5" />
      </Link>
      {segments.map((seg, idx) => {
        const href = '/' + segments.slice(0, idx + 1).join('/')
        const isLast = idx === segments.length - 1
        return (
          <span key={href} className="flex items-center gap-1.5 min-w-0">
            <ChevronRight className="h-3.5 w-3.5 shrink-0 opacity-50" />
            {isLast ? (
              <span className="text-foreground font-medium truncate">{labelize(seg)}</span>
            ) : (
              <Link href={href} className="hover:text-foreground transition-colors truncate">
                {labelize(seg)}
              </Link>
            )}
          </span>
        )
      })}
    </nav>
  )
}
