'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  useDepositoSaldo,
  useTecnicos,
  useTransferir,
} from '@/lib/api/queries'

interface Props {
  onClose: () => void
}

export function DialogTransferir({ onClose }: Props) {
  const { data: deposito } = useDepositoSaldo()
  const { data: tecnicos } = useTecnicos({ ativo: true })
  const transferir = useTransferir()

  const [itemId, setItemId] = useState('')
  const [tecnicoId, setTecnicoId] = useState('')
  const [quantidade, setQuantidade] = useState('')
  const [serial, setSerial] = useState('')
  const [observacao, setObservacao] = useState('')
  const [erro, setErro] = useState<string | null>(null)

  const item = deposito?.linhas.find((l) => l.item_id === itemId)
  const serializado = item?.serializado ?? false
  const saldoDisponivel = item?.saldo ?? 0

  async function submit() {
    setErro(null)
    const qtd = parseInt(quantidade, 10)
    if (!itemId) return setErro('Selecione um item.')
    if (!tecnicoId) return setErro('Selecione o técnico.')
    if (!qtd || qtd <= 0) return setErro('Quantidade inválida.')
    if (qtd > saldoDisponivel) {
      return setErro(
        `Saldo do depósito é ${saldoDisponivel}. Não dá pra transferir ${qtd}.`,
      )
    }
    if (serializado && qtd !== 1) {
      return setErro('Item serializado exige quantidade = 1.')
    }
    if (serializado && !serial.trim()) {
      return setErro('Item serializado exige serial.')
    }
    try {
      await transferir.mutateAsync({
        item_id: itemId,
        tecnico_id: tecnicoId,
        quantidade: qtd,
        serial: serial.trim() || null,
        observacao: observacao.trim() || null,
      })
      onClose()
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao transferir')
    }
  }

  // Filtra itens só com saldo > 0 no depósito.
  const itensDisponiveis = (deposito?.linhas ?? []).filter((l) => l.saldo > 0)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto py-4">
      <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-lg space-y-4 mx-4">
        <div>
          <h2 className="text-lg font-semibold">Transferir → Técnico</h2>
          <p className="text-xs text-muted-foreground">
            Sai do depósito e entra no estoque pessoal do técnico (atômico).
          </p>
        </div>

        <div>
          <Label htmlFor="item">Item do depósito *</Label>
          <Select
            id="item"
            value={itemId}
            onChange={(e) => setItemId(e.target.value)}
          >
            <option value="">Selecione…</option>
            {itensDisponiveis.map((l) => (
              <option key={l.item_id} value={l.item_id}>
                {l.nome} ({l.sku}) — {l.saldo} disponível
              </option>
            ))}
          </Select>
          {itensDisponiveis.length === 0 && (
            <p className="mt-1 text-xs text-amber-700">
              Depósito vazio. Registre uma entrada primeiro.
            </p>
          )}
        </div>

        <div>
          <Label htmlFor="tec">Técnico *</Label>
          <Select
            id="tec"
            value={tecnicoId}
            onChange={(e) => setTecnicoId(e.target.value)}
          >
            <option value="">Selecione…</option>
            {(tecnicos?.items ?? []).map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
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
            max={saldoDisponivel || undefined}
            value={quantidade}
            onChange={(e) => setQuantidade(e.target.value)}
            placeholder={serializado ? '1' : '1, 2, …'}
          />
          {item && (
            <p className="mt-1 text-xs text-muted-foreground">
              Disponível: <strong>{saldoDisponivel}</strong>
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
            rows={2}
            placeholder="Ex: kit instalação"
          />
        </div>

        {erro && <p className="text-sm text-destructive">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={submit} disabled={transferir.isPending}>
            {transferir.isPending ? 'Transferindo…' : 'Transferir'}
          </Button>
        </div>
      </div>
    </div>
  )
}
