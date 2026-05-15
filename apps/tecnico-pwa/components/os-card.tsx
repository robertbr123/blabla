'use client'
import Link from 'next/link'
import { ChevronRight, MapPin, User } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { OsListItem } from '@/lib/api/types'

const STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  pendente: 'destructive',
  em_andamento: 'default',
  concluida: 'secondary',
  cancelada: 'outline',
}

export function OsCard({ os }: { os: OsListItem }) {
  return (
    <Link
      href={`/os/${os.id}`}
      className="block rounded-lg border bg-card p-4 active:bg-muted/50"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-semibold">{os.codigo}</span>
            <Badge variant={STATUS_VARIANTS[os.status] ?? 'outline'} className="text-[10px]">
              {os.status}
            </Badge>
          </div>
          {os.nome_cliente && (
            <div className="mt-1 flex items-center gap-1 text-xs font-medium text-foreground">
              <User className="h-3 w-3 shrink-0" />
              {os.nome_cliente}
            </div>
          )}
          <p className="mt-1 text-sm line-clamp-2 text-muted-foreground">{os.problema}</p>
          <div className="mt-1 flex items-start gap-1 text-xs text-muted-foreground">
            <MapPin className="h-3 w-3 shrink-0 mt-0.5" />
            <span className="line-clamp-1">{os.endereco}</span>
          </div>
        </div>
        <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground" />
      </div>
    </Link>
  )
}
