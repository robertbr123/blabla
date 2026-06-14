'use client'
import { useState } from 'react'
import { toast } from 'sonner'
import { RefreshCw, Plus } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { apiFetch } from '@/lib/api/client'
import { useBroadcastTemplates, useSyncTemplates } from '@/lib/api/queries'

export function ComunicadoTemplates() {
  const { data: templates, isLoading } = useBroadcastTemplates()
  const sync = useSyncTemplates()
  const qc = useQueryClient()

  const [novoNome, setNovoNome] = useState('')
  const [salvando, setSalvando] = useState(false)

  async function criarManual() {
    if (!novoNome.trim()) return
    setSalvando(true)
    try {
      await apiFetch('/api/v1/admin/comunicados/templates', {
        method: 'POST',
        body: JSON.stringify({ name: novoNome.trim() }),
      })
      toast.success('Template criado')
      setNovoNome('')
      qc.invalidateQueries({ queryKey: ['broadcast-templates'] })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao criar')
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() =>
            sync.mutate(undefined, {
              onSuccess: (r) => toast.success(`${r.sincronizados} sincronizados (${r.canais} canais)`),
              onError: (e) => toast.error(e instanceof Error ? e.message : 'Erro'),
            })
          }
          disabled={sync.isPending}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          <RefreshCw className="h-4 w-4" /> Sincronizar com a Meta
        </button>
      </div>

      <div className="flex items-end gap-3">
        <div className="space-y-1.5 flex-1 max-w-xs">
          <label className="text-sm font-medium">Cadastrar manual (nome do template)</label>
          <Input value={novoNome} onChange={(e) => setNovoNome(e.target.value)}
                 placeholder="ex: comunicado_geral" />
        </div>
        <button type="button" onClick={criarManual} disabled={salvando}
                className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent disabled:opacity-50">
          <Plus className="h-4 w-4" /> Adicionar
        </button>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {templates && (
        <div className="rounded-md border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Nome</th>
                <th className="px-4 py-2.5 font-semibold">Idioma</th>
                <th className="px-4 py-2.5 font-semibold">Variáveis</th>
                <th className="px-4 py-2.5 font-semibold">Botões</th>
              </tr>
            </thead>
            <tbody>
              {templates.map((t) => (
                <tr key={t.id} className="border-b last:border-b-0">
                  <td className="px-4 py-3 font-mono text-xs">{t.name}</td>
                  <td className="px-4 py-3 text-muted-foreground">{t.language}</td>
                  <td className="px-4 py-3 text-muted-foreground">{t.variaveis.length}</td>
                  <td className="px-4 py-3">
                    {(t.botoes ?? []).map((b) => (
                      <Badge key={b.index} variant="outline" className="mr-1">
                        {b.texto}{b.url_dinamica ? ' (dinâmico)' : ''}
                      </Badge>
                    ))}
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
