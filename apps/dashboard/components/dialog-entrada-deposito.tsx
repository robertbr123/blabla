'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useDepositoEntrada, useEstoqueItens } from '@/lib/api/queries'

interface Props {
  onClose: () => void
}

export function DialogEntradaDeposito({ onClose }: Props) {
  const { data: itens } = useEstoqueItens(true)
  const entrada = useDepositoEntrada()
  const [itemId, setItemId] = useState('')
  const [quantidade, setQuantidade] = useState('')
  const [serial, setSerial] = useState('')
  const [observacao, setObservacao] = useState('')
  const [erro, setErro] = useState<string | null>(null)

  const item = itens?.find((i) => i.id === itemId)
  const serializado = item?.serializado ?? false

  async function submit() {
    setErro(null)
    const qtd = parseInt(quantidade, 10)
    if (!itemId) {
      setErro('Selecione um item.')
      return
    }
    if (!qtd || qtd <= 0) {
      setErro('Quantidade inválida.')
      return
    }
    if (serializado && qtd !== 1) {
      setErro('Item serializado exige quantidade = 1.')
      return
    }
    if (serializado && !serial.trim()) {
      setErro('Item serializado exige serial.')
      return
    }
    try {
      await entrada.mutateAsync({
        item_id: itemId,
        quantidade: qtd,
        serial: serial.trim() || null,
        observacao: observacao.trim() || null,
      })
      onClose()
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao registrar entrada')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto py-4">
      <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-lg space-y-4 mx-4">
        <div>
          <h2 className="text-lg font-semibold">Entrada no depósito</h2>
          <p className="text-xs text-muted-foreground">
            Registra recebimento de mercadoria no depósito central.
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
            {(itens ?? []).map((i) => (
              <option key={i.id} value={i.id}>
                {i.nome} ({i.sku}){i.serializado ? ' · serial' : ''}
              </option>
            ))}
          </Select>
        </div>

        <div>
          <Label htmlFor="qtd">Quantidade *</Label>
          <Input
            id="qtd"
            type="number"
            min={1}
            value={quantidade}
            onChange={(e) => setQuantidade(e.target.value)}
            placeholder={serializado ? '1' : 'Ex: 10'}
          />
          {serializado && (
            <p className="mt-1 text-xs text-muted-foreground">
              Serializado: precisa registrar uma unidade por vez.
            </p>
          )}
        </div>

        {serializado && (
          <div>
            <Label htmlFor="serial">Serial *</Label>
            <Input
              id="serial"
              value={serial}
              onChange={(e) => setSerial(e.target.value)}
              placeholder="Ex: ZTEGC0FE1234"
            />
          </div>
        )}

        <div>
          <Label htmlFor="obs">Observação (opcional)</Label>
          <Textarea
            id="obs"
            value={observacao}
            onChange={(e) => setObservacao(e.target.value)}
            placeholder="Ex: NF 1234 — fornecedor X"
            rows={2}
          />
        </div>

        {erro && <p className="text-sm text-destructive">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={submit} disabled={entrada.isPending}>
            {entrada.isPending ? 'Registrando…' : 'Registrar entrada'}
          </Button>
        </div>
      </div>
    </div>
  )
}
