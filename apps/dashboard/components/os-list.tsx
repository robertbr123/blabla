'use client'
import Link from 'next/link'
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { useOsList } from '@/lib/api/queries'

const STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  pendente: 'destructive',
  em_andamento: 'default',
  concluida: 'secondary',
  cancelada: 'outline',
}

export function OsList() {
  const [status, setStatus] = useState('')
  const { data, isLoading, error } = useOsList({ status: status || undefined })

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="max-w-[200px]"
        >
          <option value="">Todos os status</option>
          <option value="pendente">Pendente</option>
          <option value="em_andamento">Em andamento</option>
          <option value="concluida">Concluída</option>
          <option value="cancelada">Cancelada</option>
        </Select>
        <div className="ml-auto">
          <Link href="/os/nova">
            <Button>
              <Plus className="h-4 w-4" /> Nova OS
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
                <th className="px-4 py-3">Código</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Problema</th>
                <th className="px-4 py-3">Endereço</th>
                <th className="px-4 py-3">Criada</th>
              </tr>
            </thead>
            <tbody>
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-muted-foreground">
                    Nenhuma OS
                  </td>
                </tr>
              )}
              {data.items.map((o) => (
                <tr key={o.id} className="border-b last:border-b-0 hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <Link href={`/os/${o.id}`} className="font-medium hover:underline">
                      {o.codigo}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={STATUS_VARIANTS[o.status] ?? 'outline'}>
                      {o.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 max-w-xs truncate">{o.problema}</td>
                  <td className="px-4 py-3 max-w-xs truncate text-muted-foreground">
                    {o.endereco}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {new Date(o.criada_em).toLocaleString('pt-BR')}
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
