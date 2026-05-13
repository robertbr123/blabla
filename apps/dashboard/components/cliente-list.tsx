'use client'
import Link from 'next/link'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
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

      {data && (
        <div className="rounded-md border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b text-left text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-3">WhatsApp</th>
                <th className="px-4 py-3">Plano</th>
                <th className="px-4 py-3">Cidade</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Provider</th>
              </tr>
            </thead>
            <tbody>
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-muted-foreground">
                    Nenhum cliente
                  </td>
                </tr>
              )}
              {data.items.map((c) => (
                <tr key={c.id} className="border-b last:border-b-0 hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <Link href={`/clientes/${c.id}`} className="font-medium hover:underline">
                      {c.whatsapp}
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
