'use client'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { AlertTriangle, ClipboardList, Plus, Search, Trash2, UserCog, UserX } from 'lucide-react'

import {
  Age,
  Avatar,
  FilterTabs,
  SkeletonRows,
  TONE_SOFT,
  type FilterTab,
} from '@/components/noc/primitives'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDeleteOs, useOsListInfinite, useTecnicos } from '@/lib/api/queries'
import { cn } from '@/lib/utils'
import { DialogReatribuirTecnico } from './dialog-reatribuir-tecnico'
import { OsStatusPill } from './os-status-pill'
import { TABS_SCROLL } from './responsive'
import type { OsListItem } from '@/lib/api/types'

const STATUS_TABS: ReadonlyArray<FilterTab<string>> = [
  { value: '', label: 'Todas' },
  { value: 'pendente', label: 'Pendente', tone: 'info' },
  { value: 'em_andamento', label: 'Em andamento', tone: 'warning' },
  { value: 'concluida', label: 'Concluída', tone: 'success' },
  { value: 'cancelada', label: 'Cancelada', tone: 'destructive' },
]

function DeleteButton({
  osId,
  codigo,
  touch = false,
}: {
  osId: string
  codigo: string
  /** Alvo de toque maior (cartão do celular). */
  touch?: boolean
}) {
  const deleteOs = useDeleteOs(osId)
  async function handleDelete() {
    if (!confirm('Excluir esta OS? O técnico será notificado.')) return
    await deleteOs.mutateAsync()
  }
  return (
    <Button
      variant="ghost"
      size="icon"
      className={cn(
        touch ? 'h-9 w-9' : 'h-7 w-7',
        'text-muted-foreground hover:bg-destructive/10 hover:text-destructive',
      )}
      onClick={handleDelete}
      disabled={deleteOs.isPending}
      title="Excluir OS"
      aria-label={`Excluir OS ${codigo}`}
    >
      <Trash2 className="h-3.5 w-3.5" />
    </Button>
  )
}

/** Ações de uma OS — as mesmas na linha da tabela (md+) e no cartão (celular). */
function OsRowActions({
  o,
  onReatribuir,
  touch = false,
}: {
  o: OsListItem
  onReatribuir: (id: string) => void
  touch?: boolean
}) {
  return (
    <div className="flex items-center justify-end gap-0.5">
      {/* Reatribuir técnico — em qualquer status menos cancelada
          (a API já permite reatribuir concluída). */}
      {o.status !== 'cancelada' && (
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            touch ? 'h-9 w-9' : 'h-7 w-7',
            'text-muted-foreground hover:text-foreground',
          )}
          onClick={() => onReatribuir(o.id)}
          title="Reatribuir técnico"
          aria-label={`Reatribuir técnico da OS ${o.codigo}`}
        >
          <UserCog className="h-3.5 w-3.5" />
        </Button>
      )}
      {/* Excluir = avisa o técnico (cancelado) e apaga de vez. */}
      <DeleteButton osId={o.id} codigo={o.codigo} touch={touch} />
    </div>
  )
}

/** Técnico da OS: "Sem técnico", avatar + nome, ou traço se o nome não carregou. */
function OsTecnico({ o, nome }: { o: OsListItem; nome: string | null }) {
  if (!o.tecnico_id) {
    return (
      <span
        className={cn(
          'inline-flex h-[22px] items-center gap-1 whitespace-nowrap rounded-md px-2 text-xs font-medium ring-1 ring-inset',
          TONE_SOFT.warning,
        )}
      >
        <UserX aria-hidden className="h-3 w-3" />
        Sem técnico
      </span>
    )
  }
  if (!nome) return <span className="text-muted-foreground">—</span>
  return (
    <span className="flex min-w-0 items-center gap-2">
      <Avatar name={nome} size="sm" />
      <span className="max-w-[160px] truncate" title={nome}>
        {nome}
      </span>
    </span>
  )
}

interface OsItemProps {
  o: OsListItem
  tecnicoNome: string | null
  onReatribuir: (id: string) => void
}

/** Linha da tabela (md+). */
function OsRow({ o, tecnicoNome, onReatribuir }: OsItemProps) {
  return (
    <tr>
      <td className="whitespace-nowrap">
        <Link
          href={`/os/${o.id}`}
          className="num rounded-sm font-medium text-foreground underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {o.codigo}
        </Link>
      </td>
      <td>
        <span className="block max-w-[220px] truncate" title={o.nome_cliente ?? undefined}>
          {o.nome_cliente ?? '—'}
        </span>
      </td>
      <td>
        <OsStatusPill status={o.status} size="sm" />
      </td>
      <td>
        <OsTecnico o={o} nome={tecnicoNome} />
      </td>
      <td>
        <span className="block max-w-xs truncate text-muted-foreground" title={o.problema}>
          {o.problema}
        </span>
      </td>
      <td className="whitespace-nowrap">
        <Age iso={o.criada_em} />
      </td>
      <td>
        <OsRowActions o={o} onReatribuir={onReatribuir} />
      </td>
    </tr>
  )
}

