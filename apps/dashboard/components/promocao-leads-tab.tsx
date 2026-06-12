'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  usePatchPromocaoLead,
  usePromocaoLeads,
  usePromocoesAdmin,
} from '@/lib/api/queries'
import type { PromocaoLeadAdmin, PromocaoLeadStatus } from '@/lib/api/types'

const STATUS_LABEL: Record<PromocaoLeadStatus, string> = {
  novo: 'Novo',
  contatado: 'Contatado',
  convertido: 'Convertido',
  descartado: 'Descartado',
}

const STATUS_STYLE: Record<PromocaoLeadStatus, string> = {
  novo: 'bg-blue-50 text-blue-700 border border-blue-200',
  contatado: 'bg-amber-50 text-amber-700 border border-amber-200',
  convertido: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  descartado: 'bg-zinc-100 text-zinc-600 border border-zinc-200',
}

const ALL_STATUSES: PromocaoLeadStatus[] = [
  'novo',
  'contatado',
  'convertido',
  'descartado',
]

function LeadStatusSelect({ lead }: { lead: PromocaoLeadAdmin }) {
  const patch = usePatchPromocaoLead(lead.id)
  return (
    <select
      className="rounded-md border bg-background px-2 py-1 text-xs"
      value={lead.status}
      disabled={patch.isPending}
      onChange={(e) => patch.mutate({ status: e.target.value as PromocaoLeadStatus })}
    >
      {ALL_STATUSES.map((s) => (
        <option key={s} value={s}>
          {STATUS_LABEL[s]}
        </option>
      ))}
    </select>
  )
}

export function PromocaoLeadsTab() {
  const [statusFiltro, setStatusFiltro] = useState<PromocaoLeadStatus | ''>('')
  const [promoFiltro, setPromoFiltro] = useState('')
  const { data: promos } = usePromocoesAdmin()
  const { data: leads, isLoading } = usePromocaoLeads({
    promocaoId: promoFiltro || undefined,
    status: statusFiltro || undefined,
  })

  const total = leads?.length ?? 0
  const novos = leads?.filter((l) => l.status === 'novo').length ?? 0
  const convertidos = leads?.filter((l) => l.status === 'convertido').length ?? 0
  const conversao = total > 0 ? Math.round((convertidos / total) * 100) : 0

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground">Leads novos</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">{novos}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground">Total (filtro atual)</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">{total}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground">Conversão</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">{conversao}%</CardContent>
        </Card>
      </div>

      <div className="flex flex-wrap gap-2">
        <select
          className="rounded-md border bg-background px-2 py-1.5 text-sm"
          value={promoFiltro}
          onChange={(e) => setPromoFiltro(e.target.value)}
        >
          <option value="">Todas as promoções</option>
          {(promos ?? []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.titulo}
            </option>
          ))}
        </select>
        <select
          className="rounded-md border bg-background px-2 py-1.5 text-sm"
          value={statusFiltro}
          onChange={(e) => setStatusFiltro(e.target.value as PromocaoLeadStatus | '')}
        >
          <option value="">Todos os status</option>
          {ALL_STATUSES.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABEL[s]}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-hidden rounded-md border bg-card">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-4 py-2.5 font-semibold">Cliente</th>
              <th className="px-4 py-2.5 font-semibold">Telefone</th>
              <th className="px-4 py-2.5 font-semibold">Contrato</th>
              <th className="px-4 py-2.5 font-semibold">Promoção</th>
              <th className="px-4 py-2.5 font-semibold">Data</th>
              <th className="px-4 py-2.5 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td className="px-4 py-6 text-muted-foreground" colSpan={6}>
                  Carregando…
                </td>
              </tr>
            )}
            {!isLoading && (leads ?? []).length === 0 && (
              <tr>
                <td className="px-4 py-6 text-muted-foreground" colSpan={6}>
                  Nenhum lead ainda. Quando um cliente tocar em &quot;Tenho interesse&quot; no
                  app, ele aparece aqui.
                </td>
              </tr>
            )}
            {(leads ?? []).map((l) => (
              <tr key={l.id} className="border-b last:border-b-0 hover:bg-accent/40">
                <td className="px-4 py-3 font-medium">{l.nome || '—'}</td>
                <td className="px-4 py-3">{l.telefone || '—'}</td>
                <td className="px-4 py-3 text-muted-foreground">{l.contrato_id ?? '—'}</td>
                <td className="px-4 py-3 text-muted-foreground">{l.promocao_titulo}</td>
                <td className="px-4 py-3 text-muted-foreground">
                  {new Date(l.created_at).toLocaleDateString('pt-BR')}
                </td>
                <td className="px-4 py-3">
                  <span className="flex items-center gap-2">
                    <Badge className={STATUS_STYLE[l.status]} variant="outline">
                      {STATUS_LABEL[l.status]}
                    </Badge>
                    <LeadStatusSelect lead={l} />
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
