'use client'

import { useState } from 'react'
import { Award, CheckCircle2, Clock, XCircle, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import {
  useFidelidadeResgates,
  usePatchFidelidadeResgate,
} from '@/lib/api/queries'
import type {
  AdminFidelidadeResgate,
  FidelidadeResgateStatus,
} from '@/lib/api/types'

const STATUS_LABEL: Record<FidelidadeResgateStatus, string> = {
  pendente: 'Aguardando aprovação',
  aprovado: 'Aprovado',
  aplicado: 'Aplicado',
  rejeitado: 'Rejeitado',
}

const STATUS_STYLE: Record<FidelidadeResgateStatus, string> = {
  pendente: 'bg-amber-50 text-amber-700 border border-amber-200',
  aprovado: 'bg-blue-50 text-blue-700 border border-blue-200',
  aplicado: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  rejeitado: 'bg-zinc-100 text-zinc-600 border border-zinc-200',
}

const STATUS_ICON: Record<FidelidadeResgateStatus, React.ComponentType<{ className?: string }>> = {
  pendente: Clock,
  aprovado: CheckCircle2,
  aplicado: Sparkles,
  rejeitado: XCircle,
}

export default function FidelidadePage() {
  const { data: resgates, isLoading } = useFidelidadeResgates()
  const [filtro, setFiltro] = useState<FidelidadeResgateStatus | 'all'>('pendente')

  const list = (resgates ?? []).filter(
    (r) => filtro === 'all' || r.status === filtro,
  )

  const counts: Record<FidelidadeResgateStatus, number> = {
    pendente: 0,
    aprovado: 0,
    aplicado: 0,
    rejeitado: 0,
  }
  for (const r of resgates ?? []) counts[r.status]++

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-amber-50 text-amber-600">
          <Award className="size-5" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Fidelidade — Resgates</h1>
          <p className="text-sm text-muted-foreground">
            Aprove resgates de pontos solicitados pelo app cliente.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {(['pendente', 'aprovado', 'aplicado', 'rejeitado', 'all'] as const).map((k) => (
          <Button
            key={k}
            size="sm"
            variant={filtro === k ? 'default' : 'outline'}
            onClick={() => setFiltro(k)}
          >
            {k === 'all' ? 'Todos' : STATUS_LABEL[k]}
            <span className="ml-2 text-xs opacity-70">
              {k === 'all' ? (resgates?.length ?? 0) : counts[k]}
            </span>
          </Button>
        ))}
      </div>

      {isLoading && (
        <div className="text-sm text-muted-foreground">Carregando…</div>
      )}

      {!isLoading && list.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <Award className="mx-auto mb-3 size-10 text-muted-foreground" />
            <p className="font-semibold">Nenhum resgate {filtro === 'all' ? '' : STATUS_LABEL[filtro as FidelidadeResgateStatus].toLowerCase()}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Quando um cliente trocar pontos, ele aparece aqui.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {list.map((r) => (
          <ResgateRow key={r.id} resgate={r} />
        ))}
      </div>
    </div>
  )
}

function ResgateRow({ resgate }: { resgate: AdminFidelidadeResgate }) {
  const patch = usePatchFidelidadeResgate(resgate.id)
  const [obs, setObs] = useState(resgate.obs_admin ?? '')
  const [open, setOpen] = useState(false)
  const Icon = STATUS_ICON[resgate.status]

  async function setStatus(novo: FidelidadeResgateStatus) {
    await patch.mutateAsync({ status: novo, obs_admin: obs.trim() || null })
    setOpen(false)
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3 pb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">
              {resgate.recompensa_label}
            </CardTitle>
            <Badge className={STATUS_STYLE[resgate.status]} variant="outline">
              <Icon className="mr-1 size-3" />
              {STATUS_LABEL[resgate.status]}
            </Badge>
          </div>
          <div className="mt-1 flex flex-wrap gap-3 text-xs text-muted-foreground">
            <span>
              <strong className="text-foreground">{resgate.pontos_gastos}</strong> pts
            </span>
            <span>Slug: {resgate.recompensa_slug}</span>
            <span>
              {new Date(resgate.criado_em).toLocaleString('pt-BR')}
            </span>
            <span className="font-mono text-[10px]">
              user: {resgate.cliente_app_user_id.slice(0, 8)}…
            </span>
          </div>
          {resgate.obs_admin && !open && (
            <div className="mt-2 rounded border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs text-zinc-700">
              <strong>Obs:</strong> {resgate.obs_admin}
            </div>
          )}
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setOpen((o) => !o)}
        >
          {open ? 'Fechar' : 'Agir'}
        </Button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-3 border-t pt-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Observação (opcional, visível no histórico do cliente)
            </label>
            <Textarea
              value={obs}
              onChange={(e) => setObs(e.target.value)}
              placeholder="Ex: aplicado na fatura X — desconto de R$5,50"
              rows={2}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {resgate.status !== 'aprovado' && (
              <Button
                size="sm"
                variant="default"
                onClick={() => setStatus('aprovado')}
                disabled={patch.isPending}
              >
                <CheckCircle2 className="mr-1 size-4" /> Aprovar
              </Button>
            )}
            {resgate.status !== 'aplicado' && (
              <Button
                size="sm"
                variant="default"
                onClick={() => setStatus('aplicado')}
                disabled={patch.isPending}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                <Sparkles className="mr-1 size-4" /> Marcar como aplicado
              </Button>
            )}
            {resgate.status !== 'rejeitado' && (
              <Button
                size="sm"
                variant="destructive"
                onClick={() => setStatus('rejeitado')}
                disabled={patch.isPending}
              >
                <XCircle className="mr-1 size-4" /> Rejeitar
              </Button>
            )}
            {resgate.status !== 'pendente' && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setStatus('pendente')}
                disabled={patch.isPending}
              >
                <Clock className="mr-1 size-4" /> Voltar pra pendente
              </Button>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            <strong>Fluxo sugerido:</strong> aprovar → aplicar desconto no SGP manualmente
            → marcar como aplicado. V2 vai integrar SGP automático.
          </p>
        </CardContent>
      )}
    </Card>
  )
}
