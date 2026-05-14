'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { useReatribuirOs, useTecnicos } from '@/lib/api/queries'

interface Props {
  osId: string
  onClose: () => void
}

export function DialogReatribuirTecnico({ osId, onClose }: Props) {
  const { data: tecnicos } = useTecnicos({ ativo: true })
  const reatribuir = useReatribuirOs(osId)
  const [tecnicoId, setTecnicoId] = useState('')

  async function handleConfirm() {
    if (!tecnicoId) return
    await reatribuir.mutateAsync({ tecnico_id: tecnicoId })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-sm rounded-lg border bg-card p-6 shadow-lg space-y-4">
        <h2 className="text-lg font-semibold">Reatribuir técnico</h2>
        <div>
          <Label htmlFor="novo-tecnico">Novo técnico</Label>
          <Select
            id="novo-tecnico"
            value={tecnicoId}
            onChange={(e) => setTecnicoId(e.target.value)}
            className="mt-1"
          >
            <option value="" disabled>Selecione o técnico</option>
            {tecnicos?.items.map((t) => (
              <option key={t.id} value={t.id}>{t.nome}</option>
            ))}
          </Select>
        </div>
        {reatribuir.error && (
          <p className="text-xs text-destructive">
            {reatribuir.error instanceof Error ? reatribuir.error.message : 'Erro'}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={reatribuir.isPending}>
            Cancelar
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!tecnicoId || reatribuir.isPending}
          >
            {reatribuir.isPending ? 'Reatribuindo…' : 'Confirmar'}
          </Button>
        </div>
      </div>
    </div>
  )
}
