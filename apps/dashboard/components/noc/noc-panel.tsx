'use client'
/**
 * Painel NOC — visao unica da operacao, pensada pra ficar aberta num monitor.
 * Nao tem dado proprio: compoe as mesmas queries das outras telas (todas ja
 * com polling) e responde a tres perguntas, nesta ordem:
 *   1. Esta tudo no ar?            -> barra de sistemas
 *   2. Tem alguem esperando?       -> fila de atendimento + SLA
 *   3. O campo esta dando conta?   -> OS abertas + carga por tecnico
 */
import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Clock,
  Headphones,
  Maximize2,
  MessageSquare,
  Minimize2,
  Star,
  UserX,
  Users,
  Wrench,
} from 'lucide-react'
import {
  useConversas,
  useManutencoes,
  useMetricas,
  useOsList,
  useTecnicos,
  useTimeseries,
} from '@/lib/api/queries'
import type { ConversaListItem, ManutencaoOut, OsListItem } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { OsStatusPill } from '@/components/os-status-pill'
import {
  Avatar,
  PageHeader,
  Panel,
  PanelHeader,
  Skeleton,
  SkeletonRows,
  StatTile,
  StatusChip,
  StatusDot,
  TONE_SOFT,
  ageShort,
  useNow,
  type Tone,
} from './primitives'
import { Sparkline } from './sparkline'
import { useSystemHealth } from './system-status'

/* ── helpers ─────────────────────────────────────────────────────────── */

/** "5511987654321@s.whatsapp.net" -> "(11) 9 8765-4321". */
function formatWhatsapp(jid: string): string {
  const digits = jid.replace(/\D/g, '')
  const local = digits.startsWith('55') && digits.length >= 12 ? digits.slice(2) : digits
  if (local.length === 11) return `(${local.slice(0, 2)}) ${local.slice(2, 3)} ${local.slice(3, 7)}-${local.slice(7)}`
  if (local.length === 10) return `(${local.slice(0, 2)}) ${local.slice(2, 6)}-${local.slice(6)}`
  return jid
}

function waitMs(c: ConversaListItem, now: number): number {
  const since = c.transferred_at ?? c.last_message_at ?? c.created_at
  return Math.max(0, now - new Date(since).getTime())
}

function fmtWait(ms: number): string {
  const totalMin = Math.floor(ms / 60_000)
  if (totalMin < 60) return `${totalMin} min`
  return `${Math.floor(totalMin / 60)} h ${String(totalMin % 60).padStart(2, '0')}`
}

function fmtHora(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function EmptyOk({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-1.5 px-4 py-10 text-center">
      <CheckCircle2 className="h-7 w-7 text-success" />
      <p className="text-sm font-medium">{title}</p>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

function PanelError({ what }: { what: string }) {
  return (
    <div className="flex flex-1 items-center justify-center gap-2 px-4 py-10 text-sm text-muted-foreground">
      <AlertTriangle className="h-4 w-4 text-warning" />
      Não foi possível carregar {what}.
    </div>
  )
}

/* ── barra de sistemas ───────────────────────────────────────────────── */

function SystemBar() {
  const { checks, overall, summary, apiDown, isLoading } = useSystemHealth()
  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border bg-card px-4 py-2.5',
        overall === 'destructive' && 'border-destructive/40',
        overall === 'warning' && 'border-warning/40',
      )}
    >
      <div className="flex items-center gap-2.5">
        <StatusDot tone={overall} pulse={overall !== 'muted'} />
        <span className="text-sm font-medium">{summary}</span>
      </div>
      <div className="flex flex-wrap items-center gap-2 sm:ml-auto">
        {isLoading && <Skeleton className="h-7 w-56" />}
        {apiDown && <StatusChip tone="destructive" label="API" value="Inacessível" />}
        {checks.map((c) => (
          <StatusChip key={c.key} tone={c.tone} label={c.label} value={c.state} />
        ))}
      </div>
    </div>
  )
}

/* ── fila de atendimento ─────────────────────────────────────────────── */

