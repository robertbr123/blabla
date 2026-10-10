'use client'
import { useRef, useState } from 'react'
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  ClipboardList,
  FileDown,
  History,
  MapPin,
  Package,
  RotateCcw,
  Send,
  SlidersHorizontal,
  Star,
  Upload,
  User,
  UserX,
  Wrench,
} from 'lucide-react'
import { toast } from 'sonner'
import { OsStatusPill } from './os-status-pill'
import { OsMapa } from './os-mapa'
import { FotosGaleria } from './os-fotos-galeria'
import {
  Age,
  Avatar,
  Panel,
  PanelBody,
  PanelHeader,
  Skeleton,
  StatusDot,
  TONE_SOFT,
  type Tone,
} from '@/components/noc/primitives'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  useConcluirOs,
  useOs,
  useOsConsumo,
  usePatchOs,
  useReabrirOs,
  useTecnicos,
  useUploadFoto,
} from '@/lib/api/queries'
import { apiFetch } from '@/lib/api/client'
import { getAccessToken } from '@/lib/api/token'
import { cn } from '@/lib/utils'

function fmtDataHora(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR')
}

/** Par rotulo/valor da grade de definicoes. */
function Field({
  label,
  children,
  className,
}: {
  label: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('min-w-0', className)}>
      <dt className="eyebrow">{label}</dt>
      <dd className="mt-1 break-words text-sm">{children}</dd>
    </div>
  )
}

function ErroPainel({ mensagem }: { mensagem: string }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/[0.08] p-4"
    >
      <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
      <div className="min-w-0">
        <p className="text-sm font-medium">Não foi possível carregar a OS</p>
        <p className="mt-0.5 break-words text-xs text-muted-foreground">{mensagem}</p>
      </div>
    </div>
  )
}

function Marco({
  tone,
  label,
  iso,
}: {
  tone: Tone
  label: string
  iso: string | null | undefined
}) {
  return (
    <li className="flex items-center gap-2.5 text-sm">
      <StatusDot tone={iso ? tone : 'muted'} className={iso ? undefined : 'opacity-40'} />
      <span className="text-muted-foreground">{label}</span>
      <span className="num ml-auto text-[13px]">{iso ? fmtDataHora(iso) : '—'}</span>
    </li>
  )
}

