'use client'
import { useEffect, useState } from 'react'
import { X, Wrench, CheckCircle2, RefreshCw } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import {
  useClienteSgpInfo,
  useCreateOs,
  useTecnicos,
} from '@/lib/api/queries'
import type { OsOut } from '@/lib/api/types'
import { cn } from '@/lib/utils'

interface Props {
  open: boolean
  onClose: () => void
  /** Texto pre-preenchido pro campo "problema" (descricao do chamado app). */
  problemaSugerido: string
  /** Nome do cliente vindo do app (vai pro campo nome_sgp). */
  clienteNome: string
  /** Telefone do cliente — exibido como referencia, nao vai no body. */
  clienteTelefone: string
  /** CPF (apenas digitos) — usado pra puxar endereco/plano do SGP. */
  clienteCpf: string
  /** Callback chamado depois da OS criada com sucesso, passando a OS. */
  onCreated?: (os: OsOut) => void
}

export function DialogDespacharTecnico(props: Props) {
  const [problema, setProblema] = useState(props.problemaSugerido)
  const [endereco, setEndereco] = useState('')
  const [plano, setPlano] = useState<string>('')
  const [pppoeLogin, setPppoeLogin] = useState<string>('')
  const [pppoeSenha, setPppoeSenha] = useState<string>('')
  const [tecnicoId, setTecnicoId] = useState<string>('')
  const [agendamento, setAgendamento] = useState('')
  const [criada, setCriada] = useState<OsOut | null>(null)
  const [enderecoUserEditou, setEnderecoUserEditou] = useState(false)

  const tecnicos = useTecnicos({ ativo: true })
  const createOs = useCreateOs()
  const sgp = useClienteSgpInfo(props.open ? props.clienteCpf || null : null)

  // Pre-preenche dados do SGP quando dispoivel (so se user nao editou ainda).
  useEffect(() => {
    if (sgp.data && !enderecoUserEditou) {
      if (sgp.data.endereco) setEndereco(sgp.data.endereco)
      if (sgp.data.plano) setPlano(sgp.data.plano)
      if (sgp.data.pppoe_login) setPppoeLogin(sgp.data.pppoe_login)
      if (sgp.data.pppoe_senha) setPppoeSenha(sgp.data.pppoe_senha)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sgp.data])

  // Reseta state ao fechar
  function close() {
    setCriada(null)
    setProblema(props.problemaSugerido)
    setEndereco('')
    setPlano('')
    setPppoeLogin('')
    setPppoeSenha('')
    setTecnicoId('')
    setAgendamento('')
    setEnderecoUserEditou(false)
    props.onClose()
  }

  async function submit() {
    if (!tecnicoId) {
      alert('Selecione um técnico')
      return
    }
    if (!problema.trim() || !endereco.trim()) {
      alert('Preencha problema e endereço')
      return
    }
    try {
      const os = await createOs.mutateAsync({
        cliente_id: null,
        nome_sgp: props.clienteNome || null,
        tecnico_id: tecnicoId,
        problema: problema.trim(),
        endereco: endereco.trim(),
        plano: plano.trim() || null,
        pppoe_login: pppoeLogin.trim() || null,
        pppoe_senha: pppoeSenha.trim() || null,
        agendamento_at: agendamento
          ? new Date(agendamento).toISOString()
          : null,
      })
      setCriada(os)
      props.onCreated?.(os)
    } catch (e) {
      alert((e as Error).message)
    }
  }

  if (!props.open) return null

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4"
      onClick={close}
    >
      <div
        className="max-h-[90dvh] w-full max-w-lg overflow-y-auto rounded-xl bg-card shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border p-5">
          <div className="flex items-center gap-2">
            <Wrench className="h-5 w-5 text-info" />
            <h2 className="text-lg font-bold">Despachar pra técnico</h2>
          </div>
          <button
            onClick={close}
            className="rounded-md p-1 text-muted-foreground hover:bg-muted"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {criada ? (
          <div className="p-6 text-center">
            <CheckCircle2 className="mx-auto h-12 w-12 text-success" />
            <h3 className="mt-3 text-lg font-bold">OS {criada.codigo} criada</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              O técnico foi notificado por WhatsApp.
            </p>
            <div className="mt-5 flex gap-2 justify-center">
              <Link
                href={`/os/${criada.id}`}
                className="rounded-md bg-info px-4 py-2 text-sm font-semibold text-info-foreground hover:bg-info"
              >
                Abrir OS
              </Link>
              <Button variant="outline" onClick={close}>
                Fechar
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4 p-5">
            <Field label="Cliente">
              <div className="rounded-md bg-muted/50 px-3 py-2 text-sm">
                <div className="font-medium">{props.clienteNome || '—'}</div>
                <div className="text-xs text-muted-foreground">
                  CPF {fmtCpf(props.clienteCpf)} · {props.clienteTelefone || '—'}
                </div>
                {sgp.isLoading && (
                  <div className="mt-1 flex items-center gap-1 text-xs text-info">
                    <RefreshCw className="h-3 w-3 animate-spin" />
                    Buscando dados no SGP…
                  </div>
                )}
                {sgp.error && (
                  <div className="mt-1 text-xs text-warning">
                    Não encontrei dados no SGP — preencha manualmente.
                  </div>
                )}
              </div>
            </Field>

            <Field label="Técnico" required>
              <select
                value={tecnicoId}
                onChange={(e) => setTecnicoId(e.target.value)}
                className="w-full rounded-md border border-border px-3 py-2 text-sm"
              >
                <option value="">— Selecione —</option>
                {(tecnicos.data?.items ?? [])
                  .filter((t) => t.ativo)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.nome}
                    </option>
                  ))}
              </select>
            </Field>

            <Field label="Problema" required>
              <textarea
                value={problema}
                onChange={(e) => setProblema(e.target.value)}
                rows={4}
                placeholder="Descreva o que o técnico vai fazer"
                className="w-full resize-none rounded-md border border-border px-3 py-2 text-sm"
              />
            </Field>

            <Field label="Endereço" required>
              <input
                value={endereco}
                onChange={(e) => {
                  setEndereco(e.target.value)
                  setEnderecoUserEditou(true)
                }}
                placeholder="Rua, número, bairro, cidade"
                className="w-full rounded-md border border-border px-3 py-2 text-sm"
              />
            </Field>

            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Plano">
                <input
                  value={plano}
                  onChange={(e) => setPlano(e.target.value)}
                  placeholder="Ex: Fibra 600"
                  className="w-full rounded-md border border-border px-3 py-2 text-sm"
                />
              </Field>
              <Field label="PPPoE login">
                <input
                  value={pppoeLogin}
                  onChange={(e) => setPppoeLogin(e.target.value)}
                  className="w-full rounded-md border border-border px-3 py-2 text-sm"
                />
              </Field>
            </div>

            <Field label="PPPoE senha">
              <input
                value={pppoeSenha}
                onChange={(e) => setPppoeSenha(e.target.value)}
                className="w-full rounded-md border border-border px-3 py-2 text-sm"
              />
            </Field>

            <Field label="Agendamento (opcional)">
              <input
                type="datetime-local"
                value={agendamento}
                onChange={(e) => setAgendamento(e.target.value)}
                className="w-full rounded-md border border-border px-3 py-2 text-sm"
              />
            </Field>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={close}>
                Cancelar
              </Button>
              <Button
                onClick={submit}
                disabled={createOs.isPending}
                className="bg-info hover:bg-info"
              >
                {createOs.isPending ? 'Criando…' : 'Criar OS'}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function fmtCpf(d: string): string {
  const digits = (d ?? '').replace(/\D/g, '')
  if (digits.length !== 11) return d || '—'
  return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`
}

function Field(props: {
  label: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <div>
      <label
        className={cn(
          'mb-1 block text-xs font-semibold uppercase tracking-wide text-muted-foreground',
        )}
      >
        {props.label}
        {props.required && <span className="ml-0.5 text-destructive">*</span>}
      </label>
      {props.children}
    </div>
  )
}
