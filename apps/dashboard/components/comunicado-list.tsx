'use client'
import Link from 'next/link'
import { Megaphone, Plus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/ui/empty-state'
import { useCampanhas } from '@/lib/api/queries'

const STATUS_VARIANT: Record<string, string> = {
  rascunho: 'outline',
  enviando: 'default',
  concluida: 'secondary',
  cancelada: 'outline',
  erro: 'destructive',
}

export function ComunicadoList() {
  const { data, isLoading, error } = useCampanhas()

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Link
          href="/comunicados/nova"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" /> Nova campanha
        </Link>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {data && data.length === 0 && (
        <EmptyState
          icon={Megaphone}
          title="Nenhuma campanha ainda"
          description="Crie um comunicado para disparar em massa para os clientes."
        />
      )}

      {data && data.length > 0 && (
        <div className="rounded-md border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Título</th>
                <th className="px-4 py-2.5 font-semibold">Template</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
                <th className="px-4 py-2.5 font-semibold">Enviadas</th>
                <th className="px-4 py-2.5 font-semibold">Falhas</th>
              </tr>
            </thead>
            <tbody>
              {data.map((c) => (
                <tr key={c.id} className="border-b last:border-b-0 transition-colors hover:bg-accent/40">
                  <td className="px-4 py-3">
                    <Link href={`/comunicados/${c.id}`} className="font-medium hover:underline">
                      {c.titulo}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground font-mono text-xs">{c.template_name}</td>
                  <td className="px-4 py-3">
                    <Badge variant={(STATUS_VARIANT[c.status] ?? 'outline') as never}>{c.status}</Badge>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {c.enviadas}/{c.total_destinatarios}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{c.falhas}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
