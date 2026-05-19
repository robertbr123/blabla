'use client'
import { CloudDone, CloudOff, MapPin, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useClienteCampoDetail } from '@/lib/api/queries'

interface Props {
  id: string
  onClose: () => void
}

export function DialogClienteCampoDetail({ id, onClose }: Props) {
  const { data: c, isLoading, error } = useClienteCampoDetail(id)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto py-4">
      <div className="w-full max-w-2xl rounded-lg border bg-card p-6 shadow-lg space-y-4 mx-4">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold">
              {c?.nome ?? 'Carregando…'}
            </h2>
            {c && (
              <p className="text-xs text-muted-foreground font-mono">
                {fmtCpf(c.cpf)}
              </p>
            )}
          </div>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
        {error && (
          <p className="text-sm text-destructive">
            {error instanceof Error ? error.message : 'Erro ao carregar'}
          </p>
        )}

        {c && (
          <>
            <div className="flex items-center gap-2">
              {c.sgp_synced_at ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">
                  <CloudDone className="h-3.5 w-3.5" />
                  Sincronizado SGP{c.sgp_id ? ` · ${c.sgp_id}` : ''}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded-full border border-amber-400 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
                  <CloudOff className="h-3.5 w-3.5" />
                  Pendente SGP
                </span>
              )}
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Telefone" value={fmtPhone(c.telefone)} />
              <Field label="Nascimento" value={fmtDate(c.dob)} />
              <Field label="Plano" value={c.plan_nome} />
              <Field label="Vencimento" value={`dia ${c.due_date}`} />
              <Field
                label="PPPoE login"
                value={c.pppoe_user ?? '—'}
                mono
                copyable={!!c.pppoe_user}
              />
              <Field
                label="PPPoE senha"
                value={c.pppoe_pass ?? '—'}
                mono
                copyable={!!c.pppoe_pass}
              />
              <Field
                label="Serial"
                value={c.serial ?? '—'}
                mono
                copyable={!!c.serial}
              />
              <Field label="Contrato" value={c.contrato ?? '—'} />
              <Field label="Instalador" value={c.installer_nome} />
              <Field label="Registrado em" value={fmtDate(c.registration_date)} />
            </div>

            <div className="rounded-md border bg-muted/30 p-3 space-y-1">
              <div className="text-xs uppercase text-muted-foreground">
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
              {c.latitude != null && c.longitude != null && (
                <a
                  href={`https://maps.google.com/?q=${c.latitude},${c.longitude}`}
                  target="_blank"
                  rel="noopener"
                  className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  <MapPin className="h-3 w-3" />
                  {c.latitude.toFixed(6)}, {c.longitude.toFixed(6)}
                </a>
              )}
            </div>

            {c.observation && (
              <div className="rounded-md border bg-muted/30 p-3">
                <div className="text-xs uppercase text-muted-foreground mb-1">
                  Observação
                </div>
                <p className="text-sm whitespace-pre-wrap">{c.observation}</p>
              </div>
            )}

            {c.fotos && c.fotos.length > 0 && (
              <div>
                <div className="text-xs uppercase text-muted-foreground mb-2">
                  {c.fotos.length} foto(s) anexada(s)
                </div>
                <p className="text-xs text-muted-foreground">
                  Acessível no app do técnico ou via{' '}
                  <code className="font-mono text-[11px]">
                    /api/v1/clientes-campo/{c.id}/foto/&lt;idx&gt;
                  </code>
                </p>
              </div>
            )}
          </>
        )}

        <div className="flex justify-end pt-2">
          <Button variant="outline" onClick={onClose}>
            Fechar
          </Button>
        </div>
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
            }
          : undefined
      }
      title={copyable ? 'Clique pra copiar' : undefined}
    >
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className={`text-sm ${mono ? 'font-mono' : ''}`}>{value}</div>
    </div>
  )
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
