'use client'
import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertCircle,
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Headphones,
  Loader2,
  Paperclip,
  Search,
  Send,
  Trash2,
  User,
  UserCheck,
  X,
  Zap,
} from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  Age,
  Avatar,
  FilterTabs,
  Panel,
  PanelBody,
  PanelHeader,
  Skeleton,
  SkeletonRows,
  StatusDot,
  type FilterTab,
} from '@/components/noc/primitives'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
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
import { formatWhatsappBr } from './conversa-list'
import { ConversaSlaTimer } from './conversa-sla-timer'
import { ConversaStatusPill } from './conversa-status-pill'
import { ConversaMedia, mediaKind } from './conversa-media'
import { ConversaRedePanel, RedeBadge } from './conversa-rede-panel'

type Tab = 'mensagens' | 'cliente' | 'nova-os' | 'rede'

const ROLE_LABEL: Record<string, string> = {
  cliente: 'Cliente',
  bot: 'Bot',
  atendente: 'Atendente',
}

const ROLE_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  cliente: User,
  bot: Bot,
  atendente: Headphones,
}

/** Bolha por papel: cliente à esquerda; bot (discreto) e atendente à direita. */
const ROLE_BUBBLE: Record<string, string> = {
  cliente: 'bg-secondary text-secondary-foreground',
  bot: 'bg-muted text-foreground',
  atendente: 'bg-primary/[0.15] text-foreground',
}

/** Mensagens seguidas do mesmo papel dentro desta janela formam um grupo. */
const AGRUPAR_MS = 5 * 60_000

const OS_STATUS_ABERTA = ['pendente', 'em_andamento']

/** True se as duas datas caem no mesmo dia (horário local). */
function mesmoDia(a: string, b: string): boolean {
  const da = new Date(a)
  const db = new Date(b)
  return (
    da.getFullYear() === db.getFullYear() &&
    da.getMonth() === db.getMonth() &&
    da.getDate() === db.getDate()
  )
}

