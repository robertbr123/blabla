'use client'
import Link from 'next/link'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { useConversas } from '@/lib/api/queries'

const STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  bot: 'secondary',
  aguardando: 'destructive',
  humano: 'default',
  encerrada: 'outline',
}

export function ConversaList() {
  const [status, setStatus] = useState('')
  const [q, setQ] = useState('')
  const { data, isLoading, error } = useConversas({
    status: status || undefined,
    q: q || undefined,
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Input
          placeholder="Buscar por whatsapp…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs"
        />
        <Select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="max-w-[200px]"
        >
          <option value="">Todos os status</option>
          <option value="aguardando">Aguardando</option>
          <option value="humano">Humano</option>
          <option value="bot">Bot</option>
          <option value="encerrada">Encerrada</option>
        </Select>
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
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3">Última msg</th>
              </tr>
            </thead>
            <tbody>
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={4} className="p-6 text-center text-muted-foreground">
                    Nenhuma conversa
                  </td>
                </tr>
              )}
              {data.items.map((c) => (
                <tr key={c.id} className="border-b last:border-b-0 hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <Link href={`/conversas/${c.id}`} className="font-medium hover:underline">
                      {c.whatsapp}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={STATUS_VARIANTS[c.status] ?? 'outline'}>
                      {c.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{c.estado}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {c.last_message_at
                      ? new Date(c.last_message_at).toLocaleString('pt-BR')
                      : '—'}
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
