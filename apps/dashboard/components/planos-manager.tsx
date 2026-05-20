'use client'
import { useState } from 'react'
import { Package, Star } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { usePlanos, useDeletePlano } from '@/lib/api/queries'
import { PlanoModal } from '@/components/plano-modal'
import { cn } from '@/lib/utils'
import type { PlanoOut } from '@/lib/api/types'

export function PlanosManager() {
  const { data: planos, isLoading, error } = usePlanos()
  const deletePlano = useDeletePlano()
  const [editingPlano, setEditingPlano] = useState<PlanoOut | null | undefined>(undefined)

  // undefined = modal fechado, null = modal aberto para criação, PlanoOut = edição
  const modalOpen = editingPlano !== undefined

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando planos…</p>
  if (error) return <p className="text-sm text-destructive">Erro ao carregar planos</p>

  async function handleDelete(plano: PlanoOut) {
    if (!confirm(`Excluir o plano "${plano.nome}"?`)) return
    await deletePlano.mutateAsync(plano.index)
  }

  const lista = planos ?? []

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Planos de Internet</h2>
        <Button onClick={() => setEditingPlano(null)}>+ Novo Plano</Button>
      </div>

      {lista.length === 0 ? (
        <EmptyState
          icon={Package}
          title="Nenhum plano cadastrado"
          description="Cadastre os planos vendidos para que o bot e os técnicos possam oferecer/consultar."
          action={
            <Button size="sm" onClick={() => setEditingPlano(null)}>
              + Novo Plano
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {lista.map((plano) => (
            <div
              key={plano.index}
              className={cn(
                'rounded-lg border p-4 transition-shadow hover:shadow-md',
                plano.destaque
                  ? 'border-warning/40 bg-warning/[0.06]'
                  : 'border-border bg-card',
              )}
            >
              <div className="mb-1 flex items-start justify-between gap-2">
                <span className="font-semibold">{plano.nome}</span>
                <div className="flex gap-1 shrink-0">
                  {plano.destaque && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-warning/[0.15] px-2 py-0.5 text-xs font-medium text-warning ring-1 ring-inset ring-warning/30">
                      <Star className="h-3 w-3 fill-current" /> destaque
                    </span>
                  )}
                  {!plano.ativo && (
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                      inativo
                    </span>
                  )}
                </div>
              </div>
              <p className="text-sm text-muted-foreground" style={{ fontVariantNumeric: 'tabular-nums' }}>
                {plano.velocidade} · R$ {plano.preco.toFixed(2)}
              </p>
              {plano.descricao && (
                <p className="mt-1 text-xs text-muted-foreground">{plano.descricao}</p>
              )}
              {plano.extras.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {plano.extras.map((ex, i) => (
                    <span
                      key={i}
                      className="rounded-full bg-info/[0.12] px-2 py-0.5 text-xs text-info ring-1 ring-inset ring-info/30"
                    >
                      {ex}
                    </span>
                  ))}
                </div>
              )}
              <div className="mt-3 flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setEditingPlano(plano)}
                >
                  Editar
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={deletePlano.isPending}
                  onClick={() => handleDelete(plano)}
                >
                  Excluir
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {modalOpen && (
        <PlanoModal
          plano={editingPlano}
          onClose={() => setEditingPlano(undefined)}
        />
      )}
    </div>
  )
}
