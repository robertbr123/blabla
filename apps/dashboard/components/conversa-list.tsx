'use client'
import Link from 'next/link'
import { useState } from 'react'
import { MessageSquare, Trash2, Wrench, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { useCanais, useConversas, useDeleteConversa, useEncerrar } from '@/lib/api/queries'
import type { ConversaListItem } from '@/lib/api/types'
import { DialogAbrirOsFromConversa } from './dialog-abrir-os-from-conversa'
import { ConversaSlaTimer } from './conversa-sla-timer'
import { ConversaStatusPill } from './conversa-status-pill'

function ConversaRowActions({
  c,
  onAbrirOs,
}: {
  c: ConversaListItem
  onAbrirOs: (id: string) => void
}) {
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
    <div className="flex flex-wrap gap-1">
      {c.status !== 'encerrada' && (
        <Button
          variant="ghost"
          size="sm"
          className="h-7 gap-1 text-xs"
          onClick={() => void handleEncerrar()}
          disabled={encerrar.isPending}
          title="Encerrar conversa"
        >
          <X className="h-3 w-3" /> Encerrar
        </Button>
      )}
      {c.cliente_id && (
        <Button
          variant="ghost"
          size="sm"
          className="h-7 gap-1 text-xs"
          onClick={() => onAbrirOs(c.id)}
          title="Abrir OS para este cliente"
        >
          <Wrench className="h-3 w-3" /> Abrir OS
        </Button>
      )}
      <Button
        variant="ghost"
        size="sm"
        className="h-7 gap-1 text-xs text-destructive hover:text-destructive"
        onClick={() => void handleExcluir()}
        disabled={excluir.isPending}
        title="Excluir conversa"
      >
        <Trash2 className="h-3 w-3" /> Excluir
      </Button>
    </div>
  )
}

/** Formata "5511987654321@s.whatsapp.net" -> "(11) 9 8765-4321". */
function formatWhatsappBr(jid: string): string {
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

export function ConversaList() {
  const [status, setStatus] = useState('')
  const [q, setQ] = useState('')
  const [canalId, setCanalId] = useState('')
  const [abrirOsConversaId, setAbrirOsConversaId] = useState<string | null>(null)
  const { data: canais } = useCanais()
  const canalById = new Map((canais ?? []).map((c) => [c.id, c]))
  const {
    data, isLoading, error, hasNextPage, fetchNextPage, isFetchingNextPage,
  } = useConversas({
    status: status || undefined,
    q: q || undefined,
    canal_id: canalId || undefined,
  })
  const conversas = data?.pages.flatMap((p) => p.items) ?? []

  return (
    <div className="space-y-4">
      {abrirOsConversaId && (
        <DialogAbrirOsFromConversa
          conversaId={abrirOsConversaId}
          onClose={() => setAbrirOsConversaId(null)}
        />
      )}

      <div className="flex flex-wrap items-center gap-3">
        <Input
          placeholder="Buscar por whatsapp…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs"
        />
        <Select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="max-w-[200px]"
        >
          <option value="">Todos os status</option>
          <option value="aguardando">Aguardando</option>
          <option value="humano">Humano</option>
          <option value="bot">Bot</option>
          <option value="encerrada">Encerrada</option>
        </Select>
        {canais && canais.length > 1 && (
          <Select
            value={canalId}
            onChange={(e) => setCanalId(e.target.value)}
            className="max-w-[200px]"
          >
            <option value="">Todos os canais</option>
            {canais.map((c) => (
              <option key={c.id} value={c.id}>{c.nome}</option>
            ))}
          </Select>
        )}
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {!isLoading && conversas.length === 0 && (
        <div className="rounded-md border bg-card p-12 text-center">
          <MessageSquare className="mx-auto h-10 w-10 text-muted-foreground/50" />
          <h3 className="mt-3 text-sm font-medium">Nenhuma conversa encontrada</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {q || status || canalId
              ? 'Ajuste os filtros para ver outras conversas.'
              : 'Quando alguém mandar mensagem no WhatsApp, aparece aqui.'}
          </p>
        </div>
      )}

      {conversas.length > 0 && (
        <div className="rounded-md border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Cliente</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
                <th className="px-4 py-2.5 font-semibold">Estado</th>
                <th className="px-4 py-2.5 font-semibold">Última msg</th>
                <th className="px-4 py-2.5 font-semibold">Fila / SLA</th>
                <th className="px-4 py-2.5 font-semibold">Ações</th>
              </tr>
            </thead>
            <tbody>
              {conversas.map((c) => {
                const telefone = formatWhatsappBr(c.whatsapp)
                const tituloFull = c.cliente_nome ?? telefone
                const titulo = truncate(tituloFull)
                const subtitulo = c.cliente_nome ? telefone : null
                const canal = c.canal_id ? canalById.get(c.canal_id) : null
                return (
                <tr key={c.id} className="border-b last:border-b-0 transition-colors hover:bg-accent/40">
                  <td className="px-4 py-3">
                    <Link
                      href={`/conversas/${c.id}`}
                      className="font-medium text-primary hover:underline"
                      title={tituloFull}
                    >
                      {titulo}
                    </Link>
                    {subtitulo && (
                      <div className="text-xs text-muted-foreground" style={{ fontVariantNumeric: 'tabular-nums' }}>
                        {subtitulo}
                      </div>
                    )}
                    {canal && canais && canais.length > 1 && (
                      <Badge variant="outline" className="mt-1 text-[10px]">
                        {canal.nome}
                      </Badge>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <ConversaStatusPill status={c.status} size="sm" />
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{c.estado}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {c.last_message_at
                      ? new Date(c.last_message_at).toLocaleString('pt-BR')
                      : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {c.status === 'aguardando' && c.transferred_at ? (
                      <ConversaSlaTimer
                        transferredAt={c.transferred_at}
                        slaMinutes={c.sla_minutes ?? 15}
                      />
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <ConversaRowActions c={c} onAbrirOs={setAbrirOsConversaId} />
                  </td>
                </tr>
                )
              })}
            </tbody>
          </table>
        </div>
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
