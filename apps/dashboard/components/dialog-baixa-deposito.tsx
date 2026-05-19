'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useDepositoBaixa, useDepositoSaldo } from '@/lib/api/queries'

interface Props {
  onClose: () => void
}

export function DialogBaixaDeposito({ onClose }: Props) {
  const { data: deposito } = useDepositoSaldo()
  const baixa = useDepositoBaixa()

  const [itemId, setItemId] = useState('')
  const [quantidade, setQuantidade] = useState('')
  const [tipo, setTipo] = useState<'perda' | 'ajuste_negativo'>('perda')
  const [serial, setSerial] = useState('')
  const [observacao, setObservacao] = useState('')
  const [erro, setErro] = useState<string | null>(null)

  const item = deposito?.linhas.find((l) => l.item_id === itemId)
  const serializado = item?.serializado ?? false
  const saldo = item?.saldo ?? 0

  async function submit() {
    setErro(null)
    const qtd = parseInt(quantidade, 10)
    if (!itemId) return setErro('Selecione um item.')
    if (!qtd || qtd <= 0) return setErro('Quantidade inválida.')
    if (qtd > saldo) {
      return setErro(`Saldo do depósito é ${saldo}.`)
    }
    if (!observacao.trim()) {
      return setErro('Observação obrigatória pra audit.')
    }
    try {
      await baixa.mutateAsync({
        item_id: itemId,
        quantidade: qtd,
        tipo,
        serial: serial.trim() || null,
        observacao: observacao.trim(),
      })
      onClose()
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao registrar baixa')
    }
  }

  const itensDisponiveis = (deposito?.linhas ?? []).filter((l) => l.saldo > 0)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto py-4">
      <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-lg space-y-4 mx-4">
        <div>
          <h2 className="text-lg font-semibold">Baixa no depósito</h2>
          <p className="text-xs text-muted-foreground">
            Registre perda física, dano ou ajuste negativo no depósito. Esta
            ação é irreversível — preencha a observação com o motivo.
          </p>
        </div>

        <div>
          <Label htmlFor="item">Item *</Label>
          <Select
            id="item"
            value={itemId}
            onChange={(e) => setItemId(e.target.value)}
          >
            <option value="">Selecione…</option>
            {itensDisponiveis.map((l) => (
              <option key={l.item_id} value={l.item_id}>
                {l.nome} — {l.saldo} disponível
              </option>
            ))}
          </Select>
        </div>

        <div>
          <Label htmlFor="tipo">Tipo *</Label>
          <Select
            id="tipo"
            value={tipo}
            onChange={(e) =>
              setTipo(e.target.value as 'perda' | 'ajuste_negativo')
            }
          >
            <option value="perda">Perda (item danificado / extraviado)</option>
            <option value="ajuste_negativo">Ajuste negativo (inventário)</option>
          </Select>
        </div>

        <div>
          <Label htmlFor="qtd">Quantidade *</Label>
          <Input
            id="qtd"
            type="number"
            min={1}
            max={saldo || undefined}
            value={quantidade}
            onChange={(e) => setQuantidade(e.target.value)}
            placeholder={serializado ? '1' : 'Ex: 5'}
          />
        </div>

        {serializado && (
          <div>
            <Label htmlFor="serial">Serial</Label>
            <Input
              id="serial"
              value={serial}
              onChange={(e) => setSerial(e.target.value)}
              placeholder="Serial específico (opcional)"
            />
          </div>
        )}

        <div>
          <Label htmlFor="obs">Motivo *</Label>
          <Textarea
            id="obs"
            value={observacao}
            onChange={(e) => setObservacao(e.target.value)}
            rows={2}
            placeholder="Ex: ONU danificada na queda. Sem garantia."
          />
        </div>

        {erro && <p className="text-sm text-destructive">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={submit} disabled={baixa.isPending}>
            {baixa.isPending ? 'Registrando…' : 'Registrar baixa'}
          </Button>
        </div>
      </div>
    </div>
  )
}
