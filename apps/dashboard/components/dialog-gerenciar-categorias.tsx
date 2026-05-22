'use client'
import { useState } from 'react'
import { Pencil, Plus, Trash2, X } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  useCreateCategoria,
  useDeleteCategoria,
  useEstoqueCategorias,
  useUpdateCategoria,
} from '@/lib/api/queries'

interface Props {
  onClose: () => void
}

function slugify(s: string): string {
  return s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
    .slice(0, 40)
}

export function DialogGerenciarCategorias({ onClose }: Props) {
  const { data: cats } = useEstoqueCategorias(false)
  const create = useCreateCategoria()
  const update = useUpdateCategoria()
  const del = useDeleteCategoria()

  const [nome, setNome] = useState('')
  const [slug, setSlug] = useState('')
  const [editId, setEditId] = useState<string | null>(null)
  const [editNome, setEditNome] = useState('')

  async function handleCreate() {
    const finalSlug = slug.trim() || slugify(nome)
    if (!nome.trim() || !finalSlug) return
    try {
      await create.mutateAsync({ slug: finalSlug, nome: nome.trim() })
      setNome('')
      setSlug('')
      toast.success('Categoria criada')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao criar')
    }
  }

  async function handleToggleAtivo(id: string, ativo: boolean) {
    try {
      await update.mutateAsync({ id, body: { ativo: !ativo } })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao atualizar')
    }
  }

  async function handleSaveNome(id: string) {
    if (!editNome.trim()) return
    try {
      await update.mutateAsync({ id, body: { nome: editNome.trim() } })
      setEditId(null)
      setEditNome('')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao salvar')
    }
  }

  async function handleDelete(id: string, nomeCat: string) {
    if (!confirm(`Excluir categoria "${nomeCat}"?`)) return
    try {
      await del.mutateAsync(id)
      toast.success('Categoria removida')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao excluir')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto py-4">
      <div className="w-full max-w-lg rounded-lg border bg-card p-6 shadow-lg space-y-4 mx-4">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold">Categorias de estoque</h2>
            <p className="text-xs text-muted-foreground">
              Categorias inativas não aparecem nos selects de novo item.
            </p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="rounded-md border bg-muted/30 p-3 space-y-2">
          <Label className="text-xs uppercase">Nova categoria</Label>
          <div className="grid gap-2 sm:grid-cols-2">
            <Input
              placeholder="Nome (ex: Fonte 12V)"
              value={nome}
              onChange={(e) => {
                setNome(e.target.value)
                if (!slug) setSlug(slugify(e.target.value))
              }}
            />
            <Input
              placeholder="slug-auto"
              value={slug}
              onChange={(e) => setSlug(slugify(e.target.value))}
            />
          </div>
          <Button
            size="sm"
            onClick={handleCreate}
            disabled={create.isPending || !nome.trim()}
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            Adicionar
          </Button>
        </div>

        <div className="rounded-md border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b text-left text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-3 py-2">Nome</th>
                <th className="px-3 py-2">Slug</th>
                <th className="px-3 py-2">Ativa</th>
                <th className="px-3 py-2 text-right">Ações</th>
              </tr>
            </thead>
            <tbody>
              {(cats ?? []).length === 0 && (
                <tr>
                  <td
                    colSpan={4}
                    className="p-4 text-center text-muted-foreground"
                  >
                    Nenhuma categoria.
                  </td>
                </tr>
              )}
              {(cats ?? []).map((c) => (
                <tr key={c.id} className="border-b last:border-b-0">
                  <td className="px-3 py-2 font-medium">
                    {editId === c.id ? (
                      <Input
                        autoFocus
                        value={editNome}
                        onChange={(e) => setEditNome(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') void handleSaveNome(c.id)
                          if (e.key === 'Escape') {
                            setEditId(null)
                            setEditNome('')
                          }
                        }}
                        onBlur={() => void handleSaveNome(c.id)}
                        className="h-7"
                      />
                    ) : (
                      c.nome
                    )}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                    {c.slug}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={c.ativo}
                        onCheckedChange={() => handleToggleAtivo(c.id, c.ativo)}
                      />
                      <Badge variant={c.ativo ? 'default' : 'outline'}>
                        {c.ativo ? 'Ativa' : 'Inativa'}
                      </Badge>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="inline-flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setEditId(c.id)
                          setEditNome(c.nome)
                        }}
                        title="Renomear"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:text-destructive"
                        onClick={() => void handleDelete(c.id, c.nome)}
                        title="Excluir"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex justify-end">
          <Button variant="outline" onClick={onClose}>
            Fechar
          </Button>
        </div>
      </div>
    </div>
  )
}
