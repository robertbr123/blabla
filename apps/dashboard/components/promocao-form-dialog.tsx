'use client'
import { useEffect, useRef, useState } from 'react'
import { Upload, X, Save, Trash2, Image as ImageIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import {
  useCreatePromocao,
  useDeletePromocao,
  usePatchPromocao,
  useUploadPromocaoImagem,
} from '@/lib/api/queries'
import type {
  PromocaoAdmin,
  PromocaoCreate,
  PromocaoSegmento,
  PromocaoTipo,
} from '@/lib/api/types'
import { PromocaoPreviewCard } from './promocao-preview-card'

interface Props {
  open: boolean
  promocao: PromocaoAdmin | null
  apiBase: string // pra resolver imagem_url relativa
  onClose: () => void
}

const TIPOS: Array<{ value: PromocaoTipo; label: string }> = [
  { value: 'generica', label: 'Genérica' },
  { value: 'indicacao', label: 'Indicação' },
]

const SEGMENTOS: Array<{ value: PromocaoSegmento; label: string }> = [
  { value: 'todos', label: 'Todos os clientes' },
  { value: 'inadimplentes', label: 'Inadimplentes (TODO)' },
  { value: 'adimplentes', label: 'Adimplentes (TODO)' },
]

function emptyDraft(): PromocaoCreate {
  return {
    titulo: '',
    subtitulo: '',
    cta_label: 'Saiba mais',
    cta_action: 'info',
    tipo: 'generica',
    ativa: true,
    ordem: 0,
    segmento: 'todos',
    gradient_from: null,
    gradient_to: null,
    icon: null,
    imagem_url: null,
    valido_de: null,
    valido_ate: null,
  }
}

function fromExisting(p: PromocaoAdmin): PromocaoCreate {
  return {
    titulo: p.titulo,
    subtitulo: p.subtitulo,
    cta_label: p.cta_label,
    cta_action: p.cta_action,
    tipo: p.tipo,
    ativa: p.ativa,
    ordem: p.ordem,
    segmento: p.segmento,
    gradient_from: p.gradient_from,
    gradient_to: p.gradient_to,
    icon: p.icon,
    imagem_url: p.imagem_url,
    valido_de: p.valido_de,
    valido_ate: p.valido_ate,
  }
}

function ctaParts(cta: string): { kind: 'info' | 'url' | 'tela'; value: string } {
  if (cta === 'info') return { kind: 'info', value: '' }
  if (cta.startsWith('url:')) return { kind: 'url', value: cta.slice(4) }
  if (cta.startsWith('tela:')) return { kind: 'tela', value: cta.slice(5) }
  return { kind: 'info', value: '' }
}

export function PromocaoFormDialog(props: Props) {
  const isEditing = !!props.promocao
  const [draft, setDraft] = useState<PromocaoCreate>(emptyDraft())
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const create = useCreatePromocao()
  const patch = usePatchPromocao(props.promocao?.id ?? '')
  const del = useDeletePromocao()
  const upload = useUploadPromocaoImagem(props.promocao?.id ?? '')

  useEffect(() => {
    setError(null)
    if (props.promocao) setDraft(fromExisting(props.promocao))
    else setDraft(emptyDraft())
  }, [props.promocao, props.open])

  if (!props.open) return null

  const cta = ctaParts(draft.cta_action ?? 'info')

  function setField<K extends keyof PromocaoCreate>(
    key: K,
    value: PromocaoCreate[K],
  ) {
    setDraft((d) => ({ ...d, [key]: value }))
  }

  function setCta(kind: 'info' | 'url' | 'tela', value: string) {
    if (kind === 'info') setField('cta_action', 'info')
    else setField('cta_action', `${kind}:${value}`)
  }

  async function handleSave() {
    setError(null)
    if (!draft.titulo.trim()) {
      setError('Título é obrigatório')
      return
    }
    try {
      if (isEditing && props.promocao) {
        await patch.mutateAsync(draft)
      } else {
        await create.mutateAsync(draft)
      }
      props.onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro ao salvar')
    }
  }

  async function handleDelete() {
    if (!props.promocao) return
    if (
      !confirm(
        `Excluir promoção "${props.promocao.titulo}"? Esta ação não pode ser desfeita.`,
      )
    )
      return
    try {
      await del.mutateAsync(props.promocao.id)
      props.onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro ao excluir')
    }
  }

  async function handleUpload(file: File) {
    if (!isEditing || !props.promocao) {
      setError('Salve a promoção antes de enviar a imagem.')
      return
    }
    try {
      const updated = await upload.mutateAsync(file)
      setField('imagem_url', updated.imagem_url)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro no upload')
    }
  }

  const previewImagemUrl = draft.imagem_url
    ? draft.imagem_url.startsWith('http')
      ? draft.imagem_url
      : `${props.apiBase}${draft.imagem_url}`
    : null

  return (
    <div className="fixed inset-0 z-50 flex">
      <div
        className="absolute inset-0 bg-black/50"
        onClick={props.onClose}
        aria-hidden
      />
      <div className="relative ml-auto flex h-full w-full max-w-3xl flex-col bg-background shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold">
              {isEditing ? 'Editar promoção' : 'Nova promoção'}
            </h2>
            <p className="text-xs text-muted-foreground">
              {isEditing
                ? 'Alterações refletem no app em tempo real.'
                : 'Salve pra habilitar upload de imagem.'}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={props.onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="grid flex-1 grid-cols-1 gap-6 overflow-y-auto p-6 lg:grid-cols-2">
          {/* Form */}
          <div className="space-y-4">
            <div>
              <Label htmlFor="titulo">Título *</Label>
              <Input
                id="titulo"
                value={draft.titulo}
                onChange={(e) => setField('titulo', e.target.value)}
                maxLength={120}
                placeholder="Upgrade pra 1 Giga"
              />
            </div>
            <div>
              <Label htmlFor="subtitulo">Subtítulo</Label>
              <Textarea
                id="subtitulo"
                value={draft.subtitulo ?? ''}
                onChange={(e) => setField('subtitulo', e.target.value)}
                maxLength={240}
                rows={2}
                placeholder="Velocidade dobrada com o mesmo valor no primeiro mês."
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="tipo">Tipo</Label>
                <select
                  id="tipo"
                  value={draft.tipo ?? 'generica'}
                  onChange={(e) =>
                    setField('tipo', e.target.value as PromocaoTipo)
                  }
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
                >
                  {TIPOS.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
                {draft.tipo === 'indicacao' && (
                  <p className="mt-1 text-[10px] text-pink-700">
                    Tipo Indicação fixa CTA pra <code>tela:/indicacao</code>. Ao salvar, o backend força esse valor.
                  </p>
                )}
              </div>
              <div>
                <Label htmlFor="segmento">Segmento</Label>
                <select
                  id="segmento"
                  value={draft.segmento ?? 'todos'}
                  onChange={(e) =>
                    setField('segmento', e.target.value as PromocaoSegmento)
                  }
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
                >
                  {SEGMENTOS.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <Label htmlFor="cta_label">CTA — Texto do botão</Label>
              <Input
                id="cta_label"
                value={draft.cta_label ?? ''}
                onChange={(e) => setField('cta_label', e.target.value)}
                maxLength={40}
                placeholder="Quero esse"
              />
            </div>

            {draft.tipo === 'indicacao' ? (
              <div className="rounded-md border border-pink-200 bg-pink-50 p-3 text-xs text-pink-700">
                <p className="font-medium">CTA fixo: abrir tela in-app</p>
                <p className="mt-1">
                  Ao clicar, o app navega pra <code>/indicacao</code> onde o cliente vê o próprio código e compartilha via WhatsApp.
                </p>
              </div>
            ) : (
              <div className="rounded-md border bg-muted/30 p-3 space-y-2">
                <Label className="text-xs">CTA — Ação ao clicar</Label>
                <div className="flex gap-2">
                  {(['info', 'url', 'tela'] as const).map((k) => (
                    <button
                      key={k}
                      type="button"
                      onClick={() => setCta(k, cta.value)}
                      className={`rounded-md border px-3 py-1 text-xs font-medium ${
                        cta.kind === k
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-input bg-background'
                      }`}
                    >
                      {k === 'info'
                        ? 'Apenas informativo'
                        : k === 'url'
                          ? 'Abrir URL externa'
                          : 'Abrir tela in-app'}
                    </button>
                  ))}
                </div>
                {cta.kind !== 'info' && (
                  <Input
                    value={cta.value}
                    onChange={(e) => setCta(cta.kind, e.target.value)}
                    placeholder={
                      cta.kind === 'url'
                        ? 'https://exemplo.com/promo'
                        : '/indicacao ou /suporte/novo'
                    }
                  />
                )}
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="gradient_from">Cor inicial (hex)</Label>
                <Input
                  id="gradient_from"
                  value={draft.gradient_from ?? ''}
                  onChange={(e) =>
                    setField('gradient_from', e.target.value || null)
                  }
                  placeholder="#8B5CF6"
                />
              </div>
              <div>
                <Label htmlFor="gradient_to">Cor final (hex)</Label>
                <Input
                  id="gradient_to"
                  value={draft.gradient_to ?? ''}
                  onChange={(e) =>
                    setField('gradient_to', e.target.value || null)
                  }
                  placeholder="#5B6CFF"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="valido_de">Válido de</Label>
                <Input
                  id="valido_de"
                  type="datetime-local"
                  value={draft.valido_de?.slice(0, 16) ?? ''}
                  onChange={(e) =>
                    setField(
                      'valido_de',
                      e.target.value ? new Date(e.target.value).toISOString() : null,
                    )
                  }
                />
              </div>
              <div>
                <Label htmlFor="valido_ate">Válido até</Label>
                <Input
                  id="valido_ate"
                  type="datetime-local"
                  value={draft.valido_ate?.slice(0, 16) ?? ''}
                  onChange={(e) =>
                    setField(
                      'valido_ate',
                      e.target.value ? new Date(e.target.value).toISOString() : null,
                    )
                  }
                />
              </div>
            </div>

            <div>
              <Label htmlFor="icon">Ícone (nome Material)</Label>
              <Input
                id="icon"
                value={draft.icon ?? ''}
                onChange={(e) => setField('icon', e.target.value || null)}
                placeholder="rocket_launch_rounded"
              />
              <p className="mt-1 text-[10px] text-muted-foreground">
                O app mapeia esse nome pro IconData. Lista de suportados será documentada em C.3.
              </p>
            </div>

            <div className="flex items-center justify-between rounded-md border p-3">
              <div>
                <p className="text-sm font-medium">Ativa</p>
                <p className="text-xs text-muted-foreground">
                  Promoção desativada não aparece no app.
                </p>
              </div>
              <Switch
                checked={draft.ativa ?? true}
                onCheckedChange={(v: boolean) => setField('ativa', v)}
              />
            </div>

            {/* Upload imagem */}
            <div className="rounded-md border p-3 space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-xs">Imagem de fundo (opcional)</Label>
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (f) handleUpload(f)
                    e.target.value = ''
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => fileRef.current?.click()}
                  disabled={!isEditing || upload.isPending}
                >
                  <Upload className="mr-1 h-3 w-3" />
                  {upload.isPending ? 'Enviando…' : 'Enviar'}
                </Button>
              </div>
              {draft.imagem_url ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <ImageIcon className="h-3 w-3" />
                  <code className="truncate font-mono">{draft.imagem_url}</code>
                  <button
                    type="button"
                    onClick={() => setField('imagem_url', null)}
                    className="text-destructive hover:underline"
                  >
                    remover
                  </button>
                </div>
              ) : (
                <p className="text-[10px] text-muted-foreground">
                  Sem imagem. JPG/PNG/WEBP até 2MB.
                </p>
              )}
            </div>
          </div>

          {/* Preview */}
          <div className="space-y-4">
            <PromocaoPreviewCard
              titulo={draft.titulo}
              subtitulo={draft.subtitulo ?? ''}
              ctaLabel={draft.cta_label ?? 'Saiba mais'}
              gradientFrom={draft.gradient_from}
              gradientTo={draft.gradient_to}
              imagemUrl={previewImagemUrl}
              icon={draft.icon}
            />
            {isEditing && props.promocao && (
              <div className="rounded-md border p-3 text-xs">
                <p className="font-medium">Métricas</p>
                <div className="mt-2 grid grid-cols-3 gap-2 text-center">
                  <div>
                    <p className="text-lg font-semibold">{props.promocao.views}</p>
                    <p className="text-[10px] text-muted-foreground">Views</p>
                  </div>
                  <div>
                    <p className="text-lg font-semibold">{props.promocao.clicks}</p>
                    <p className="text-[10px] text-muted-foreground">Clicks</p>
                  </div>
                  <div>
                    <p className="text-lg font-semibold">{props.promocao.ctr}%</p>
                    <p className="text-[10px] text-muted-foreground">CTR</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t px-6 py-3">
          <div>
            {isEditing && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDelete}
                disabled={del.isPending}
                className="text-destructive hover:text-destructive"
              >
                <Trash2 className="mr-1 h-3 w-3" />
                Excluir
              </Button>
            )}
          </div>
          <div className="flex items-center gap-2">
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            <Button variant="outline" onClick={props.onClose}>
              Cancelar
            </Button>
            <Button
              onClick={handleSave}
              disabled={create.isPending || patch.isPending}
            >
              <Save className="mr-1 h-3 w-3" />
              {isEditing
                ? patch.isPending
                  ? 'Salvando…'
                  : 'Salvar'
                : create.isPending
                  ? 'Criando…'
                  : 'Criar'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
