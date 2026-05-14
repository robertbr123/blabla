'use client'
import { useEffect, useRef, useState } from 'react'
import { Send, UserCheck, Wrench, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import {
  useAtender,
  useConversa,
  useEncerrar,
  useOsList,
  useResponder,
} from '@/lib/api/queries'
import type { MensagemOut } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { DialogAbrirOsFromConversa } from './dialog-abrir-os-from-conversa'

interface SseEvent {
  type: string
  id?: string
  role?: string
  text?: string | null
  ts?: string | null
}

const ROLE_LABEL: Record<string, string> = {
  cliente: 'Cliente',
  bot: 'Bot',
  atendente: 'Atendente',
}

const OS_STATUS_ABERTA = ['pendente', 'em_andamento']

export function ConversaChat({ conversaId }: { conversaId: string }) {
  const { data, isLoading, refetch } = useConversa(conversaId)
  const responder = useResponder(conversaId)
  const atender = useAtender(conversaId)
  const encerrar = useEncerrar(conversaId)
  const [text, setText] = useState('')
  const [liveMsgs, setLiveMsgs] = useState<MensagemOut[]>([])
  const [showAbrirOs, setShowAbrirOs] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const clienteId = data?.cliente_id ?? undefined
  const { data: osAberta } = useOsList(
    clienteId ? { cliente_id: clienteId } : {}
  )
  const osAbertas = (osAberta?.items ?? []).filter((o) =>
    OS_STATUS_ABERTA.includes(o.status)
  )

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
      } catch {
        // ignore malformed
      }
    }
    es.onerror = () => {}
    return () => es.close()
  }, [conversaId])

  const allMsgs = [...(data?.mensagens ?? []), ...liveMsgs]
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [allMsgs.length])

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Carregando conversa…</p>
  }
  if (!data) {
    return <p className="text-sm text-destructive">Conversa não encontrada</p>
  }

  async function handleSend() {
    const trimmed = text.trim()
    if (!trimmed) return
    await responder.mutateAsync(trimmed)
    setText('')
    void refetch()
  }

  return (
    <div className="flex h-full flex-col gap-4">
      {showAbrirOs && (
        <DialogAbrirOsFromConversa
          conversaId={conversaId}
          onClose={() => setShowAbrirOs(false)}
        />
      )}

      {/* OS abertas alert */}
      {osAbertas.length > 0 && (
        <div className="rounded-md border border-yellow-400 bg-yellow-50 dark:bg-yellow-950/20 p-3 text-sm space-y-1">
          <p className="font-semibold text-yellow-800 dark:text-yellow-300">
            ⚠️ OS(s) em aberto para este cliente
          </p>
          {osAbertas.map((o) => (
            <p key={o.id} className="text-yellow-700 dark:text-yellow-400">
              #{o.codigo} · {o.status} · {o.problema.slice(0, 60)}
            </p>
          ))}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between rounded-md border bg-card p-4">
        <div>
          <div className="font-semibold">{data.whatsapp}</div>
          <div className="text-xs text-muted-foreground">
            Estado: {data.estado} · Status: {data.status}
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowAbrirOs(true)}
            title="Abrir OS para este cliente"
          >
            <Wrench className="h-4 w-4" /> Abrir OS
          </Button>
          {data.status === 'aguardando' && (
            <Button
              size="sm"
              variant="default"
              onClick={() => atender.mutate()}
              disabled={atender.isPending}
            >
              <UserCheck className="h-4 w-4" /> Atender
            </Button>
          )}
          {data.status !== 'encerrada' && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => encerrar.mutate()}
              disabled={encerrar.isPending}
            >
              <X className="h-4 w-4" /> Encerrar
            </Button>
          )}
        </div>
      </div>

      {/* Messages */}
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

      {/* Composer */}
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
            <span className="text-xs text-muted-foreground">Ctrl/Cmd + Enter para enviar</span>
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
  )
}
