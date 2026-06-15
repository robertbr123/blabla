'use client'
import { useRouter } from 'next/navigation'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { Save } from 'lucide-react'
import { Input } from '@/components/ui/input'
import {
  useBroadcastTemplates,
  useCampanha,
  usePatchCampanha,
  useSegmentoValores,
} from '@/lib/api/queries'
import type { SegmentoFiltros } from '@/lib/api/types'

const EDITAVEL = new Set(['rascunho', 'erro'])

export function ComunicadoEditForm({ id }: { id: string }) {
  const router = useRouter()
  const { data: c, isLoading } = useCampanha(id)
  const { data: templates } = useBroadcastTemplates()
  const { data: valores } = useSegmentoValores()
  const patch = usePatchCampanha()

  const [titulo, setTitulo] = useState('')
  const [vars, setVars] = useState<Record<number, string>>({})
  const [botao, setBotao] = useState('')
  const [filtros, setFiltros] = useState<SegmentoFiltros>({})
  const [carregado, setCarregado] = useState(false)

  const template = useMemo(
    () => templates?.find((t) => t.name === c?.template_name),
    [templates, c?.template_name],
  )
  const botaoDinamico = template?.botoes?.find((b) => b.url_dinamica)

  // Prefill uma vez quando a campanha chega.
  useEffect(() => {
    if (!c || carregado) return
    setTitulo(c.titulo)
    setBotao(c.button_param ?? '')
    setFiltros(c.segmentacao ?? {})
    const m: Record<number, string> = {}
    ;(c.body_params ?? []).forEach((v, i) => {
      m[i + 1] = v
    })
    setVars(m)
    setCarregado(true)
  }, [c, carregado])

  if (isLoading || !c) return <p className="text-sm text-muted-foreground">Carregando…</p>

  if (!EDITAVEL.has(c.status)) {
    return (
      <p className="text-sm text-muted-foreground">
        Só dá pra editar campanhas em rascunho ou com erro. Esta está em {c.status}.
      </p>
    )
  }

  function buildBodyParams(): string[] {
    return (template?.variaveis ?? [])
      .slice()
      .sort((a, b) => a.indice - b.indice)
      .map((v) => vars[v.indice] ?? '')
  }

  async function salvar() {
    try {
      await patch.mutateAsync({
        id,
        body: {
          titulo,
          body_params: buildBodyParams(),
          segmentacao: filtros,
          ...(botaoDinamico ? { button_param: botao || null } : {}),
        },
      })
      toast.success('Comunicado atualizado')
      router.push(`/comunicados/${id}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao salvar')
    }
  }

  return (
    <div className="space-y-5">
      <div className="space-y-1.5">
        <label className="text-sm font-medium">Título</label>
        <Input value={titulo} onChange={(e) => setTitulo(e.target.value)} />
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium">Template</label>
        <p className="rounded-md border bg-muted/40 px-3 py-2 text-sm font-mono">
          {c.template_name}
        </p>
        <p className="text-xs text-muted-foreground">
          Pra trocar o template ou o canal, exclua e crie de novo.
        </p>
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

      {botaoDinamico && (
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Valor do botão ({botaoDinamico.texto})</label>
          <Input value={botao} onChange={(e) => setBotao(e.target.value)} placeholder="https://…" />
        </div>
      )}

      <div className="grid grid-cols-3 gap-3">
        <select
          className="rounded-md border bg-background px-3 py-2 text-sm"
          value={filtros.cidade ?? ''}
          onChange={(e) => setFiltros((f) => ({ ...f, cidade: e.target.value || undefined }))}
        >
          <option value="">Cidade (todas)</option>
          {(valores?.cidades ?? []).map((x) => <option key={x} value={x}>{x}</option>)}
        </select>
        <select
          className="rounded-md border bg-background px-3 py-2 text-sm"
          value={filtros.status ?? ''}
          onChange={(e) => setFiltros((f) => ({ ...f, status: e.target.value || undefined }))}
        >
          <option value="">Status (todos)</option>
          {(valores?.status ?? []).map((x) => <option key={x} value={x}>{x}</option>)}
        </select>
        <select
          className="rounded-md border bg-background px-3 py-2 text-sm"
          value={filtros.plano ?? ''}
          onChange={(e) => setFiltros((f) => ({ ...f, plano: e.target.value || undefined }))}
        >
          <option value="">Plano (todos)</option>
          {(valores?.planos ?? []).map((x) => <option key={x} value={x}>{x}</option>)}
        </select>
      </div>

      <button
        type="button"
        onClick={salvar}
        disabled={!titulo || patch.isPending}
        className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        <Save className="h-4 w-4" /> {patch.isPending ? 'Salvando…' : 'Salvar'}
      </button>
    </div>
  )
}
