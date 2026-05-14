'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useCreateOs, useConversa, useTecnicos } from '@/lib/api/queries'
import type { ClienteEmbutido } from '@/lib/api/types'

const schema = z.object({
  tecnico_id: z.string().uuid('Selecione o técnico responsável'),
  problema: z.string().min(1, 'Obrigatório').max(2000),
  endereco: z.string().min(1, 'Obrigatório').max(500),
  agendamento_at: z.string().optional().nullable(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  conversaId: string
  onClose: () => void
}

export function DialogAbrirOsFromConversa({ conversaId, onClose }: Props) {
  const router = useRouter()
  const { data: conversa } = useConversa(conversaId)
  const createOs = useCreateOs()
  const { data: tecnicos } = useTecnicos({ ativo: true })
  const cliente: ClienteEmbutido | null = conversa?.cliente ?? null

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      endereco: cliente?.endereco ?? '',
    },
  })

  async function onSubmit(values: FormValues) {
    if (!conversa?.cliente_id) return
    const created = await createOs.mutateAsync({
      cliente_id: conversa.cliente_id,
      tecnico_id: values.tecnico_id,
      problema: values.problema,
      endereco: values.endereco,
      agendamento_at: values.agendamento_at || null,
    })
    onClose()
    router.push(`/os/${created.id}`)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto py-4">
      <div className="w-full max-w-lg rounded-lg border bg-card p-6 shadow-lg space-y-4 mx-4">
        <h2 className="text-lg font-semibold">Abrir OS</h2>

        {cliente && (
          <div className="rounded-md bg-muted p-3 text-sm space-y-1">
            <p><span className="font-medium">Cliente:</span> {cliente.nome}</p>
            {cliente.whatsapp && <p><span className="font-medium">WhatsApp:</span> {cliente.whatsapp}</p>}
            {cliente.plano && <p><span className="font-medium">Plano:</span> {cliente.plano}</p>}
            {cliente.cidade && <p><span className="font-medium">Cidade:</span> {cliente.cidade}</p>}
          </div>
        )}

        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
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
            <Textarea id="problema" {...register('problema')} placeholder="Descreva o problema…" />
            {errors.problema && (
              <p className="mt-1 text-xs text-destructive">{errors.problema.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="endereco">Endereço *</Label>
            <Input
              id="endereco"
              {...register('endereco')}
              defaultValue={cliente?.endereco ?? ''}
            />
            {errors.endereco && (
              <p className="mt-1 text-xs text-destructive">{errors.endereco.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="agendamento_at">Agendamento (opcional)</Label>
            <Input id="agendamento_at" type="datetime-local" {...register('agendamento_at')} />
          </div>
          {createOs.error && (
            <p className="text-xs text-destructive">
              {createOs.error instanceof Error ? createOs.error.message : 'Erro ao criar OS'}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting || !conversa?.cliente_id}>
              {isSubmitting ? 'Criando…' : 'Abrir OS'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
