'use client'
import { useEffect, useState } from 'react'
import {
  CloudOff,
  CloudUpload,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Download,
  MapPin,
  Trash2,
  Users,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { DialogMarcarSyncSgp } from '@/components/dialog-marcar-sync-sgp'
import { DialogImportarClientesCsv } from '@/components/dialog-importar-clientes-csv'
import { DialogClienteCampoDetail } from '@/components/dialog-cliente-campo-detail'
import {
  useClientesCampo,
  useClientesCampoStats,
  useDeleteClienteCampo,
} from '@/lib/api/queries'
import type { ClienteCampoListItem } from '@/lib/api/types'
import { cn } from '@/lib/utils'

type FiltroSgp = 'all' | 'synced' | 'pending'
const PAGE_SIZE = 50

export default function ClientesCampoPage() {
  const [busca, setBusca] = useState('')
  const [filtroSgp, setFiltroSgp] = useState<FiltroSgp>('all')
  const [showSync, setShowSync] = useState<ClienteCampoListItem | null>(null)
  const [showImport, setShowImport] = useState(false)
  const [showDetail, setShowDetail] = useState<string | null>(null)

  // Pilha de cursors: posição 0 = primeira página (cursor undefined).
  // Avançar empurra next_cursor; voltar dá pop.
  const [cursorStack, setCursorStack] = useState<(string | undefined)[]>([undefined])
  const currentCursor = cursorStack[cursorStack.length - 1]
  const pageNum = cursorStack.length

  // Resetar paginação quando filtros mudam
  useEffect(() => {
    setCursorStack([undefined])
  }, [busca, filtroSgp])

  const { data, isLoading, error, isFetching } = useClientesCampo({
    q: busca || undefined,
    sgp_status: filtroSgp === 'all' ? undefined : filtroSgp,
    cursor: currentCursor,
  })
  const { data: stats } = useClientesCampoStats()
  const deleteCliente = useDeleteClienteCampo()

  const items = data?.items ?? []
  const hasNext = !!data?.next_cursor
  const hasPrev = cursorStack.length > 1

  function goNext() {
    if (data?.next_cursor) {
      setCursorStack([...cursorStack, data.next_cursor])
    }
  }
  function goPrev() {
    if (hasPrev) setCursorStack(cursorStack.slice(0, -1))
  }

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

  // Range visível desta página: ex "1-50 de 953"
  const start = (pageNum - 1) * PAGE_SIZE + 1
  const end = (pageNum - 1) * PAGE_SIZE + items.length
  const total = stats?.total ?? 0

  return (
    <div className="space-y-6">
      {showSync && (
        <DialogMarcarSyncSgp cliente={showSync} onClose={() => setShowSync(null)} />
      )}
      {showImport && <DialogImportarClientesCsv onClose={() => setShowImport(false)} />}
      {showDetail && (
        <DialogClienteCampoDetail id={showDetail} onClose={() => setShowDetail(null)} />
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
        <Kpi label="Total" value={stats?.total ?? 0} icon={Users} tone="info" />
        <Kpi
          label="Sincronizados c/ SGP"
          value={stats?.synced ?? 0}
          icon={CheckCircle2}
          tone="success"
        />
        <Kpi
          label="Pendentes"
          value={stats?.pending ?? 0}
          icon={CloudOff}
          tone="warning"
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
          <FiltroChip label="Todos" active={filtroSgp === 'all'} onClick={() => setFiltroSgp('all')} />
          <FiltroChip
            label="Sincronizado"
            active={filtroSgp === 'synced'}
            tone="success"
            onClick={() => setFiltroSgp('synced')}
          />
          <FiltroChip
            label="Pendente SGP"
            active={filtroSgp === 'pending'}
            tone="warning"
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
        <div className="overflow-hidden rounded-md border bg-card">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-4 py-2.5 font-semibold">Cliente</th>
                  <th className="px-4 py-2.5 font-semibold">CPF</th>
                  <th className="px-4 py-2.5 font-semibold">Endereço</th>
                  <th className="px-4 py-2.5 font-semibold">Cidade</th>
                  <th className="px-4 py-2.5 font-semibold">Plano</th>
                  <th className="px-4 py-2.5 font-semibold">Instalador</th>
                  <th className="px-4 py-2.5 font-semibold">SGP</th>
                  <th className="px-4 py-2.5 font-semibold text-right">Ações</th>
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
                    className="border-b last:border-b-0 cursor-pointer transition-colors hover:bg-accent/40"
                    onClick={() => setShowDetail(c.id)}
                  >
                    <td className="px-4 py-3 font-medium">{c.nome}</td>
                    <td className="px-4 py-3 font-mono text-xs" style={{ fontVariantNumeric: 'tabular-nums' }}>
                      {fmtCpf(c.cpf)}
                    </td>
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
                        <span className="inline-flex items-center gap-1 rounded-full bg-success/[0.12] px-2 py-0.5 text-xs font-medium text-success ring-1 ring-inset ring-success/30">
                          <CheckCircle2 className="h-3 w-3" />
                          {c.sgp_id ?? 'sync'}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-warning/[0.15] px-2 py-0.5 text-xs font-medium text-warning ring-1 ring-inset ring-warning/30">
                          <CloudOff className="h-3 w-3" />
                          Pendente
                        </span>
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
                            aria-label={`Marcar ${c.nome} como sincronizado com SGP`}
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
                          aria-label={`Excluir ${c.nome}`}
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

          {/* Paginação anterior/próximo */}
          <div className="flex items-center justify-between gap-3 border-t bg-muted/20 px-4 py-2.5 text-xs">
            <span className="text-muted-foreground" style={{ fontVariantNumeric: 'tabular-nums' }}>
              {items.length > 0 ? (
                <>
                  {start}–{end}
                  {total > 0 && filtroSgp === 'all' && !busca ? ` de ${total}` : ''} · página {pageNum}
                </>
              ) : (
                'Nenhum resultado'
              )}
              {isFetching && <span className="ml-2 opacity-70">atualizando…</span>}
            </span>
            <div className="flex items-center gap-1">
              <Button
                size="sm"
                variant="outline"
                onClick={goPrev}
                disabled={!hasPrev || isFetching}
                aria-label="Página anterior"
                className="h-8 gap-1"
              >
                <ChevronLeft className="h-4 w-4" />
                Anterior
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={goNext}
                disabled={!hasNext || isFetching}
                aria-label="Próxima página"
                className="h-8 gap-1"
              >
                Próximo
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const KPI_TONE: Record<'info' | 'success' | 'warning', string> = {
  info: 'bg-info/[0.12] text-info',
  success: 'bg-success/[0.12] text-success',
  warning: 'bg-warning/[0.15] text-warning',
}

function Kpi({
  label,
  value,
  icon: Icon,
  tone = 'info',
}: {
  label: string
  value: number
  icon: React.ComponentType<{ className?: string }>
  tone?: keyof typeof KPI_TONE
}) {
  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardContent className="flex items-start justify-between gap-3 p-5">
        <div className="min-w-0">
          <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </div>
          <div
            className="mt-2 text-3xl font-semibold leading-none"
            style={{ fontVariantNumeric: 'tabular-nums' }}
          >
            {value}
          </div>
        </div>
        <div className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-md', KPI_TONE[tone])}>
          <Icon className="h-4 w-4" />
        </div>
      </CardContent>
    </Card>
  )
}

const CHIP_TONE: Record<'success' | 'warning', string> = {
  success: 'bg-success/[0.12] text-success ring-success/30',
  warning: 'bg-warning/[0.15] text-warning ring-warning/30',
}

function FiltroChip({
  label,
  active,
  tone,
  onClick,
}: {
  label: string
  active: boolean
  tone?: keyof typeof CHIP_TONE
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'rounded-full border px-3 py-1.5 text-xs font-medium ring-1 ring-inset transition-colors',
        active
          ? tone
            ? CHIP_TONE[tone]
            : 'bg-primary text-primary-foreground ring-primary border-primary'
          : 'border-border ring-transparent text-muted-foreground hover:bg-muted',
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
