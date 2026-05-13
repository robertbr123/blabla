'use client'
import { useRef, useState } from 'react'
import { CheckCircle2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  useConcluirOs,
  useOs,
  usePatchOs,
  useUploadFoto,
} from '@/lib/api/queries'

export function OsDetail({ id }: { id: string }) {
  const { data, isLoading, error } = useOs(id)
  const patchOs = usePatchOs(id)
  const concluirOs = useConcluirOs(id)
  const uploadFoto = useUploadFoto(id)
  const fileRef = useRef<HTMLInputElement>(null)
  const [csat, setCsat] = useState('')
  const [comentario, setComentario] = useState('')

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando…</p>
  if (error) {
    return (
      <p className="text-sm text-destructive">
        {error instanceof Error ? error.message : 'Erro ao carregar'}
      </p>
    )
  }
  if (!data) return <p className="text-sm text-destructive">OS não encontrada</p>

  async function handleConcluir() {
    await concluirOs.mutateAsync({
      csat: csat ? Number(csat) : undefined,
      comentario: comentario || undefined,
    })
    setCsat('')
    setComentario('')
  }

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    await uploadFoto.mutateAsync(file)
    if (fileRef.current) fileRef.current.value = ''
  }

  const isConcluida = data.status === 'concluida'

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{data.codigo}</CardTitle>
            <Badge variant={isConcluida ? 'secondary' : 'default'}>{data.status}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <div className="text-xs uppercase text-muted-foreground">Problema</div>
            <p className="mt-1 text-sm whitespace-pre-wrap">{data.problema}</p>
          </div>
          <div>
            <div className="text-xs uppercase text-muted-foreground">Endereço</div>
            <p className="mt-1 text-sm">{data.endereco}</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs uppercase text-muted-foreground">Criada em</div>
              <p className="mt-1 text-sm">
                {new Date(data.criada_em).toLocaleString('pt-BR')}
              </p>
            </div>
            <div>
              <div className="text-xs uppercase text-muted-foreground">Concluída em</div>
              <p className="mt-1 text-sm">
                {data.concluida_em
                  ? new Date(data.concluida_em).toLocaleString('pt-BR')
                  : '—'}
              </p>
            </div>
          </div>
          {data.csat !== null && (
            <div>
              <div className="text-xs uppercase text-muted-foreground">CSAT</div>
              <p className="mt-1 text-sm">{data.csat}/5</p>
            </div>
          )}
          {data.comentario_cliente && (
            <div>
              <div className="text-xs uppercase text-muted-foreground">Comentário do cliente</div>
              <p className="mt-1 text-sm whitespace-pre-wrap">{data.comentario_cliente}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="space-y-4">
        {!isConcluida && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Mudar status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Select
                defaultValue={data.status}
                onChange={(e) => patchOs.mutate({ status: e.target.value })}
                disabled={patchOs.isPending}
              >
                <option value="pendente">Pendente</option>
                <option value="em_andamento">Em andamento</option>
                <option value="cancelada">Cancelada</option>
              </Select>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Fotos ({data.fotos?.length ?? 0})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              ref={fileRef}
              type="file"
              accept="image/*"
              onChange={handleFile}
              disabled={uploadFoto.isPending}
            />
            {uploadFoto.isPending && (
              <p className="text-xs text-muted-foreground">Enviando…</p>
            )}
            {data.fotos && data.fotos.length > 0 && (
              <ul className="space-y-1 text-xs text-muted-foreground">
                {data.fotos.map((f, i) => (
                  <li key={i} className="truncate">
                    {f.url.split('/').pop()} —{' '}
                    {new Date(f.ts).toLocaleString('pt-BR')}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {!isConcluida && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Concluir OS</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label htmlFor="csat">CSAT (1-5)</Label>
                <Input
                  id="csat"
                  type="number"
                  min={1}
                  max={5}
                  value={csat}
                  onChange={(e) => setCsat(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="comentario">Comentário do cliente</Label>
                <Textarea
                  id="comentario"
                  value={comentario}
                  onChange={(e) => setComentario(e.target.value)}
                  className="mt-1"
                />
              </div>
              <Button
                className="w-full"
                onClick={handleConcluir}
                disabled={concluirOs.isPending}
              >
                <CheckCircle2 className="h-4 w-4" /> Concluir
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
