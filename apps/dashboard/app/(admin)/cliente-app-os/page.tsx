'use client'
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Smartphone,
  WifiOff,
  Home,
  ArrowLeftRight,
  Clock,
  CheckCircle2,
  XCircle,
  PlayCircle,
  Phone,
  Mail,
  User as UserIcon,
  FileText,
  Send,
  MessageSquare,
  Headphones,
  Wrench,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { DialogDespacharTecnico } from '@/components/dialog-despachar-tecnico'
import {
  useClienteAppChatRelease,
  useClienteAppChatSend,
  useClienteAppChatTake,
  useClienteAppChatThread,
  useClienteAppOsList,
  usePatchClienteAppOs,
  type ClienteAppOsFilter,
} from '@/lib/api/queries'
import type {
  ClienteAppChatMessage,
  ClienteAppOsAdminItem,
} from '@/lib/api/types'
import { cn } from '@/lib/utils'

type StatusFilter = ClienteAppOsAdminItem['status'] | 'all'

const STATUS_LABEL: Record<ClienteAppOsAdminItem['status'], string> = {
  aberto: 'Aberto',
  em_atendimento: 'Em atendimento',
  concluido: 'Concluído',
  cancelado: 'Cancelado',
}

const STATUS_STYLE: Record<ClienteAppOsAdminItem['status'], string> = {
  aberto: 'bg-info/[0.10] text-info border border-info/30',
  em_atendimento: 'bg-warning/[0.10] text-warning border border-warning/30',
  concluido: 'bg-success/[0.10] text-success border border-success/30',
  cancelado: 'bg-muted text-muted-foreground border border-border',
}

const TIPO_LABEL: Record<ClienteAppOsAdminItem['tipo'], string> = {
  sem_internet: 'Sem internet',
  mudanca_endereco: 'Mudança de endereço',
  troca_plano: 'Troca de plano',
}

const TIPO_ICON: Record<ClienteAppOsAdminItem['tipo'], React.ComponentType<{ className?: string }>> = {
  sem_internet: WifiOff,
  mudanca_endereco: Home,
  troca_plano: ArrowLeftRight,
}

function fmtDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

