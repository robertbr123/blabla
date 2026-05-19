'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { useUpdateEstoqueItem } from '@/lib/api/queries'
import type { EstoqueItem } from '@/lib/api/types'

interface Props {
  item: EstoqueItem
  onClose: () => void
}

export function DialogEditarItemEstoque({ item, onClose }: Props) {
  const update = useUpdateEstoqueItem()
  const [nome, setNome] = useState(item.nome)
  const [categoria, setCategoria] = useState<EstoqueItem['categoria']>(
    item.categoria as EstoqueItem['categoria'],
  )
  const [ativo, setAtivo] = useState(item.ativo)
  const [erro, setErro] = useState<string | null>(null)

  async function submit() {
    setErro(null)
    try {
      await update.mutateAsync({
        id: item.id,
        body: { nome: nome.trim(), categoria, ativo },
      })
      onClose()
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao atualizar')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto py-4">
      <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-lg space-y-4 mx-4">
        <div>
          <h2 className="text-lg font-semibold">Editar item</h2>
          <p className="text-xs text-muted-foreground">
            SKU não pode ser alterado (referenciado em movimentos). Pra trocar
            SKU, crie um item novo e desative este.
          </p>
        </div>

        <div>
          <Label>SKU</Label>
          <Input value={item.sku} disabled />
        </div>

        <div>
          <Label htmlFor="nome">Nome *</Label>
          <Input
            id="nome"
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            autoFocus
          />
        </div>

        <div>
          <Label htmlFor="categoria">Categoria *</Label>
          <Select
            id="categoria"
            value={categoria}
            onChange={(e) =>
              setCategoria(e.target.value as EstoqueItem['categoria'])
            }
          >
            <option value="onu">ONU</option>
            <option value="roteador">Roteador</option>
            <option value="cabo">Cabo</option>
            <option value="conector">Conector</option>
            <option value="outro">Outro</option>
          </Select>
        </div>

        <div className="flex items-center justify-between rounded-md border p-3">
          <div>
            <p className="text-sm font-medium">Ativo?</p>
            <p className="text-xs text-muted-foreground">
              Itens inativos não aparecem em movimentos novos.
            </p>
          </div>
          <Switch checked={ativo} onCheckedChange={setAtivo} />
        </div>

        {erro && <p className="text-sm text-destructive">{erro}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={submit} disabled={update.isPending || !nome.trim()}>
            {update.isPending ? 'Salvando…' : 'Salvar'}
          </Button>
        </div>
      </div>
    </div>
  )
}
