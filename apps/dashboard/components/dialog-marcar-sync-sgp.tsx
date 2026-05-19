'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useMarcarSyncSgp } from '@/lib/api/queries'
import type { ClienteCampoListItem } from '@/lib/api/types'

interface Props {
  cliente: ClienteCampoListItem
  onClose: () => void
}

export function DialogMarcarSyncSgp({ cliente, onClose }: Props) {
  const [sgpId, setSgpId] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const marcar = useMarcarSyncSgp()

  async function submit() {
    setErro(null)
    const id = sgpId.trim()
    if (!id) return setErro('Informe o ID do SGP.')
    try {
      await marcar.mutateAsync({ id: cliente.id, sgp_id: id })
      onClose()
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao marcar')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto py-4">
      <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-lg space-y-4 mx-4">
        <div>
          <h2 className="text-lg font-semibold">Marcar como sincronizado</h2>
          <p className="text-xs text-muted-foreground">
            Use depois de cadastrar este cliente no SGP manualmente. Cole o
            ID que o SGP gerou.
          </p>
        </div>

        <div className="rounded-md bg-muted/40 p-3 text-sm">
          <p className="font-medium">{cliente.nome}</p>
          <p className="text-xs text-muted-foreground">
            {cliente.address}, {cliente.number} · {cliente.city}
          </p>
          <p className="text-xs text-muted-foreground">
            Plano: {cliente.plan_nome}
          </p>
        </div>

        <div>
          <Label htmlFor="sgp-id">ID no SGP *</Label>
          <Input
            id="sgp-id"
            value={sgpId}
            onChange={(e) => setSgpId(e.target.value)}
            placeholder="Ex: 12345"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter') submit()
            }}
          />
        </div>

        {erro && <p className="text-sm text-destructive">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={submit} disabled={marcar.isPending}>
            {marcar.isPending ? 'Salvando…' : 'Marcar como sincronizado'}
          </Button>
        </div>
      </div>
    </div>
  )
}
