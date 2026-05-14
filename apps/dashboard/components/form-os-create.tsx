'use client'
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
import { useCreateOs, useTecnicos } from '@/lib/api/queries'

const schema = z.object({
  cliente_id: z.string().uuid('UUID inválido'),
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
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function onSubmit(values: FormValues) {
    const created = await createOs.mutateAsync({
      cliente_id: values.cliente_id,
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
          <div>
            <Label htmlFor="cliente_id">Cliente ID</Label>
            <Input id="cliente_id" {...register('cliente_id')} />
            {errors.cliente_id && (
              <p className="mt-1 text-xs text-destructive">{errors.cliente_id.message}</p>
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
            <Label htmlFor="problema">Problema</Label>
            <Textarea id="problema" {...register('problema')} />
            {errors.problema && (
              <p className="mt-1 text-xs text-destructive">{errors.problema.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="endereco">Endereço</Label>
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
