'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { AlertCircle, MessageSquare, Search, Trash2, Wrench, X } from 'lucide-react'
import {
  Age,
  Avatar,
  FilterTabs,
  SkeletonRows,
  useNow,
  type FilterTab,
} from '@/components/noc/primitives'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import {
  useCanais,
  useConversas,
  useDeleteConversa,
  useEncerrar,
  useMetricas,
} from '@/lib/api/queries'
import type { ConversaListItem } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { TABS_SCROLL } from './responsive'
import { DialogAbrirOsFromConversa } from './dialog-abrir-os-from-conversa'
import { ConversaSlaTimer } from './conversa-sla-timer'
import { ConversaStatusPill } from './conversa-status-pill'

function ConversaRowActions({
  c,
  onAbrirOs,
  touch = false,
}: {
  c: ConversaListItem
  onAbrirOs: (id: string) => void
  /** Alvos de toque maiores (cartão do celular). */
  touch?: boolean
}) {
  const btn = touch ? 'h-9 w-9' : 'h-7 w-7'
  const encerrar = useEncerrar(c.id)
  const excluir = useDeleteConversa(c.id)

  async function handleEncerrar() {
    if (!confirm('Encerrar esta conversa?')) return
    try {
      await encerrar.mutateAsync()
    } catch { /* toast no onError do hook */ }
  }

  async function handleExcluir() {
    if (!confirm('Excluir esta conversa? O histórico será preservado por 30 dias.')) return
    try {
      await excluir.mutateAsync()
    } catch { /* toast no onError do hook */ }
  }

  return (
    <div className="flex items-center justify-end gap-0.5">
      {c.status !== 'encerrada' && (
        <Button
          variant="ghost"
          size="icon"
          className={cn(btn, 'text-muted-foreground')}
          onClick={() => void handleEncerrar()}
          disabled={encerrar.isPending}
          title="Encerrar conversa"
          aria-label="Encerrar conversa"
        >
          <X />
        </Button>
      )}
      {c.cliente_id && (
        <Button
          variant="ghost"
          size="icon"
          className={cn(btn, 'text-muted-foreground')}
          onClick={() => onAbrirOs(c.id)}
          title="Abrir OS para este cliente"
          aria-label="Abrir OS para este cliente"
        >
          <Wrench />
        </Button>
      )}
      <Button
        variant="ghost"
        size="icon"
        className={cn(btn, 'text-muted-foreground hover:bg-destructive/[0.13] hover:text-destructive')}
        onClick={() => void handleExcluir()}
        disabled={excluir.isPending}
        title="Excluir conversa"
        aria-label="Excluir conversa"
      >
        <Trash2 />
      </Button>
    </div>
  )
}

/** Formata "5511987654321@s.whatsapp.net" -> "(11) 9 8765-4321". */
export function formatWhatsappBr(jid: string): string {
  const digits = jid.replace(/\D/g, '')
  // tira código país BR (55) se presente
  const local = digits.startsWith('55') && digits.length >= 12 ? digits.slice(2) : digits
  if (local.length === 11) {
    return `(${local.slice(0, 2)}) ${local.slice(2, 3)} ${local.slice(3, 7)}-${local.slice(7)}`
  }
  if (local.length === 10) {
    return `(${local.slice(0, 2)}) ${local.slice(2, 6)}-${local.slice(6)}`
  }
  return jid
}

/** Trunca nome longo pra caber na lista. */
function truncate(s: string, max = 24): string {
  return s.length > max ? `${s.slice(0, max - 1)}…` : s
}

type StatusFilter = '' | 'aguardando' | 'humano' | 'bot' | 'encerrada'

/** True se a conversa está na fila humana há mais tempo que o SLA. */
function slaExcedido(c: ConversaListItem, now: number): boolean {
  if (c.status !== 'aguardando' || !c.transferred_at) return false
  const desde = new Date(c.transferred_at).getTime()
  if (Number.isNaN(desde)) return false
  return now - desde > (c.sla_minutes ?? 15) * 60_000
}

/** Tudo que linha (tabela) e cartão (celular) mostram de uma conversa. */
interface ConversaLinha {
  c: ConversaListItem
  href: string
  telefone: string
  tituloFull: string
  /** Telefone abaixo do nome — null quando o próprio título já é o telefone. */
  subtitulo: string | null
  /** Nome do canal, só quando há mais de um canal configurado. */
  canalNome: string | null
  estourou: boolean
  temSla: boolean
}

function derivarLinha(c: ConversaListItem, canalNome: string | null, now: number): ConversaLinha {
  const telefone = formatWhatsappBr(c.whatsapp)
  return {
    c,
    href: `/conversas/${c.id}`,
    telefone,
    tituloFull: c.cliente_nome ?? telefone,
    subtitulo: c.cliente_nome ? telefone : null,
    canalNome,
    estourou: slaExcedido(c, now),
    temSla: c.status === 'aguardando' && !!c.transferred_at,
  }
}

