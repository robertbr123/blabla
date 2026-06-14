'use client'
import { useRouter } from 'next/navigation'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { Download, Send, Upload } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { getAccessToken } from '@/lib/api/token'
import {
  exportClientesUrl,
  useBroadcastTemplates,
  useCanais,
  useContagemImport,
  useCreateCampanha,
  usePreviewSegmento,
  useSegmentoValores,
  useSelecionarImport,
  useSendCampanha,
} from '@/lib/api/queries'
import type { ImportResult, SegmentoFiltros, SegmentoValores } from '@/lib/api/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? ''

export function ComunicadoForm() {
  const router = useRouter()
  const { data: templates } = useBroadcastTemplates()
  const { data: canais } = useCanais()
  const { data: valores } = useSegmentoValores()
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
  const [botao, setBotao] = useState('')
  const [filtros, setFiltros] = useState<SegmentoFiltros>({})
  const [origem, setOrigem] = useState<'segmento' | 'importado'>('segmento')
  const [csvFile, setCsvFile] = useState<File | null>(null)

  const [campanhaId, setCampanhaId] = useState<string | null>(null)
  const [valoresImport, setValoresImport] = useState<SegmentoValores | null>(null)
  const [importInfo, setImportInfo] = useState<ImportResult | null>(null)
  const [importando, setImportando] = useState(false)
  const [contagem, setContagem] = useState<number | null>(null)
  const [amostraImport, setAmostraImport] = useState<import('@/lib/api/types').AmostraDestinatario[]>([])
  const contar = useContagemImport(campanhaId ?? '')
  const selecionar = useSelecionarImport(campanhaId ?? '')

  const template = templates?.find((t) => t.name === templateName)
  const botaoDinamico = template?.botoes?.find((b) => b.url_dinamica)

  function buildBodyParams(): string[] {
    return (template?.variaveis ?? [])
      .slice()
      .sort((a, b) => a.indice - b.indice)
      .map((v) => vars[v.indice] ?? '')
  }

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

  function baixarExemplo() {
    const exemplo =
      'telefone;cidade;status;plano\n' +
      '5592991112222;Manaus;Ativo;100MB\n' +
      '559784272884;Eirunepe;Ativo;50MB\n'
    const blob = new Blob(['﻿' + exemplo], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'exemplo-comunicado.csv'
    a.click()
    URL.revokeObjectURL(a.href)
  }

  async function handleImportar() {
    if (!template || !csvFile) {
      toast.error('Escolha template e arquivo')
      return
    }
    setImportando(true)
    try {
      const camp = await createCampanha.mutateAsync({
        titulo,
        canal_id: canalId,
        template_name: templateName,
        body_params: buildBodyParams(),
        segmentacao: {},
        origem: 'importado',
        button_param: botaoDinamico ? botao || null : null,
      })
      const fd = new FormData()
      fd.append('file', csvFile)
      const res = await fetch(
        `${API_URL}/api/v1/admin/comunicados/${camp.id}/destinatarios/importar`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getAccessToken() ?? ''}` },
          credentials: 'include',
          body: fd,
        },
      )
      if (!res.ok) {
        toast.error('Falha ao importar CSV')
        return
      }
      const imp = (await res.json()) as ImportResult
      setCampanhaId(camp.id)
      setValoresImport(imp.valores)
      setImportInfo(imp)
      setContagem(imp.importados)
      setAmostraImport(imp.amostra)
      setFiltros({})
      toast.success(`${imp.importados} importados, ${imp.invalidos} inválidos`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao importar')
    } finally {
      setImportando(false)
    }
  }

  function recontar(novos: SegmentoFiltros) {
    setFiltros(novos)
    contar.mutate(novos, {
      onSuccess: (r) => {
        setContagem(r.total)
        setAmostraImport(r.amostra)
      },
    })
  }

  async function handleDispararSegmento() {
    if (!template) return
    try {
      const camp = await createCampanha.mutateAsync({
        titulo,
        canal_id: canalId,
        template_name: templateName,
        body_params: buildBodyParams(),
        segmentacao: filtros,
        origem: 'segmento',
        button_param: botaoDinamico ? botao || null : null,
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

  async function handleDispararImport() {
    if (!campanhaId) return
    try {
      const sel = await selecionar.mutateAsync(filtros)
      if (!window.confirm(`Disparar para ${sel.selecionados} contato(s)?`)) return
      await sendCampanha.mutateAsync(campanhaId)
      toast.success('Campanha enfileirada')
      router.push(`/comunicados/${campanhaId}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao disparar')
    }
  }

  const cabecalhoOk = titulo && canalId && templateName

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
          <Input value={vars[v.indice] ?? ''}
                 onChange={(e) => setVars((s) => ({ ...s, [v.indice]: e.target.value }))}
                 placeholder={v.tipo === 'url' ? 'https://…' : ''} />
        </div>
      ))}

      {botaoDinamico && (
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Valor do botão ({botaoDinamico.texto})</label>
          <Input value={botao} onChange={(e) => setBotao(e.target.value)} placeholder="https://…" />
        </div>
      )}

      <div className="rounded-md border p-4 space-y-3">
        <div className="flex gap-4 text-sm">
          <label className="flex items-center gap-2">
            <input type="radio" checked={origem === 'segmento'}
                   onChange={() => { setOrigem('segmento'); setCampanhaId(null) }} /> Segmento da base
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" checked={origem === 'importado'}
                   onChange={() => setOrigem('importado')} /> Importar CSV
          </label>
        </div>

        {origem === 'segmento' && (
          <>
            <div className="grid grid-cols-3 gap-3">
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.cidade ?? ''}
                      onChange={(e) => setFiltros((f) => ({ ...f, cidade: e.target.value || undefined }))}>
                <option value="">Cidade (todas)</option>
                {(valores?.cidades ?? []).map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.status ?? ''}
                      onChange={(e) => setFiltros((f) => ({ ...f, status: e.target.value || undefined }))}>
                <option value="">Status (todos)</option>
                {(valores?.status ?? []).map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.plano ?? ''}
                      onChange={(e) => setFiltros((f) => ({ ...f, plano: e.target.value || undefined }))}>
                <option value="">Plano (todos)</option>
                {(valores?.planos ?? []).map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <button onClick={runPreview} type="button"
                      className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent">Calcular alcance</button>
              {preview.data && (
                <span className="text-sm font-medium">{preview.data.total} cliente(s) vão receber</span>
              )}
              <button type="button" onClick={() => handleExport('csv')}
                      className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-accent">
                <Download className="h-4 w-4" /> CSV
              </button>
              <button type="button" onClick={() => handleExport('xlsx')}
                      className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-accent">
                <Download className="h-4 w-4" /> Excel
              </button>
            </div>
            {preview.data && preview.data.amostra.length > 0 && (
              <div className="rounded-md border bg-card overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Nome</th>
                      <th className="px-3 py-2 font-semibold">Telefone</th>
                      <th className="px-3 py-2 font-semibold">Cidade</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.data.amostra.map((a) => (
                      <tr key={a.id} className="border-b last:border-b-0">
                        <td className="px-3 py-2">{a.nome ?? '—'}</td>
                        <td className="px-3 py-2 font-mono text-xs">{a.whatsapp}</td>
                        <td className="px-3 py-2 text-muted-foreground">{a.cidade ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="px-3 py-2 text-xs text-muted-foreground">
                  mostrando {preview.data.amostra.length} de {preview.data.total}
                </p>
              </div>
            )}
            <button type="button" onClick={handleDispararSegmento} disabled={!cabecalhoOk}
                    className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              <Send className="h-4 w-4" /> Disparar
            </button>
          </>
        )}

        {origem === 'importado' && !campanhaId && (
          <div className="space-y-2">
            <input type="file" accept=".csv,text/csv"
                   onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)} />
            <p className="text-xs text-muted-foreground">
              CSV com a coluna de telefone + (opcional) cidade, status, plano para filtrar.
              O conteúdo da mensagem (links etc.) você preenche acima no formulário.
            </p>
            <div className="flex gap-3">
              <button type="button" onClick={baixarExemplo}
                      className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent">
                <Download className="h-4 w-4" /> Baixar exemplo
              </button>
            </div>
            <button type="button" onClick={handleImportar} disabled={!cabecalhoOk || !csvFile || importando}
                    className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              <Upload className="h-4 w-4" /> {importando ? 'Importando…' : 'Importar'}
            </button>
          </div>
        )}

        {origem === 'importado' && campanhaId && (
          <>
            <p className="text-sm text-muted-foreground">
              {importInfo?.importados} importados, {importInfo?.invalidos} inválidos. Filtre quem recebe:
            </p>
            <div className="grid grid-cols-3 gap-3">
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.cidade ?? ''}
                      onChange={(e) => recontar({ ...filtros, cidade: e.target.value || undefined })}>
                <option value="">Cidade (todas)</option>
                {(valoresImport?.cidades ?? []).map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.status ?? ''}
                      onChange={(e) => recontar({ ...filtros, status: e.target.value || undefined })}>
                <option value="">Status (todos)</option>
                {(valoresImport?.status ?? []).map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.plano ?? ''}
                      onChange={(e) => recontar({ ...filtros, plano: e.target.value || undefined })}>
                <option value="">Plano (todos)</option>
                {(valoresImport?.planos ?? []).map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <p className="text-sm font-medium">{contagem ?? 0} contato(s) vão receber</p>
            {amostraImport.length > 0 && (
              <div className="rounded-md border bg-card overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Telefone</th>
                      <th className="px-3 py-2 font-semibold">Cidade</th>
                      <th className="px-3 py-2 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {amostraImport.map((a, i) => (
                      <tr key={`${a.whatsapp}-${i}`} className="border-b last:border-b-0">
                        <td className="px-3 py-2 font-mono text-xs">{a.whatsapp}</td>
                        <td className="px-3 py-2 text-muted-foreground">{a.cidade ?? '—'}</td>
                        <td className="px-3 py-2 text-muted-foreground">{a.status ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="px-3 py-2 text-xs text-muted-foreground">
                  mostrando {amostraImport.length} de {contagem ?? 0}
                </p>
              </div>
            )}
            <button type="button" onClick={handleDispararImport}
                    className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
              <Send className="h-4 w-4" /> Disparar
            </button>
          </>
        )}
      </div>
    </div>
  )
}
