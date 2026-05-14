'use client'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useClientes, useCreateOs, useTecnicos } from '@/lib/api/queries'

const schema = z.object({
  tecnico_id: z.string().uuid('Selecione o técnico responsável'),
  problema: z.string().min(1, 'Obrigatório').max(2000),
  endereco: z.string().min(1, 'Obrigatório').max(500),
  agendamento_at: z.string().optional().nullable(),
})

type FormValues = z.infer<typeof schema>

export function FormOsCreate() {
  const router = useRouter()
  const createOs = useCreateOs()
  const { data: tecnicos } = useTecnicos({ ativo: true })

  const [clienteSearch, setClienteSearch] = useState('')
  const [clienteId, setClienteId] = useState<string | null>(null)
  const [clienteLabel, setClienteLabel] = useState<string | null>(null)

  const { data: clientesResult } = useClientes(
    clienteSearch.length >= 4 ? { q: clienteSearch } : {}
  )
  const clienteSugestoes = clienteSearch.length >= 4 ? (clientesResult?.items ?? []) : []

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function onSubmit(values: FormValues) {
    const created = await createOs.mutateAsync({
      ...(clienteId ? { cliente_id: clienteId } : {}),
      tecnico_id: values.tecnico_id,
      problema: values.problema,
      endereco: values.endereco,
      agendamento_at: values.agendamento_at || null,
    })
    router.push(`/os/${created.id}`)
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Nova OS</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          {/* Cliente — opcional */}
          <div>
            <Label htmlFor="cliente_search">
              Cliente <span className="text-muted-foreground font-normal">(opcional — busca por WhatsApp)</span>
            </Label>
            {clienteLabel ? (
              <div className="flex items-center gap-2 mt-1">
                <span className="text-sm font-medium">{clienteLabel}</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs text-muted-foreground"
                  onClick={() => { setClienteId(null); setClienteLabel(null); setClienteSearch('') }}
                >
                  Trocar
                </Button>
              </div>
            ) : (
              <div className="relative">
                <Input
                  id="cliente_search"
                  placeholder="Digite o WhatsApp (mín. 4 dígitos)…"
                  value={clienteSearch}
                  onChange={(e) => { setClienteSearch(e.target.value); setClienteId(null) }}
                  autoComplete="off"
                />
                {clienteSugestoes.length > 0 && (
                  <div className="absolute z-10 mt-1 w-full rounded-md border bg-card shadow-md">
                    {clienteSugestoes.slice(0, 6).map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        className="w-full px-3 py-2 text-left text-sm hover:bg-muted"
                        onClick={() => {
                          setClienteId(c.id)
                          setClienteLabel(c.whatsapp)
                          setClienteSearch('')
                        }}
                      >
                        {c.whatsapp}
                      </button>
                    ))}
                  </div>
                )}
                {clienteSearch.length >= 4 && clienteSugestoes.length === 0 && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Nenhum cliente encontrado — a OS será aberta sem cliente vinculado.
                  </p>
                )}
              </div>
            )}
          </div>

          <div>
            <Label htmlFor="tecnico_id">Técnico responsável *</Label>
            <Select id="tecnico_id" {...register('tecnico_id')} defaultValue="">
              <option value="" disabled>Selecione o técnico responsável</option>
              {tecnicos?.items.map((t) => (
                <option key={t.id} value={t.id}>{t.nome}</option>
              ))}
            </Select>
            {errors.tecnico_id && (
              <p className="mt-1 text-xs text-destructive">{errors.tecnico_id.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="problema">Problema *</Label>
            <Textarea id="problema" {...register('problema')} />
            {errors.problema && (
              <p className="mt-1 text-xs text-destructive">{errors.problema.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="endereco">Endereço *</Label>
            <Input id="endereco" {...register('endereco')} />
            {errors.endereco && (
              <p className="mt-1 text-xs text-destructive">{errors.endereco.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="agendamento_at">Agendamento (opcional)</Label>
            <Input id="agendamento_at" type="datetime-local" {...register('agendamento_at')} />
          </div>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Criando…' : 'Criar OS'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
