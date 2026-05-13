'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useCreateManutencao } from '@/lib/api/queries'

const schema = z.object({
  titulo: z.string().min(1).max(255),
  descricao: z.string().max(4000).optional(),
  inicio_at: z.string().min(1, 'Obrigatório'),
  fim_at: z.string().min(1, 'Obrigatório'),
  cidades: z.string().optional(), // comma-separated
  notificar: z.boolean().default(true),
})

type FormValues = z.infer<typeof schema>

export function FormManutencao() {
  const router = useRouter()
  const create = useCreateManutencao()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { notificar: true },
  })

  async function onSubmit(values: FormValues) {
    const cidades = values.cidades
      ? values.cidades.split(',').map((s) => s.trim()).filter(Boolean)
      : null
    const created = await create.mutateAsync({
      titulo: values.titulo,
      descricao: values.descricao || null,
      inicio_at: new Date(values.inicio_at).toISOString(),
      fim_at: new Date(values.fim_at).toISOString(),
      cidades,
      notificar: values.notificar,
    })
    router.push(`/manutencoes/${created.id}`)
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Nova manutenção</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <Label htmlFor="titulo">Título</Label>
            <Input id="titulo" {...register('titulo')} />
            {errors.titulo && <p className="mt-1 text-xs text-destructive">{errors.titulo.message}</p>}
          </div>
          <div>
            <Label htmlFor="descricao">Descrição</Label>
            <Textarea id="descricao" {...register('descricao')} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="inicio_at">Início</Label>
              <Input id="inicio_at" type="datetime-local" {...register('inicio_at')} />
              {errors.inicio_at && (
                <p className="mt-1 text-xs text-destructive">{errors.inicio_at.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="fim_at">Fim</Label>
              <Input id="fim_at" type="datetime-local" {...register('fim_at')} />
              {errors.fim_at && (
                <p className="mt-1 text-xs text-destructive">{errors.fim_at.message}</p>
              )}
            </div>
          </div>
          <div>
            <Label htmlFor="cidades">Cidades afetadas (separar por vírgula)</Label>
            <Input id="cidades" {...register('cidades')} placeholder="São Paulo, Campinas" />
          </div>
          <div className="flex items-center gap-2">
            <input id="notificar" type="checkbox" {...register('notificar')} />
            <Label htmlFor="notificar">Notificar clientes via WhatsApp</Label>
          </div>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Criando…' : 'Criar manutenção'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