function QueueRow({ c, now }: { c: ConversaListItem; now: number }) {
  const ms = waitMs(c, now)
  const slaMs = (c.sla_minutes || 15) * 60_000
  const ratio = ms / slaMs
  const breached = ratio >= 1
  const tone: Tone = breached ? 'destructive' : ratio >= 0.7 ? 'warning' : 'info'
  const telefone = formatWhatsapp(c.whatsapp)
  const nome = c.cliente_nome ?? telefone
  return (
    <li className={cn('border-b border-border/70 last:border-b-0', breached && 'animate-breach')}>
      <Link
        href={`/conversas/${c.id}`}
        className="flex items-center gap-3 px-4 py-2.5 transition-colors hover:bg-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
      >
        <Avatar name={nome} />
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium">{nome}</div>
          <div className={cn('truncate text-xs text-muted-foreground', c.cliente_nome && 'num')}>
            {c.cliente_nome ? telefone : 'Cliente não identificado'}
          </div>
        </div>
        <div className="w-28 shrink-0 text-right sm:w-36">
          <div className="flex items-center justify-end gap-1.5">
            {breached && <AlertTriangle className="h-3.5 w-3.5 text-destructive" aria-hidden />}
            <span className={cn('num text-sm font-semibold', breached && 'text-destructive')}>
              {fmtWait(ms)}
            </span>
          </div>
          {/* Medidor: quanto do SLA ja foi consumido. */}
          <div
            className="mt-1.5 h-1 overflow-hidden rounded-full bg-muted"
            role="meter"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.min(100, Math.round(ratio * 100))}
            aria-label={`${Math.round(ratio * 100)}% do SLA de ${c.sla_minutes || 15} min`}
          >
            <div
              className={cn(
                'h-full rounded-full',
                tone === 'destructive' ? 'bg-destructive' : tone === 'warning' ? 'bg-warning' : 'bg-info',
              )}
              style={{ width: `${Math.min(100, ratio * 100)}%` }}
            />
          </div>
          <div className="mt-1 text-[11px] text-muted-foreground">
            {breached ? 'SLA estourado' : `SLA ${c.sla_minutes || 15} min`}
          </div>
        </div>
      </Link>
    </li>
  )
}

function QueuePanel({
  fila,
  isLoading,
  isError,
  hasMore,
  now,
}: {
  fila: ConversaListItem[]
  isLoading: boolean
  isError: boolean
  hasMore: boolean
  now: number
}) {
  return (
    <Panel className="min-h-[320px]">
      <PanelHeader
        title="Fila de atendimento"
        icon={Clock}
        meta={isLoading ? undefined : `${fila.length}${hasMore ? '+' : ''}`}
        actions={
          <Link href="/conversas" className="text-xs text-muted-foreground hover:text-foreground hover:underline">
            Ver conversas
          </Link>
        }
      />
      {isLoading ? (
        <SkeletonRows rows={5} />
      ) : isError ? (
        <PanelError what="a fila" />
      ) : fila.length === 0 ? (
        <EmptyOk title="Fila zerada" hint="Nenhuma conversa aguardando atendente." />
      ) : (
        <ul className="max-h-[420px] overflow-y-auto">
          {fila.map((c) => (
            <QueueRow key={c.id} c={c} now={now} />
          ))}
        </ul>
      )}
    </Panel>
  )
}

/* ── OS abertas ──────────────────────────────────────────────────────── */

