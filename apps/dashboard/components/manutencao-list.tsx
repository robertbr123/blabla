'use client'
import Link from 'next/link'
import { useState } from 'react'
import { CalendarClock, Plus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { Select } from '@/components/ui/select'
import { useManutencoes } from '@/lib/api/queries'

export function ManutencaoList() {
  const [filter, setFilter] = useState('')
  const { data, isLoading, error } = useManutencoes({
    ativas: filter === 'ativas' ? true : undefined,
  })
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Select value={filter} onChange={(e) => setFilter(e.target.value)} className="max-w-[200px]">
          <option value="">Todas</option>
          <option value="ativas">Ativas agora</option>
        </Select>
        <div className="ml-auto">
          <Link href="/manutencoes/nova">
            <Button>
              <Plus className="h-4 w-4" /> Nova manutenção
            </Button>
          </Link>
        </div>
      </div>
      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && <p className="text-sm text-destructive">{error instanceof Error ? error.message : 'Erro'}</p>}
      {data && data.items.length === 0 && (
        <EmptyState
          icon={CalendarClock}
          title="Nenhuma manutenção agendada"
          description={
            filter
              ? 'Mude o filtro para ver manutenções passadas ou todas.'
              : 'Agende manutenções programadas para notificar clientes antes da interrupção.'
          }
        />
      )}
      {data && data.items.length > 0 && (
        <div className="rounded-md border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Título</th>
                <th className="px-4 py-2.5 font-semibold">Início</th>
                <th className="px-4 py-2.5 font-semibold">Fim</th>
                <th className="px-4 py-2.5 font-semibold">Cidades</th>
                <th className="px-4 py-2.5 font-semibold">Notifica?</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((m) => (
                <tr key={m.id} className="border-b last:border-b-0 transition-colors hover:bg-accent/40">
                  <td className="px-4 py-3">
                    <Link href={`/manutencoes/${m.id}`} className="font-medium hover:underline">
                      {m.titulo}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {new Date(m.inicio_at).toLocaleString('pt-BR')}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {new Date(m.fim_at).toLocaleString('pt-BR')}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {m.cidades?.join(', ') ?? 'todas'}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={m.notificar ? 'default' : 'outline'}>
                      {m.notificar ? 'Sim' : 'Não'}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
