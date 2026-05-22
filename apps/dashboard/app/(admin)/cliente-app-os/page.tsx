'use client'
import { useEffect, useRef, useState } from 'react'
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
  aberto: 'bg-blue-50 text-blue-700 border border-blue-200',
  em_atendimento: 'bg-amber-50 text-amber-700 border border-amber-200',
  concluido: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  cancelado: 'bg-zinc-100 text-zinc-600 border border-zinc-200',
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

  return (
    <div className="space-y-6 p-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 flex items-center gap-2">
            <Smartphone className="h-6 w-6 text-indigo-600" />
            Chamados do app cliente
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
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
            <div className="p-6 text-sm text-zinc-500">Carregando…</div>
          )}
          {error && (
            <div className="p-6 text-sm text-red-600">
              Erro ao carregar: {(error as Error).message}
            </div>
          )}
          {!isLoading && !error && items.length === 0 && (
            <div className="p-12 text-center text-sm text-zinc-500">
              Nenhum chamado nessa categoria.
            </div>
          )}
          <ul className="divide-y divide-zinc-100">
            {items.map((o) => {
              const Icon = TIPO_ICON[o.tipo]
              return (
                <li
                  key={o.id}
                  className="cursor-pointer p-4 hover:bg-zinc-50 transition"
                  onClick={() => setOpenDetail(o)}
                >
                  <div className="flex items-start gap-3">
                    <div className="rounded-lg bg-indigo-50 p-2 mt-0.5">
                      <Icon className="h-5 w-5 text-indigo-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-zinc-900">
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
                      </div>
                      <p className="mt-1 text-sm text-zinc-700 line-clamp-2">
                        {o.descricao || '—'}
                      </p>
                      <div className="mt-1.5 flex items-center gap-3 text-xs text-zinc-500">
                        <span>
                          <UserIcon className="inline h-3 w-3 mr-0.5" />
                          {o.cliente_nome || '(sem nome)'} · CPF ***-{o.cliente_cpf_last4}
                        </span>
                        <span>
                          <Phone className="inline h-3 w-3 mr-0.5" />
                          {o.cliente_telefone || '—'}
                        </span>
                        <span>
                          <Clock className="inline h-3 w-3 mr-0.5" />
                          {fmtDate(o.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                </li>
              )
            })}
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
    blue: 'border-blue-200 bg-blue-50',
    amber: 'border-amber-200 bg-amber-50',
    emerald: 'border-emerald-200 bg-emerald-50',
    zinc: 'border-zinc-200 bg-zinc-50',
  }
  return (
    <button
      onClick={props.onClick}
      className={cn(
        'rounded-xl border bg-white p-4 text-left transition hover:shadow-sm',
        props.active && colors[props.color],
        props.active && 'ring-2 ring-offset-1 ring-indigo-300',
      )}
    >
      <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">
        {props.label}
      </div>
      <div className="mt-1 text-2xl font-bold text-zinc-900">{props.value}</div>
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

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/30"
        onClick={props.onClose}
      />
      <aside className="fixed inset-y-0 right-0 z-50 w-full max-w-xl overflow-y-auto bg-white shadow-xl">
        <div className="border-b border-zinc-200 p-6">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                {TIPO_LABEL[o.tipo]}
              </div>
              <h2 className="mt-1 text-xl font-bold text-zinc-900">
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
          <div className="mt-4 flex border-b border-zinc-200 -mb-px">
            {(['detalhes', 'chat'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cn(
                  'px-4 py-2 text-sm font-semibold border-b-2 transition',
                  tab === t
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-zinc-500 hover:text-zinc-700',
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
        <div className="space-y-5 p-6">
          {/* Acao primaria — despachar pra tecnico */}
          <button
            onClick={() => setDespacharOpen(true)}
            className="flex w-full items-center gap-3 rounded-lg border-2 border-indigo-200 bg-indigo-50 px-4 py-3 text-left transition hover:border-indigo-300 hover:bg-indigo-100"
          >
            <div className="rounded-md bg-indigo-600 p-2">
              <Wrench className="h-5 w-5 text-white" />
            </div>
            <div className="flex-1">
              <div className="font-semibold text-indigo-900">
                Despachar pra técnico
              </div>
              <div className="text-xs text-indigo-700">
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
              value={`***.***.***-${o.cliente_cpf_last4}`}
            />
          </Section>

          <Section title="Descrição">
            <div className="whitespace-pre-wrap text-sm text-zinc-800">
              {o.descricao || '—'}
            </div>
          </Section>

          {Object.keys(o.payload).length > 0 && (
            <Section title="Dados adicionais">
              <pre className="overflow-x-auto rounded-md bg-zinc-50 p-3 text-xs text-zinc-700">
                {JSON.stringify(o.payload, null, 2)}
              </pre>
            </Section>
          )}

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
                className="flex-1 rounded-md border border-zinc-200 px-3 py-1.5 text-sm"
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
        </div>
        )}
      </aside>
      <DialogDespacharTecnico
        open={despacharOpen}
        onClose={() => setDespacharOpen(false)}
        problemaSugerido={o.descricao}
        clienteNome={o.cliente_nome}
        clienteTelefone={o.cliente_telefone}
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
    <div className="flex h-[calc(100vh-180px)] flex-col">
      {/* Status bar */}
      <div className="border-b border-zinc-200 bg-zinc-50 px-6 py-3">
        {isLoading ? (
          <div className="text-xs text-zinc-500">Carregando conversa…</div>
        ) : data?.handoff_active ? (
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-emerald-700">
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
          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-600">
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
        className="flex-1 space-y-2 overflow-y-auto bg-zinc-50 p-6"
      >
        {(data?.messages ?? []).map((m) => (
          <ChatMessageBubble key={m.id} msg={m} />
        ))}
        {!isLoading && (data?.messages.length ?? 0) === 0 && (
          <div className="py-8 text-center text-sm text-zinc-500">
            Nenhuma mensagem ainda.
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-zinc-200 bg-white p-4">
        <div className="flex items-end gap-2">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Mensagem como atendente…"
            rows={2}
            className="flex-1 resize-none rounded-md border border-zinc-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
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
            className="bg-indigo-600 hover:bg-indigo-700"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="mt-1 text-[10px] text-zinc-400">
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
          isUser && 'rounded-bl-md bg-white text-zinc-900 shadow-sm',
          isAtendente && 'rounded-br-md bg-indigo-600 text-white',
          !isUser &&
            !isAtendente &&
            'rounded-br-md bg-zinc-200 text-zinc-700',
        )}
      >
        {!isUser && (
          <div
            className={cn(
              'mb-0.5 text-[10px] font-semibold uppercase tracking-wide',
              isAtendente ? 'text-indigo-200' : 'text-zinc-500',
            )}
          >
            {isAtendente ? 'Você' : 'Bot'}
          </div>
        )}
        <div className="whitespace-pre-wrap">{m.content}</div>
        <div
          className={cn(
            'mt-1 text-[10px]',
            isAtendente ? 'text-indigo-200' : 'text-zinc-400',
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
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
        {props.title}
      </h3>
      <div className="space-y-2 rounded-lg bg-zinc-50 p-3">{props.children}</div>
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
      <Icon className="h-4 w-4 text-zinc-400" />
      <span className="text-zinc-500">{props.label}:</span>
      <span className="font-medium text-zinc-900">{props.value}</span>
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
          ? 'border-indigo-300 bg-indigo-50 text-indigo-700 cursor-default'
          : 'border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50',
        props.disabled && !props.active && 'opacity-50 cursor-not-allowed',
      )}
    >
      <Icon className="h-4 w-4" />
      {props.label}
    </button>
  )
}
