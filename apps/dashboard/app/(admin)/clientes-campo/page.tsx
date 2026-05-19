'use client'
import { useState } from 'react'
import {
  CloudOff,
  CloudUpload,
  CloudDone,
  Download,
  MapPin,
  Trash2,
  Users,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { DialogMarcarSyncSgp } from '@/components/dialog-marcar-sync-sgp'
import { DialogImportarClientesCsv } from '@/components/dialog-importar-clientes-csv'
import { DialogClienteCampoDetail } from '@/components/dialog-cliente-campo-detail'
import {
  useClientesCampo,
  useDeleteClienteCampo,
} from '@/lib/api/queries'
import type { ClienteCampoListItem } from '@/lib/api/types'
import { cn } from '@/lib/utils'

type FiltroSgp = 'all' | 'synced' | 'pending'

export default function ClientesCampoPage() {
  const [busca, setBusca] = useState('')
  const [filtroSgp, setFiltroSgp] = useState<FiltroSgp>('all')
  const [showSync, setShowSync] = useState<ClienteCampoListItem | null>(null)
  const [showImport, setShowImport] = useState(false)
  const [showDetail, setShowDetail] = useState<string | null>(null)

  const { data, isLoading, error } = useClientesCampo({
    q: busca || undefined,
    sgp_status: filtroSgp === 'all' ? undefined : filtroSgp,
  })
  const deleteCliente = useDeleteClienteCampo()

  const items = data?.items ?? []
  const synced = items.filter((c) => c.sgp_synced_at).length
  const pending = items.filter((c) => !c.sgp_synced_at).length

  async function handleDelete(c: ClienteCampoListItem) {
    if (
      !confirm(
        `Excluir cadastro de "${c.nome}"?\n\n` +
          'A baixa de material no estoque NÃO é revertida — só o cadastro some.',
      )
    )
      return
    try {
      await deleteCliente.mutateAsync(c.id)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Erro ao excluir')
    }
  }

  return (
    <div className="space-y-6">
      {showSync && (
        <DialogMarcarSyncSgp
          cliente={showSync}
          onClose={() => setShowSync(null)}
        />
      )}
      {showImport && (
        <DialogImportarClientesCsv onClose={() => setShowImport(false)} />
      )}
      {showDetail && (
        <DialogClienteCampoDetail
          id={showDetail}
          onClose={() => setShowDetail(null)}
        />
      )}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Clientes em campo</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Cadastros feitos pelos técnicos durante a instalação. Diferente
            de <strong>Clientes</strong> (cache do SGP), aqui está a fonte
            primária do que foi instalado.
          </p>
        </div>
        <Button onClick={() => setShowImport(true)} className="gap-2">
          <Download className="h-4 w-4" />
          Importar CSV (MySQL)
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Kpi
          label="Total"
          value={items.length}
          icon={Users}
          color="text-blue-700"
        />
        <Kpi
          label="Sincronizados c/ SGP"
          value={synced}
          icon={CloudDone}
          color="text-emerald-700"
        />
        <Kpi
          label="Pendentes"
          value={pending}
          icon={CloudOff}
          color="text-amber-700"
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          placeholder="Buscar por endereço, cidade, bairro, serial…"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          className="max-w-sm"
        />
        <div className="flex gap-1">
          <FiltroChip
            label="Todos"
            active={filtroSgp === 'all'}
            onClick={() => setFiltroSgp('all')}
          />
          <FiltroChip
            label="Sincronizado"
            active={filtroSgp === 'synced'}
            color="text-emerald-700 border-emerald-400 bg-emerald-50"
            onClick={() => setFiltroSgp('synced')}
          />
          <FiltroChip
            label="Pendente SGP"
            active={filtroSgp === 'pending'}
            color="text-amber-700 border-amber-400 bg-amber-50"
            onClick={() => setFiltroSgp('pending')}
          />
        </div>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {data && (
        <div className="overflow-x-auto rounded-md border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b text-left text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Cliente</th>
                <th className="px-4 py-3">CPF</th>
                <th className="px-4 py-3">Endereço</th>
                <th className="px-4 py-3">Cidade</th>
                <th className="px-4 py-3">Plano</th>
                <th className="px-4 py-3">Instalador</th>
                <th className="px-4 py-3">SGP</th>
                <th className="px-4 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-6 text-center text-muted-foreground">
                    Nenhum cliente cadastrado{busca || filtroSgp !== 'all' ? ' com esses filtros' : ' ainda'}.
                  </td>
                </tr>
              )}
              {items.map((c) => (
                <tr
                  key={c.id}
                  className="border-b last:border-b-0 hover:bg-muted/50 cursor-pointer"
                  onClick={() => setShowDetail(c.id)}
                >
                  <td className="px-4 py-3 font-medium">{c.nome}</td>
                  <td className="px-4 py-3 font-mono text-xs">{fmtCpf(c.cpf)}</td>
                  <td className="px-4 py-3 text-xs">
                    {c.address}, {c.number}
                    {c.neighborhood ? ` · ${c.neighborhood}` : ''}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      {c.city}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs">{c.plan_nome}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {c.installer_nome}
                  </td>
                  <td className="px-4 py-3">
                    {c.sgp_synced_at ? (
                      <Badge className="gap-1 bg-emerald-100 text-emerald-700 hover:bg-emerald-100">
                        <CloudDone className="h-3 w-3" />
                        {c.sgp_id ?? 'sync'}
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="gap-1 border-amber-400 text-amber-700">
                        <CloudOff className="h-3 w-3" />
                        Pendente
                      </Badge>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="inline-flex gap-1">
                      {!c.sgp_synced_at && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setShowSync(c)}
                          title="Marcar como sincronizado"
                          className="h-8 gap-1"
                        >
                          <CloudUpload className="h-3.5 w-3.5" />
                          Marcar SGP
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 text-destructive hover:text-destructive"
                        onClick={() => handleDelete(c)}
                        title="Excluir"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
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

function Kpi({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string
  value: number
  icon: React.ComponentType<{ className?: string }>
  color: string
}) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-5">
        <div>
          <div className="text-xs uppercase text-muted-foreground">{label}</div>
          <div className="mt-1 text-3xl font-bold">{value}</div>
        </div>
        <Icon className={cn('h-7 w-7', color)} />
      </CardContent>
    </Card>
  )
}

function FiltroChip({
  label,
  active,
  color,
  onClick,
}: {
  label: string
  active: boolean
  color?: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
        active
          ? color ?? 'bg-primary text-primary-foreground border-primary'
          : 'border-border text-muted-foreground hover:bg-muted',
      )}
    >
      {label}
    </button>
  )
}

function fmtCpf(cpf: string): string {
  const d = cpf.replace(/\D/g, '')
  if (d.length === 11) {
    return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`
  }
  if (d.length === 14) {
    return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`
  }
  return cpf
}
