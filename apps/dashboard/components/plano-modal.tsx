'use client'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useCreatePlano, useUpdatePlano } from '@/lib/api/queries'
import type { PlanoIn, PlanoOut } from '@/lib/api/types'

interface PlanoModalProps {
  plano?: PlanoOut | null
  onClose: () => void
}

const EMPTY: PlanoIn = {
  nome: '',
  preco: 0,
  velocidade: '',
  extras: [],
  descricao: '',
  ativo: true,
  destaque: false,
}

export function PlanoModal({ plano, onClose }: PlanoModalProps) {
  const [form, setForm] = useState<PlanoIn>(plano ? { ...plano } : EMPTY)
  const [extrasInput, setExtrasInput] = useState('')
  const createPlano = useCreatePlano()
  const updatePlano = useUpdatePlano(plano?.index ?? -1)

  useEffect(() => {
    setForm(plano ? { ...plano } : EMPTY)
    setExtrasInput('')
  }, [plano])

  const isEditing = plano !== null && plano !== undefined
  const mutation = isEditing ? updatePlano : createPlano
  const isPending = mutation.isPending

  function setField<K extends keyof PlanoIn>(key: K, value: PlanoIn[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  function addExtra() {
    const trimmed = extrasInput.trim()
    if (!trimmed) return
    setField('extras', [...form.extras, trimmed])
    setExtrasInput('')
  }

  function removeExtra(i: number) {
    setField('extras', form.extras.filter((_, idx) => idx !== i))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await mutation.mutateAsync(form)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold">
          {isEditing ? 'Editar Plano' : 'Novo Plano'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="nome">Nome</Label>
              <Input
                id="nome"
                value={form.nome}
                onChange={(e) => setField('nome', e.target.value)}
                required
              />
            </div>
            <div>
              <Label htmlFor="preco">Preço (R$)</Label>
              <Input
                id="preco"
                type="number"
                min={0.01}
                step={0.01}
                value={form.preco}
                onChange={(e) => setField('preco', Number(e.target.value))}
                required
              />
            </div>
          </div>
          <div>
            <Label htmlFor="velocidade">Velocidade</Label>
            <Input
              id="velocidade"
              placeholder="ex: 55MB"
              value={form.velocidade}
              onChange={(e) => setField('velocidade', e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="descricao">Descrição (usada pelo bot)</Label>
            <Textarea
              id="descricao"
              rows={2}
              value={form.descricao}
              onChange={(e) => setField('descricao', e.target.value)}
            />
          </div>
          <div>
            <Label>Extras</Label>
            <div className="mt-1 flex gap-2">
              <Input
                placeholder="ex: IPTV gratis"
                value={extrasInput}
                onChange={(e) => setExtrasInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addExtra() } }}
              />
              <Button type="button" variant="outline" onClick={addExtra}>
                +
              </Button>
            </div>
            {form.extras.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {form.extras.map((ex, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800"
                  >
                    {ex}
                    <button
                      type="button"
                      onClick={() => removeExtra(i)}
                      className="ml-0.5 text-blue-600 hover:text-blue-900"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="flex gap-4">
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.ativo}
                onChange={(e) => setField('ativo', e.target.checked)}
              />
              Ativo
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.destaque}
                onChange={(e) => setField('destaque', e.target.checked)}
              />
              Destaque (recomendado pelo bot)
            </label>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Salvando…' : isEditing ? 'Salvar' : 'Criar'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
