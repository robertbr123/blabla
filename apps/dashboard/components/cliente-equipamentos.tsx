'use client'
import { useState } from 'react'
import { Package, PackageX } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useClienteEquipamentos } from '@/lib/api/queries'

export function ClienteEquipamentos({ clienteId }: { clienteId: string }) {
  const [ativosOnly, setAtivosOnly] = useState(false)
  const { data, isLoading, error } = useClienteEquipamentos(clienteId, ativosOnly)

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Package className="h-4 w-4" /> Equipamentos
          </CardTitle>
          <label className="flex items-center gap-1 text-xs">
            <input
              type="checkbox"
              checked={ativosOnly}
              onChange={(e) => setAtivosOnly(e.target.checked)}
              className="h-3 w-3"
            />
            Só ativos
          </label>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <p className="text-sm text-muted-foreground">Carregando…</p>
        )}
        {error && (
          <p className="text-sm text-destructive">
            {error instanceof Error ? error.message : 'Erro ao carregar'}
          </p>
        )}
        {data && data.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Nenhum equipamento registrado pra este cliente.
          </p>
        )}
        {data && data.length > 0 && (
          <ul className="space-y-3">
            {data.map((eq) => (
              <li
                key={eq.id}
                className={
                  eq.removido_em
                    ? 'rounded-md border bg-muted/30 p-3 opacity-70'
                    : 'rounded-md border bg-card p-3'
                }
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate font-medium">{eq.item_nome}</p>
                      {eq.removido_em ? (
                        <Badge variant="outline" className="gap-1">
                          <PackageX className="h-3 w-3" /> Removido
                        </Badge>
                      ) : (
                        <Badge variant="default">Ativo</Badge>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      Serial: <span className="font-mono">{eq.serial}</span>
                      {' · '}
                      <span className="capitalize">{eq.item_categoria}</span>
                    </p>
                  </div>
                </div>

                <div className="mt-2 grid gap-1 text-xs text-muted-foreground sm:grid-cols-2">
                  <div>
                    <span className="font-medium">Instalado:</span>{' '}
                    {new Date(eq.instalado_em).toLocaleString('pt-BR')}
                  </div>
                  {eq.instalado_por_tecnico_nome && (
                    <div>
                      <span className="font-medium">Técnico:</span>{' '}
                      {eq.instalado_por_tecnico_nome}
                    </div>
                  )}
                  {eq.instalado_em_os_codigo && (
                    <div>
                      <span className="font-medium">OS instalação:</span>{' '}
                      <span className="font-mono">{eq.instalado_em_os_codigo}</span>
                    </div>
                  )}
                  {eq.removido_em && (
                    <div>
                      <span className="font-medium">Removido:</span>{' '}
                      {new Date(eq.removido_em).toLocaleString('pt-BR')}
                    </div>
                  )}
                  {eq.removido_em_os_codigo && (
                    <div>
                      <span className="font-medium">OS retirada:</span>{' '}
                      <span className="font-mono">{eq.removido_em_os_codigo}</span>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
