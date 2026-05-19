'use client'
import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronDown, ChevronUp, Search, Send, Trash2, UserCheck, X } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { QuickRepliesMenu, useQuickRepliesKeyHandler } from '@/components/quick-replies'
import {
  useAtender,
  useConversa,
  useCreateOs,
  useDeleteConversa,
  useEncerrar,
  useOsList,
  useResponder,
  useTecnicos,
  useVincularCliente,
} from '@/lib/api/queries'
import type { MensagemOut } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { ConversaSlaTimer } from './conversa-sla-timer'

type Tab = 'mensagens' | 'cliente' | 'nova-os'

const ROLE_LABEL: Record<string, string> = {
  cliente: 'Cliente',
  bot: 'Bot',
  atendente: 'Atendente',
}

const OS_STATUS_ABERTA = ['pendente', 'em_andamento']

interface SseEvent {
  type: string
  id?: string
  role?: string
  text?: string | null
  ts?: string | null
}

export function ConversaChat({ conversaId }: { conversaId: string }) {
  const router = useRouter()
  const { data, isLoading, refetch } = useConversa(conversaId)
  const responder = useResponder(conversaId)
  const atender = useAtender(conversaId)
  const encerrar = useEncerrar(conversaId)
  const deleteConversa = useDeleteConversa(conversaId)
  const createOs = useCreateOs()
  const { data: tecnicos } = useTecnicos({ ativo: true })

  const [tab, setTab] = useState<Tab>('mensagens')
  const [text, setText] = useState('')
  const [liveMsgs, setLiveMsgs] = useState<MensagemOut[]>([])
  const [osProblema, setOsProblema] = useState('')
  const [osEndereco, setOsEndereco] = useState('')
  const [osTecnicoId, setOsTecnicoId] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [currentMatch, setCurrentMatch] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)
  const msgRefs = useRef<Map<string, HTMLDivElement>>(new Map())

  const clienteId = data?.cliente_id ?? undefined
  // F13b: so buscamos OSs quando temos cliente_id. Sem isso, useOsList({})
  // devolveria TODAS as OS e o alerta apareceria em qualquer conversa.
  const { data: osAberta } = useOsList({ cliente_id: clienteId })
  const osAbertas = clienteId
    ? (osAberta?.items ?? []).filter((o) => OS_STATUS_ABERTA.includes(o.status))
    : []

  // Init OS form with client address
  useEffect(() => {
    if (data?.cliente?.endereco && !osEndereco) {
      setOsEndereco(data.cliente.endereco)
    }
  }, [data?.cliente?.endereco, osEndereco])

  // SSE real-time
  useEffect(() => {
    if (!conversaId) return
    const es = new EventSource(`/api/v1/conversas/${conversaId}/stream`, {
      withCredentials: true,
    })
    es.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data as string) as SseEvent
        if (payload.type !== 'msg' || !payload.role || !payload.text) return
        setLiveMsgs((prev) => [
          ...prev,
          {
            id: payload.id ?? `live-${Date.now()}`,
            conversa_id: conversaId,
            role: payload.role as MensagemOut['role'],
            content: payload.text ?? null,
            media_type: null,
            media_url: null,
            created_at: payload.ts ?? new Date().toISOString(),
          },
        ])
      } catch { /* ignore */ }
    }
    es.onerror = () => {}
    return () => es.close()
  }, [conversaId])

  const allMsgs = [...(data?.mensagens ?? []), ...liveMsgs]
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [allMsgs.length])

  // Indices de mensagens que casam com a busca (case-insensitive).
  const matchedIds = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return [] as string[]
    return allMsgs
      .filter((m) => (m.content ?? '').toLowerCase().includes(q))
      .map((m) => m.id)
  }, [searchQuery, allMsgs])

  // Reset cursor quando busca muda.
  useEffect(() => {
    setCurrentMatch(0)
  }, [searchQuery])

  // Scroll automatico pra match atual.
  useEffect(() => {
    if (matchedIds.length === 0) return
    const idx = Math.min(currentMatch, matchedIds.length - 1)
    const id = matchedIds[idx]
    const el = msgRefs.current.get(id)
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [currentMatch, matchedIds])

  // Atalho Cmd/Ctrl+F abre busca.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
        e.preventDefault()
        setSearchOpen(true)
      }
      if (e.key === 'Escape' && searchOpen) {
        setSearchOpen(false)
        setSearchQuery('')
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [searchOpen])

  function nextMatch() {
    if (matchedIds.length === 0) return
    setCurrentMatch((c) => (c + 1) % matchedIds.length)
  }
  function prevMatch() {
    if (matchedIds.length === 0) return
    setCurrentMatch((c) => (c - 1 + matchedIds.length) % matchedIds.length)
  }

  async function handleSend() {
    const trimmed = text.trim()
    if (!trimmed) return
    await responder.mutateAsync(trimmed)
    setText('')
    void refetch()
  }

  async function handleAbrirOs() {
    if (!data?.cliente_id || !osTecnicoId || !osProblema || !osEndereco) return
    await createOs.mutateAsync({
      cliente_id: data.cliente_id,
      tecnico_id: osTecnicoId,
      problema: osProblema,
      endereco: osEndereco,
    })
    setTab('mensagens')
    setOsProblema('')
    setOsEndereco('')
    void refetch()
  }

  async function handleDelete() {
    if (!confirm('Excluir esta conversa? O histórico será preservado por 30 dias.')) return
    await deleteConversa.mutateAsync()
    router.push('/conversas')
  }

  if (isLoading) return <p className="text-sm text-muted-foreground">Carregando…</p>
  if (!data) return <p className="text-sm text-destructive">Conversa não encontrada</p>

  const TABS: { id: Tab; label: string }[] = [
    { id: 'mensagens', label: 'Mensagens' },
    { id: 'cliente', label: 'Cliente SGP' },
    { id: 'nova-os', label: '+ Nova OS' },
  ]

  return (
    <div className="flex h-full gap-4">
      {/* ── centro: abas ── */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* OS abertas alert */}
        {osAbertas.length > 0 && (
          <div className="mb-3 rounded-md border border-yellow-400 bg-yellow-50 dark:bg-yellow-950/20 p-3 text-sm">
            <p className="font-semibold text-yellow-800 dark:text-yellow-300">
              ⚠️ OS em aberto para este cliente
            </p>
            {osAbertas.map((o) => (
              <p key={o.id} className="text-yellow-700 dark:text-yellow-400 text-xs">
                #{o.codigo} · {o.status} · {o.problema.slice(0, 50)}
              </p>
            ))}
          </div>
        )}

        {/* Resumo do handoff (F1) — TL;DR gerado pelo bot ao transferir pro humano */}
        {data.resumo_handoff && (
          <div className="mb-3 rounded-md border border-blue-300 bg-blue-50 dark:bg-blue-950/20 p-3 text-sm">
            <p className="mb-1 flex items-center gap-2 font-semibold text-blue-900 dark:text-blue-200">
              <span>🤖 Resumo do bot</span>
              {data.resumo_handoff_at && (
                <span className="text-xs font-normal opacity-70">
                  {new Date(data.resumo_handoff_at).toLocaleString('pt-BR')}
                </span>
              )}
            </p>
            <p className="whitespace-pre-line text-blue-900 dark:text-blue-100">
              {data.resumo_handoff}
            </p>
          </div>
        )}

        {/* Tab bar */}
        <div className="flex border-b mb-0">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                tab === t.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Tab: Mensagens */}
        {tab === 'mensagens' && (
          <div className="flex flex-1 flex-col gap-3 pt-3 min-h-0">
            {/* Barra de busca (toggle pelo botao ou Cmd+F) */}
            {searchOpen && (
              <div className="flex items-center gap-2 rounded-md border bg-card px-3 py-2">
                <Search className="h-4 w-4 text-muted-foreground" />
                <Input
                  autoFocus
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Buscar nesta conversa…"
                  className="h-8 border-0 px-0 shadow-none focus-visible:ring-0"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      if (e.shiftKey) prevMatch()
                      else nextMatch()
                    }
                  }}
                />
                <span className="whitespace-nowrap text-xs text-muted-foreground">
                  {matchedIds.length === 0
                    ? searchQuery ? '0' : ''
                    : `${currentMatch + 1}/${matchedIds.length}`}
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 w-7 p-0"
                  onClick={prevMatch}
                  disabled={matchedIds.length === 0}
                >
                  <ChevronUp className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 w-7 p-0"
                  onClick={nextMatch}
                  disabled={matchedIds.length === 0}
                >
                  <ChevronDown className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 w-7 p-0"
                  onClick={() => {
                    setSearchOpen(false)
                    setSearchQuery('')
                  }}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            )}

            <div
              ref={scrollRef}
              className="flex-1 space-y-3 overflow-y-auto rounded-md border bg-card p-4"
            >
              {allMsgs.length === 0 && (
                <p className="text-center text-sm text-muted-foreground">Sem mensagens</p>
              )}
              {allMsgs.map((m) => {
                const isMatch = matchedIds.includes(m.id)
                const isCurrent = isMatch && matchedIds[currentMatch] === m.id
                return (
                  <div
                    key={m.id}
                    ref={(el) => {
                      if (el) msgRefs.current.set(m.id, el)
                      else msgRefs.current.delete(m.id)
                    }}
                    className={cn(
                      'max-w-[70%] rounded-lg px-3 py-2 text-sm',
                      m.role === 'cliente'
                        ? 'bg-muted'
                        : m.role === 'bot'
                        ? 'ml-auto bg-secondary text-secondary-foreground'
                        : 'ml-auto bg-primary text-primary-foreground',
                      isCurrent && 'ring-2 ring-yellow-400 ring-offset-1',
                    )}
                  >
                    <div className="mb-1 flex items-center gap-2 text-xs opacity-70">
                      <Badge variant="outline" className="capitalize">
                        {ROLE_LABEL[m.role] ?? m.role}
                      </Badge>
                      <span>{new Date(m.created_at).toLocaleTimeString('pt-BR')}</span>
                    </div>
                    <div className="whitespace-pre-wrap">
                      {highlightMatches(m.content ?? '', searchQuery)}
                    </div>
                  </div>
                )
              })}
            </div>
            {data.status !== 'encerrada' && <ResponderBox text={text} setText={setText} handleSend={handleSend} pending={responder.isPending} />}
          </div>
        )}

        {/* Tab: Cliente SGP */}
        {tab === 'cliente' && (
          <div className="flex-1 overflow-y-auto rounded-md border bg-card p-4 mt-3 space-y-3 text-sm">
            {!data.cliente ? (
              <VincularClienteBox conversaId={conversaId} onSuccess={() => void refetch()} />
            ) : (
              <>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Nome</p>
                  <p className="font-semibold">{data.cliente.nome}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">CPF/CNPJ</p>
                  <p className="font-mono">{data.cliente.cpf_cnpj}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">WhatsApp</p>
                  <p>{data.cliente.whatsapp}</p>
                </div>
                {data.cliente.plano && (
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Plano</p>
                    <p>{data.cliente.plano}</p>
                  </div>
                )}
                {data.cliente.cidade && (
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Cidade</p>
                    <p>{data.cliente.cidade}</p>
                  </div>
                )}
                {data.cliente.endereco && (
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Endereço</p>
                    <p>{data.cliente.endereco}</p>
                  </div>
                )}
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Estado da conversa</p>
                  <div className="flex gap-2">
                    <Badge variant="outline">{data.estado}</Badge>
                    <Badge
                      variant={
                        data.status === 'aguardando'
                          ? 'destructive'
                          : data.status === 'humano'
                          ? 'default'
                          : 'secondary'
                      }
                    >
                      {data.status}
                    </Badge>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* Tab: Nova OS */}
        {tab === 'nova-os' && (
          <div className="flex-1 overflow-y-auto rounded-md border bg-card p-4 mt-3">
            {!data.cliente_id ? (
              <p className="text-sm text-muted-foreground">
                Cliente não identificado — não é possível abrir OS sem cliente vinculado.
              </p>
            ) : (
              <div className="space-y-4">
                {data.cliente && (
                  <div className="rounded-md bg-muted p-3 text-sm space-y-1">
                    <p><span className="font-medium">Cliente:</span> {data.cliente.nome}</p>
                    {data.cliente.cidade && (
                      <p><span className="font-medium">Cidade:</span> {data.cliente.cidade}</p>
                    )}
                  </div>
                )}
                <div className="space-y-3">
                  <div>
                    <Label htmlFor="os-tecnico">Técnico responsável *</Label>
                    <select
                      id="os-tecnico"
                      value={osTecnicoId}
                      onChange={(e) => setOsTecnicoId(e.target.value)}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="" disabled>Selecione o técnico</option>
                      {tecnicos?.items.map((t) => (
                        <option key={t.id} value={t.id}>{t.nome}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <Label htmlFor="os-problema">Problema *</Label>
                    <Textarea
                      id="os-problema"
                      placeholder="Descreva o problema…"
                      value={osProblema}
                      onChange={(e) => setOsProblema(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="os-endereco">Endereço *</Label>
                    <Input
                      id="os-endereco"
                      value={osEndereco}
                      onChange={(e) => setOsEndereco(e.target.value)}
                      placeholder="Rua e número"
                    />
                  </div>
                  {createOs.error && (
                    <p className="text-xs text-destructive">
                      {createOs.error instanceof Error ? createOs.error.message : 'Erro ao criar OS'}
                    </p>
                  )}
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={() => setTab('mensagens')}
                    >
                      Cancelar
                    </Button>
                    <Button
                      onClick={() => void handleAbrirOs()}
                      disabled={
                        createOs.isPending ||
                        !osTecnicoId ||
                        !osProblema.trim() ||
                        !osEndereco.trim()
                      }
                    >
                      {createOs.isPending ? 'Criando…' : 'Abrir OS e Notificar Técnico'}
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── direita: ações + SLA ── */}
      <div className="flex w-44 shrink-0 flex-col gap-3">
        <p className="text-xs font-medium uppercase text-muted-foreground">Ações</p>

        <Button
          size="sm"
          variant="outline"
          onClick={() => setSearchOpen((v) => !v)}
          className="w-full"
        >
          <Search className="h-4 w-4" /> Buscar
        </Button>

        {/* Botão Assumir: aguardando (bot escalou) ou bot (atendente quer
            intervir mesmo sem escalação). Esconde quando já estou atendendo. */}
        {(data.status === 'aguardando' || data.status === 'bot') && (
          <Button
            size="sm"
            onClick={() => atender.mutate()}
            disabled={atender.isPending}
            className="w-full"
          >
            <UserCheck className="h-4 w-4" />{' '}
            {data.status === 'aguardando' ? 'Assumir' : 'Atender'}
          </Button>
        )}

        {/* Encerrar: só faz sentido em atendimento humano ou aguardando.
            Em BOT, não tem o que encerrar (bot já está respondendo). */}
        {(data.status === 'humano' || data.status === 'aguardando') && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => encerrar.mutate()}
            disabled={encerrar.isPending}
            className="w-full"
          >
            <X className="h-4 w-4" /> Encerrar atendimento
          </Button>
        )}

        <Button
          size="sm"
          variant="ghost"
          className="w-full text-destructive hover:text-destructive"
          onClick={() => void handleDelete()}
          disabled={deleteConversa.isPending}
        >
          <Trash2 className="h-4 w-4" /> Excluir
        </Button>

        {data.status === 'aguardando' && data.transferred_at && (
          <ConversaSlaTimer
            transferredAt={data.transferred_at}
            slaMinutes={data.sla_minutes ?? 15}
          />
        )}

        <div className="mt-2 space-y-1 text-xs text-muted-foreground">
          <p><span className="font-medium">Estado:</span> {data.estado}</p>
          <p><span className="font-medium">Status:</span> {data.status}</p>
          {data.atendente_id && (
            <p className="text-xs text-green-600 dark:text-green-400">✓ Atendente atribuído</p>
          )}
        </div>
      </div>
    </div>
  )
}


interface ResponderBoxProps {
  text: string
  setText: (v: string) => void
  handleSend: () => Promise<void> | void
  pending: boolean
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function highlightMatches(content: string, query: string): React.ReactNode {
  const q = query.trim()
  if (!q) return content
  const re = new RegExp(`(${escapeRegex(q)})`, 'gi')
  const parts = content.split(re)
  const qLower = q.toLowerCase()
  return parts.map((part, i) =>
    part.toLowerCase() === qLower ? (
      <mark key={i} className="rounded bg-yellow-300/70 px-0.5 text-foreground">
        {part}
      </mark>
    ) : (
      <span key={i}>{part}</span>
    ),
  )
}

function VincularClienteBox({
  conversaId,
  onSuccess,
}: {
  conversaId: string
  onSuccess: () => void
}) {
  const [cpf, setCpf] = useState('')
  const vincular = useVincularCliente(conversaId)
  const cpfDigits = cpf.replace(/\D/g, '')
  const valid = cpfDigits.length === 11 || cpfDigits.length === 14

  async function handleVincular() {
    if (!valid) return
    try {
      await vincular.mutateAsync(cpfDigits)
      setCpf('')
      onSuccess()
    } catch {
      /* erro exibido abaixo */
    }
  }

  const errMsg =
    vincular.error instanceof Error
      ? vincular.error.message
      : vincular.error
      ? 'Erro ao vincular cliente'
      : null

  return (
    <div className="space-y-3">
      <div>
        <p className="text-muted-foreground mb-1">Cliente ainda não identificado nesta conversa.</p>
        <p className="text-xs text-muted-foreground">
          Se o cliente digitou o CPF errado ou o bot não conseguiu identificar, vincule
          manualmente abaixo — consulta o SGP e libera a conversa para atendimento.
        </p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="vincular-cpf">CPF ou CNPJ do cliente</Label>
        <Input
          id="vincular-cpf"
          value={cpf}
          onChange={(e) => setCpf(e.target.value)}
          placeholder="Somente números (11 ou 14 dígitos)"
          inputMode="numeric"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && valid && !vincular.isPending) {
              e.preventDefault()
              void handleVincular()
            }
          }}
        />
        {cpf && !valid && (
          <p className="text-xs text-destructive">CPF/CNPJ deve ter 11 ou 14 dígitos.</p>
        )}
        {errMsg && <p className="text-xs text-destructive">{errMsg}</p>}
        <Button
          onClick={() => void handleVincular()}
          disabled={!valid || vincular.isPending}
        >
          {vincular.isPending ? 'Consultando SGP…' : 'Buscar e vincular'}
        </Button>
      </div>
    </div>
  )
}

function ResponderBox({ text, setText, handleSend, pending }: ResponderBoxProps) {
  const qr = useQuickRepliesKeyHandler(text, setText)
  return (
    <div className="relative rounded-md border bg-card p-3">
      <QuickRepliesMenu text={text} onSelect={setText} position="above" />
      <Textarea
        placeholder="Digite sua resposta… (ou /  pra respostas rápidas)"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (qr.onKeyDown(e)) return
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            e.preventDefault()
            void handleSend()
          }
        }}
      />
      <div className="mt-2 flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          Ctrl/Cmd + Enter · use <code className="font-mono">/</code> pra respostas rápidas
        </span>
        <Button
          onClick={() => void handleSend()}
          disabled={pending || !text.trim()}
        >
          <Send className="h-4 w-4" /> Enviar
        </Button>
      </div>
    </div>
  )
}
