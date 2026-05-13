'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useDeleteLead, useLead, usePatchLead } from '@/lib/api/queries'

const STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  novo: 'default',
  contato: 'secondary',
  convertido: 'secondary',
  perdido: 'destructive',
}

export function LeadDetail({ id }: { id: string }) {
  const router = useRouter()
  const { data, isLoading, error } = useLead(id)
  const patchLead = usePatchLead(id)
  const deleteLead = useDeleteLead(id)

  const [nome, setNome] = useState('')
  const [interesse, setInteresse] = useState('')
  const [notas, setNotas] = useState('')
  const [editMode, setEditMode] = useState(false)

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando…</p>
  if (error) {
    return (
      <p className="text-sm text-destructive">
        {error instanceof Error ? error.message : 'Erro ao carregar'}
      </p>
    )
  }
  if (!data) return <p className="text-sm text-destructive">Lead não encontrado</p>

  function startEdit() {
    if (!data) return
    setNome(data.nome)
    setInteresse(data.interesse ?? '')
    setNotas(data.notas ?? '')
    setEditMode(true)
  }

  async function handleSave() {
    await patchLead.mutateAsync({
      nome: nome || undefined,
      interesse: interesse || null,
      notas: notas || null,
    })
    setEditMode(false)
  }

  async function handleDelete() {
    if (!confirm('Excluir este lead?')) return
    await deleteLead.mutateAsync()
    router.push('/leads')
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{data.nome}</CardTitle>
            <Badge variant={STATUS_VARIANTS[data.status] ?? 'outline'}>{data.status}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {editMode ? (
            <div className="space-y-4">
              <div>
                <Label htmlFor="nome">Nome</Label>
                <Input
                  id="nome"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="interesse">Interesse</Label>
                <Input
                  id="interesse"
                  value={interesse}
                  onChange={(e) => setInteresse(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="notas">Notas</Label>
                <Textarea
                  id="notas"
                  value={notas}
                  onChange={(e) => setNotas(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleSave} disabled={patchLead.isPending}>
                  {patchLead.isPending ? 'Salvando…' : 'Salvar'}
                </Button>
                <Button variant="outline" onClick={() => setEditMode(false)}>
                  Cancelar
                </Button>
              </div>
            </div>
          ) : (
            <>
              <div>
                <div className="text-xs uppercase text-muted-foreground">WhatsApp</div>
                <p className="mt-1 text-sm">{data.whatsapp}</p>
              </div>
              <div>
                <div className="text-xs uppercase text-muted-foreground">Interesse</div>
                <p className="mt-1 text-sm">{data.interesse ?? '—'}</p>
              </div>
              {data.notas && (
                <div>
                  <div className="text-xs uppercase text-muted-foreground">Notas</div>
                  <p className="mt-1 text-sm whitespace-pre-wrap">{data.notas}</p>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs uppercase text-muted-foreground">Criado</div>
                  <p className="mt-1 text-sm">
                    {new Date(data.created_at).toLocaleString('pt-BR')}
                  </p>
                </div>
                <div>
                  <div className="text-xs uppercase text-muted-foreground">Atualizado</div>
                  <p className="mt-1 text-sm">
                    {new Date(data.updated_at).toLocaleString('pt-BR')}
                  </p>
                </div>
              </div>
              <Button variant="outline" onClick={startEdit}>
                Editar
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Mudar status</CardTitle>
          </CardHeader>
          <CardContent>
            <Select
              defaultValue={data.status}
              onChange={(e) => patchLead.mutate({ status: e.target.value })}
              disabled={patchLead.isPending}
            >
              <option value="novo">Novo</option>
              <option value="contato">Em contato</option>
              <option value="convertido">Convertido</option>
              <option value="perdido">Perdido</option>
            </Select>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base text-destructive">Excluir</CardTitle>
          </CardHeader>
          <CardContent>
            <Button
              variant="destructive"
              className="w-full"
              onClick={handleDelete}
              disabled={deleteLead.isPending}
            >
              <Trash2 className="h-4 w-4" /> Excluir Lead
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
