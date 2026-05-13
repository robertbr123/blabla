'use client'
import Link from 'next/link'
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { useLeads } from '@/lib/api/queries'

const STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  novo: 'default',
  contato: 'secondary',
  convertido: 'secondary',
  perdido: 'destructive',
}

export function LeadList() {
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const { data, isLoading, error } = useLeads({ status: status || undefined, q: q || undefined })

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Input
          placeholder="Buscar nome…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs"
        />
        <Select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="max-w-[200px]"
        >
          <option value="">Todos</option>
          <option value="novo">Novo</option>
          <option value="contato">Em contato</option>
          <option value="convertido">Convertido</option>
          <option value="perdido">Perdido</option>
        </Select>
        <div className="ml-auto">
          <Link href="/leads/novo">
            <Button>
              <Plus className="h-4 w-4" /> Novo
            </Button>
          </Link>
        </div>
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
                <th className="px-4 py-3">Nome</th>
                <th className="px-4 py-3">WhatsApp</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Interesse</th>
                <th className="px-4 py-3">Criado</th>
              </tr>
            </thead>
            <tbody>
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-muted-foreground">
                    Nenhum lead
                  </td>
                </tr>
              )}
              {data.items.map((l) => (
                <tr key={l.id} className="border-b last:border-b-0 hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <Link href={`/leads/${l.id}`} className="font-medium hover:underline">
                      {l.nome}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{l.whatsapp}</td>
                  <td className="px-4 py-3">
                    <Badge variant={STATUS_VARIANTS[l.status] ?? 'outline'}>{l.status}</Badge>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{l.interesse ?? '—'}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {new Date(l.created_at).toLocaleDateString('pt-BR')}
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