function OsPanel({
  oss,
  tecnicoNome,
  isLoading,
  isError,
  hasMore,
  now,
}: {
  oss: OsListItem[]
  tecnicoNome: (id: string) => string
  isLoading: boolean
  isError: boolean
  hasMore: boolean
  now: number
}) {
  return (
    <Panel className="min-h-[320px]">
      <PanelHeader
        title="Ordens de serviço abertas"
        icon={ClipboardList}
        meta={isLoading ? undefined : `${oss.length}${hasMore ? '+' : ''}`}
        actions={
          <Link href="/os" className="text-xs text-muted-foreground hover:text-foreground hover:underline">
            Ver todas
          </Link>
        }
      />
      {isLoading ? (
        <SkeletonRows rows={5} />
      ) : isError ? (
        <PanelError what="as ordens de serviço" />
      ) : oss.length === 0 ? (
        <EmptyOk title="Nenhuma OS aberta" hint="Sem pendências no campo." />
      ) : (
        <ul className="max-h-[420px] overflow-y-auto">
          {oss.map((o) => (
            <li key={o.id} className="border-b border-border/70 last:border-b-0">
              <Link
                href={`/os/${o.id}`}
                className="flex items-center gap-3 px-4 py-2.5 transition-colors hover:bg-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="num text-sm font-medium">{o.codigo}</span>
                    <OsStatusPill status={o.status} size="sm" />
                  </div>
                  <div className="mt-0.5 truncate text-xs text-muted-foreground" title={o.problema}>
                    {o.nome_cliente ? `${o.nome_cliente} · ` : ''}
                    {o.problema}
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  {o.tecnico_id ? (
                    <div className="max-w-[140px] truncate text-xs">{tecnicoNome(o.tecnico_id)}</div>
                  ) : (
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium ring-1 ring-inset',
                        TONE_SOFT.warning,
                      )}
                    >
                      <UserX className="h-3 w-3" aria-hidden />
                      Sem técnico
                    </span>
                  )}
                  <div className="num mt-0.5 text-[11px] text-muted-foreground" title={fmtHora(o.criada_em)}>
                    há {ageShort(o.criada_em, now)}
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}

/* ── carga por tecnico ───────────────────────────────────────────────── */

interface Carga {
  id: string
  nome: string
  andamento: number
  pendente: number
}

function CargaPanel({ carga, isLoading }: { carga: Carga[]; isLoading: boolean }) {
  const max = Math.max(1, ...carga.map((c) => c.andamento + c.pendente))
  return (
    <Panel>
      <PanelHeader
        title="Carga por técnico"
        icon={Users}
        actions={
          <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-sm bg-warning" aria-hidden /> Em andamento
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-sm bg-info" aria-hidden /> Pendente
            </span>
          </div>
        }
      />
      {isLoading ? (
        <SkeletonRows rows={4} />
      ) : carga.length === 0 ? (
        <EmptyOk title="Sem OS atribuídas" />
      ) : (
        <ul className="space-y-2.5 p-4">
          {carga.map((c) => {
            const total = c.andamento + c.pendente
            return (
              <li
                key={c.id}
                className="flex items-center gap-3 text-sm"
                title={`${c.nome}: ${c.andamento} em andamento, ${c.pendente} pendente(s)`}
              >
                <span className="w-32 shrink-0 truncate text-muted-foreground">{c.nome}</span>
                {/* Barra empilhada: segmentos separados por 2px da cor da superficie. */}
                <div className="flex h-3.5 flex-1 items-center gap-[2px]">
                  {c.andamento > 0 && (
                    <span
                      className="h-full rounded-sm bg-warning"
                      style={{ width: `${(c.andamento / max) * 100}%` }}
                    />
                  )}
                  {c.pendente > 0 && (
                    <span
                      className="h-full rounded-sm bg-info"
                      style={{ width: `${(c.pendente / max) * 100}%` }}
                    />
                  )}
                </div>
                <span className="num w-6 shrink-0 text-right font-medium">{total}</span>
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}

/* ── manutencoes ─────────────────────────────────────────────────────── */

function ManutencoesPanel({
  itens,
  isLoading,
  now,
}: {
  itens: ManutencaoOut[]
  isLoading: boolean
  now: number
}) {
  return (
    <Panel>
      <PanelHeader
        title="Manutenções"
        icon={CalendarClock}
        meta={isLoading ? undefined : itens.length}
        actions={
          <Link href="/manutencoes" className="text-xs text-muted-foreground hover:text-foreground hover:underline">
            Agenda
          </Link>
        }
      />
      {isLoading ? (
        <SkeletonRows rows={3} />
      ) : itens.length === 0 ? (
        <EmptyOk title="Nenhuma manutenção programada" hint="Rede sem janelas em andamento ou agendadas." />
      ) : (
        <ul>
          {itens.map((m) => {
            const emAndamento = new Date(m.inicio_at).getTime() <= now
            return (
              <li key={m.id} className="border-b border-border/70 last:border-b-0">
                <Link
                  href={`/manutencoes/${m.id}`}
                  className="flex items-start gap-3 px-4 py-2.5 transition-colors hover:bg-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                >
                  <StatusDot tone={emAndamento ? 'warning' : 'info'} pulse={emAndamento} className="mt-1.5" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{m.titulo}</div>
                    <div className="truncate text-xs text-muted-foreground">
                      {emAndamento ? 'Em andamento' : 'Agendada'}
                      {m.cidades && m.cidades.length > 0 ? ` · ${m.cidades.join(', ')}` : ''}
                    </div>
                  </div>
                  <div className="num shrink-0 text-right text-[11px] text-muted-foreground">
                    <div>{fmtHora(m.inicio_at)}</div>
                    <div>até {fmtHora(m.fim_at)}</div>
                  </div>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}

/* ── tela cheia ──────────────────────────────────────────────────────── */

function useFullscreen() {
  const [on, setOn] = useState(false)
  useEffect(() => {
    const sync = () => setOn(Boolean(document.fullscreenElement))
    document.addEventListener('fullscreenchange', sync)
    return () => document.removeEventListener('fullscreenchange', sync)
  }, [])
  const toggle = useCallback(() => {
    if (document.fullscreenElement) void document.exitFullscreen()
    else void document.documentElement.requestFullscreen().catch(() => undefined)
  }, [])
  return { on, toggle }
}

/* ── painel ──────────────────────────────────────────────────────────── */

export function NocPanel() {
  // Relogio de 1s: os tempos de espera da fila andam sozinhos entre os polls.
  const now = useNow(1000)
  const fs = useFullscreen()

  const metricas = useMetricas()
  const ts = useTimeseries(7)
  const filaQ = useConversas({ status: 'aguardando' })
  const pendQ = useOsList({ status: 'pendente' })
  const andQ = useOsList({ status: 'em_andamento' })
  const tecQ = useTecnicos({ ativo: true })
  const manQ = useManutencoes()

  const m = metricas.data
  const pontos = ts.data?.pontos ?? []

  // Fila: quem espera ha mais tempo primeiro.
  const fila = (filaQ.data?.pages.flatMap((p) => p.items) ?? [])
    .slice()
    .sort((a, b) => waitMs(b, now) - waitMs(a, now))
  const slaEstourado = fila.filter((c) => waitMs(c, now) >= (c.sla_minutes || 15) * 60_000).length
  const maiorEspera = fila[0] ? waitMs(fila[0], now) : 0

  const pendentes = pendQ.data?.items ?? []
  const emAndamento = andQ.data?.items ?? []
  // OS abertas: sem tecnico primeiro (exige acao), depois as mais antigas.
  const abertas = [...pendentes, ...emAndamento].sort((a, b) => {
    const semA = a.tecnico_id ? 1 : 0
    const semB = b.tecnico_id ? 1 : 0
    if (semA !== semB) return semA - semB
    return new Date(a.criada_em).getTime() - new Date(b.criada_em).getTime()
  })
  const semTecnico = abertas.filter((o) => !o.tecnico_id).length
  const osHasMore = Boolean(pendQ.data?.next_cursor || andQ.data?.next_cursor)

  // Em andamento agora ou ainda por vir; a mais proxima primeiro.
  const manutencoes = (manQ.data?.items ?? [])
    .filter((x) => new Date(x.fim_at).getTime() >= now)
    .sort((a, b) => new Date(a.inicio_at).getTime() - new Date(b.inicio_at).getTime())
    .slice(0, 6)

  const nomes = new Map((tecQ.data?.items ?? []).map((t) => [t.id, t.nome]))
  const tecnicoNome = (id: string) => nomes.get(id) ?? 'Atribuída'
  // Tecnicos e manutencoes sao endpoints so de admin: pro atendente a query
  // falha (403) e o painel correspondente simplesmente nao aparece.
  const showCarga = !tecQ.isError
  const showManutencoes = !manQ.isError

  const cargaMap = new Map<string, Carga>()
  for (const o of abertas) {
    if (!o.tecnico_id) continue
    const c = cargaMap.get(o.tecnico_id) ?? {
      id: o.tecnico_id,
      nome: tecnicoNome(o.tecnico_id),
      andamento: 0,
      pendente: 0,
    }
    if (o.status === 'em_andamento') c.andamento += 1
    else c.pendente += 1
    cargaMap.set(o.tecnico_id, c)
  }
  const carga = [...cargaMap.values()]
    .sort((a, b) => b.andamento + b.pendente - (a.andamento + a.pendente))
    .slice(0, 8)

  const atualizadoHa = metricas.dataUpdatedAt
    ? Math.max(0, Math.round((now - metricas.dataUpdatedAt) / 1000))
    : null

  const filaCount = m?.conversas_aguardando ?? fila.length
  const filaTone: Tone = slaEstourado > 0 ? 'destructive' : filaCount > 0 ? 'warning' : 'success'

  return (
    <div className="space-y-4">
      <PageHeader
        title="Painel NOC"
        description="Operação em tempo real — atendimento, campo e sistemas."
        actions={
          <>
            <span className="inline-flex items-center gap-2 text-xs text-muted-foreground" aria-live="off">
              <StatusDot tone={metricas.isError ? 'destructive' : 'success'} pulse={!metricas.isError} />
              {metricas.isError ? (
                'Sem atualização'
              ) : (
                <>
                  Ao vivo
                  {atualizadoHa !== null && (
                    <span className="num" suppressHydrationWarning>
                      · há {atualizadoHa}s
                    </span>
                  )}
                </>
              )}
            </span>
            <Button variant="outline" size="sm" onClick={fs.toggle} aria-pressed={fs.on}>
              {fs.on ? <Minimize2 /> : <Maximize2 />}
              {fs.on ? 'Sair da tela cheia' : 'Tela cheia'}
            </Button>
          </>
        }
      />

      <SystemBar />

      {/* KPIs: da esquerda pra direita, do que exige acao agora pro contexto. */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 2xl:grid-cols-6">
        <StatTile
          label="Fila aguardando"
          value={m ? filaCount : '—'}
          icon={Clock}
          tone={filaTone}
          alert={filaCount > 0}
          href="/conversas"
          hint={
            filaCount === 0
              ? 'Ninguém esperando'
              : slaEstourado > 0
                ? `${slaEstourado} com SLA estourado`
                : `Maior espera ${fmtWait(maiorEspera)}`
          }
        />
        <StatTile
          label="Em atendimento"
          value={m ? m.conversas_humano : '—'}
          icon={Headphones}
          tone="info"
          href="/conversas"
          hint="Com atendente humano"
        />
        <StatTile
          label="OS abertas"
          value={m ? m.os_abertas : '—'}
          icon={Wrench}
          tone={semTecnico > 0 ? 'warning' : 'muted'}
          alert={semTecnico > 0}
          href="/os"
          hint={
            semTecnico > 0
              ? `${semTecnico} sem técnico`
              : `${emAndamento.length} em andamento · ${pendentes.length} pendente(s)`
          }
        />
        <StatTile
          label="OS concluídas 24h"
          value={m ? m.os_concluidas_24h : '—'}
          icon={CheckCircle2}
          tone="success"
          hint="Últimas 24 horas"
        >
          <Sparkline
            values={pontos.map((p) => p.os_concluidas)}
            color="var(--chart-3)"
            label="OS concluídas por dia, últimos 7 dias"
          />
        </StatTile>
        <StatTile
          label="Mensagens 24h"
          value={m ? m.msgs_24h.toLocaleString('pt-BR') : '—'}
          icon={MessageSquare}
          tone="muted"
          hint="Últimas 24 horas"
        >
          <Sparkline
            values={pontos.map((p) => p.msgs)}
            color="var(--chart-1)"
            label="Mensagens por dia, últimos 7 dias"
          />
        </StatTile>
        <StatTile
          label="CSAT 30 dias"
          value={m && m.csat_avg_30d !== null ? m.csat_avg_30d.toFixed(2).replace('.', ',') : '—'}
          unit="/ 5"
          icon={Star}
          tone="primary"
          hint={`${m ? m.leads_novos_7d : '—'} leads novos em 7 dias`}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <QueuePanel
          fila={fila}
          isLoading={filaQ.isLoading}
          isError={filaQ.isError}
          hasMore={Boolean(filaQ.hasNextPage)}
          now={now}
        />
        <OsPanel
          oss={abertas}
          tecnicoNome={tecnicoNome}
          isLoading={pendQ.isLoading || andQ.isLoading}
          isError={pendQ.isError || andQ.isError}
          hasMore={osHasMore}
          now={now}
        />
      </div>

      {(showCarga || showManutencoes) && (
        <div className={cn('grid gap-4', showCarga && showManutencoes && 'xl:grid-cols-2')}>
          {showCarga && (
            <CargaPanel
              carga={carga}
              isLoading={pendQ.isLoading || andQ.isLoading || tecQ.isLoading}
            />
          )}
          {showManutencoes && (
            <ManutencoesPanel itens={manutencoes} isLoading={manQ.isLoading} now={now} />
          )}
        </div>
      )}
    </div>
  )
}