interface ConversaItemProps {
  v: ConversaLinha
  onOpen: (e: React.MouseEvent<HTMLElement>, href: string) => void
  onAbrirOs: (id: string) => void
}

function CanalTag({ nome }: { nome: string }) {
  return (
    <span className="rounded border px-1.5 text-[10px] leading-4 text-muted-foreground">
      {nome}
    </span>
  )
}

/** Linha da tabela (md+). */
function ConversaRow({ v, onOpen, onAbrirOs }: ConversaItemProps) {
  const { c } = v
  return (
    <tr
      className={cn('cursor-pointer', v.estourou && 'animate-breach')}
      onClick={(e) => onOpen(e, v.href)}
    >
      <td>
        <div className="flex items-center gap-3">
          <Avatar name={c.cliente_nome ?? '?'} />
          <div className="min-w-0">
            <Link
              href={v.href}
              className={cn(
                'rounded-sm font-medium text-foreground hover:underline',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                !c.cliente_nome && 'num',
              )}
              title={v.tituloFull}
            >
              {truncate(v.tituloFull)}
            </Link>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
              {v.subtitulo && (
                <span className="num text-xs text-muted-foreground">{v.subtitulo}</span>
              )}
              {v.canalNome && <CanalTag nome={v.canalNome} />}
            </div>
          </div>
        </div>
      </td>
      <td>
        <ConversaStatusPill status={c.status} size="sm" />
      </td>
      <td>
        <span className="num rounded border bg-muted/60 px-1.5 py-0.5 text-[11px] text-muted-foreground">
          {c.estado}
        </span>
      </td>
      <td>
        <Age iso={c.last_message_at} />
      </td>
      <td>
        {v.temSla && c.transferred_at ? (
          <ConversaSlaTimer transferredAt={c.transferred_at} slaMinutes={c.sla_minutes ?? 15} />
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </td>
      <td>
        <ConversaRowActions c={c} onAbrirOs={onAbrirOs} />
      </td>
    </tr>
  )
}

/** Cartão da lista no celular (abaixo de md) — mesmos dados e ações da linha. */
function ConversaCard({ v, onOpen, onAbrirOs }: ConversaItemProps) {
  const { c } = v
  return (
    <li
      className={cn(
        'relative cursor-pointer overflow-hidden rounded-lg border bg-card p-3 transition-colors active:bg-elevated',
        v.estourou && 'border-destructive/40',
      )}
      onClick={(e) => onOpen(e, v.href)}
    >
      {/* SLA estourado: mesmo pulso da linha da tabela, por cima do fundo do cartão. */}
      {v.estourou && (
        <span aria-hidden className="pointer-events-none absolute inset-0 animate-breach" />
      )}
      <div className="flex items-start gap-3">
        <Avatar name={c.cliente_nome ?? '?'} className="mt-0.5" />
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-2">
            <Link
              href={v.href}
              className={cn(
                'min-w-0 flex-1 truncate rounded-sm text-sm font-medium text-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                !c.cliente_nome && 'num',
              )}
              title={v.tituloFull}
            >
              {v.tituloFull}
            </Link>
            <Age iso={c.last_message_at} className="shrink-0" />
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5">
            {v.subtitulo && (
              <span className="num text-xs text-muted-foreground">{v.subtitulo}</span>
            )}
            {v.canalNome && <CanalTag nome={v.canalNome} />}
          </div>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
          <ConversaStatusPill status={c.status} size="sm" />
          {v.temSla && c.transferred_at && (
            <ConversaSlaTimer transferredAt={c.transferred_at} slaMinutes={c.sla_minutes ?? 15} />
          )}
        </div>
        <ConversaRowActions c={c} onAbrirOs={onAbrirOs} touch />
      </div>
    </li>
  )
}

export function ConversaList() {
  const router = useRouter()
  const [status, setStatus] = useState<StatusFilter>('')
  const [busca, setBusca] = useState('')
  const [q, setQ] = useState('')
  const [canalId, setCanalId] = useState('')
  const [abrirOsConversaId, setAbrirOsConversaId] = useState<string | null>(null)
  // debounce 300ms: digita em `busca`, aplica em `q` (o que vai pra API)
  useEffect(() => {
    const t = setTimeout(() => setQ(busca.trim()), 300)
    return () => clearTimeout(t)
  }, [busca])
  const now = useNow(15_000)
  const { data: metricas } = useMetricas()
  const { data: canais } = useCanais()
  const canalById = new Map((canais ?? []).map((c) => [c.id, c]))
  const multiCanal = !!canais && canais.length > 1
  const {
    data, isLoading, error, hasNextPage, fetchNextPage, isFetchingNextPage,
  } = useConversas({
    status: status || undefined,
    q: q || undefined,
    canal_id: canalId || undefined,
  })
  const conversas = data?.pages.flatMap((p) => p.items) ?? []
  // Valores derivados por conversa — calculados uma vez, usados pela linha da
  // tabela (md+) e pelo cartão (celular).
  const linhas = conversas.map((c) =>
    derivarLinha(
      c,
      multiCanal && c.canal_id ? (canalById.get(c.canal_id)?.nome ?? null) : null,
      now,
    ),
  )

  function abrirConversa(e: React.MouseEvent<HTMLElement>, href: string) {
    // Links e botões da linha/cartão cuidam do próprio clique.
    if ((e.target as HTMLElement).closest('a, button')) return
    router.push(href)
  }

  const tabs: FilterTab<StatusFilter>[] = [
    { value: '', label: 'Todas' },
    {
      value: 'aguardando',
      label: 'Aguardando',
      tone: 'warning',
      count: metricas?.conversas_aguardando,
    },
    { value: 'humano', label: 'Humano', tone: 'info', count: metricas?.conversas_humano },
    { value: 'bot', label: 'Bot', tone: 'muted' },
    { value: 'encerrada', label: 'Encerrada', tone: 'success' },
  ]

  return (
    <div className="space-y-3">
      {abrirOsConversaId && (
        <DialogAbrirOsFromConversa
          conversaId={abrirOsConversaId}
          onClose={() => setAbrirOsConversaId(null)}
        />
      )}

      <div className="flex flex-wrap items-center gap-2">
        <FilterTabs
          tabs={tabs}
          value={status}
          onChange={setStatus}
          ariaLabel="Filtrar conversas por status"
          className={TABS_SCROLL}
        />
        <div className="flex w-full flex-wrap items-center gap-2 md:ml-auto md:w-auto">
          {multiCanal && (
            <Select
              value={canalId}
              onChange={(e) => setCanalId(e.target.value)}
              className="w-full md:w-[180px]"
              aria-label="Filtrar por canal"
            >
              <option value="">Todos os canais</option>
              {(canais ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.nome}</option>
              ))}
            </Select>
          )}
          <div className="relative w-full md:w-64">
            <Search
              aria-hidden
              className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            />
            <Input
              type="search"
              placeholder="Buscar por nome ou WhatsApp…"
              aria-label="Buscar por nome ou WhatsApp"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="pl-8 max-md:h-10 max-md:text-base"
            />
          </div>
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/[0.08] p-4"
        >
          <AlertCircle aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground">
              Não foi possível carregar as conversas
            </p>
            <p className="mt-0.5 break-words text-xs text-muted-foreground">
              {error instanceof Error ? error.message : 'Erro ao carregar'}
            </p>
          </div>
        </div>
      )}

      {isLoading && (
        <div className="overflow-hidden rounded-lg border bg-card">
          <SkeletonRows rows={8} />
        </div>
      )}

      {!isLoading && !error && conversas.length === 0 && (
        <div className="rounded-lg border bg-card px-6 py-14 text-center">
          <span className="mx-auto flex h-10 w-10 items-center justify-center rounded-md bg-muted">
            <MessageSquare aria-hidden className="h-5 w-5 text-muted-foreground" />
          </span>
          <h3 className="mt-3 text-sm font-medium">Nenhuma conversa encontrada</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {q || status || canalId
              ? 'Ajuste os filtros para ver outras conversas.'
              : 'Quando alguém mandar mensagem no WhatsApp, aparece aqui.'}
          </p>
        </div>
      )}

      {linhas.length > 0 && (
        <>
          {/* Celular: um cartão tocável por conversa. */}
          <ul className="space-y-2 md:hidden">
            {linhas.map((v) => (
              <ConversaCard
                key={v.c.id}
                v={v}
                onOpen={abrirConversa}
                onAbrirOs={setAbrirOsConversaId}
              />
            ))}
          </ul>

          {/* De md pra cima: tabela. */}
          <div className="hidden overflow-hidden rounded-lg border bg-card md:block">
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Cliente</th>
                    <th>Status</th>
                    <th>Estado</th>
                    <th>Última msg</th>
                    <th>Fila / SLA</th>
                    <th className="text-right">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {linhas.map((v) => (
                    <ConversaRow
                      key={v.c.id}
                      v={v}
                      onOpen={abrirConversa}
                      onAbrirOs={setAbrirOsConversaId}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
      {hasNextPage && (
        <div className="flex justify-center pt-2">
          <Button
            variant="outline"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
          >
            {isFetchingNextPage ? 'Carregando…' : 'Carregar mais'}
          </Button>
        </div>
      )}
    </div>
  )
}
