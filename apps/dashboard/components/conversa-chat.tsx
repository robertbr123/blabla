'use client'
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ChevronDown,
  ChevronUp,
  Paperclip,
  Search,
  Send,
  Trash2,
  UserCheck,
  X,
} from 'lucide-react'
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
  useEnviarMidia,
  useOsList,
  useResponder,
  useTecnicos,
  useVincularCliente,
} from '@/lib/api/queries'
import { apiFetch } from '@/lib/api/client'
import type { MensagemOut } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { ConversaSlaTimer } from './conversa-sla-timer'
import { ConversaMedia, mediaKind } from './conversa-media'

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
  media_type?: string | null
  media_url?: string | null
  ts?: string | null
}

export function ConversaChat({ conversaId }: { conversaId: string }) {
  const router = useRouter()
  const [sseDown, setSseDown] = useState(false)
  const { data, isLoading, refetch } = useConversa(conversaId, { refetchInterval: sseDown ? 10_000 : false })
  const responder = useResponder(conversaId)
  const atender = useAtender(conversaId)
  const encerrar = useEncerrar(conversaId)
  const enviarMidia = useEnviarMidia(conversaId)
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

  // SSE real-time (ticket de 60s: EventSource nao envia Authorization)
  useEffect(() => {
    if (!conversaId) return
    let es: EventSource | null = null
    let cancelled = false
    let retryTimer: ReturnType<typeof setTimeout> | null = null

    async function connect(attempt: number) {
      try {
        const { ticket } = await apiFetch<{ ticket: string }>(
          `/api/v1/conversas/${conversaId}/stream-ticket`,
          { method: 'POST' },
        )
        if (cancelled) return
        es = new EventSource(
          `/api/v1/conversas/${conversaId}/stream?ticket=${encodeURIComponent(ticket)}`,
        )
        es.onopen = () => setSseDown(false)
        // Backend emite eventos nomeados com `event: msg` (sse-starlette).
        // es.onmessage so captura eventos sem nome ou `event: message`,
        // entao usamos addEventListener('msg', ...) para pegar os eventos reais.
        es.addEventListener('msg', (ev) => {
          try {
            const payload = JSON.parse(ev.data as string) as SseEvent
            if (payload.type !== 'msg' || !payload.role) return
            // Mensagem so de midia (foto/audio sem legenda) chega sem `text` — antes
            // era descartada aqui. Aceita se tiver texto OU midia.
            if (!payload.text && !payload.media_url) return
            setLiveMsgs((prev) => [
              ...prev,
              {
                id: payload.id ?? `live-${Date.now()}`,
                conversa_id: conversaId,
                role: payload.role as MensagemOut['role'],
                content: payload.text ?? null,
                media_type: payload.media_type ?? null,
                media_url: payload.media_url ?? null,
                created_at: payload.ts ?? new Date().toISOString(),
              },
            ])
          } catch { /* ignore */ }
        })
        es.onerror = () => {
          es?.close()
          if (cancelled) return
          setSseDown(true)
          retryTimer = setTimeout(
            () => connect(attempt + 1),
            Math.min(30_000, 2_000 * 2 ** attempt),
          )
        }
      } catch {
        if (cancelled) return
        setSseDown(true)
        retryTimer = setTimeout(
          () => connect(attempt + 1),
          Math.min(30_000, 2_000 * 2 ** attempt),
        )
      }
    }

    void connect(0)
    return () => {
      cancelled = true
      if (retryTimer) clearTimeout(retryTimer)
      es?.close()
    }
  }, [conversaId])

  // Prune: quando o refetch já trouxe a mensagem (mesmo id), tira do buffer
  // live — senão liveMsgs cresce sem teto num plantão longo.
  useEffect(() => {
    const ids = new Set((data?.mensagens ?? []).map((m) => m.id))
    if (ids.size === 0) return
    setLiveMsgs((prev) => {
      const next = prev.filter((m) => !ids.has(m.id))
      return next.length === prev.length ? prev : next
    })
  }, [data?.mensagens])

  const baseMsgs = data?.mensagens ?? []
  const baseIds = new Set(baseMsgs.map((m) => m.id))
  const allMsgs = [...baseMsgs, ...liveMsgs.filter((m) => !baseIds.has(m.id))]
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

  async function handleUploadMedia(file: File) {
    try {
      await enviarMidia.mutateAsync({ file, caption: text.trim() })
      setText('')
      void refetch()
    } catch (e) {
      alert(`Falha ao enviar: ${e instanceof Error ? e.message : 'erro'}`)
    }
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
                    <MensagemBody m={m} searchQuery={searchQuery} />
                  </div>
                )
              })}
            </div>
            {data.status !== 'encerrada' && (
              <ResponderBox
                text={text}
                setText={setText}
                handleSend={handleSend}
                pending={responder.isPending}
                onUploadMedia={handleUploadMedia}
                uploading={enviarMidia.isPending}
              />
            )}
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
  onUploadMedia: (file: File) => Promise<void>
  uploading: boolean
}

/** Corpo de uma mensagem: midia (foto/audio/video/doc) + texto/legenda/transcricao. */
function MensagemBody({
  m,
  searchQuery,
}: {
  m: MensagemOut
  searchQuery: string
}) {
  const kind = mediaKind(m.media_type)
  // So renderiza player/imagem quando a URL aponta pra rota servivel (inbound do
  // cliente). Midia legada do atendente (media_url = caminho /tmp) cai no texto.
  const hasMedia = !!m.media_url && m.media_url.startsWith('/api/') && !!kind
  // ASR espelha a transcricao em `content`; so mostra separada se diferir.
  const showTranscricao =
    kind === 'audio' && !!m.transcricao && m.transcricao !== m.content

  return (
    <div className="space-y-1">
      {hasMedia && <ConversaMedia src={m.media_url!} kind={kind!} />}
      {m.content && (
        <div className="whitespace-pre-wrap">
          {highlightMatches(m.content, searchQuery)}
        </div>
      )}
      {showTranscricao && (
        <div className="whitespace-pre-wrap text-xs italic opacity-80">
          “{highlightMatches(m.transcricao!, searchQuery)}”
        </div>
      )}
      {!m.content && !hasMedia && kind && (
        <div className="text-xs italic opacity-70">[{kind}]</div>
      )}
    </div>
  )
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

function ResponderBox({
  text,
  setText,
  handleSend,
  pending,
  onUploadMedia,
  uploading,
}: ResponderBoxProps) {
  const qr = useQuickRepliesKeyHandler(text, setText)
  const fileRef = useRef<HTMLInputElement>(null)

  function handleFilePick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    if (f.size > 10 * 1024 * 1024) {
      alert('Arquivo excede 10MB')
      return
    }
    void onUploadMedia(f)
  }

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
      <input
        ref={fileRef}
        type="file"
        accept="image/*,application/pdf,audio/*,video/*"
        onChange={handleFilePick}
        className="hidden"
      />
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="text-xs text-muted-foreground">
          Ctrl/Cmd + Enter · <code className="font-mono">/</code> respostas rápidas · 📎 anexo (max 10MB, vira legenda)
        </span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploading || pending}
            title="Anexar imagem, PDF, áudio ou vídeo"
            aria-label="Anexar arquivo"
          >
            {uploading ? (
              <span className="text-xs">…</span>
            ) : (
              <Paperclip className="h-4 w-4" />
            )}
          </Button>
          <Button
            onClick={() => void handleSend()}
            disabled={pending || uploading || !text.trim()}
          >
            <Send className="h-4 w-4" /> Enviar
          </Button>
        </div>
      </div>
    </div>
  )
}
