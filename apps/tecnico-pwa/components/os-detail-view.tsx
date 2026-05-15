'use client'
import { Calendar, MapPin, Wifi } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import type { OsOut } from '@/lib/api/types'

const STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  pendente: 'destructive',
  em_andamento: 'default',
  concluida: 'secondary',
  cancelada: 'outline',
}

export function OsDetailView({ os }: { os: OsOut }) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex items-center justify-between">
          <span className="font-mono font-semibold">{os.codigo}</span>
          <Badge variant={STATUS_VARIANTS[os.status] ?? 'outline'}>{os.status}</Badge>
        </div>

        {os.plano && (
          <div>
            <div className="text-xs uppercase text-muted-foreground">Plano</div>
            <p className="mt-1 text-sm font-medium">{os.plano}</p>
          </div>
        )}

        <div>
          <div className="text-xs uppercase text-muted-foreground">Problema</div>
          <p className="mt-1 text-sm whitespace-pre-wrap">{os.problema}</p>
        </div>

        <div>
          <div className="text-xs uppercase text-muted-foreground">Endereço</div>
          <p className="mt-1 flex items-start gap-1 text-sm">
            <MapPin className="h-4 w-4 shrink-0 mt-0.5 text-muted-foreground" />
            {os.endereco}
          </p>
        </div>

        {(os.pppoe_login || os.pppoe_senha) && (
          <div>
            <div className="text-xs uppercase text-muted-foreground flex items-center gap-1">
              <Wifi className="h-3 w-3" /> PPPoE
            </div>
            <div className="mt-1 space-y-0.5 text-sm font-mono">
              {os.pppoe_login && <p>Login: {os.pppoe_login}</p>}
              {os.pppoe_senha && <p>Senha: {os.pppoe_senha}</p>}
            </div>
          </div>
        )}

        {os.agendamento_at && (
          <div>
            <div className="text-xs uppercase text-muted-foreground">Agendamento</div>
            <p className="mt-1 flex items-center gap-1 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              {new Date(os.agendamento_at).toLocaleString('pt-BR')}
            </p>
          </div>
        )}

        {os.relatorio && (
          <div>
            <div className="text-xs uppercase text-muted-foreground">Relatório do técnico</div>
            <p className="mt-1 text-sm whitespace-pre-wrap">{os.relatorio}</p>
          </div>
        )}

        {os.houve_visita !== null && os.houve_visita !== undefined && (
          <div>
            <div className="text-xs uppercase text-muted-foreground">Houve visita</div>
            <p className="mt-1 text-sm">{os.houve_visita ? 'Sim' : 'Não'}</p>
          </div>
        )}

        {os.materiais && (
          <div>
            <div className="text-xs uppercase text-muted-foreground">Materiais / Gastos</div>
            <p className="mt-1 text-sm whitespace-pre-wrap">{os.materiais}</p>
          </div>
        )}

        {os.csat !== null && (
          <div>
            <div className="text-xs uppercase text-muted-foreground">CSAT</div>
            <p className="mt-1 text-sm">{os.csat}/5</p>
          </div>
        )}

        {os.comentario_cliente && (
          <div>
            <div className="text-xs uppercase text-muted-foreground">Comentário do cliente</div>
            <p className="mt-1 text-sm whitespace-pre-wrap">{os.comentario_cliente}</p>
          </div>
        )}

        {os.fotos && os.fotos.length > 0 && (
          <div>
            <div className="text-xs uppercase text-muted-foreground">Fotos ({os.fotos.length})</div>
            <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
              {os.fotos.map((f, i) => (
                <li key={i} className="truncate">
                  {new Date(f.ts).toLocaleString('pt-BR')}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
