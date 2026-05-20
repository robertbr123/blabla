'use client'
import Link from 'next/link'
import { useState } from 'react'
import { Plus, Wrench } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { Select } from '@/components/ui/select'
import { useTecnicos } from '@/lib/api/queries'

export function TecnicoList() {
  const [ativoFilter, setAtivoFilter] = useState<string>('')
  const ativo =
    ativoFilter === 'true' ? true : ativoFilter === 'false' ? false : undefined
  const { data, isLoading, error } = useTecnicos({ ativo })

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Select
          value={ativoFilter}
          onChange={(e) => setAtivoFilter(e.target.value)}
          className="max-w-[200px]"
        >
          <option value="">Todos</option>
          <option value="true">Ativos</option>
          <option value="false">Inativos</option>
        </Select>
        <div className="ml-auto">
          <Link href="/tecnicos/novo">
            <Button>
              <Plus className="h-4 w-4" /> Novo técnico
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

      {data && data.items.length === 0 && (
        <EmptyState
          icon={Wrench}
          title="Nenhum técnico cadastrado"
          description={
            ativoFilter
              ? 'Mude o filtro para ver técnicos inativos ou todos.'
              : 'Cadastre técnicos para atribuí-los a ordens de serviço.'
          }
        />
      )}
      {data && data.items.length > 0 && (
        <div className="rounded-md border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Nome</th>
                <th className="px-4 py-2.5 font-semibold">WhatsApp</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
                <th className="px-4 py-2.5 font-semibold">GPS</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((t) => (
                <tr key={t.id} className="border-b last:border-b-0 transition-colors hover:bg-accent/40">
                  <td className="px-4 py-3">
                    <Link href={`/tecnicos/${t.id}`} className="font-medium hover:underline">
                      {t.nome}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{t.whatsapp ?? '—'}</td>
                  <td className="px-4 py-3">
                    <Badge variant={t.ativo ? 'default' : 'outline'}>
                      {t.ativo ? 'Ativo' : 'Inativo'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {t.gps_lat !== null && t.gps_lng !== null
                      ? `${t.gps_lat.toFixed(4)}, ${t.gps_lng.toFixed(4)}`
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
