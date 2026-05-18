'use client'
import { useState } from 'react'
import { ArrowDownLeft, ArrowUpRight, Package } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  useCreateMyMovimento,
  useEstoqueCatalogo,
  useMyEstoqueMovimentos,
  useMyEstoqueSaldo,
} from '@/lib/api/queries'
import type { EstoqueItemInfo } from '@/lib/api/types'

interface Props {
  osId: string
}

type Modo = 'saida' | 'recolhido' | null

export function OsEstoquePanel({ osId }: Props) {
  const { data: saldo } = useMyEstoqueSaldo()
  const { data: catalogo } = useEstoqueCatalogo()
  const { data: movsDaOs } = useMyEstoqueMovimentos(osId)
  const create = useCreateMyMovimento()

  const [modo, setModo] = useState<Modo>(null)
  const [itemId, setItemId] = useState('')
  const [quantidade, setQuantidade] = useState('1')
  const [serial, setSerial] = useState('')
  const [observacao, setObservacao] = useState('')
  const [error, setError] = useState<string | null>(null)

  // Pra `saida` mostramos só itens com saldo > 0 (técnico só usa o que tem).
  // Pra `recolhido` mostramos catálogo completo (qualquer item ativo).
  const itensComSaldo = (saldo?.linhas ?? []).filter((l) => l.saldo > 0)
  const itensRecolhiveis: EstoqueItemInfo[] = catalogo ?? []

  const itemSelecionado =
    modo === 'saida'
      ? itensComSaldo.find((l) => l.item_id === itemId)
      : itensRecolhiveis.find((i) => i.id === itemId)

  const serializado =
    modo === 'saida'
      ? (itensComSaldo.find((l) => l.item_id === itemId)?.serializado ?? false)
      : (itensRecolhiveis.find((i) => i.id === itemId)?.serializado ?? false)

  function reset() {
    setModo(null)
    setItemId('')
    setQuantidade('1')
    setSerial('')
    setObservacao('')
    setError(null)
  }

  async function handleSubmit() {
    if (!modo || !itemId) {
      setError('Selecione o item')
      return
    }
    const qty = parseInt(quantidade, 10)
    if (!qty || qty < 1) {
      setError('Quantidade inválida')
      return
    }
    if (serializado && !serial.trim()) {
      setError('Serial obrigatório para este item')
      return
    }
    setError(null)
    try {
      await create.mutateAsync({
        item_id: itemId,
        tipo: modo,
        quantidade: serializado ? 1 : qty,
        serial: serial.trim() || null,
        ordem_servico_id: osId,
        observacao: observacao.trim() || null,
      })
      reset()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro ao registrar movimento')
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Package className="h-4 w-4" />
          Equipamentos desta OS
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Movimentos ja registrados nesta OS */}
        {movsDaOs && movsDaOs.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs uppercase text-muted-foreground">Já registrados</p>
            {movsDaOs.map((m) => {
              const it =
                catalogo?.find((i) => i.id === m.item_id) ??
                saldo?.linhas.find((l) => l.item_id === m.item_id)
              const nome = it
                ? 'nome' in it
                  ? it.nome
                  : (it as { nome?: string }).nome
                : 'Item'
              return (
                <div
                  key={m.id}
                  className="flex items-center justify-between rounded-md border bg-muted/30 p-2 text-sm"
                >
                  <div className="flex items-center gap-2">
                    {m.tipo === 'saida' ? (
                      <ArrowUpRight className="h-4 w-4 text-red-600" />
                    ) : (
                      <ArrowDownLeft className="h-4 w-4 text-green-600" />
                    )}
                    <div>
                      <p className="font-medium">{nome}</p>
                      <p className="text-xs text-muted-foreground">
                        {m.tipo === 'saida' ? 'Instalado' : 'Recolhido'}
                        {m.serial ? ` · ${m.serial}` : ''}
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline">{m.quantidade}x</Badge>
                </div>
              )
            })}
          </div>
        )}

        {/* Botoes pra abrir formulario */}
        {modo === null && (
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="outline"
              onClick={() => setModo('saida')}
              className="h-auto flex-col gap-1 py-3"
              disabled={itensComSaldo.length === 0}
            >
              <ArrowUpRight className="h-5 w-5 text-red-600" />
              <span className="text-xs">Instalei equipamento</span>
            </Button>
            <Button
              variant="outline"
              onClick={() => setModo('recolhido')}
              className="h-auto flex-col gap-1 py-3"
            >
              <ArrowDownLeft className="h-5 w-5 text-green-600" />
              <span className="text-xs">Recolhi equipamento</span>
            </Button>
          </div>
        )}

        {itensComSaldo.length === 0 && modo === null && (
          <p className="text-xs text-muted-foreground">
            Você não tem itens em estoque pra instalar. Para registrar
            recolhimento, use o botão acima.
          </p>
        )}

        {/* Formulario */}
        {modo !== null && (
          <div className="space-y-3 rounded-md border bg-card p-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold">
                {modo === 'saida' ? 'Instalar do meu estoque' : 'Recolher do cliente'}
              </p>
              <Button variant="ghost" size="sm" onClick={reset}>
                Cancelar
              </Button>
            </div>

            <div>
              <Label htmlFor="item">Item *</Label>
              <select
                id="item"
                value={itemId}
                onChange={(e) => setItemId(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">Selecione…</option>
                {modo === 'saida'
                  ? itensComSaldo.map((l) => (
                      <option key={l.item_id} value={l.item_id}>
                        {l.nome} ({l.saldo} disp.)
                      </option>
                    ))
                  : itensRecolhiveis.map((it) => (
                      <option key={it.id} value={it.id}>
                        {it.nome}
                      </option>
                    ))}
              </select>
              {modo === 'saida' && itensComSaldo.length === 0 && (
                <p className="mt-1 text-xs text-destructive">
                  Sem itens em estoque.
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label htmlFor="qty">Quantidade</Label>
                <Input
                  id="qty"
                  type="number"
                  min={1}
                  step={1}
                  value={quantidade}
                  disabled={serializado}
                  onChange={(e) => setQuantidade(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="serial">
                  Serial {serializado ? '*' : '(opcional)'}
                </Label>
                <Input
                  id="serial"
                  placeholder={serializado ? 'Obrigatório' : '—'}
                  value={serial}
                  onChange={(e) => setSerial(e.target.value)}
                />
              </div>
            </div>

            <div>
              <Label htmlFor="obs">Observação</Label>
              <Input
                id="obs"
                placeholder="ex: ONU velha defeituosa"
                value={observacao}
                onChange={(e) => setObservacao(e.target.value)}
              />
            </div>

            {error && (
              <p className="text-xs text-destructive">{error}</p>
            )}

            <Button
              onClick={handleSubmit}
              disabled={create.isPending}
              className="w-full"
            >
              {create.isPending ? 'Salvando…' : 'Registrar'}
            </Button>
          </div>
        )}

        {/* Saldo resumido */}
        {saldo && saldo.linhas.length > 0 && modo === null && (
          <details className="text-xs">
            <summary className="cursor-pointer text-muted-foreground">
              Ver meu estoque atual
            </summary>
            <ul className="mt-1 space-y-0.5">
              {saldo.linhas
                .filter((l) => l.saldo !== 0)
                .map((l) => (
                  <li key={l.item_id} className="flex justify-between">
                    <span>{l.nome}</span>
                    <span className="font-medium">{l.saldo}</span>
                  </li>
                ))}
            </ul>
          </details>
        )}
      </CardContent>
    </Card>
  )
}
