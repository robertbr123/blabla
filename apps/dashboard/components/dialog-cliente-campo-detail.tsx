'use client'
import { useEffect, useState } from 'react'
import { CheckCircle2, CloudOff, ExternalLink, MapPin, Pencil, X } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useClienteCampoDetail, usePatchClienteCampo } from '@/lib/api/queries'
import type { ClienteCampoOut } from '@/lib/api/types'

interface Props {
  id: string
  onClose: () => void
}

type EditPatch = Partial<Omit<ClienteCampoOut, 'id' | 'cpf' | 'dob' | 'created_at' | 'updated_at' | 'sgp_synced_at' | 'sgp_id' | 'fotos'>>

export function DialogClienteCampoDetail({ id, onClose }: Props) {
  const { data: c, isLoading, error } = useClienteCampoDetail(id)
  const patch = usePatchClienteCampo(id)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<EditPatch>({})

  // Reset form quando cliente carrega ou modo edição muda
  useEffect(() => {
    if (c && editing) {
      setForm({
        nome: c.nome,
        telefone: c.telefone,
        email: c.email,
        cep: c.cep,
        address: c.address,
        number: c.number,
        complement: c.complement,
        neighborhood: c.neighborhood,
        city: c.city,
        state: c.state,
        plan_nome: c.plan_nome,
        pppoe_user: c.pppoe_user,
        pppoe_pass: c.pppoe_pass,
        due_date: c.due_date,
        installer_nome: c.installer_nome,
        serial: c.serial,
        contrato: c.contrato,
        observation: c.observation,
        latitude: c.latitude,
        longitude: c.longitude,
      })
    }
  }, [c, editing])

  function setField<K extends keyof EditPatch>(k: K, v: EditPatch[K]) {
    setForm((f) => ({ ...f, [k]: v }))
  }

  async function handleSave() {
    // Limpa strings vazias → null pra campos opcionais
    const payload: EditPatch = {}
    for (const [k, v] of Object.entries(form)) {
      if (typeof v === 'string' && v.trim() === '') {
        ;(payload as Record<string, unknown>)[k] = null
      } else {
        ;(payload as Record<string, unknown>)[k] = v
      }
    }
    try {
      await patch.mutateAsync(payload)
      toast.success('Cliente atualizado.')
      setEditing(false)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao salvar')
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="flex w-full max-w-3xl max-h-[90vh] flex-col overflow-hidden rounded-lg border bg-card shadow-lg">
        <div className="flex items-start justify-between gap-3 shrink-0 border-b bg-card px-6 py-4">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold truncate">
              {c?.nome ?? 'Carregando…'}
            </h2>
            {c && (
              <p className="text-xs text-muted-foreground font-mono" style={{ fontVariantNumeric: 'tabular-nums' }}>
                {fmtCpf(c.cpf)}
              </p>
            )}
          </div>
          <div className="flex items-center gap-1 shrink-0">
            {c && !editing && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setEditing(true)}
                className="gap-1.5"
              >
                <Pencil className="h-3.5 w-3.5" /> Editar
              </Button>
            )}
            <Button size="icon" variant="ghost" onClick={onClose} aria-label="Fechar">
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">

        {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
        {error && (
          <p className="text-sm text-destructive">
            {error instanceof Error ? error.message : 'Erro ao carregar'}
          </p>
        )}

        {c && (
          <>
            {/* SGP status pill */}
            <div className="flex items-center gap-2">
              {c.sgp_synced_at ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-success/[0.12] px-2.5 py-1 text-xs font-medium text-success ring-1 ring-inset ring-success/30">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Sincronizado SGP{c.sgp_id ? ` · ${c.sgp_id}` : ''}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded-full bg-warning/[0.15] px-2.5 py-1 text-xs font-medium text-warning ring-1 ring-inset ring-warning/30">
                  <CloudOff className="h-3.5 w-3.5" />
                  Pendente SGP
                </span>
              )}
            </div>

            {/* Conteúdo: read-only OU formulário */}
            {!editing ? (
              <>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Telefone" value={fmtPhone(c.telefone)} />
                  <Field label="Email" value={c.email ?? '—'} copyable={!!c.email} />
                  <Field label="Nascimento" value={fmtDate(c.dob)} />
                  <Field label="Plano" value={c.plan_nome} />
                  <Field label="Vencimento" value={`dia ${c.due_date}`} />
                  <Field label="PPPoE login" value={c.pppoe_user ?? '—'} mono copyable={!!c.pppoe_user} />
                  <Field label="PPPoE senha" value={c.pppoe_pass ?? '—'} mono copyable={!!c.pppoe_pass} />
                  <Field label="Serial / MAC" value={c.serial ?? '—'} mono copyable={!!c.serial} />
                  <Field label="Contrato" value={c.contrato ?? '—'} />
                  <Field label="Instalador" value={c.installer_nome} />
                  <Field label="Registrado em" value={fmtDate(c.registration_date)} />
                </div>

                <div className="rounded-md border bg-muted/30 p-3 space-y-2">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                    Endereço
                  </div>
                  <p className="text-sm">
                    {c.address}, {c.number}
                    {c.complement ? ` (${c.complement})` : ''}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {c.neighborhood ? `${c.neighborhood} · ` : ''}
                    {c.city}
                    {c.state ? ` / ${c.state}` : ''}
                    {c.cep ? ` · CEP ${c.cep}` : ''}
                  </p>
                </div>

                {c.latitude != null && c.longitude != null && (
                  <div className="rounded-md border overflow-hidden">
                    <iframe
                      title="Mapa do cliente"
                      src={mapEmbedUrl(c.latitude, c.longitude)}
                      className="h-64 w-full"
                      loading="lazy"
                    />
                    <div className="flex items-center justify-between bg-muted/30 px-3 py-2 text-xs">
                      <span className="flex items-center gap-1 text-muted-foreground" style={{ fontVariantNumeric: 'tabular-nums' }}>
                        <MapPin className="h-3 w-3" />
                        {c.latitude.toFixed(6)}, {c.longitude.toFixed(6)}
                        {c.location_accuracy != null && (
                          <span className="ml-2">· precisão ±{Math.round(c.location_accuracy)}m</span>
                        )}
                      </span>
                      <a
                        href={`https://maps.google.com/?q=${c.latitude},${c.longitude}`}
                        target="_blank"
                        rel="noopener"
                        className="inline-flex items-center gap-1 text-primary hover:underline"
                      >
                        Abrir no Google Maps <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                )}

                {c.observation && (
                  <div className="rounded-md border bg-muted/30 p-3">
                    <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
                      Observação
                    </div>
                    <p className="text-sm whitespace-pre-wrap">{c.observation}</p>
                  </div>
                )}

                {c.fotos && c.fotos.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {c.fotos.length} foto(s) anexada(s) · acessíveis pelo app do técnico.
                  </p>
                )}
              </>
            ) : (
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  void handleSave()
                }}
                className="space-y-4"
              >
                <div className="rounded-md border bg-muted/30 p-3 space-y-2">
                  <p className="text-xs text-muted-foreground">
                    <strong className="text-foreground">CPF</strong> e <strong className="text-foreground">data de nascimento</strong> são imutáveis (identificam a pessoa e estão em auditoria). Para corrigi-los, exclua este cadastro e crie um novo.
                  </p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <FormField label="CPF (imutável)" value={fmtCpf(c.cpf)} onChange={() => {}} disabled mono />
                    <FormField label="Nascimento (imutável)" value={fmtDate(c.dob)} onChange={() => {}} disabled />
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <FormField label="Nome" value={form.nome ?? ''} onChange={(v) => setField('nome', v)} maxLength={255} />
                  <FormField label="Telefone" value={form.telefone ?? ''} onChange={(v) => setField('telefone', v)} maxLength={15} />
                  <FormField label="Email" value={form.email ?? ''} onChange={(v) => setField('email', v)} maxLength={255} type="email" />
                  <FormField label="Plano" value={form.plan_nome ?? ''} onChange={(v) => setField('plan_nome', v)} maxLength={255} />
                  <FormField
                    label="Vencimento (10-30)"
                    type="number"
                    value={form.due_date != null ? String(form.due_date) : ''}
                    onChange={(v) => setField('due_date', v ? Number(v) : undefined)}
                  />
                  <FormField label="PPPoE login" value={form.pppoe_user ?? ''} onChange={(v) => setField('pppoe_user', v)} maxLength={100} mono />
                  <FormField label="PPPoE senha" value={form.pppoe_pass ?? ''} onChange={(v) => setField('pppoe_pass', v)} maxLength={100} mono />
                  <FormField label="Serial / MAC" value={form.serial ?? ''} onChange={(v) => setField('serial', v)} maxLength={100} mono />
                  <FormField label="Contrato" value={form.contrato ?? ''} onChange={(v) => setField('contrato', v)} maxLength={20} />
                  <FormField label="Instalador" value={form.installer_nome ?? ''} onChange={(v) => setField('installer_nome', v)} maxLength={255} />
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <FormField label="Endereço" value={form.address ?? ''} onChange={(v) => setField('address', v)} maxLength={255} />
                  <FormField label="Número" value={form.number ?? ''} onChange={(v) => setField('number', v)} maxLength={10} />
                  <FormField label="Complemento" value={form.complement ?? ''} onChange={(v) => setField('complement', v)} maxLength={255} />
                  <FormField label="Bairro" value={form.neighborhood ?? ''} onChange={(v) => setField('neighborhood', v)} maxLength={100} />
                  <FormField label="Cidade" value={form.city ?? ''} onChange={(v) => setField('city', v)} maxLength={100} />
                  <FormField label="UF (2 letras)" value={form.state ?? ''} onChange={(v) => setField('state', v.toUpperCase())} maxLength={2} />
                  <FormField label="CEP" value={form.cep ?? ''} onChange={(v) => setField('cep', v)} maxLength={10} />
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <FormField
                    label="Latitude"
                    type="number"
                    value={form.latitude != null ? String(form.latitude) : ''}
                    onChange={(v) => setField('latitude', v ? Number(v) : null)}
                  />
                  <FormField
                    label="Longitude"
                    type="number"
                    value={form.longitude != null ? String(form.longitude) : ''}
                    onChange={(v) => setField('longitude', v ? Number(v) : null)}
                  />
                </div>
                <div>
                  <Label htmlFor="observation" className="text-[10px] uppercase tracking-wide text-muted-foreground">
                    Observação
                  </Label>
                  <Textarea
                    id="observation"
                    value={form.observation ?? ''}
                    onChange={(e) => setField('observation', e.target.value)}
                    rows={3}
                    className="mt-1"
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2 border-t">
                  <Button type="button" variant="outline" onClick={() => setEditing(false)} disabled={patch.isPending}>
                    Cancelar
                  </Button>
                  <Button type="submit" disabled={patch.isPending}>
                    {patch.isPending ? 'Salvando…' : 'Salvar'}
                  </Button>
                </div>
              </form>
            )}
          </>
        )}

        </div>
        {!editing && (
          <div className="flex justify-end shrink-0 border-t bg-card px-6 py-3">
            <Button variant="outline" onClick={onClose}>
              Fechar
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

function Field({
  label,
  value,
  mono = false,
  copyable = false,
}: {
  label: string
  value: string
  mono?: boolean
  copyable?: boolean
}) {
  return (
    <div
      className={copyable ? 'cursor-pointer' : ''}
      onClick={
        copyable
          ? () => {
              navigator.clipboard.writeText(value).catch(() => {})
              toast.success('Copiado.')
            }
          : undefined
      }
      title={copyable ? 'Clique pra copiar' : undefined}
    >
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className={`text-sm ${mono ? 'font-mono' : ''}`} style={mono ? { fontVariantNumeric: 'tabular-nums' } : undefined}>
        {value}
      </div>
    </div>
  )
}

function FormField({
  label,
  value,
  onChange,
  type = 'text',
  maxLength,
  mono = false,
  disabled = false,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: 'text' | 'number' | 'email'
  maxLength?: number
  mono?: boolean
  disabled?: boolean
}) {
  const id = `f-${label.toLowerCase().replace(/[^a-z0-9]/g, '-')}`
  return (
    <div>
      <Label htmlFor={id} className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </Label>
      <Input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxLength={maxLength}
        disabled={disabled}
        readOnly={disabled}
        className={`mt-1 ${mono ? 'font-mono' : ''} ${disabled ? 'cursor-not-allowed opacity-70' : ''}`}
      />
    </div>
  )
}

function mapEmbedUrl(lat: number, lng: number): string {
  // OpenStreetMap embed (sem API key). Bounding box ~600m em volta do ponto.
  const d = 0.003
  const bbox = `${lng - d},${lat - d},${lng + d},${lat + d}`
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat},${lng}`
}

function fmtCpf(cpf: string): string {
  const d = cpf.replace(/\D/g, '')
  if (d.length === 11) {
    return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`
  }
  if (d.length === 14) {
    return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`
  }
  return cpf
}

function fmtPhone(s: string): string {
  const d = s.replace(/\D/g, '')
  if (d.length === 11) return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`
  if (d.length === 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  return s
}

function fmtDate(s: string): string {
  try {
    const [y, m, d] = s.split('-')
    return `${d}/${m}/${y}`
  } catch {
    return s
  }
}
