'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useCreateOs, useSgpLookup, useTecnicos } from '@/lib/api/queries'
import type { SgpClienteOut } from '@/lib/api/types'

export function OsCreatePanel({ onCreated }: { onCreated?: () => void }) {
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

  return (
    <div className="rounded-md border bg-card p-5 space-y-4 h-full overflow-y-auto">
      <h2 className="text-base font-semibold border-b pb-3">Nova OS</h2>

      {/* Busca CPF */}
      <div className="space-y-2">
        <Label htmlFor="cpf-lookup">CPF / CNPJ do cliente</Label>
        <div className="flex gap-2">
          <Input
            id="cpf-lookup"
            placeholder="000.000.000-00"
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
          <p className="text-xs text-destructive">Cliente não encontrado no SGP</p>
        )}
      </div>

      {/* Card do cliente (pós-busca) */}
      {cliente && (
        <div className="rounded-md bg-muted p-3 text-sm space-y-1 border border-green-400">
          <div className="flex items-center justify-between">
            <p className="font-semibold">{cliente.nome}</p>
            <span className="text-xs text-green-600 dark:text-green-400 font-medium">SGP ✓</span>
          </div>
          {cliente.plano && <p className="text-muted-foreground">Plano: {cliente.plano}</p>}
          {cliente.status_contrato && (
            <p className={cliente.status_contrato.toLowerCase() === 'ativo' ? 'text-green-600' : 'text-destructive'}>
              Status: {cliente.status_contrato}
            </p>
          )}
          {cliente.cidade && <p className="text-muted-foreground">Cidade: {cliente.cidade}</p>}
          {!cliente.cliente_id && (
            <p className="text-xs text-yellow-600">⚠️ Cliente ainda não no banco — só é possível abrir OS via conversa ativa</p>
          )}
        </div>
      )}

      {/* Formulário — só aparece após busca com sucesso e cliente no banco */}
      {cliente?.cliente_id && (
        <div className="space-y-3">
          <div>
            <Label htmlFor="os-tecnico">Técnico responsável *</Label>
            <select
              id="os-tecnico"
              value={tecnicoId}
              onChange={(e) => setTecnicoId(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="" disabled>Selecione o técnico</option>
              {tecnicos?.items.map((t) => (
                <option key={t.id} value={t.id}>{t.nome}</option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="os-problema">Problema *</Label>
            <Textarea
              id="os-problema"
              placeholder="Descreva o problema…"
              value={problema}
              onChange={(e) => setProblema(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="os-endereco">Endereço *</Label>
            <Input
              id="os-endereco"
              value={endereco}
              onChange={(e) => setEndereco(e.target.value)}
              placeholder="Rua e número"
            />
          </div>
          {createOs.error && (
            <p className="text-xs text-destructive">
              {createOs.error instanceof Error ? createOs.error.message : 'Erro ao criar OS'}
            </p>
          )}
          <Button
            className="w-full"
            onClick={() => void handleSubmit()}
            disabled={createOs.isPending || !tecnicoId || !problema.trim() || !endereco.trim()}
          >
            {createOs.isPending ? 'Criando…' : 'Abrir OS e Notificar Técnico'}
          </Button>
        </div>
      )}
    </div>
  )
}
