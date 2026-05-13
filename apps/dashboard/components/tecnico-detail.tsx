'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Trash2, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  useAddArea,
  useDeleteTecnico,
  usePatchTecnico,
  useRemoveArea,
  useTecnico,
} from '@/lib/api/queries'

export function TecnicoDetail({ id }: { id: string }) {
  const router = useRouter()
  const { data, isLoading, error } = useTecnico(id)
  const patchTecnico = usePatchTecnico(id)
  const deleteTecnico = useDeleteTecnico(id)
  const addArea = useAddArea(id)
  const removeArea = useRemoveArea(id)

  const [editMode, setEditMode] = useState(false)
  const [nome, setNome] = useState('')
  const [whatsapp, setWhatsapp] = useState('')

  const [areaCidade, setAreaCidade] = useState('')
  const [areaRua, setAreaRua] = useState('')
  const [areaPrioridade, setAreaPrioridade] = useState('1')

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando…</p>
  if (error) {
    return (
      <p className="text-sm text-destructive">
        {error instanceof Error ? error.message : 'Erro ao carregar'}
      </p>
    )
  }
  if (!data) return <p className="text-sm text-destructive">Técnico não encontrado</p>

  function startEdit() {
    if (!data) return
    setNome(data.nome)
    setWhatsapp(data.whatsapp ?? '')
    setEditMode(true)
  }

  async function handleSave() {
    await patchTecnico.mutateAsync({
      nome: nome || undefined,
      whatsapp: whatsapp || null,
    })
    setEditMode(false)
  }

  async function handleToggleAtivo() {
    if (!data) return
    await patchTecnico.mutateAsync({ ativo: !data.ativo })
  }

  async function handleDelete() {
    if (!confirm('Excluir este técnico?')) return
    await deleteTecnico.mutateAsync()
    router.push('/tecnicos')
  }

  async function handleAddArea() {
    if (!areaCidade || !areaRua) return
    await addArea.mutateAsync({
      cidade: areaCidade,
      rua: areaRua,
      prioridade: Number(areaPrioridade) || 1,
    })
    setAreaCidade('')
    setAreaRua('')
    setAreaPrioridade('1')
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{data.nome}</CardTitle>
            <Badge variant={data.ativo ? 'default' : 'outline'}>
              {data.ativo ? 'Ativo' : 'Inativo'}
            </Badge>
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
                <Label htmlFor="whatsapp">WhatsApp</Label>
                <Input
                  id="whatsapp"
                  value={whatsapp}
                  onChange={(e) => setWhatsapp(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleSave} disabled={patchTecnico.isPending}>
                  {patchTecnico.isPending ? 'Salvando…' : 'Salvar'}
                </Button>
                <Button variant="outline" onClick={() => setEditMode(false)}>
                  Cancelar
                </Button>
              </div>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs uppercase text-muted-foreground">WhatsApp</div>
                  <p className="mt-1 text-sm">{data.whatsapp ?? '—'}</p>
                </div>
                <div>
                  <div className="text-xs uppercase text-muted-foreground">User ID</div>
                  <p className="mt-1 text-sm font-mono text-xs">{data.user_id ?? '—'}</p>
                </div>
              </div>
              {data.gps_lat !== null && data.gps_lng !== null && (
                <div>
                  <div className="text-xs uppercase text-muted-foreground">GPS</div>
                  <p className="mt-1 text-sm">
                    {data.gps_lat.toFixed(6)}, {data.gps_lng.toFixed(6)}
                    {data.gps_ts && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        ({new Date(data.gps_ts).toLocaleString('pt-BR')})
                      </span>
                    )}
                  </p>
                </div>
              )}
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
            <CardTitle className="text-base">Áreas de atuação</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.areas.length === 0 && (
              <p className="text-xs text-muted-foreground">Nenhuma área cadastrada</p>
            )}
            {data.areas.map((a) => (
              <div
                key={`${a.cidade}|${a.rua}`}
                className="flex items-center justify-between rounded border px-3 py-2 text-sm"
              >
                <div>
                  <span className="font-medium">{a.cidade}</span>
                  <span className="mx-1 text-muted-foreground">—</span>
                  <span>{a.rua}</span>
                  <span className="ml-2 text-xs text-muted-foreground">p{a.prioridade}</span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => removeArea.mutate({ cidade: a.cidade, rua: a.rua })}
                  disabled={removeArea.isPending}
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ))}

            <div className="space-y-2 pt-2">
              <p className="text-xs font-medium uppercase text-muted-foreground">Adicionar área</p>
              <Input
                placeholder="Cidade"
                value={areaCidade}
                onChange={(e) => setAreaCidade(e.target.value)}
                className="text-sm"
              />
              <Input
                placeholder="Rua"
                value={areaRua}
                onChange={(e) => setAreaRua(e.target.value)}
                className="text-sm"
              />
              <Input
                placeholder="Prioridade (1)"
                type="number"
                min={1}
                value={areaPrioridade}
                onChange={(e) => setAreaPrioridade(e.target.value)}
                className="text-sm"
              />
              <Button
                className="w-full"
                onClick={handleAddArea}
                disabled={addArea.isPending || !areaCidade || !areaRua}
              >
                {addArea.isPending ? 'Adicionando…' : 'Adicionar'}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ações</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button
              variant="outline"
              className="w-full"
              onClick={handleToggleAtivo}
              disabled={patchTecnico.isPending}
            >
              {data.ativo ? 'Desativar' : 'Ativar'}
            </Button>
            <Button
              variant="destructive"
              className="w-full"
              onClick={handleDelete}
              disabled={deleteTecnico.isPending}
            >
              <Trash2 className="h-4 w-4" /> Excluir técnico
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
