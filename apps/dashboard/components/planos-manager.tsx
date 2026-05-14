'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { usePlanos, useDeletePlano } from '@/lib/api/queries'
import { PlanoModal } from '@/components/plano-modal'
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

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Planos de Internet</h2>
        <Button onClick={() => setEditingPlano(null)}>+ Novo Plano</Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {(planos ?? []).map((plano) => (
          <div
            key={plano.index}
            className={`rounded-lg border p-4 ${plano.destaque ? 'border-yellow-400 bg-yellow-50' : 'border-border bg-card'}`}
          >
            <div className="mb-1 flex items-start justify-between">
              <span className="font-semibold">{plano.nome}</span>
              <div className="flex gap-1">
                {plano.destaque && (
                  <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs text-yellow-800">
                    ⭐ destaque
                  </span>
                )}
                {!plano.ativo && (
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                    inativo
                  </span>
                )}
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
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
                    className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700"
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

      {modalOpen && (
        <PlanoModal
          plano={editingPlano}
          onClose={() => setEditingPlano(undefined)}
        />
      )}
    </div>
  )
}