export function OsDetail({ id }: { id: string }) {
  const { data, isLoading, error } = useOs(id)
  const { data: consumo } = useOsConsumo(id)
  const { data: tecnicosData, isLoading: tecnicosLoading } = useTecnicos({})
  const patchOs = usePatchOs(id)
  const concluirOs = useConcluirOs(id)
  const reabrirOs = useReabrirOs(id)
  const uploadFoto = useUploadFoto(id)
  const fileRef = useRef<HTMLInputElement>(null)
  const [csat, setCsat] = useState('')
  const [comentario, setComentario] = useState('')
  const [reaberturaMotivo, setReaberturaMotivo] = useState('')
  const [enviandoPdf, setEnviandoPdf] = useState(false)

  if (isLoading) {
    return (
      <div role="status" aria-label="Carregando OS" className="space-y-4">
        <div className="flex items-center gap-3">
          <Skeleton className="h-7 w-40" />
          <Skeleton className="h-7 w-28" />
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <Skeleton className="h-36 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        </div>
      </div>
    )
  }
  if (error) {
    return <ErroPainel mensagem={error instanceof Error ? error.message : 'Erro ao carregar'} />
  }
  if (!data) return <ErroPainel mensagem="OS não encontrada" />

  async function handleConcluir() {
    await concluirOs.mutateAsync({
      csat: csat ? Number(csat) : undefined,
      comentario: comentario || undefined,
    })
    setCsat('')
    setComentario('')
  }

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    await uploadFoto.mutateAsync(file)
    if (fileRef.current) fileRef.current.value = ''
  }

  async function handleBaixarPdf() {
    const token = getAccessToken()
    const res = await fetch(`/api/v1/os/${id}/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: 'include',
    })
    if (!res.ok) {
      toast.error('Erro ao gerar PDF')
      return
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
    setTimeout(() => URL.revokeObjectURL(url), 10000)
  }

  async function handleEnviarPdfTecnico() {
    setEnviandoPdf(true)
    try {
      await apiFetch(`/api/v1/os/${id}/enviar-pdf-tecnico`, { method: 'POST' })
      toast.success('PDF enviado ao técnico via WhatsApp')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Erro ao enviar PDF')
    } finally {
      setEnviandoPdf(false)
    }
  }

  const isConcluida = data.status === 'concluida'
  const tecnicoNome = data.tecnico_id
    ? (tecnicosData?.items ?? []).find((t) => t.id === data.tecnico_id)?.nome ?? null
    : null
  const temConsumo =
    !!consumo && (consumo.movimentos.length > 0 || consumo.equipamentos.length > 0)
  const temAtendimento =
    !!data.relatorio ||
    (data.houve_visita !== null && data.houve_visita !== undefined) ||
    !!data.materiais
  const temAvaliacao = data.csat !== null || !!data.comentario_cliente
  const qtdFotos = data.fotos?.length ?? 0

  return (
    <div className="space-y-4">
      {/* Cabeçalho: identidade + estado à esquerda, ações à direita */}
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="num text-xl font-semibold tracking-tight">{data.codigo}</h1>
            <OsStatusPill status={data.status} />
          </div>
          <p className="mt-1 flex flex-wrap items-center gap-x-1.5 text-sm text-muted-foreground">
            {data.nome_cliente && (
              <>
                <span className="text-foreground">{data.nome_cliente}</span>
                <span aria-hidden>·</span>
              </>
            )}
            <span>Aberta há</span>
            <Age iso={data.criada_em} className="text-sm" />
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" onClick={handleBaixarPdf}>
            <FileDown className="h-4 w-4" /> Baixar PDF
          </Button>
          <Button
            disabled={enviandoPdf || !data?.tecnico_id}
            onClick={handleEnviarPdfTecnico}
            title={!data?.tecnico_id ? 'OS sem técnico atribuído' : undefined}
          >
            <Send className="h-4 w-4" />
            {enviandoPdf ? 'Enviando…' : 'Enviar PDF ao técnico'}
          </Button>
        </div>
      </header>

      <div className="grid items-start gap-4 lg:grid-cols-3">
        {/* ── Coluna principal ─────────────────────────────────────── */}
        <div className="min-w-0 space-y-4 lg:col-span-2">
          <Panel>
            <PanelHeader title="Cliente e endereço" icon={User} />
            <PanelBody>
              <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
                {data.nome_cliente && (
                  <Field label="Cliente">
                    <span className="font-medium">{data.nome_cliente}</span>
                  </Field>
                )}
                {data.plano && <Field label="Plano">{data.plano}</Field>}
                <Field label="Endereço" className="sm:col-span-2">
                  {data.endereco}
                </Field>
              </dl>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader title="Problema" icon={ClipboardList} />
            <PanelBody>
              <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                {data.problema}
              </p>
            </PanelBody>
          </Panel>

          {temAtendimento && (
            <Panel>
              <PanelHeader title="Atendimento" icon={Wrench} />
              <PanelBody>
                <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
                  {data.houve_visita !== null && data.houve_visita !== undefined && (
                    <Field label="Houve visita">{data.houve_visita ? 'Sim' : 'Não'}</Field>
                  )}
                  {data.relatorio && (
                    <Field label="Relatório do técnico" className="sm:col-span-2">
                      <span className="whitespace-pre-wrap">{data.relatorio}</span>
                    </Field>
                  )}
                  {data.materiais && (
                    <Field label="Materiais (relato do técnico)" className="sm:col-span-2">
                      <span className="whitespace-pre-wrap">{data.materiais}</span>
                    </Field>
                  )}
                </dl>
              </PanelBody>
            </Panel>
          )}

          {consumo && temConsumo && (
            <Panel>
              <PanelHeader
                title="Consumo de estoque registrado"
                icon={Package}
                meta={consumo.movimentos.length + consumo.equipamentos.length}
              />
              <PanelBody className="space-y-4">
                {consumo.movimentos.length > 0 && (
                  <ul className="divide-y divide-border/70 text-sm">
                    {consumo.movimentos.map((m) => (
                      <li
                        key={m.movimento_id}
                        className="flex flex-wrap items-baseline gap-x-2 gap-y-1 py-2 first:pt-0 last:pb-0"
                      >
                        <span className="font-medium">
                          <span className="num">{m.quantidade}×</span> {m.item_nome}
                        </span>
                        <span className="eyebrow">{m.tipo}</span>
                        {m.serial && (
                          <code className="num rounded bg-muted px-1.5 py-0.5 text-xs">
                            {m.serial}
                          </code>
                        )}
                        {m.tecnico_nome && (
                          <span className="text-xs text-muted-foreground">
                            · {m.tecnico_nome}
                          </span>
                        )}
                        {m.observacao && (
                          <span className="text-xs text-muted-foreground">
                            · {m.observacao}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
                {consumo.equipamentos.length > 0 && (
                  <div>
                    <div className="eyebrow">Equipamentos serializados nesta OS</div>
                    <ul className="mt-2 divide-y divide-border/70 text-sm">
                      {consumo.equipamentos.map((e) => (
                        <li
                          key={e.id}
                          className="flex flex-wrap items-baseline gap-x-2 gap-y-1 py-2 first:pt-0 last:pb-0"
                        >
                          <span className="font-medium">{e.item_nome}</span>
                          <code className="num rounded bg-muted px-1.5 py-0.5 text-xs">
                            {e.serial}
                          </code>
                          <span className="eyebrow">{e.evento}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </PanelBody>
            </Panel>
          )}

          {temAvaliacao && (
            <Panel>
              <PanelHeader title="Avaliação do cliente" icon={Star} />
              <PanelBody>
                <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
                  {data.csat !== null && (
                    <Field label="CSAT">
                      <span className="num font-medium">{data.csat}/5</span>
                    </Field>
                  )}
                  {data.comentario_cliente && (
                    <Field label="Comentário do cliente" className="sm:col-span-2">
                      <span className="whitespace-pre-wrap">{data.comentario_cliente}</span>
                    </Field>
                  )}
                </dl>
              </PanelBody>
            </Panel>
          )}

          <Panel>
            <PanelHeader
              title="Fotos"
              icon={Camera}
              meta={qtdFotos}
              actions={
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 px-2.5 text-xs"
                  onClick={() => fileRef.current?.click()}
                  disabled={uploadFoto.isPending}
                >
                  <Upload className="h-3.5 w-3.5" />
                  {uploadFoto.isPending ? 'Enviando…' : 'Adicionar foto'}
                </Button>
              }
            />
            <PanelBody className="space-y-3">
              <Input
                ref={fileRef}
                type="file"
                accept="image/*"
                onChange={handleFile}
                disabled={uploadFoto.isPending}
                className="hidden"
                aria-label="Adicionar foto à OS"
                tabIndex={-1}
              />
              {uploadFoto.isPending && (
                <p role="status" className="text-xs text-muted-foreground">Enviando…</p>
              )}
              {data.fotos && data.fotos.length > 0 ? (
                <FotosGaleria osId={id} fotos={data.fotos} />
              ) : (
                !uploadFoto.isPending && (
                  <p className="text-sm text-muted-foreground">Nenhuma foto anexada.</p>
                )
              )}
            </PanelBody>
          </Panel>
        </div>

        {/* ── Coluna lateral ───────────────────────────────────────── */}
        <div className="min-w-0 space-y-4">
          <Panel>
            <PanelHeader title="Técnico" icon={Wrench} />
            <PanelBody>
              {!data.tecnico_id ? (
                <div className="space-y-2">
                  <span
                    className={cn(
                      'inline-flex h-[22px] items-center gap-1 rounded-md px-2 text-xs font-medium ring-1 ring-inset',
                      TONE_SOFT.warning,
                    )}
                  >
                    <UserX aria-hidden className="h-3 w-3" />
                    Sem técnico
                  </span>
                  <p className="text-xs text-muted-foreground">
                    Atribua um técnico para habilitar o envio.
                  </p>
                </div>
              ) : tecnicoNome ? (
                <div className="flex min-w-0 items-center gap-2.5">
                  <Avatar name={tecnicoNome} />
                  <span className="truncate text-sm font-medium" title={tecnicoNome}>
                    {tecnicoNome}
                  </span>
                </div>
              ) : tecnicosLoading ? (
                <Skeleton className="h-8 w-40" />
              ) : (
                <p className="text-sm text-muted-foreground">Técnico atribuído</p>
              )}
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader title="Linha do tempo" icon={History} />
            <PanelBody>
              <ol className="space-y-2.5">
                <Marco tone="info" label="Criada em" iso={data.criada_em} />
                {data.agendamento_at && (
                  <Marco tone="info" label="Agendamento" iso={data.agendamento_at} />
                )}
                <Marco tone="success" label="Concluída em" iso={data.concluida_em} />
              </ol>
            </PanelBody>
          </Panel>

          {!isConcluida && (
            <Panel>
              <PanelHeader title="Mudar status" icon={SlidersHorizontal} />
              <PanelBody>
                <Select
                  aria-label="Status da OS"
                  defaultValue={data.status}
                  onChange={(e) => patchOs.mutate({ status: e.target.value })}
                  disabled={patchOs.isPending}
                >
                  <option value="pendente">Pendente</option>
                  <option value="em_andamento">Em andamento</option>
                  <option value="cancelada">Cancelada</option>
                </Select>
              </PanelBody>
            </Panel>
          )}

          {!isConcluida && (
            <Panel>
              <PanelHeader title="Concluir OS" icon={CheckCircle2} />
              <PanelBody className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="csat" className="text-xs text-muted-foreground">
                    CSAT (1-5)
                  </Label>
                  <Input
                    id="csat"
                    type="number"
                    min={1}
                    max={5}
                    value={csat}
                    onChange={(e) => setCsat(e.target.value)}
                    className="num"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="comentario" className="text-xs text-muted-foreground">
                    Comentário do cliente
                  </Label>
                  <Textarea
                    id="comentario"
                    value={comentario}
                    onChange={(e) => setComentario(e.target.value)}
                  />
                </div>
                <Button
                  className="w-full"
                  onClick={handleConcluir}
                  disabled={concluirOs.isPending}
                >
                  <CheckCircle2 className="h-4 w-4" /> Concluir
                </Button>
              </PanelBody>
            </Panel>
          )}

          {(data.status === 'concluida' || data.status === 'cancelada') && (
            <Panel>
              <PanelHeader title="Reabrir OS" icon={RotateCcw} />
              <PanelBody className="space-y-3">
                <p className="text-xs text-muted-foreground">
                  Use quando o cliente reclamar que o problema voltou. A OS volta
                  pra <em>em andamento</em> e o técnico pode atender novamente.
                  {data.csat !== null && data.csat !== undefined && (
                    <> O CSAT atual ({data.csat}/5) fica preservado no histórico.</>
                  )}
                </p>
                <div className="space-y-1.5">
                  <Label htmlFor="motivo-reabertura" className="text-xs text-muted-foreground">
                    Motivo (obrigatório)
                  </Label>
                  <Textarea
                    id="motivo-reabertura"
                    value={reaberturaMotivo}
                    onChange={(e) => setReaberturaMotivo(e.target.value)}
                    placeholder="Ex: Cliente reclamou que internet voltou a oscilar"
                    rows={3}
                  />
                </div>
                <Button
                  variant="outline"
                  onClick={async () => {
                    if (reaberturaMotivo.trim().length < 3) {
                      toast.error('Informe o motivo (mín. 3 caracteres).')
                      return
                    }
                    try {
                      await reabrirOs.mutateAsync(reaberturaMotivo.trim())
                      toast.success('OS reaberta.')
                      setReaberturaMotivo('')
                    } catch (e) {
                      toast.error(
                        e instanceof Error ? e.message : 'Erro ao reabrir',
                      )
                    }
                  }}
                  disabled={reabrirOs.isPending || reaberturaMotivo.trim().length < 3}
                  className="w-full"
                >
                  <RotateCcw className="h-4 w-4" />
                  {reabrirOs.isPending ? 'Reabrindo…' : 'Reabrir OS'}
                </Button>
                {data.historico_reaberturas && data.historico_reaberturas.length > 0 && (
                  <div className="border-t pt-3">
                    <p className="eyebrow">
                      Reaberturas anteriores:{' '}
                      <span className="num">{data.historico_reaberturas.length}</span>
                    </p>
                    <ul className="mt-2 space-y-1.5 text-xs text-muted-foreground">
                      {data.historico_reaberturas.slice(-3).reverse().map((h, i) => (
                        <li key={i} className="truncate" title={String(h.motivo ?? '')}>
                          <span className="num">{fmtDataHora(h.ts as string)}</span> —{' '}
                          {String(h.motivo ?? '')}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </PanelBody>
            </Panel>
          )}

          {(data.gps_inicio_lat || data.gps_fim_lat) && (
            <Panel>
              <PanelHeader title="Localização da visita" icon={MapPin} />
              <PanelBody className="space-y-2">
                <OsMapa
                  inicio={
                    data.gps_inicio_lat && data.gps_inicio_lng
                      ? { lat: data.gps_inicio_lat, lng: data.gps_inicio_lng }
                      : null
                  }
                  fim={
                    data.gps_fim_lat && data.gps_fim_lng
                      ? { lat: data.gps_fim_lat, lng: data.gps_fim_lng }
                      : null
                  }
                />
              </PanelBody>
            </Panel>
          )}
        </div>
      </div>
    </div>
  )
}
