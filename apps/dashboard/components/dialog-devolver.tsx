'use client'
import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  useDevolver,
  useEstoqueItens,
  useSeriaisAtivos,
  useTecnicos,
  useTecnicosSaldos,
} from '@/lib/api/queries'

interface Props {
  onClose: () => void
  /** Pre-seleciona o tecnico quando aberto a partir da aba dele. */
  tecnicoIdInicial?: string
  /** Pre-seleciona item+serial quando aberto a partir de um chip de serial. */
  itemIdInicial?: string
  serialInicial?: string
}

export function DialogDevolver({
  onClose,
  tecnicoIdInicial,
  itemIdInicial,
  serialInicial,
}: Props) {
  const { data: tecnicos } = useTecnicos({ ativo: true })
  const { data: saldos } = useTecnicosSaldos()
  const { data: itens } = useEstoqueItens(false)
  const { data: seriais } = useSeriaisAtivos()
  const devolver = useDevolver()

  const [tecnicoId, setTecnicoId] = useState(tecnicoIdInicial ?? '')
  const [itemId, setItemId] = useState(itemIdInicial ?? '')
  const [quantidade, setQuantidade] = useState('1')
  const [serial, setSerial] = useState(serialInicial ?? '')
  const [observacao, setObservacao] = useState('')
  const [erro, setErro] = useState<string | null>(null)

  // Itens que esse técnico tem com saldo > 0
  const itensDoTecnico = useMemo(() => {
    if (!tecnicoId) return []
    return (saldos?.linhas ?? []).filter(
      (l) => l.tecnico_id === tecnicoId && l.saldo > 0,
    )
  }, [saldos, tecnicoId])

  const itemSel = (itens ?? []).find((i) => i.id === itemId)
  const serializado = itemSel?.serializado ?? false
  const saldoTec =
    (saldos?.linhas ?? []).find(
      (l) => l.tecnico_id === tecnicoId && l.item_id === itemId,
    )?.saldo ?? 0

  const seriaisDoTecItem = useMemo(() => {
    return (seriais?.linhas ?? [])
      .filter((s) => s.tecnico_id === tecnicoId && s.item_id === itemId)
      .map((s) => s.serial)
  }, [seriais, tecnicoId, itemId])

  async function submit() {
    setErro(null)
    const qtd = parseInt(quantidade, 10)
    if (!tecnicoId) return setErro('Selecione o técnico.')
    if (!itemId) return setErro('Selecione um item.')
    if (!qtd || qtd <= 0) return setErro('Quantidade inválida.')
    if (qtd > saldoTec) {
      return setErro(
        `Técnico só tem ${saldoTec} desse item. Não dá pra devolver ${qtd}.`,
      )
    }
    if (serializado && qtd !== 1) {
      return setErro('Item serializado exige quantidade = 1.')
    }
    if (serializado && !serial.trim()) {
      return setErro('Item serializado exige serial.')
    }
    try {
      await devolver.mutateAsync({
        item_id: itemId,
        tecnico_id: tecnicoId,
        quantidade: qtd,
        serial: serial.trim() || null,
        observacao: observacao.trim() || null,
      })
      onClose()
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao devolver')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto py-4">
      <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-lg space-y-4 mx-4">
        <div>
          <h2 className="text-lg font-semibold">Devolver → Depósito</h2>
          <p className="text-xs text-muted-foreground">
            Sai do estoque do técnico e volta pro depósito (atômico).
          </p>
        </div>

        <div>
          <Label htmlFor="tec">Técnico *</Label>
          <Select
            id="tec"
            value={tecnicoId}
            onChange={(e) => {
              setTecnicoId(e.target.value)
              setItemId('')
              setSerial('')
            }}
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
          <Label htmlFor="item">Item *</Label>
          <Select
            id="item"
            value={itemId}
            onChange={(e) => {
              setItemId(e.target.value)
              setSerial('')
            }}
            disabled={!tecnicoId}
          >
            <option value="">Selecione…</option>
            {itensDoTecnico.map((l) => (
              <option key={l.item_id} value={l.item_id}>
                {l.nome} ({l.sku}) — {l.saldo} em mãos
              </option>
            ))}
          </Select>
          {tecnicoId && itensDoTecnico.length === 0 && (
            <p className="mt-1 text-xs text-amber-700">
              Esse técnico não tem nada em mãos.
            </p>
          )}
        </div>

        <div>
          <Label htmlFor="qtd">Quantidade *</Label>
          <Input
            id="qtd"
            type="number"
            min={1}
            max={saldoTec || undefined}
            value={quantidade}
            onChange={(e) => setQuantidade(e.target.value)}
          />
          {itemSel && (
            <p className="mt-1 text-xs text-muted-foreground">
              Em mãos: <strong>{saldoTec}</strong>
            </p>
          )}
        </div>

        {serializado && (
          <div>
            <Label htmlFor="serial">Serial *</Label>
            {seriaisDoTecItem.length > 0 ? (
              <Select
                id="serial"
                value={serial}
                onChange={(e) => setSerial(e.target.value)}
              >
                <option value="">Selecione um serial…</option>
                {seriaisDoTecItem.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            ) : (
              <Input
                id="serial"
                value={serial}
                onChange={(e) => setSerial(e.target.value)}
                placeholder="Ex: ZTEGC0FE1234"
              />
            )}
          </div>
        )}

        <div>
          <Label htmlFor="obs">Observação (opcional)</Label>
          <Textarea
            id="obs"
            value={observacao}
            onChange={(e) => setObservacao(e.target.value)}
            rows={2}
            placeholder="Ex: técnico saiu de férias"
          />
        </div>

        {erro && <p className="text-sm text-destructive">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={submit} disabled={devolver.isPending}>
            {devolver.isPending ? 'Devolvendo…' : 'Devolver'}
          </Button>
        </div>
      </div>
    </div>
  )
}
