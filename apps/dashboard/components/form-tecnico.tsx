'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useCreateTecnico } from '@/lib/api/queries'

const schema = z.object({
  nome: z.string().min(1, 'Obrigatório').max(200),
  whatsapp: z.string().max(20).optional().nullable(),
  ativo: z.boolean().default(true),
})

type FormValues = z.infer<typeof schema>

export function FormTecnico() {
  const router = useRouter()
  const createTecnico = useCreateTecnico()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { ativo: true } })

  async function onSubmit(values: FormValues) {
    const created = await createTecnico.mutateAsync({
      nome: values.nome,
      whatsapp: values.whatsapp || null,
      ativo: values.ativo,
    })
    router.push(`/tecnicos/${created.id}`)
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Novo Técnico</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <Label htmlFor="nome">Nome</Label>
            <Input id="nome" {...register('nome')} className="mt-1" />
            {errors.nome && (
              <p className="mt-1 text-xs text-destructive">{errors.nome.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="whatsapp">WhatsApp (opcional)</Label>
            <Input
              id="whatsapp"
              {...register('whatsapp')}
              placeholder="+55..."
              className="mt-1"
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              id="ativo"
              type="checkbox"
              {...register('ativo')}
              defaultChecked
              className="h-4 w-4"
            />
            <Label htmlFor="ativo">Ativo</Label>
          </div>
          <Button type="submit" disabled={isSubmitting || createTecnico.isPending}>
            {isSubmitting || createTecnico.isPending ? 'Criando…' : 'Criar Técnico'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
