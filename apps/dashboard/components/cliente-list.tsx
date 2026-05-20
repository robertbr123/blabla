'use client'
import Link from 'next/link'
import { useState } from 'react'
import { Users } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/ui/empty-state'
import { Input } from '@/components/ui/input'
import { useClientes } from '@/lib/api/queries'

export function ClienteList() {
  const [q, setQ] = useState('')
  const [cidade, setCidade] = useState('')
  const { data, isLoading, error } = useClientes({
    q: q || undefined,
    cidade: cidade || undefined,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Input
          placeholder="Buscar WhatsApp…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs"
        />
        <Input
          placeholder="Cidade…"
          value={cidade}
          onChange={(e) => setCidade(e.target.value)}
          className="max-w-[200px]"
        />
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {data && data.items.length === 0 && (
        <EmptyState
          icon={Users}
          title="Nenhum cliente encontrado"
          description={
            q || cidade
              ? 'Ajuste a busca ou o filtro de cidade.'
              : 'Importe a base de clientes ou cadastre individualmente.'
          }
        />
      )}

      {data && data.items.length > 0 && (
        <div className="rounded-md border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Cliente</th>
                <th className="px-4 py-2.5 font-semibold">Plano</th>
                <th className="px-4 py-2.5 font-semibold">Cidade</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
                <th className="px-4 py-2.5 font-semibold">Provider</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((c) => (
                <tr key={c.id} className="border-b last:border-b-0 transition-colors hover:bg-accent/40">
                  <td className="px-4 py-3">
                    <Link href={`/clientes/${c.id}`} className="block hover:underline">
                      <span className="font-medium">{c.nome ?? '—'}</span>
                      <span className="block text-xs text-muted-foreground font-mono">
                        {c.whatsapp}
                      </span>
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{c.plano ?? '—'}</td>
                  <td className="px-4 py-3 text-muted-foreground">{c.cidade ?? '—'}</td>
                  <td className="px-4 py-3">
                    {c.status ? <Badge variant="outline">{c.status}</Badge> : '—'}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{c.sgp_provider ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
