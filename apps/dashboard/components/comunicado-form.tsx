'use client'
import { useRouter } from 'next/navigation'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { Download, Send } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { getAccessToken } from '@/lib/api/token'
import {
  exportClientesUrl,
  useBroadcastTemplates,
  useCanais,
  useCreateCampanha,
  usePreviewSegmento,
  useSendCampanha,
} from '@/lib/api/queries'
import type { SegmentoFiltros } from '@/lib/api/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? ''

export function ComunicadoForm() {
  const router = useRouter()
  const { data: templates } = useBroadcastTemplates()
  const { data: canais } = useCanais()
  const preview = usePreviewSegmento()
  const createCampanha = useCreateCampanha()
  const sendCampanha = useSendCampanha()

  const cloudCanais = useMemo(
    () => (canais ?? []).filter((c) => c.provider === 'cloud'),
    [canais],
  )

  const [titulo, setTitulo] = useState('')
  const [canalId, setCanalId] = useState('')
  const [templateName, setTemplateName] = useState('')
  const [vars, setVars] = useState<Record<number, string>>({})
  const [filtros, setFiltros] = useState<SegmentoFiltros>({})

  const template = templates?.find((t) => t.name === templateName)

  function runPreview() {
    preview.mutate(filtros)
  }

  async function handleExport(fmt: 'csv' | 'xlsx') {
    const path = exportClientesUrl(filtros, fmt)
    const res = await fetch(`${API_URL}${path}`, {
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
    a.download = `clientes.${fmt}`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  async function handleDisparar() {
    if (!template) return
    const body_params = (template.variaveis ?? [])
      .slice()
      .sort((a, b) => a.indice - b.indice)
      .map((v) => vars[v.indice] ?? '')
    try {
      const camp = await createCampanha.mutateAsync({
        titulo,
        canal_id: canalId,
        template_name: templateName,
        body_params,
        segmentacao: filtros,
      })
      const total = preview.data?.total ?? 0
      if (!window.confirm(`Disparar para ${total} cliente(s)?`)) return
      await sendCampanha.mutateAsync(camp.id)
      toast.success('Campanha enfileirada')
      router.push(`/comunicados/${camp.id}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao disparar')
    }
  }

  const podeDisparar = titulo && canalId && templateName

  return (
    <div className="space-y-5">
      <div className="space-y-1.5">
        <label className="text-sm font-medium">Título</label>
        <Input value={titulo} onChange={(e) => setTitulo(e.target.value)}
               placeholder="Ex: Lançamento do app" />
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium">Canal (Cloud)</label>
        <select className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={canalId} onChange={(e) => setCanalId(e.target.value)}>
          <option value="">Selecione…</option>
          {cloudCanais.map((c) => (
            <option key={c.id} value={c.id}>{c.nome}</option>
          ))}
        </select>
        {cloudCanais.length === 0 && (
          <p className="text-xs text-destructive">
            Nenhum canal Cloud cadastrado. Cadastre um em Canais WhatsApp.
          </p>
        )}
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium">Template</label>
        <select className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={templateName}
                onChange={(e) => { setTemplateName(e.target.value); setVars({}) }}>
          <option value="">Selecione…</option>
          {(templates ?? []).map((t) => (
            <option key={t.id} value={t.name}>{t.name}</option>
          ))}
        </select>
      </div>

      {template?.variaveis.map((v) => (
        <div key={v.indice} className="space-y-1.5">
          <label className="text-sm font-medium">{v.label}</label>
          <Input
            value={vars[v.indice] ?? ''}
            onChange={(e) => setVars((s) => ({ ...s, [v.indice]: e.target.value }))}
            placeholder={v.tipo === 'url' ? 'https://…' : ''}
          />
        </div>
      ))}

      <div className="rounded-md border p-4 space-y-3">
        <p className="text-sm font-medium">Segmentação</p>
        <div className="grid grid-cols-3 gap-3">
          <Input placeholder="Cidade" value={filtros.cidade ?? ''}
                 onChange={(e) => setFiltros((f) => ({ ...f, cidade: e.target.value || undefined }))} />
          <Input placeholder="Status" value={filtros.status ?? ''}
                 onChange={(e) => setFiltros((f) => ({ ...f, status: e.target.value || undefined }))} />
          <Input placeholder="Plano" value={filtros.plano ?? ''}
                 onChange={(e) => setFiltros((f) => ({ ...f, plano: e.target.value || undefined }))} />
        </div>
        <p className="text-xs text-muted-foreground">Sem filtros = base inteira.</p>
        <div className="flex items-center gap-3">
          <button onClick={runPreview} type="button"
                  className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent">
            Calcular alcance
          </button>
          {preview.data && (
            <span className="text-sm font-medium">
              {preview.data.total} cliente(s) vão receber
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={() => handleExport('csv')}
                className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent">
          <Download className="h-4 w-4" /> Exportar CSV
        </button>
        <button type="button" onClick={() => handleExport('xlsx')}
                className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent">
          <Download className="h-4 w-4" /> Exportar Excel
        </button>
        <button type="button" onClick={handleDisparar} disabled={!podeDisparar}
                className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
          <Send className="h-4 w-4" /> Disparar
        </button>
      </div>
    </div>
  )
}
