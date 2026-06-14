'use client'
import { useState } from 'react'
import { toast } from 'sonner'
import { Download, RotateCcw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { getAccessToken } from '@/lib/api/token'
import {
  resultadoExportUrl,
  useCampanha,
  useDestinatarios,
  useReenviarFalhas,
  useTestCampanha,
} from '@/lib/api/queries'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? ''
const STATUS_TABS: Array<{ key: string | null; label: string }> = [
  { key: null, label: 'Todos' },
  { key: 'enviada', label: 'Enviadas' },
  { key: 'entregue', label: 'Entregues' },
  { key: 'lida', label: 'Lidas' },
  { key: 'falha', label: 'Falhas' },
]

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border bg-card p-4">
      <p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  )
}

export function ComunicadoDetail({ id }: { id: string }) {
  const { data: c, isLoading } = useCampanha(id)
  const testSend = useTestCampanha(id)
  const reenviar = useReenviarFalhas(id)
  const [testNum, setTestNum] = useState('')
  const [statusFiltro, setStatusFiltro] = useState<string | null>(null)
  const { data: destinatarios } = useDestinatarios(id, statusFiltro, !isLoading)

  if (isLoading || !c) return <p className="text-sm text-muted-foreground">Carregando…</p>

  const counts = c.status_counts ?? {}

  async function exportar() {
    const res = await fetch(`${API_URL}${resultadoExportUrl(id)}`, {
      headers: { Authorization: `Bearer ${getAccessToken() ?? ''}` },
      credentials: 'include',
    })
    if (!res.ok) {
      toast.error('Falha ao exportar')
      return
    }
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `resultado-${id}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{c.titulo}</h1>
          <p className="mt-1 text-sm text-muted-foreground font-mono">{c.template_name}</p>
        </div>
        <Badge variant="outline">{c.status}</Badge>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <Metric label="Total" value={c.total_destinatarios} />
        <Metric label="Enviadas" value={c.enviadas} />
        <Metric label="Entregues" value={counts.entregue ?? 0} />
        <Metric label="Lidas" value={counts.lida ?? 0} />
        <Metric label="Falhas" value={c.falhas} />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {c.falhas > 0 && (
          <button type="button"
                  onClick={() => reenviar.mutate(undefined, {
                    onSuccess: (r) => toast.success(`${r.reenfileirados} reenfileirados`),
                    onError: (e) => toast.error(e instanceof Error ? e.message : 'Erro'),
                  })}
                  disabled={reenviar.isPending}
                  className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent disabled:opacity-50">
            <RotateCcw className="h-4 w-4" /> Reenviar falhas
          </button>
        )}
        <button type="button" onClick={exportar}
                className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent">
          <Download className="h-4 w-4" /> Exportar resultado
        </button>
      </div>

      <div className="space-y-3">
        <div className="flex gap-2 flex-wrap">
          {STATUS_TABS.map((t) => (
            <button key={t.label} type="button" onClick={() => setStatusFiltro(t.key)}
                    className={`rounded-md border px-3 py-1.5 text-sm ${statusFiltro === t.key ? 'bg-accent' : 'hover:bg-accent'}`}>
              {t.label}
            </button>
          ))}
        </div>
        <div className="rounded-md border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Telefone</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
                <th className="px-4 py-2.5 font-semibold">Erro</th>
              </tr>
            </thead>
            <tbody>
              {(destinatarios ?? []).map((d, i) => (
                <tr key={`${d.whatsapp}-${i}`} className="border-b last:border-b-0">
                  <td className="px-4 py-2.5 font-mono text-xs">{d.whatsapp}</td>
                  <td className="px-4 py-2.5">
                    <Badge variant="outline">{d.status}</Badge>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">{d.erro ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {destinatarios && destinatarios.length === 0 && (
            <p className="px-4 py-6 text-sm text-muted-foreground">Nenhum contato neste filtro.</p>
          )}
        </div>
      </div>

      <div className="rounded-md border p-4 space-y-3 max-w-md">
        <p className="text-sm font-medium">Enviar teste</p>
        <div className="flex gap-3">
          <Input placeholder="5592999999999" value={testNum}
                 onChange={(e) => setTestNum(e.target.value)} />
          <button type="button"
                  onClick={() => testSend.mutate(testNum, {
                    onSuccess: () => toast.success('Teste enviado'),
                    onError: (e) => toast.error(e instanceof Error ? e.message : 'Erro'),
                  })}
                  className="rounded-md border px-3 py-2 text-sm hover:bg-accent whitespace-nowrap">
            Enviar
          </button>
        </div>
      </div>
    </div>
  )
}
