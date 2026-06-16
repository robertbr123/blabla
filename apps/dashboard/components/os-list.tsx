'use client'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Ban, ClipboardList, Plus, Search, Trash2, UserCog } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { useDeleteOs, useOsListInfinite, usePatchOs, useTecnicos } from '@/lib/api/queries'
import { DialogReatribuirTecnico } from './dialog-reatribuir-tecnico'
import { OsStatusPill } from './os-status-pill'
import type { OsListItem } from '@/lib/api/types'

function CancelButton({ osId }: { osId: string }) {
  const patchOs = usePatchOs(osId)
  function handleCancel() {
    if (!confirm('Cancelar esta OS?')) return
    patchOs.mutate({ status: 'cancelada' })
  }
  return (
    <Button
      variant="ghost"
      size="sm"
      className="h-7 gap-1.5 px-2 text-amber-600 hover:text-amber-700"
      onClick={handleCancel}
      disabled={patchOs.isPending}
    >
      <Ban className="h-3.5 w-3.5" /> Cancelar
    </Button>
  )
}

function DeleteButton({ osId }: { osId: string }) {
  const deleteOs = useDeleteOs(osId)
  async function handleDelete() {
    if (!confirm('Excluir esta OS? O técnico será notificado.')) return
    await deleteOs.mutateAsync()
  }
  return (
    <Button
      variant="ghost"
      size="sm"
      className="h-7 gap-1.5 px-2 text-destructive hover:text-destructive"
      onClick={handleDelete}
      disabled={deleteOs.isPending}
    >
      <Trash2 className="h-3.5 w-3.5" /> Excluir
    </Button>
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

  return (
    <div className="space-y-4">
      {reatribuirOsId && (
        <DialogReatribuirTecnico
          osId={reatribuirOsId}
          onClose={() => setReatribuirOsId(null)}
        />
      )}
      <div className="flex items-center gap-3">
        <div className="relative max-w-xs flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por código, cliente ou técnico…"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="pl-8"
          />
        </div>
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
          <Button onClick={() => onNovaOs?.()}>
            <Plus className="h-4 w-4" /> Nova OS
          </Button>
        </div>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {!isLoading && oss.length === 0 && (
        <div className="rounded-md border bg-card p-12 text-center">
          <ClipboardList className="mx-auto h-10 w-10 text-muted-foreground/50" />
          <h3 className="mt-3 text-sm font-medium">Nenhuma OS encontrada</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {status
              ? 'Tente outro filtro de status ou limpe a seleção.'
              : 'Crie a primeira ordem de serviço pra começar.'}
          </p>
          {!status && (
            <Button onClick={() => onNovaOs?.()} className="mt-4" size="sm">
              <Plus className="h-4 w-4" /> Nova OS
            </Button>
          )}
        </div>
      )}

      {oss.length > 0 && (
        <div className="rounded-md border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Código</th>
                <th className="px-4 py-2.5 font-semibold">Cliente</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
                <th className="px-4 py-2.5 font-semibold">Técnico</th>
                <th className="px-4 py-2.5 font-semibold">Problema</th>
                <th className="px-4 py-2.5 font-semibold">Endereço</th>
                <th className="px-4 py-2.5 font-semibold">Criada</th>
                <th className="px-4 py-2.5 font-semibold">Ações</th>
              </tr>
            </thead>
            <tbody>
              {oss.map((o: OsListItem) => (
                <tr key={o.id} className="border-b last:border-b-0 transition-colors hover:bg-accent/40">
                  <td className="px-4 py-3">
                    <Link href={`/os/${o.id}`} className="font-medium text-primary hover:underline">
                      {o.codigo}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{o.nome_cliente ?? '—'}</td>
                  <td className="px-4 py-3">
                    <OsStatusPill status={o.status} size="sm" />
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {o.tecnico_id
                      ? tecnicoNomePorId.get(o.tecnico_id) ?? '—'
                      : <span className="italic">sem técnico</span>}
                  </td>
                  <td className="px-4 py-3 max-w-xs truncate">{o.problema}</td>
                  <td className="px-4 py-3 max-w-xs truncate text-muted-foreground">
                    {o.endereco}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {new Date(o.criada_em).toLocaleString('pt-BR')}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      {o.status !== 'concluida' && o.status !== 'cancelada' && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 gap-1.5 px-2"
                            onClick={() => setReatribuirOsId(o.id)}
                          >
                            <UserCog className="h-3.5 w-3.5" /> Técnico
                          </Button>
                          <CancelButton osId={o.id} />
                        </>
                      )}
                      <DeleteButton osId={o.id} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {hasNextPage && (
        <div className="flex justify-center pt-2">
          <Button
            variant="outline"
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
