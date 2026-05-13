'use client'
import { useRouter } from 'next/navigation'
import { Download, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { exportClienteUrl, useCliente, useDeleteCliente } from '@/lib/api/queries'

export function ClienteDetail({ id }: { id: string }) {
  const router = useRouter()
  const { data, isLoading, error } = useCliente(id)
  const deleteCliente = useDeleteCliente(id)

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando…</p>
  if (error) {
    return (
      <p className="text-sm text-destructive">
        {error instanceof Error ? error.message : 'Erro ao carregar'}
      </p>
    )
  }
  if (!data) return <p className="text-sm text-destructive">Cliente não encontrado</p>

  async function handleDelete() {
    if (
      !confirm(
        'Excluir este cliente? Esta ação é irreversível e atende ao direito de exclusão (LGPD).',
      )
    )
      return
    await deleteCliente.mutateAsync()
    router.push('/clientes')
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{data.nome}</CardTitle>
            {data.status && <Badge variant="outline">{data.status}</Badge>}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs uppercase text-muted-foreground">WhatsApp</div>
              <p className="mt-1 text-sm">{data.whatsapp}</p>
            </div>
            <div>
              <div className="text-xs uppercase text-muted-foreground">CPF/CNPJ</div>
              <p className="mt-1 text-sm">{data.cpf_cnpj}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs uppercase text-muted-foreground">Plano</div>
              <p className="mt-1 text-sm">{data.plano ?? '—'}</p>
            </div>
            <div>
              <div className="text-xs uppercase text-muted-foreground">Cidade</div>
              <p className="mt-1 text-sm">{data.cidade ?? '—'}</p>
            </div>
          </div>
          {data.endereco && (
            <div>
              <div className="text-xs uppercase text-muted-foreground">Endereço</div>
              <p className="mt-1 text-sm">{data.endereco}</p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs uppercase text-muted-foreground">SGP Provider</div>
              <p className="mt-1 text-sm">{data.sgp_provider ?? '—'}</p>
            </div>
            <div>
              <div className="text-xs uppercase text-muted-foreground">SGP ID</div>
              <p className="mt-1 text-sm">{data.sgp_id ?? '—'}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs uppercase text-muted-foreground">Criado</div>
              <p className="mt-1 text-sm">{new Date(data.created_at).toLocaleString('pt-BR')}</p>
            </div>
            <div>
              <div className="text-xs uppercase text-muted-foreground">Último contato</div>
              <p className="mt-1 text-sm">
                {data.last_seen_at
                  ? new Date(data.last_seen_at).toLocaleString('pt-BR')
                  : '—'}
              </p>
            </div>
          </div>
          {data.retention_until && (
            <div>
              <div className="text-xs uppercase text-muted-foreground">Retenção até (LGPD)</div>
              <p className="mt-1 text-sm">
                {new Date(data.retention_until).toLocaleDateString('pt-BR')}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">LGPD</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <a href={exportClienteUrl(id)} download>
              <Button variant="outline" className="w-full">
                <Download className="h-4 w-4" /> Exportar dados
              </Button>
            </a>
            <Button
              variant="destructive"
              className="w-full"
              onClick={handleDelete}
              disabled={deleteCliente.isPending}
            >
              <Trash2 className="h-4 w-4" /> Excluir (direito de apagamento)
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
