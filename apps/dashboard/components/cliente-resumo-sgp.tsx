'use client'
import { AlertCircle, Calendar, ClipboardList, DollarSign } from 'lucide-react'
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { OsStatusPill } from './os-status-pill'
import { useClienteSgpInfo, useOsList } from '@/lib/api/queries'

function fmtR(v: number | null): string {
  if (v === null) return '—'
  return v.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
  })
}

function fmtDate(s: string | null): string {
  if (!s) return '—'
  try {
    const d = new Date(s.length === 10 ? s + 'T00:00:00' : s)
    return d.toLocaleDateString('pt-BR')
  } catch {
    return s
  }
}

interface Props {
  clienteId: string
  cpf: string
}

export function ClienteResumoSgp({ clienteId, cpf }: Props) {
  const cpfDigits = cpf.replace(/\D/g, '')
  const { data: sgp, isLoading: sgpLoading, error: sgpError } = useClienteSgpInfo(
    cpfDigits || null,
  )
  const { data: osData, isLoading: osLoading } = useOsList({ cliente_id: clienteId })
  const osList = osData?.items ?? []
  const abertas = osList.filter((o) => o.status !== 'concluida' && o.status !== 'cancelada')

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Resumo SGP / faturas */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <DollarSign className="h-4 w-4" /> Plano & faturas
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {sgpLoading && (
            <p className="text-sm text-muted-foreground">Consultando SGP…</p>
          )}
          {sgpError && (
            <p className="text-sm text-destructive">
              Erro ao consultar SGP. Cliente pode não existir lá.
            </p>
          )}
          {sgp && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs uppercase text-muted-foreground">Plano</div>
                  <p className="mt-1 text-sm font-medium">{sgp.plano ?? '—'}</p>
                </div>
                <div>
                  <div className="text-xs uppercase text-muted-foreground">Status SGP</div>
                  <p className="mt-1 text-sm capitalize">{sgp.status_contrato ?? '—'}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs uppercase text-muted-foreground">
                    Próxima fatura
                  </div>
                  <p className="mt-1 text-sm font-semibold">
                    {fmtR(sgp.proxima_fatura_valor)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Venc. {fmtDate(sgp.proxima_fatura_vencimento)}
                  </p>
                </div>
                <div>
                  <div className="text-xs uppercase text-muted-foreground">Em aberto</div>
                  <p className="mt-1 text-sm">
                    {sgp.faturas_em_aberto} fatura{sgp.faturas_em_aberto !== 1 ? 's' : ''}
                  </p>
                  {sgp.faturas_em_atraso > 0 && (
                    <p className="mt-0.5 flex items-center gap-1 text-xs text-destructive">
                      <AlertCircle className="h-3 w-3" />
                      {sgp.faturas_em_atraso} em atraso
                    </p>
                  )}
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* OS do cliente */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ClipboardList className="h-4 w-4" /> Ordens de serviço
            {abertas.length > 0 && (
              <Badge variant="destructive" className="ml-2">
                {abertas.length} aberta{abertas.length > 1 ? 's' : ''}
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {osLoading && (
            <p className="text-sm text-muted-foreground">Carregando…</p>
          )}
          {osData && osList.length === 0 && (
            <p className="text-sm text-muted-foreground">Nenhuma OS pra este cliente.</p>
          )}
          {osList.slice(0, 10).map((o) => (
            <Link
              key={o.id}
              href={`/os/${o.id}`}
              className="block rounded-md border bg-card px-3 py-2 text-sm transition-colors hover:bg-accent/40 hover:border-accent"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono font-semibold text-primary">{o.codigo}</span>
                <OsStatusPill status={o.status} size="sm" />
              </div>
              <p className="mt-1 truncate text-xs text-muted-foreground">{o.problema}</p>
              <p className="mt-0.5 flex items-center gap-1 text-[10px] text-muted-foreground">
                <Calendar className="h-3 w-3" />
                {new Date(o.criada_em).toLocaleDateString('pt-BR')}
              </p>
            </Link>
          ))}
          {osList.length > 10 && (
            <p className="text-xs text-muted-foreground">
              + {osList.length - 10} mais. Veja todas em <Link href="/os" className="underline">/os</Link>.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
