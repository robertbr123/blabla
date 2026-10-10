'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertTriangle, CheckCircle2, ClipboardList, X } from 'lucide-react'
import { Panel, PanelBody, PanelHeader, StatusDot } from '@/components/noc/primitives'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useCreateOs, useSgpLookup, useTecnicos } from '@/lib/api/queries'
import type { SgpClienteOut } from '@/lib/api/types'

export function OsCreatePanel({
  onCreated,
  onClose,
}: {
  onCreated?: () => void
  onClose?: () => void
}) {
  const router = useRouter()
  const sgpLookup = useSgpLookup()
  const createOs = useCreateOs()
  const { data: tecnicos } = useTecnicos({ ativo: true })

  const [cpf, setCpf] = useState('')
  const [cliente, setCliente] = useState<SgpClienteOut | null>(null)
  const [problema, setProblema] = useState('')
  const [endereco, setEndereco] = useState('')
  const [tecnicoId, setTecnicoId] = useState('')

  async function handleBuscar() {
    const digits = cpf.replace(/\D/g, '')
    if (digits.length < 11) return
    try {
      const result = await sgpLookup.mutateAsync(digits)
      setCliente(result)
      setEndereco(result.endereco ?? '')
    } catch {
      setCliente(null)
    }
  }

  async function handleSubmit() {
    if (!cliente?.cliente_id || !tecnicoId || !problema || !endereco) return
    const created = await createOs.mutateAsync({
      cliente_id: cliente.cliente_id,
      tecnico_id: tecnicoId,
      problema,
      endereco,
    })
    onCreated?.()
    router.push(`/os/${created.id}`)
  }

  const contratoAtivo = cliente?.status_contrato?.toLowerCase() === 'ativo'

  return (
    <Panel className="h-full overflow-y-auto">
      <PanelHeader
        title="Nova OS"
        icon={ClipboardList}
        actions={
          onClose && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-foreground"
              onClick={onClose}
              title="Fechar"
              aria-label="Fechar painel de nova OS"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          )
        }
      />
      <PanelBody className="space-y-4">
        {/* Busca CPF */}
        <div className="space-y-1.5">
          <Label htmlFor="cpf-lookup" className="text-xs text-muted-foreground">CPF / CNPJ do cliente</Label>
          <div className="flex gap-2">
            <Input
              id="cpf-lookup"
              placeholder="000.000.000-00"
              inputMode="numeric"
              className="num"
              value={cpf}
              onChange={(e) => setCpf(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') void handleBuscar() }}
            />
            <Button
              type="button"
              variant="outline"
              onClick={() => void handleBuscar()}
              disabled={sgpLookup.isPending}
            >
              {sgpLookup.isPending ? '…' : 'Buscar'}
            </Button>
          </div>
          {sgpLookup.error && (
            <p role="alert" className="flex items-center gap-1.5 text-xs text-destructive">
              <AlertTriangle aria-hidden className="h-3 w-3 shrink-0" />
              Cliente não encontrado no SGP
            </p>
          )}
        </div>

        {/* Card do cliente (pós-busca) */}
        {cliente && (
          <div className="space-y-2 rounded-md border border-success/40 bg-muted/60 p-3 text-sm">
            <div className="flex items-center justify-between gap-2">
              <p className="min-w-0 truncate font-semibold" title={cliente.nome}>{cliente.nome}</p>
              <span className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-success">
                <CheckCircle2 aria-hidden className="h-3.5 w-3.5" /> SGP
              </span>
            </div>
            <dl className="space-y-1 text-[13px]">
              {cliente.plano && (
                <div className="flex gap-2">
                  <dt className="w-14 shrink-0 text-muted-foreground">Plano</dt>
                  <dd className="min-w-0">{cliente.plano}</dd>
                </div>
              )}
              {cliente.status_contrato && (
                <div className="flex gap-2">
                  <dt className="w-14 shrink-0 text-muted-foreground">Status</dt>
                  <dd className="inline-flex min-w-0 items-center gap-1.5">
                    <StatusDot tone={contratoAtivo ? 'success' : 'destructive'} />
                    {cliente.status_contrato}
                  </dd>
                </div>
              )}
              {cliente.cidade && (
                <div className="flex gap-2">
                  <dt className="w-14 shrink-0 text-muted-foreground">Cidade</dt>
                  <dd className="min-w-0">{cliente.cidade}</dd>
                </div>
              )}
            </dl>
            {!cliente.cliente_id && (
              <p className="flex items-start gap-1.5 rounded-md bg-warning/[0.14] p-2 text-xs text-warning">
                <AlertTriangle aria-hidden className="mt-0.5 h-3 w-3 shrink-0" />
                <span>Cliente ainda não no banco — só é possível abrir OS via conversa ativa</span>
              </p>
            )}
          </div>
        )}

        {/* Formulário — só aparece após busca com sucesso e cliente no banco */}
        {cliente?.cliente_id && (
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="os-tecnico" className="text-xs text-muted-foreground">Técnico responsável *</Label>
              <Select
                id="os-tecnico"
                value={tecnicoId}
                onChange={(e) => setTecnicoId(e.target.value)}
              >
                <option value="" disabled>Selecione o técnico</option>
                {tecnicos?.items.map((t) => (
                  <option key={t.id} value={t.id}>{t.nome}</option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="os-problema" className="text-xs text-muted-foreground">Problema *</Label>
              <Textarea
                id="os-problema"
                placeholder="Descreva o problema…"
                value={problema}
                onChange={(e) => setProblema(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="os-endereco" className="text-xs text-muted-foreground">Endereço *</Label>
              <Input
                id="os-endereco"
                value={endereco}
                onChange={(e) => setEndereco(e.target.value)}
                placeholder="Rua e número"
              />
            </div>
            {createOs.error && (
              <p role="alert" className="flex items-start gap-1.5 text-xs text-destructive">
                <AlertTriangle aria-hidden className="mt-0.5 h-3 w-3 shrink-0" />
                <span>
                  {createOs.error instanceof Error ? createOs.error.message : 'Erro ao criar OS'}
                </span>
              </p>
            )}
            <Button
              className="w-full"
              onClick={() => void handleSubmit()}
              disabled={createOs.isPending || !tecnicoId || !problema.trim() || !endereco.trim()}
            >
              {createOs.isPending ? 'Criando…' : 'Abrir OS e notificar técnico'}
            </Button>
          </div>
        )}
      </PanelBody>
    </Panel>
  )
}
