'use client'
import { useRouter } from 'next/navigation'
import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  useDeleteManutencao,
  useManutencao,
} from '@/lib/api/queries'

export function ManutencaoDetail({ id }: { id: string }) {
  const { data, isLoading, error } = useManutencao(id)
  const del = useDeleteManutencao(id)
  const router = useRouter()

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando…</p>
  if (error) return <p className="text-sm text-destructive">{error instanceof Error ? error.message : 'Erro'}</p>
  if (!data) return null

  async function handleDelete() {
    if (!confirm('Excluir esta manutenção?')) return
    await del.mutateAsync()
    router.push('/manutencoes')
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{data.titulo}</CardTitle>
          <Button variant="destructive" size="sm" onClick={handleDelete} disabled={del.isPending}>
            <Trash2 className="h-4 w-4" /> Excluir
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {data.descricao && (
          <div>
            <div className="text-xs uppercase text-muted-foreground">Descrição</div>
            <p className="mt-1 whitespace-pre-wrap">{data.descricao}</p>
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-xs uppercase text-muted-foreground">Início</div>
            <p className="mt-1">{new Date(data.inicio_at).toLocaleString('pt-BR')}</p>
          </div>
          <div>
            <div className="text-xs uppercase text-muted-foreground">Fim</div>
            <p className="mt-1">{new Date(data.fim_at).toLocaleString('pt-BR')}</p>
          </div>
        </div>
        <div>
          <div className="text-xs uppercase text-muted-foreground">Cidades</div>
          <p className="mt-1">{data.cidades?.join(', ') ?? 'todas'}</p>
        </div>
        <div>
          <div className="text-xs uppercase text-muted-foreground">Notificar clientes</div>
          <p className="mt-1">{data.notificar ? 'Sim' : 'Não'}</p>
        </div>
      </CardContent>
    </Card>
  )
}
