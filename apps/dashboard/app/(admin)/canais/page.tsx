'use client'
import { useState } from 'react'
import { Radio, Plus, Pencil, Cloud, Server } from 'lucide-react'
import { useCanais } from '@/lib/api/queries'
import type { CanalOut } from '@/lib/api/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { CanalFormDialog } from '@/components/canal-form-dialog'
import { PageHeader } from '@/components/noc/primitives'

export default function CanaisPage() {
  const { data, isLoading, error } = useCanais()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<CanalOut | null>(null)

  function handleNew() {
    setEditing(null)
    setDialogOpen(true)
  }

  function handleEdit(c: CanalOut) {
    setEditing(c)
    setDialogOpen(true)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Canais WhatsApp"
        description="Mapeie cada número WhatsApp (Evolution self-hosted ou Cloud API oficial da Meta) a um canal com regras próprias."
        actions={
          <Button onClick={handleNew}>
            <Plus className="mr-2 h-4 w-4" />
            Novo canal
          </Button>
        }
      />

      {isLoading && (
        <p className="text-sm text-muted-foreground">Carregando…</p>
      )}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {data && data.length === 0 && (
        <EmptyState
          icon={Radio}
          title="Nenhum canal cadastrado"
          description='Clique em "Novo canal" pra adicionar um número Evolution ou Cloud.'
        />
      )}

      {data && data.length > 0 && (
        <div className="rounded-md border bg-card overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Nome</th>
                <th className="px-4 py-2.5 font-semibold">Slug</th>
                <th className="px-4 py-2.5 font-semibold">Provedor</th>
                <th className="px-4 py-2.5 font-semibold">Identificador</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
                <th className="px-4 py-2.5 font-semibold w-12"></th>
              </tr>
            </thead>
            <tbody>
              {data.map((c) => (
                <tr
                  key={c.id}
                  className="border-b last:border-b-0 transition-colors hover:bg-accent/40"
                >
                  <td className="px-4 py-3 font-medium">{c.nome}</td>
                  <td className="px-4 py-3 font-mono text-xs">{c.slug}</td>
                  <td className="px-4 py-3">
                    {c.provider === 'cloud' ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-info/10 px-2 py-0.5 text-[11px] font-medium text-info ">
                        <Cloud className="h-3 w-3" />
                        Cloud API
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                        <Server className="h-3 w-3" />
                        Evolution
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                    {c.provider === 'cloud'
                      ? c.cloud_phone_id || '—'
                      : c.evolution_instance || '—'}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={c.ativo ? 'default' : 'outline'}>
                      {c.ativo ? 'Ativo' : 'Desativado'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(c)}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <CanalFormDialog
        open={dialogOpen}
        canal={editing}
        onClose={() => setDialogOpen(false)}
      />
    </div>
  )
}