/** Cartão da lista no celular (abaixo de md): o topo inteiro abre a OS. */
function OsCard({ o, tecnicoNome, onReatribuir }: OsItemProps) {
  return (
    <li className="rounded-lg border bg-card">
      <Link
        href={`/os/${o.id}`}
        className="block rounded-t-lg p-3 pb-2.5 transition-colors active:bg-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
      >
        <span className="flex items-center justify-between gap-2">
          <span className="num min-w-0 truncate text-sm font-medium text-foreground">
            {o.codigo}
          </span>
          <OsStatusPill status={o.status} size="sm" className="shrink-0" />
        </span>
        <span className="mt-1.5 block truncate text-sm">{o.nome_cliente ?? '—'}</span>
        <span className="mt-0.5 line-clamp-2 break-words text-xs text-muted-foreground">
          {o.problema}
        </span>
      </Link>
      <div className="flex items-center gap-2 border-t border-border/70 py-1 pl-3 pr-1.5 text-sm">
        <div className="min-w-0 flex-1">
          <OsTecnico o={o} nome={tecnicoNome} />
        </div>
        <Age iso={o.criada_em} className="shrink-0" />
        <OsRowActions o={o} onReatribuir={onReatribuir} touch />
      </div>
    </li>
  )
}

export function OsList({ onNovaOs }: { onNovaOs?: () => void } = {}) {
  const [status, setStatus] = useState('')
  const [busca, setBusca] = useState('')
  const [q, setQ] = useState('')
  const [reatribuirOsId, setReatribuirOsId] = useState<string | null>(null)
  // debounce 300ms: digita em `busca`, aplica em `q` (o que vai pra API)
  useEffect(() => {
    const t = setTimeout(() => setQ(busca.trim()), 300)
    return () => clearTimeout(t)
  }, [busca])
  const {
    data, isLoading, error, hasNextPage, fetchNextPage, isFetchingNextPage,
  } = useOsListInfinite({ status: status || undefined, q: q || undefined })
  const oss = data?.pages.flatMap((p) => p.items) ?? []
  const { data: tecnicosData } = useTecnicos({})
  const tecnicoNomePorId = new Map(
    (tecnicosData?.items ?? []).map((t) => [t.id, t.nome])
  )
  // Nome do técnico resolvido uma vez por OS — usado pela linha e pelo cartão.
  const linhas = oss.map((o: OsListItem) => ({
    o,
    tecnicoNome: o.tecnico_id ? (tecnicoNomePorId.get(o.tecnico_id) ?? null) : null,
  }))
  const filtrando = Boolean(status || q)

  return (
    <div className="min-w-0 space-y-3">
      {reatribuirOsId && (
        <DialogReatribuirTecnico
          osId={reatribuirOsId}
          onClose={() => setReatribuirOsId(null)}
        />
      )}
      <div className="flex flex-wrap items-center gap-3">
        <FilterTabs
          tabs={STATUS_TABS}
          value={status}
          onChange={setStatus}
          ariaLabel="Filtrar por status"
          className={TABS_SCROLL}
        />
        <div className="relative w-full md:ml-auto md:w-72">
          <Search
            aria-hidden
            className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            type="search"
            aria-label="Buscar ordens de serviço"
            placeholder="Buscar por código, cliente ou técnico…"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="pl-8 max-md:h-10 max-md:text-base"
          />
        </div>
      </div>

      {isLoading && (
        <div className="overflow-hidden rounded-lg border bg-card">
          <SkeletonRows rows={8} />
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/[0.08] p-4"
        >
          <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
          <div className="min-w-0">
            <p className="text-sm font-medium">Não foi possível carregar as ordens de serviço</p>
            <p className="mt-0.5 break-words text-xs text-muted-foreground">
              {error instanceof Error ? error.message : 'Erro ao carregar'}
            </p>
          </div>
        </div>
      )}

      {!isLoading && !error && oss.length === 0 && (
        <div className="rounded-lg border bg-card px-6 py-12 text-center">
          <ClipboardList aria-hidden className="mx-auto h-10 w-10 text-muted-foreground/50" />
          <h3 className="mt-3 text-sm font-medium">Nenhuma OS encontrada</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {filtrando
              ? 'Tente outro filtro de status ou limpe a busca.'
              : 'Crie a primeira ordem de serviço pra começar.'}
          </p>
          {!filtrando && (
            <Button onClick={() => onNovaOs?.()} className="mt-4" size="sm">
              <Plus className="h-4 w-4" /> Nova OS
            </Button>
          )}
        </div>
      )}

      {linhas.length > 0 && (
        <>
          {/* Celular: um cartão por OS. */}
          <ul className="space-y-2 md:hidden">
            {linhas.map(({ o, tecnicoNome }) => (
              <OsCard
                key={o.id}
                o={o}
                tecnicoNome={tecnicoNome}
                onReatribuir={setReatribuirOsId}
              />
            ))}
          </ul>

          {/* De md pra cima: tabela. */}
          <div className="hidden overflow-hidden rounded-lg border bg-card md:block">
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Código</th>
                    <th scope="col">Cliente</th>
                    <th scope="col">Status</th>
                    <th scope="col">Técnico</th>
                    <th scope="col">Problema</th>
                    <th scope="col">Aberta há</th>
                    <th scope="col" className="text-right">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {linhas.map(({ o, tecnicoNome }) => (
                    <OsRow
                      key={o.id}
                      o={o}
                      tecnicoNome={tecnicoNome}
                      onReatribuir={setReatribuirOsId}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {hasNextPage && (
        <div className="flex justify-center pt-1">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
          >
            {isFetchingNextPage ? 'Carregando…' : 'Carregar mais'}
          </Button>
        </div>
      )}
    </div>
  )
}
