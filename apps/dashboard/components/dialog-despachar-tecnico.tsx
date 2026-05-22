'use client'
import { useState } from 'react'
import { X, Wrench, CheckCircle2 } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { useCreateOs, useTecnicos } from '@/lib/api/queries'
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
  /** Callback chamado depois da OS criada com sucesso, passando a OS. */
  onCreated?: (os: OsOut) => void
}

export function DialogDespacharTecnico(props: Props) {
  const [problema, setProblema] = useState(props.problemaSugerido)
  const [endereco, setEndereco] = useState('')
  const [tecnicoId, setTecnicoId] = useState<string>('')
  const [agendamento, setAgendamento] = useState('')
  const [criada, setCriada] = useState<OsOut | null>(null)

  const tecnicos = useTecnicos({ ativo: true })
  const createOs = useCreateOs()

  // Reseta state ao fechar
  function close() {
    setCriada(null)
    setProblema(props.problemaSugerido)
    setEndereco('')
    setTecnicoId('')
    setAgendamento('')
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
        className="w-full max-w-lg rounded-xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-zinc-200 p-5">
          <div className="flex items-center gap-2">
            <Wrench className="h-5 w-5 text-indigo-600" />
            <h2 className="text-lg font-bold">Despachar pra técnico</h2>
          </div>
          <button
            onClick={close}
            className="rounded-md p-1 text-zinc-500 hover:bg-zinc-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {criada ? (
          <div className="p-6 text-center">
            <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-500" />
            <h3 className="mt-3 text-lg font-bold">OS {criada.codigo} criada</h3>
            <p className="mt-1 text-sm text-zinc-500">
              O técnico foi notificado por WhatsApp.
            </p>
            <div className="mt-5 flex gap-2 justify-center">
              <Link
                href={`/os/${criada.id}`}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
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
              <div className="rounded-md bg-zinc-50 px-3 py-2 text-sm">
                <div className="font-medium">{props.clienteNome || '—'}</div>
                <div className="text-xs text-zinc-500">
                  {props.clienteTelefone || '—'}
                </div>
              </div>
            </Field>

            <Field label="Técnico" required>
              <select
                value={tecnicoId}
                onChange={(e) => setTecnicoId(e.target.value)}
                className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm"
              >
                <option value="">— Selecione —</option>
                {(tecnicos.data ?? []).map((t) => (
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
                className="w-full resize-none rounded-md border border-zinc-200 px-3 py-2 text-sm"
              />
            </Field>

            <Field label="Endereço" required>
              <input
                value={endereco}
                onChange={(e) => setEndereco(e.target.value)}
                placeholder="Rua, número, bairro, cidade"
                className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm"
              />
            </Field>

            <Field label="Agendamento (opcional)">
              <input
                type="datetime-local"
                value={agendamento}
                onChange={(e) => setAgendamento(e.target.value)}
                className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm"
              />
            </Field>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={close}>
                Cancelar
              </Button>
              <Button
                onClick={submit}
                disabled={createOs.isPending}
                className="bg-indigo-600 hover:bg-indigo-700"
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

function Field(props: {
  label: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <div>
      <label
        className={cn(
          'mb-1 block text-xs font-semibold uppercase tracking-wide text-zinc-500',
        )}
      >
        {props.label}
        {props.required && <span className="ml-0.5 text-red-500">*</span>}
      </label>
      {props.children}
    </div>
  )
}
