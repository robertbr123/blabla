'use client'
import { useEffect, useRef, useState } from 'react'
import { Send, UserCheck, X, Trash2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  useAtender,
  useConversa,
  useCreateOs,
  useDeleteConversa,
  useEncerrar,
  useOsList,
  useResponder,
  useTecnicos,
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
  const scrollRef = useRef<HTMLDivElement>(null)

  const clienteId = data?.cliente_id ?? undefined
  const { data: osAberta } = useOsList(clienteId ? { cliente_id: clienteId } : {})
  const osAbertas = (osAberta?.items ?? []).filter((o) =>
    OS_STATUS_ABERTA.includes(o.status)
  )

  // Init OS form with client address
  useEffect(() => {
    if (data?.cliente?.endereco && !osEndereco) {
      setOsEndereco(data.cliente.endereco)
    }
  }, [data?.cliente?.endereco])

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
            <div
              ref={scrollRef}
              className="flex-1 space-y-3 overflow-y-auto rounded-md border bg-card p-4"
            >
              {allMsgs.length === 0 && (
                <p className="text-center text-sm text-muted-foreground">Sem mensagens</p>
              )}
              {allMsgs.map((m) => (
                <div
                  key={m.id}
                  className={cn(
                    'max-w-[70%] rounded-lg px-3 py-2 text-sm',
                    m.role === 'cliente'
                      ? 'bg-muted'
                      : m.role === 'bot'
                      ? 'ml-auto bg-secondary text-secondary-foreground'
                      : 'ml-auto bg-primary text-primary-foreground',
                  )}
                >
                  <div className="mb-1 flex items-center gap-2 text-xs opacity-70">
                    <Badge variant="outline" className="capitalize">
                      {ROLE_LABEL[m.role] ?? m.role}
                    </Badge>
                    <span>{new Date(m.created_at).toLocaleTimeString('pt-BR')}</span>
                  </div>
                  <div className="whitespace-pre-wrap">{m.content}</div>
                </div>
              ))}
            </div>
            {data.status !== 'encerrada' && (
              <div className="rounded-md border bg-card p-3">
                <Textarea
                  placeholder="Digite sua resposta…"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                      e.preventDefault()
                      void handleSend()
                    }
                  }}
                />
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Ctrl/Cmd + Enter</span>
                  <Button
                    onClick={() => void handleSend()}
                    disabled={responder.isPending || !text.trim()}
                  >
                    <Send className="h-4 w-4" /> Enviar
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Cliente SGP */}
        {tab === 'cliente' && (
          <div className="flex-1 overflow-y-auto rounded-md border bg-card p-4 mt-3 space-y-3 text-sm">
            {!data.cliente ? (
              <p className="text-muted-foreground">Cliente ainda não identificado nesta conversa.</p>
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

        {data.status === 'aguardando' && (
          <Button
            size="sm"
            onClick={() => atender.mutate()}
            disabled={atender.isPending}
            className="w-full"
          >
            <UserCheck className="h-4 w-4" /> Assumir
          </Button>
        )}

        {data.status !== 'encerrada' && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => encerrar.mutate()}
            disabled={encerrar.isPending}
            className="w-full"
          >
            <X className="h-4 w-4" /> Encerrar
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
