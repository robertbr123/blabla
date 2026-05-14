'use client'
import Link from 'next/link'
import { useState } from 'react'
import { Trash2, Wrench, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { useConversas, useDeleteConversa, useEncerrar } from '@/lib/api/queries'
import type { ConversaListItem } from '@/lib/api/types'
import { DialogAbrirOsFromConversa } from './dialog-abrir-os-from-conversa'
import { ConversaSlaTimer } from './conversa-sla-timer'

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
    await encerrar.mutateAsync()
  }

  async function handleExcluir() {
    if (!confirm('Excluir esta conversa? O histórico será preservado por 30 dias.')) return
    await excluir.mutateAsync()
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

const STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  bot: 'secondary',
  aguardando: 'destructive',
  humano: 'default',
  encerrada: 'outline',
}

export function ConversaList() {
  const [status, setStatus] = useState('')
  const [q, setQ] = useState('')
  const [abrirOsConversaId, setAbrirOsConversaId] = useState<string | null>(null)
  const { data, isLoading, error } = useConversas({
    status: status || undefined,
    q: q || undefined,
  })

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
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {data && (
        <div className="rounded-md border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b text-left text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-3">WhatsApp</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3">Última msg</th>
                <th className="px-4 py-3">Fila / SLA</th>
                <th className="px-4 py-3">Ações</th>
              </tr>
            </thead>
            <tbody>
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-6 text-center text-muted-foreground">
                    Nenhuma conversa
                  </td>
                </tr>
              )}
              {data.items.map((c) => (
                <tr key={c.id} className="border-b last:border-b-0 hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <Link href={`/conversas/${c.id}`} className="font-medium hover:underline">
                      {c.whatsapp}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={STATUS_VARIANTS[c.status] ?? 'outline'}>
                      {c.status}
                    </Badge>
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
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