function fmtCpf(d: string): string {
  const digits = (d ?? '').replace(/\D/g, '')
  if (digits.length !== 11) return d || '—'
  return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`
}

export default function ClienteAppOsPage() {
  const [status, setStatus] = useState<StatusFilter>('aberto')
  const [openDetail, setOpenDetail] = useState<ClienteAppOsAdminItem | null>(null)

  const filter: ClienteAppOsFilter = {
    status: status === 'all' ? undefined : status,
    limit: 100,
  }
  const { data, isLoading, error } = useClienteAppOsList(filter)
  const items = data?.items ?? []
  const counts = data?.counts_by_status ?? {}

  // Agrupa chamados pelo cliente (cliente_app_user_id). Mantém a ordem de
  // chegada do primeiro chamado do cliente, e dentro de cada cliente ordena
  // do mais recente pro mais antigo.
  const grupos = useMemo(() => {
    const map = new Map<string, { cliente: ClienteAppOsAdminItem; chamados: ClienteAppOsAdminItem[] }>()
    for (const o of items) {
      const key = o.cliente_app_user_id
      const slot = map.get(key)
      if (slot) {
        slot.chamados.push(o)
      } else {
        map.set(key, { cliente: o, chamados: [o] })
      }
    }
    for (const g of map.values()) {
      g.chamados.sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      )
    }
    return Array.from(map.values())
  }, [items])

  return (
    <div className="space-y-6 sm:p-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-bold text-foreground sm:text-2xl">
            <Smartphone className="h-6 w-6 shrink-0 text-info" />
            Chamados do app cliente
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Chamados abertos pelos clientes via app mobile (sem internet, mudança de endereço, troca de plano).
          </p>
        </div>
      </header>

      {/* Cards de contagem */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <CountCard
          label="Abertos"
          value={counts.aberto ?? 0}
          color="blue"
          active={status === 'aberto'}
          onClick={() => setStatus('aberto')}
        />
        <CountCard
          label="Em atendimento"
          value={counts.em_atendimento ?? 0}
          color="amber"
          active={status === 'em_atendimento'}
          onClick={() => setStatus('em_atendimento')}
        />
        <CountCard
          label="Concluídos"
          value={counts.concluido ?? 0}
          color="emerald"
          active={status === 'concluido'}
          onClick={() => setStatus('concluido')}
        />
        <CountCard
          label="Todos"
          value={Object.values(counts).reduce((a, b) => a + b, 0)}
          color="zinc"
          active={status === 'all'}
          onClick={() => setStatus('all')}
        />
      </div>

      {/* Lista */}
      <Card>
        <CardContent className="p-0">
          {isLoading && (
            <div className="p-6 text-sm text-muted-foreground">Carregando…</div>
          )}
          {error && (
            <div className="p-6 text-sm text-destructive">
              Erro ao carregar: {(error as Error).message}
            </div>
          )}
          {!isLoading && !error && items.length === 0 && (
            <div className="p-12 text-center text-sm text-muted-foreground">
              Nenhum chamado nessa categoria.
            </div>
          )}
          <ul className="divide-y divide-border">
            {grupos.map(({ cliente, chamados }) => (
              <li key={cliente.cliente_app_user_id} className="p-4">
                {/* Header do cliente */}
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="rounded-full bg-muted p-2">
                      <UserIcon className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div className="min-w-0">
                      <div className="font-semibold text-foreground truncate">
                        {cliente.cliente_nome || '(sem nome)'}
                      </div>
                      <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
                        <span>
                          <Phone className="inline h-3 w-3 mr-0.5" />
                          {cliente.cliente_telefone || '—'}
                        </span>
                        <span>CPF ***-{cliente.cliente_cpf_last4}</span>
                      </div>
                    </div>
                  </div>
                  <span className="shrink-0 rounded-full bg-info/[0.10] px-2 py-0.5 text-xs font-semibold text-info border border-info/30">
                    {chamados.length}{' '}
                    {chamados.length === 1 ? 'chamado' : 'chamados'}
                  </span>
                </div>

                {/* Chamados desse cliente */}
                <ul className="mt-3 space-y-2 sm:pl-11">
                  {chamados.map((o) => {
                    const Icon = TIPO_ICON[o.tipo]
                    return (
                      <li
                        key={o.id}
                        className="cursor-pointer rounded-lg border border-border p-3 hover:border-info/30 hover:bg-info/30 transition"
                        onClick={() => setOpenDetail(o)}
                      >
                        <div className="flex items-start gap-3">
                          <div className="rounded-md bg-info/[0.10] p-1.5 mt-0.5">
                            <Icon className="h-4 w-4 text-info" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-medium text-foreground text-sm">
                                {TIPO_LABEL[o.tipo]}
                              </span>
                              <span
                                className={cn(
                                  'rounded-md px-2 py-0.5 text-xs font-medium',
                                  STATUS_STYLE[o.status],
                                )}
                              >
                                {STATUS_LABEL[o.status]}
                              </span>
                              <span className="ml-auto text-xs text-muted-foreground">
                                <Clock className="inline h-3 w-3 mr-0.5" />
                                {fmtDate(o.created_at)}
                              </span>
                            </div>
                            {o.descricao && (
                              <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                                {o.descricao}
                              </p>
                            )}
                          </div>
                        </div>
                      </li>
                    )
                  })}
                </ul>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {openDetail && (
        <DetailDrawer
          item={openDetail}
          onClose={() => setOpenDetail(null)}
        />
      )}
    </div>
  )
}

function CountCard(props: {
  label: string
  value: number
  color: 'blue' | 'amber' | 'emerald' | 'zinc'
  active: boolean
  onClick: () => void
}) {
  const colors = {
    blue: 'border-info/30 bg-info/[0.10]',
    amber: 'border-warning/30 bg-warning/[0.10]',
    emerald: 'border-success/30 bg-success/[0.10]',
    zinc: 'border-border bg-muted/50',
  }
  return (
    <button
      onClick={props.onClick}
      className={cn(
        'rounded-xl border bg-card p-4 text-left transition hover:shadow-sm',
        props.active && colors[props.color],
        props.active && 'ring-2 ring-offset-1 ring-info/30',
      )}
    >
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {props.label}
      </div>
      <div className="mt-1 text-2xl font-bold text-foreground">{props.value}</div>
    </button>
  )
}

function DetailDrawer(props: {
  item: ClienteAppOsAdminItem
  onClose: () => void
}) {
  const o = props.item
  const patch = usePatchClienteAppOs(o.id)
  const [sgpId, setSgpId] = useState(o.sgp_protocolo_id ?? '')
  const [tab, setTab] = useState<'detalhes' | 'chat'>('detalhes')
  const [despacharOpen, setDespacharOpen] = useState(false)

  async function changeStatus(s: ClienteAppOsAdminItem['status']) {
    try {
      await patch.mutateAsync({ status: s })
    } catch (e) {
      alert((e as Error).message)
    }
  }

  async function assignToMe() {
    try {
      await patch.mutateAsync({ assign_to_me: true })
    } catch (e) {
      alert((e as Error).message)
    }
  }

  async function saveSgpId() {
    try {
      await patch.mutateAsync({ sgp_protocolo_id: sgpId || null })
    } catch (e) {
      alert((e as Error).message)
    }
  }

  async function toggleVisitaTecnica() {
    try {
      await patch.mutateAsync({ teve_visita_tecnica: !o.teve_visita_tecnica })
    } catch (e) {
      alert((e as Error).message)
    }
  }

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/30"
        onClick={props.onClose}
      />
      <aside className="fixed inset-y-0 right-0 z-50 w-full max-w-xl overflow-y-auto bg-card shadow-xl">
        <div className="border-b border-border p-4 sm:p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {TIPO_LABEL[o.tipo]}
              </div>
              <h2 className="mt-1 text-xl font-bold text-foreground">
                {o.cliente_nome || '(sem nome)'}
              </h2>
              <span
                className={cn(
                  'mt-2 inline-flex rounded-md px-2 py-0.5 text-xs font-medium',
                  STATUS_STYLE[o.status],
                )}
              >
                {STATUS_LABEL[o.status]}
              </span>
            </div>
            <Button variant="ghost" size="sm" onClick={props.onClose}>
              Fechar
            </Button>
          </div>
          <div className="mt-4 flex border-b border-border -mb-px">
            {(['detalhes', 'chat'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cn(
                  'px-4 py-2 text-sm font-semibold border-b-2 transition',
                  tab === t
                    ? 'border-info text-info'
                    : 'border-transparent text-muted-foreground hover:text-foreground/90',
                )}
              >
                {t === 'detalhes' ? 'Detalhes' : 'Chat'}
              </button>
            ))}
          </div>
        </div>

        {tab === 'chat' ? (
          <ChatPanel userId={o.cliente_app_user_id} />
        ) : (
        <div className="space-y-5 p-4 sm:p-6">
          {/* Acao primaria — despachar pra tecnico */}
          <button
            onClick={() => setDespacharOpen(true)}
            className="flex w-full items-center gap-3 rounded-lg border-2 border-info/30 bg-info/[0.10] px-4 py-3 text-left transition hover:border-info/30 hover:bg-info/[0.14]"
          >
            <div className="rounded-md bg-info p-2">
              <Wrench className="h-5 w-5 text-info-foreground" />
            </div>
            <div className="flex-1">
              <div className="font-semibold text-info">
                Despachar pra técnico
              </div>
              <div className="text-xs text-info">
                Cria OS em /os com técnico atribuído e notifica via WhatsApp.
              </div>
            </div>
          </button>

          <Section title="Cliente">
            <Field icon={Phone} label="Telefone" value={o.cliente_telefone || '—'} />
            <Field
              icon={Mail}
              label="Email"
              value={o.cliente_email || '—'}
            />
            <Field
              icon={UserIcon}
              label="CPF"
              value={fmtCpf(o.cliente_cpf)}
            />
          </Section>

          <Section title="Descrição">
            <div className="whitespace-pre-wrap text-sm text-foreground">
              {o.descricao || '—'}
            </div>
          </Section>

          {(() => {
            const diag = o.payload.diagnostico as
              | { online?: boolean; total_aparelhos?: number; saude?: string; timestamp?: string; contrato_id?: string | null }
              | undefined
            return diag != null ? (
              <Section title="Diagnóstico na abertura">
                <div className="grid gap-2 sm:grid-cols-3 text-sm">
                  <div className="rounded-md border bg-card p-3">
                    <div className="text-xs text-muted-foreground">ONU</div>
                    <div className="font-semibold">
                      {diag.online ? 'Online' : 'Offline'}
                    </div>
                  </div>
                  <div className="rounded-md border bg-card p-3">
                    <div className="text-xs text-muted-foreground">Aparelhos conectados</div>
                    <div className="font-semibold">
                      {diag.total_aparelhos != null ? String(diag.total_aparelhos) : '—'}
                    </div>
                  </div>
                  <div className="rounded-md border bg-card p-3">
                    <div className="text-xs text-muted-foreground">Sinal</div>
                    <div className="font-semibold capitalize">
                      {diag.saude ?? '—'}
                    </div>
                  </div>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Capturado no momento da abertura
                  {diag.timestamp
                    ? ` — ${new Date(diag.timestamp).toLocaleString('pt-BR')}`
                    : ''}
                  {diag.contrato_id != null ? ` · Contrato ${diag.contrato_id}` : ''}
                </p>
              </Section>
            ) : null
          })()}

          {(() => {
            const rest = Object.fromEntries(
              Object.entries(o.payload).filter(([k]) => k !== 'diagnostico'),
            )
            return Object.keys(rest).length > 0 ? (
              <Section title="Dados adicionais">
                <pre className="overflow-x-auto rounded-md bg-muted/50 p-3 text-xs text-foreground/90">
                  {JSON.stringify(rest, null, 2)}
                </pre>
              </Section>
            ) : null
          })()}

          <Section title="Atendimento">
            <Field
              icon={UserIcon}
              label="Atendente"
              value={o.atendente_nome ?? '(não atribuído)'}
            />
            <Field icon={Clock} label="Aberto em" value={fmtDate(o.created_at)} />
            <Field icon={Clock} label="Atualizado em" value={fmtDate(o.updated_at)} />
            <div className="pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={assignToMe}
                disabled={patch.isPending}
              >
                Atribuir a mim
              </Button>
            </div>
          </Section>

          <Section title="Protocolo SGP">
            <div className="flex gap-2">
              <input
                type="text"
                value={sgpId}
                onChange={(e) => setSgpId(e.target.value)}
                placeholder="ID do protocolo no SGP"
                className="flex-1 rounded-md border border-border px-3 py-1.5 text-sm"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={saveSgpId}
                disabled={patch.isPending || sgpId === (o.sgp_protocolo_id ?? '')}
              >
                Salvar
              </Button>
            </div>
          </Section>

          <Section title="Mudar status">
            <div className="grid grid-cols-2 gap-2">
              <StatusButton
                icon={PlayCircle}
                label="Em atendimento"
                active={o.status === 'em_atendimento'}
                disabled={patch.isPending}
                onClick={() => changeStatus('em_atendimento')}
              />
              <StatusButton
                icon={CheckCircle2}
                label="Concluído"
                active={o.status === 'concluido'}
                disabled={patch.isPending}
                onClick={() => changeStatus('concluido')}
              />
              <StatusButton
                icon={FileText}
                label="Aberto"
                active={o.status === 'aberto'}
                disabled={patch.isPending}
                onClick={() => changeStatus('aberto')}
              />
              <StatusButton
                icon={XCircle}
                label="Cancelar"
                active={o.status === 'cancelado'}
                disabled={patch.isPending}
                onClick={() => changeStatus('cancelado')}
              />
            </div>
          </Section>

          <Section title="Visita técnica">
            <button
              type="button"
              onClick={toggleVisitaTecnica}
              disabled={patch.isPending}
              className={cn(
                'flex w-full items-center justify-between rounded-lg border-2 px-4 py-3 text-left transition',
                o.teve_visita_tecnica
                  ? 'border-success/30 bg-success/[0.10] text-success hover:border-success/30'
                  : 'border-border bg-card text-foreground/90 hover:border-border',
              )}
            >
              <div>
                <div className="font-semibold">
                  {o.teve_visita_tecnica ? 'Teve visita técnica ✓' : 'Sem visita técnica'}
                </div>
                <div className="mt-0.5 text-xs opacity-80">
                  Marque pra mostrar avaliação do técnico (3 perguntas) no NPS do cliente.
                </div>
              </div>
              <div
                className={cn(
                  'h-6 w-11 shrink-0 rounded-full transition',
                  o.teve_visita_tecnica ? 'bg-success' : 'bg-muted-foreground/30',
                )}
              >
                <div
                  className={cn(
                    'mt-0.5 h-5 w-5 rounded-full bg-card shadow transition',
                    o.teve_visita_tecnica ? 'ml-[22px]' : 'ml-0.5',
                  )}
                />
              </div>
            </button>
          </Section>

          {o.nps_respondido_em && (
            <Section title="Avaliação do cliente (NPS)">
              <div className="space-y-2">
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold">{o.nps_score ?? '—'}</span>
                  <span className="text-sm text-muted-foreground">/ 10</span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {fmtDate(o.nps_respondido_em)}
                  </span>
                </div>
                {o.teve_visita_tecnica && (
                  <div className="space-y-1 rounded-md border border-border bg-muted/50 p-3">
                    <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Sobre a visita técnica
                    </div>
                    <TecnicoAvaliacaoRow label="Chegou no horário?" valor={o.tecnico_pontual} />
                    <TecnicoAvaliacaoRow label="Foi educado?" valor={o.tecnico_educado} />
                    <TecnicoAvaliacaoRow label="Deixou limpo?" valor={o.tecnico_limpou} />
                  </div>
                )}
              </div>
            </Section>
          )}
        </div>
        )}
      </aside>
      <DialogDespacharTecnico
        open={despacharOpen}
        onClose={() => setDespacharOpen(false)}
        problemaSugerido={o.descricao}
        clienteNome={o.cliente_nome}
        clienteTelefone={o.cliente_telefone}
        clienteCpf={o.cliente_cpf}
        onCreated={() => {
          // Marca o chamado como em atendimento (best-effort)
          patch.mutate({ status: 'em_atendimento' })
        }}
      />
    </>
  )
}

function ChatPanel(props: { userId: string }) {
  const { data, isLoading } = useClienteAppChatThread(props.userId)
  const send = useClienteAppChatSend(props.userId)
  const take = useClienteAppChatTake(props.userId)
  const release = useClienteAppChatRelease(props.userId)
  const [text, setText] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [data?.messages.length])

  async function handleSend() {
    const t = text.trim()
    if (!t) return
    setText('')
    try {
      await send.mutateAsync(t)
    } catch (e) {
      alert((e as Error).message)
      setText(t)
    }
  }

  return (
    <div className="flex h-[calc(100dvh-180px)] min-h-[20rem] flex-col">
      {/* Status bar */}
      <div className="border-b border-border bg-muted/50 px-3 py-3 sm:px-6">
        {isLoading ? (
          <div className="text-xs text-muted-foreground">Carregando conversa…</div>
        ) : data?.handoff_active ? (
          <div className="flex items-center justify-between gap-2 text-xs">
            <span className="font-medium text-success">
              <Headphones className="inline h-3.5 w-3.5 mr-1" />
              Você está atendendo — bot pausado
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => release.mutate()}
              disabled={release.isPending}
            >
              Liberar pro bot
            </Button>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-2 text-xs">
            <span className="text-muted-foreground">
              <MessageSquare className="inline h-3.5 w-3.5 mr-1" />
              Bot está respondendo automaticamente
            </span>
            <Button
              size="sm"
              onClick={() => take.mutate()}
              disabled={take.isPending}
            >
              Assumir conversa
            </Button>
          </div>
        )}
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 space-y-2 overflow-y-auto bg-muted/50 p-3 sm:p-6"
      >
        {(data?.messages ?? []).map((m) => (
          <ChatMessageBubble key={m.id} msg={m} />
        ))}
        {!isLoading && (data?.messages.length ?? 0) === 0 && (
          <div className="py-8 text-center text-sm text-muted-foreground">
            Nenhuma mensagem ainda.
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-border bg-card p-4">
        <div className="flex items-end gap-2">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Mensagem como atendente…"
            rows={2}
            className="min-w-0 flex-1 resize-none rounded-md border border-border px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-info/30 sm:text-sm"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
          />
          <Button
            onClick={handleSend}
            disabled={send.isPending || !text.trim()}
            className="bg-info hover:bg-info"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="mt-1 text-[10px] text-muted-foreground">
          Enter envia · Shift+Enter quebra linha · Assumir conversa pausa o bot
        </p>
      </div>
    </div>
  )
}

function ChatMessageBubble(props: { msg: ClienteAppChatMessage }) {
  const m = props.msg
  const isUser = m.role === 'user'
  const isAtendente = m.role === 'atendente'
  return (
    <div
      className={cn(
        'flex',
        isUser ? 'justify-start' : 'justify-end',
      )}
    >
      <div
        className={cn(
          'max-w-[78%] rounded-2xl px-3 py-2 text-sm',
          isUser && 'rounded-bl-md bg-card text-foreground shadow-sm',
          isAtendente && 'rounded-br-md bg-info text-info-foreground',
          !isUser &&
            !isAtendente &&
            'rounded-br-md bg-secondary text-foreground/90',
        )}
      >
        {!isUser && (
          <div
            className={cn(
              'mb-0.5 text-[10px] font-semibold uppercase tracking-wide',
              isAtendente ? 'text-info' : 'text-muted-foreground',
            )}
          >
            {isAtendente ? 'Você' : 'Bot'}
          </div>
        )}
        <div className="whitespace-pre-wrap">{m.content}</div>
        <div
          className={cn(
            'mt-1 text-[10px]',
            isAtendente ? 'text-info' : 'text-muted-foreground',
          )}
        >
          {new Date(m.created_at).toLocaleTimeString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>
    </div>
  )
}

function Section(props: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {props.title}
      </h3>
      <div className="space-y-2 rounded-lg bg-muted/50 p-3">{props.children}</div>
    </div>
  )
}

function Field(props: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
}) {
  const Icon = props.icon
  return (
    <div className="flex items-center gap-2 text-sm">
      <Icon className="h-4 w-4 text-muted-foreground" />
      <span className="text-muted-foreground">{props.label}:</span>
      <span className="font-medium text-foreground">{props.value}</span>
    </div>
  )
}

function TecnicoAvaliacaoRow({
  label,
  valor,
}: {
  label: string
  valor: boolean | null
}) {
  let txt = '—'
  let cls = 'text-muted-foreground'
  if (valor === true) {
    txt = 'Sim'
    cls = 'text-success'
  } else if (valor === false) {
    txt = 'Não'
    cls = 'text-destructive'
  }
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-foreground/90">{label}</span>
      <span className={cn('font-bold', cls)}>{txt}</span>
    </div>
  )
}

function StatusButton(props: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  active: boolean
  disabled: boolean
  onClick: () => void
}) {
  const Icon = props.icon
  return (
    <button
      onClick={props.onClick}
      disabled={props.disabled || props.active}
      className={cn(
        'flex items-center justify-center gap-1.5 rounded-md border px-3 py-2 text-sm font-medium transition',
        props.active
          ? 'border-info/30 bg-info/[0.10] text-info cursor-default'
          : 'border-border bg-card text-foreground/90 hover:bg-muted/50',
        props.disabled && !props.active && 'opacity-50 cursor-not-allowed',
      )}
    >
      <Icon className="h-4 w-4" />
      {props.label}
    </button>
  )
}