/** Rótulo do separador de data: "Hoje", "Ontem" ou "30/06/2026". */
function rotuloDataSeparador(iso: string): string {
  const d = new Date(iso)
  const hoje = new Date()
  const ontem = new Date(hoje)
  ontem.setDate(hoje.getDate() - 1)
  if (mesmoDia(iso, hoje.toISOString())) return 'Hoje'
  if (mesmoDia(iso, ontem.toISOString())) return 'Ontem'
  return d.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

/** True se `m` continua o grupo de `prev` (mesmo papel, mesmo dia, poucos minutos). */
function continuaGrupo(prev: MensagemOut | null | undefined, m: MensagemOut): boolean {
  if (!prev || prev.role !== m.role || !mesmoDia(prev.created_at, m.created_at)) return false
  const dt = new Date(m.created_at).getTime() - new Date(prev.created_at).getTime()
  return Math.abs(dt) < AGRUPAR_MS
}

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
  // So vira true quando o EventSource abre de fato — o indicador nao mente "Ao vivo" antes disso.
  const [sseOpen, setSseOpen] = useState(false)
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
        es.onopen = () => {
          setSseDown(false)
          setSseOpen(true)
        }
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
    try {
      await responder.mutateAsync(trimmed)
      setText('')
      void refetch()
    } catch {
      // toast já emitido no onError do hook; mantém o texto pro retry
    }
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
    try {
      await deleteConversa.mutateAsync()
      router.push('/conversas')
    } catch {
      // toast já emitido no onError do hook
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-full flex-col gap-3">
        <Skeleton className="h-14 w-full shrink-0 rounded-lg" />
        <div className="min-h-0 flex-1 overflow-hidden rounded-lg border bg-card">
          <SkeletonRows rows={8} />
        </div>
      </div>
    )
  }
  if (!data) {
    return (
      <div
        role="alert"
        className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/[0.08] p-4"
      >
        <AlertCircle aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">Conversa não encontrada</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Ela pode ter sido excluída ou o endereço está incorreto.
          </p>
          <Link
            href="/conversas"
            className="mt-2 inline-block rounded-sm text-xs font-medium text-foreground underline underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Voltar para a fila de conversas
          </Link>
        </div>
      </div>
    )
  }

  const TABS: FilterTab<Tab>[] = [
    { value: 'mensagens', label: 'Mensagens' },
    { value: 'cliente', label: 'Cliente SGP' },
    { value: 'rede', label: 'Rede' },
    { value: 'nova-os', label: 'Nova OS' },
  ]

  const telefone = formatWhatsappBr(data.whatsapp)
  const nome = data.cliente?.nome ?? data.cliente_nome ?? null
  const titulo = nome ?? telefone

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      {/* ── barra do atendimento: quem é, estado, ações ── */}
      <header className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border bg-card px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-3">
          <Avatar name={nome ?? '?'} />
          <div className="min-w-0">
            <h1
              className={cn('truncate text-sm font-semibold leading-5', !nome && 'num')}
              title={titulo}
            >
              {titulo}
            </h1>
            <div className="flex flex-wrap items-center gap-x-2">
              {nome && <span className="num text-xs text-muted-foreground">{telefone}</span>}
              <RedeBadge conversaId={conversaId} temCliente={!!data.cliente_id} />
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <ConversaStatusPill status={data.status} size="sm" />
          {data.status === 'aguardando' && data.transferred_at && (
            <ConversaSlaTimer
              transferredAt={data.transferred_at}
              slaMinutes={data.sla_minutes ?? 15}
            />
          )}
          <span
            role="status"
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground"
            title={
              sseDown
                ? 'Conexão em tempo real caiu — atualizando a cada 10 s até reconectar'
                : 'Mensagens novas chegam em tempo real'
            }
          >
            <StatusDot
              tone={sseDown ? 'warning' : sseOpen ? 'success' : 'muted'}
              pulse={!sseDown && sseOpen}
            />
            {sseDown ? 'Reconectando…' : sseOpen ? 'Ao vivo' : 'Conectando…'}
          </span>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-1.5">
          <Button
            size="icon"
            variant="ghost"
            className={cn('h-8 w-8', searchOpen && 'bg-secondary')}
            onClick={() => setSearchOpen((v) => !v)}
            title="Buscar nesta conversa (Ctrl+F)"
            aria-label="Buscar nesta conversa"
            aria-pressed={searchOpen}
          >
            <Search />
          </Button>

          {/* Botão Assumir: aguardando (bot escalou) ou bot (atendente quer
              intervir mesmo sem escalação). Esconde quando já estou atendendo. */}
          {(data.status === 'aguardando' || data.status === 'bot') && (
            <Button size="sm" onClick={() => atender.mutate()} disabled={atender.isPending}>
              <UserCheck /> {data.status === 'aguardando' ? 'Assumir' : 'Atender'}
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
            >
              <X /> Encerrar atendimento
            </Button>
          )}

          <Button
            size="icon"
            variant="ghost"
            className="h-8 w-8 text-muted-foreground hover:bg-destructive/[0.13] hover:text-destructive"
            onClick={() => void handleDelete()}
            disabled={deleteConversa.isPending}
            title="Excluir conversa"
            aria-label="Excluir conversa"
          >
            <Trash2 />
          </Button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-3 lg:flex-row">
        {/* ── painel principal: abas ── */}
        <div className="order-2 flex min-h-0 min-w-0 flex-1 flex-col gap-3 lg:order-1">
          <FilterTabs
            tabs={TABS}
            value={tab}
            onChange={setTab}
            ariaLabel="Seções da conversa"
            className="shrink-0 self-start"
          />

          {/* Tab: Mensagens */}
          {tab === 'mensagens' && (
            <div className="flex min-h-0 flex-1 flex-col gap-2">
              {/* Barra de busca (toggle pelo botao ou Cmd+F) */}
              {searchOpen && (
                <div className="flex shrink-0 items-center gap-2 rounded-lg border bg-card px-3 py-1.5 focus-within:ring-2 focus-within:ring-ring">
                  <Search aria-hidden className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <Input
                    autoFocus
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Buscar nesta conversa…"
                    aria-label="Buscar nesta conversa"
                    className="h-8 border-0 bg-transparent px-0 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        if (e.shiftKey) prevMatch()
                        else nextMatch()
                      }
                    }}
                  />
                  <span className="num whitespace-nowrap text-xs text-muted-foreground" aria-live="polite">
                    {matchedIds.length === 0
                      ? searchQuery ? '0' : ''
                      : `${currentMatch + 1}/${matchedIds.length}`}
                  </span>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    onClick={prevMatch}
                    disabled={matchedIds.length === 0}
                    title="Resultado anterior (Shift+Enter)"
                    aria-label="Resultado anterior"
                  >
                    <ChevronUp />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    onClick={nextMatch}
                    disabled={matchedIds.length === 0}
                    title="Próximo resultado (Enter)"
                    aria-label="Próximo resultado"
                  >
                    <ChevronDown />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    onClick={() => {
                      setSearchOpen(false)
                      setSearchQuery('')
                    }}
                    title="Fechar busca (Esc)"
                    aria-label="Fechar busca"
                  >
                    <X />
                  </Button>
                </div>
              )}

              <div
                ref={scrollRef}
                className="min-h-0 flex-1 overflow-y-auto rounded-lg border bg-card px-4 pb-4 pt-1"
              >
                {allMsgs.length === 0 && (
                  <p className="pt-8 text-center text-sm text-muted-foreground">Sem mensagens</p>
                )}
                {allMsgs.map((m, i) => {
                  const isMatch = matchedIds.includes(m.id)
                  const isCurrent = isMatch && matchedIds[currentMatch] === m.id
                  const prev = i > 0 ? allMsgs[i - 1] : null
                  const mostraData = !prev || !mesmoDia(prev.created_at, m.created_at)
                  const agrupada = continuaGrupo(prev, m)
                  const direita = m.role !== 'cliente'
                  const RoleIcon = ROLE_ICON[m.role] ?? User
                  const hora = new Date(m.created_at)
                  return (
                    <Fragment key={m.id}>
                      {mostraData && (
                        <div className="flex items-center gap-3 pb-1 pt-4" role="separator">
                          <span aria-hidden className="h-px flex-1 bg-border" />
                          <span className="eyebrow num">{rotuloDataSeparador(m.created_at)}</span>
                          <span aria-hidden className="h-px flex-1 bg-border" />
                        </div>
                      )}
                      <div
                        ref={(el) => {
                          if (el) msgRefs.current.set(m.id, el)
                          else msgRefs.current.delete(m.id)
                        }}
                        className={cn(
                          'flex flex-col',
                          direita ? 'items-end' : 'items-start',
                          agrupada ? 'mt-1' : 'mt-3',
                        )}
                      >
                        {!agrupada && (
                          <span className="mb-1 inline-flex items-center gap-1 px-1 text-[11px] font-medium text-muted-foreground">
                            <RoleIcon aria-hidden className="h-3 w-3" />
                            {ROLE_LABEL[m.role] ?? m.role}
                          </span>
                        )}
                        <div
                          className={cn(
                            'max-w-[85%] rounded-lg px-3 py-2 text-sm sm:max-w-[70%]',
                            ROLE_BUBBLE[m.role] ?? 'bg-muted text-foreground',
                            isCurrent && 'ring-2 ring-warning ring-offset-1 ring-offset-card',
                          )}
                        >
                          <MensagemBody m={m} searchQuery={searchQuery} />
                          <time
                            dateTime={m.created_at}
                            title={hora.toLocaleString('pt-BR')}
                            className="num mt-1 block text-right text-[10px] text-muted-foreground"
                          >
                            {hora.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                          </time>
                        </div>
                      </div>
                    </Fragment>
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
            <div className="min-h-0 flex-1 overflow-y-auto rounded-lg border bg-card p-4 text-sm">
              {!data.cliente ? (
                <VincularClienteBox conversaId={conversaId} onSuccess={() => void refetch()} />
              ) : (
                <dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
                  <Campo label="Nome">
                    <span className="font-semibold">{data.cliente.nome}</span>
                  </Campo>
                  <Campo label="CPF/CNPJ">
                    <span className="num">{data.cliente.cpf_cnpj}</span>
                  </Campo>
                  <Campo label="WhatsApp">
                    <span className="num">{data.cliente.whatsapp}</span>
                  </Campo>
                  {data.cliente.plano && <Campo label="Plano">{data.cliente.plano}</Campo>}
                  {data.cliente.cidade && <Campo label="Cidade">{data.cliente.cidade}</Campo>}
                  {data.cliente.endereco && (
                    <Campo label="Endereço">{data.cliente.endereco}</Campo>
                  )}
                  <Campo label="Estado da conversa">
                    <span className="flex flex-wrap items-center gap-2">
                      <EstadoTag estado={data.estado} />
                      <ConversaStatusPill status={data.status} size="sm" />
                    </span>
                  </Campo>
                </dl>
              )}
            </div>
          )}

          {/* Tab: Rede */}
          {tab === 'rede' && (
            <div className="min-h-0 flex-1 overflow-y-auto rounded-lg border bg-card p-4">
              <ConversaRedePanel
                conversaId={conversaId}
                temCliente={!!data.cliente_id}
                onColarDiagnostico={(texto) => {
                  setText(texto)
                  setTab('mensagens')
                }}
              />
            </div>
          )}

          {/* Tab: Nova OS */}
          {tab === 'nova-os' && (
            <div className="min-h-0 flex-1 overflow-y-auto rounded-lg border bg-card p-4">
              {!data.cliente_id ? (
                <p className="text-sm text-muted-foreground">
                  Cliente não identificado — não é possível abrir OS sem cliente vinculado.
                </p>
              ) : (
                <div className="max-w-2xl space-y-4">
                  {data.cliente && (
                    <div className="space-y-1 rounded-md border bg-muted/60 p-3 text-sm">
                      <p>
                        <span className="text-muted-foreground">Cliente:</span>{' '}
                        <span className="font-medium">{data.cliente.nome}</span>
                      </p>
                      {data.cliente.cidade && (
                        <p>
                          <span className="text-muted-foreground">Cidade:</span>{' '}
                          <span className="font-medium">{data.cliente.cidade}</span>
                        </p>
                      )}
                    </div>
                  )}
                  <div className="space-y-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="os-tecnico">Técnico responsável *</Label>
                      <Select
                        id="os-tecnico"
                        value={osTecnicoId}
                        onChange={(e) => setOsTecnicoId(e.target.value)}
                      >
                        <option value="" disabled>Selecione o técnico</option>
                        {tecnicos?.items.map((t) => (
                          <option key={t.id} value={t.id}>{t.nome}</option>
                        ))}
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="os-problema">Problema *</Label>
                      <Textarea
                        id="os-problema"
                        placeholder="Descreva o problema…"
                        value={osProblema}
                        onChange={(e) => setOsProblema(e.target.value)}
                        className="bg-card"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="os-endereco">Endereço *</Label>
                      <Input
                        id="os-endereco"
                        value={osEndereco}
                        onChange={(e) => setOsEndereco(e.target.value)}
                        placeholder="Rua e número"
                      />
                    </div>
                    {createOs.error && (
                      <p role="alert" className="flex items-center gap-1.5 text-xs text-destructive">
                        <AlertCircle aria-hidden className="h-3.5 w-3.5 shrink-0" />
                        {createOs.error instanceof Error ? createOs.error.message : 'Erro ao criar OS'}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-2 pt-1">
                      <Button variant="outline" onClick={() => setTab('mensagens')}>
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

        {/* ── painel de contexto: alertas + dados do atendimento ── */}
        <aside
          aria-label="Contexto do atendimento"
          className="order-1 flex max-h-44 shrink-0 flex-col gap-3 overflow-y-auto lg:order-2 lg:max-h-none lg:w-72"
        >
          {/* OS abertas alert */}
          {osAbertas.length > 0 && (
            <div className="shrink-0 rounded-lg border border-warning/40 bg-warning/[0.08] p-3">
              <p className="flex items-center gap-1.5 text-xs font-semibold text-warning">
                <AlertTriangle aria-hidden className="h-3.5 w-3.5 shrink-0" />
                OS em aberto para este cliente
              </p>
              <ul className="mt-1.5 space-y-1">
                {osAbertas.map((o) => (
                  <li key={o.id} className="text-xs text-muted-foreground">
                    <span className="num font-medium text-foreground">#{o.codigo}</span> · {o.status} ·{' '}
                    {o.problema.slice(0, 50)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Resumo do handoff (F1) — TL;DR gerado pelo bot ao transferir pro humano */}
          {data.resumo_handoff && (
            <div className="shrink-0 rounded-lg border border-info/30 bg-info/[0.07] p-3">
              <p className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs font-semibold text-info">
                <span className="inline-flex items-center gap-1.5">
                  <Bot aria-hidden className="h-3.5 w-3.5 shrink-0" />
                  Resumo do bot
                </span>
                {data.resumo_handoff_at && (
                  <span className="num text-[10px] font-normal text-muted-foreground">
                    {new Date(data.resumo_handoff_at).toLocaleString('pt-BR')}
                  </span>
                )}
              </p>
              <p className="mt-1.5 whitespace-pre-line text-sm text-foreground">
                {data.resumo_handoff}
              </p>
            </div>
          )}

          <Panel className="hidden shrink-0 lg:flex">
            <PanelHeader title="Atendimento" />
            <PanelBody>
              <dl className="space-y-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <dt className="eyebrow">Status</dt>
                  <dd>
                    <ConversaStatusPill status={data.status} size="sm" />
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="eyebrow">Estado</dt>
                  <dd>
                    <EstadoTag estado={data.estado} />
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="eyebrow">Atendente</dt>
                  <dd className="text-xs">
                    {data.atendente_id ? (
                      <span className="inline-flex items-center gap-1 text-success">
                        <CheckCircle2 aria-hidden className="h-3.5 w-3.5" />
                        Atribuído
                      </span>
                    ) : (
                      <span className="text-muted-foreground">Não atribuído</span>
                    )}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="eyebrow">Última mensagem</dt>
                  <dd>
                    <Age iso={data.last_message_at} />
                  </dd>
                </div>
              </dl>
            </PanelBody>
          </Panel>
        </aside>
      </div>
    </div>
  )
}

/** Par rótulo/valor da aba Cliente. */
function Campo({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="eyebrow mb-1">{label}</dt>
      <dd className="break-words">{children}</dd>
    </div>
  )
}

/** Estado da máquina do bot como tag mono discreta. */
function EstadoTag({ estado }: { estado: string }) {
  return (
    <span className="num rounded border bg-muted/60 px-1.5 py-0.5 text-[11px] text-muted-foreground">
      {estado}
    </span>
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
        <div className="whitespace-pre-wrap break-words">
          {highlightMatches(m.content, searchQuery)}
        </div>
      )}
      {showTranscricao && (
        <div className="whitespace-pre-wrap break-words text-xs italic text-muted-foreground">
          &ldquo;{highlightMatches(m.transcricao!, searchQuery)}&rdquo;
        </div>
      )}
      {!m.content && !hasMedia && kind && (
        <div className="text-xs italic text-muted-foreground">[{kind}]</div>
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
      <mark key={i} className="rounded bg-warning/40 px-0.5 text-foreground">
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
    <div className="max-w-md space-y-4">
      <div>
        <p className="font-medium">Cliente ainda não identificado nesta conversa.</p>
        <p className="mt-1 text-xs text-muted-foreground">
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
          className="num"
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
        {errMsg && (
          <p role="alert" className="text-xs text-destructive">
            {errMsg}
          </p>
        )}
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
  const textareaRef = useRef<HTMLTextAreaElement>(null)

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

  // Botão de respostas rápidas: mesmo efeito de digitar "/" no campo vazio.
  // Com rascunho em andamento fica desabilitado pra não apagar o texto.
  function toggleQuickReplies() {
    if (qr.isMenuOpen) setText('')
    else if (!text.trim()) setText('/')
    textareaRef.current?.focus()
  }

  return (
    <div className="relative shrink-0 rounded-lg border bg-card transition-shadow focus-within:border-ring focus-within:ring-1 focus-within:ring-ring">
      <QuickRepliesMenu text={text} onSelect={setText} position="above" />
      <Textarea
        ref={textareaRef}
        placeholder="Digite sua resposta… (ou / pra respostas rápidas)"
        aria-label="Resposta ao cliente"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (qr.onKeyDown(e)) return
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            e.preventDefault()
            void handleSend()
          }
        }}
        className="min-h-[64px] resize-none border-0 bg-transparent px-3 pb-1 pt-2.5 focus-visible:ring-0 focus-visible:ring-offset-0"
      />
      <input
        ref={fileRef}
        type="file"
        accept="image/*,application/pdf,audio/*,video/*"
        onChange={handleFilePick}
        className="hidden"
      />
      <div className="flex items-center gap-1 px-2 pb-2">
        <Button
          variant="ghost"
          size="icon"
          type="button"
          className={cn('h-8 w-8 text-muted-foreground', qr.isMenuOpen && 'bg-secondary text-foreground')}
          onClick={toggleQuickReplies}
          disabled={!!text.trim() && !qr.isMenuOpen}
          title="Respostas rápidas (digite / no campo vazio)"
          aria-label="Respostas rápidas"
          aria-pressed={qr.isMenuOpen}
        >
          <Zap />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          type="button"
          className="h-8 w-8 text-muted-foreground"
          onClick={() => fileRef.current?.click()}
          disabled={uploading || pending}
          title="Anexar imagem, PDF, áudio ou vídeo (máx. 10 MB; o texto vira legenda)"
          aria-label={uploading ? 'Enviando anexo' : 'Anexar arquivo'}
        >
          {uploading ? <Loader2 className="animate-spin" /> : <Paperclip />}
        </Button>
        <span className="ml-1 hidden min-w-0 truncate text-[11px] text-muted-foreground md:inline">
          <kbd className="num">Ctrl/Cmd + Enter</kbd> envia · <kbd className="num">/</kbd> respostas
          rápidas · anexo até 10 MB (o texto vira legenda)
        </span>
        <Button
          size="sm"
          className="ml-auto"
          onClick={() => void handleSend()}
          disabled={pending || uploading || !text.trim()}
        >
          <Send /> Enviar
        </Button>
      </div>
    </div>
  )
}
