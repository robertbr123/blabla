'use client'
import { useState } from 'react'
import Link from 'next/link'
import {
  Award,
  CheckCircle2,
  Coins,
  Gift,
  Megaphone,
  Smartphone,
  MessageCircle,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  useIndicacaoUsos,
  useIndicacoes,
  useIndicacoesStats,
  useMarcarConvertido,
  useMarcarCredito,
  usePromocaoIndicacaoAtiva,
  useRankingIndicadores,
} from '@/lib/api/queries'

export default function IndicacoesPage() {
  const { data: indicacoes } = useIndicacoes()
  const { data: usos } = useIndicacaoUsos()
  const { data: ranking } = useRankingIndicadores()
  const { data: stats } = useIndicacoesStats()
  const { data: promoIndicacao } = usePromocaoIndicacaoAtiva()
  const converter = useMarcarConvertido()
  const aplicarCredito = useMarcarCredito()
  const [busy, setBusy] = useState<string | null>(null)

  const pendentes = (usos ?? []).filter((u) => !u.convertido_em)
  const convertidos = (usos ?? []).filter(
    (u) => u.convertido_em && !u.credito_aplicado_em,
  )
  const concluidos = (usos ?? []).filter((u) => u.credito_aplicado_em)

  async function handleConverter(usoId: string) {
    if (!confirm('Marcar como convertido (lead virou cliente)?')) return
    setBusy(usoId)
    try {
      await converter.mutateAsync({ usoId })
    } finally {
      setBusy(null)
    }
  }

  async function handleCredito(usoId: string) {
    if (!confirm('Confirma que o crédito já foi aplicado no SGP nas faturas dos 2?')) return
    setBusy(usoId)
    try {
      await aplicarCredito.mutateAsync({ usoId })
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <Gift className="h-6 w-6" /> Indicações
        </h1>
        <p className="text-sm text-muted-foreground">
          Dois canais ativos: <strong>WhatsApp</strong> (cliente manda <code>INDICAR</code> no bot)
          e <strong>App</strong> (tela <code>/indicacao</code>, ativada por promoção do tipo Indicação).
        </p>
      </div>

      {/* Banner card de indicação no app */}
      <Card>
        <CardContent className="flex flex-col items-start gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="rounded-md bg-pink-100 p-2 text-pink-700">
              <Megaphone className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium">Card de indicação no app</p>
              <p className="text-xs text-muted-foreground">
                {promoIndicacao
                  ? `Ativa: "${promoIndicacao.titulo}" · ${promoIndicacao.views} views · ${promoIndicacao.clicks} clicks`
                  : 'Nenhuma promoção do tipo Indicação ativa. Crie uma pra exibir o card no carrossel da home do app.'}
              </p>
            </div>
          </div>
          <Button asChild variant={promoIndicacao ? 'outline' : 'default'} size="sm">
            <Link href="/promocoes">
              {promoIndicacao ? 'Gerenciar' : 'Criar promoção'}
            </Link>
          </Button>
        </CardContent>
      </Card>

      {/* Stats por origem */}
      {stats && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Card>
            <CardContent className="p-4">
              <p className="flex items-center gap-1 text-xs text-muted-foreground">
                <Smartphone className="h-3 w-3" /> Compartilhamentos via app
              </p>
              <p className="text-2xl font-bold">{stats.shares_app}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="flex items-center gap-1 text-xs text-muted-foreground">
                <MessageCircle className="h-3 w-3" /> Leads via WhatsApp
              </p>
              <p className="text-2xl font-bold">{stats.leads_whatsapp}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="flex items-center gap-1 text-xs text-muted-foreground">
                <CheckCircle2 className="h-3 w-3" /> Convertidos
              </p>
              <p className="text-2xl font-bold text-emerald-600">{stats.convertidos}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Ranking */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Award className="h-4 w-4" /> Top indicadores
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!ranking || ranking.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Sem indicações registradas ainda.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="pb-2">Cliente</th>
                  <th className="pb-2 text-right">Cliques</th>
                  <th className="pb-2 text-right">Convertidos</th>
                </tr>
              </thead>
              <tbody>
                {ranking.map((r) => (
                  <tr key={r.cliente_id} className="border-t">
                    <td className="py-2">{r.cliente_nome}</td>
                    <td className="py-2 text-right">{r.usos}</td>
                    <td className="py-2 text-right font-medium">{r.convertidos}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {/* Pendentes de conversão */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Pendentes ({pendentes.length})
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              Lead chegou, mas ainda não virou cliente.
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {pendentes.length === 0 && (
            <p className="text-sm text-muted-foreground">Nada pendente.</p>
          )}
          {pendentes.map((u) => (
            <div
              key={u.id}
              className="flex items-center justify-between gap-3 border-b py-2 last:border-b-0"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm">
                  <strong>{u.lead_nome ?? 'Lead'}</strong> via código{' '}
                  <code className="font-mono text-xs">{u.indicacao_codigo}</code>
                </p>
                <p className="text-xs text-muted-foreground">
                  {new Date(u.criado_em).toLocaleString('pt-BR')}
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => handleConverter(u.id)}
                disabled={busy === u.id}
              >
                <CheckCircle2 className="h-3 w-3" /> Marcar convertido
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Convertidos aguardando crédito */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Convertidos ({convertidos.length})
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              Aplicar crédito no SGP nos 2 (indicador e indicado).
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {convertidos.length === 0 && (
            <p className="text-sm text-muted-foreground">Nada aguardando.</p>
          )}
          {convertidos.map((u) => (
            <div
              key={u.id}
              className="flex items-center justify-between gap-3 border-b py-2 last:border-b-0"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm">
                  <strong>{u.lead_nome ?? 'Lead'}</strong> · código{' '}
                  <code className="font-mono text-xs">{u.indicacao_codigo}</code>
                </p>
                <p className="text-xs text-muted-foreground">
                  Convertido em{' '}
                  {u.convertido_em
                    ? new Date(u.convertido_em).toLocaleString('pt-BR')
                    : '—'}
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleCredito(u.id)}
                disabled={busy === u.id}
              >
                <Coins className="h-3 w-3" /> Crédito aplicado
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Concluídos */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Concluídos ({concluidos.length})
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              Crédito já aplicado em ambos.
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {concluidos.length === 0 && (
            <p className="text-sm text-muted-foreground">Vazio.</p>
          )}
          {concluidos.map((u) => (
            <div
              key={u.id}
              className="flex items-center justify-between gap-3 border-b py-2 last:border-b-0"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm">
                  <strong>{u.lead_nome ?? 'Lead'}</strong> · código{' '}
                  <code className="font-mono text-xs">{u.indicacao_codigo}</code>
                </p>
                <p className="text-xs text-muted-foreground">
                  Crédito em{' '}
                  {u.credito_aplicado_em
                    ? new Date(u.credito_aplicado_em).toLocaleString('pt-BR')
                    : '—'}
                </p>
              </div>
              <Badge variant="outline">✓ Concluído</Badge>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Códigos gerados (debug) */}
      <details className="text-xs">
        <summary className="cursor-pointer text-muted-foreground">
          Ver todos os códigos gerados ({indicacoes?.length ?? 0})
        </summary>
        {indicacoes && (
          <table className="mt-2 w-full text-xs">
            <thead className="text-left uppercase text-muted-foreground">
              <tr>
                <th className="pb-1">Código</th>
                <th className="pb-1">Cliente</th>
                <th className="pb-1 text-right">Usos</th>
                <th className="pb-1">Criado</th>
              </tr>
            </thead>
            <tbody>
              {indicacoes.map((i) => (
                <tr key={i.id} className="border-t">
                  <td className="py-1 font-mono">{i.codigo}</td>
                  <td className="py-1">{i.cliente_indicador_nome}</td>
                  <td className="py-1 text-right">{i.usos}</td>
                  <td className="py-1">
                    {new Date(i.criado_em).toLocaleDateString('pt-BR')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </details>
    </div>
  )
}
