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
import { useCreateLead } from '@/lib/api/queries'

const schema = z.object({
  nome: z.string().min(1, 'Obrigatório').max(200),
  whatsapp: z.string().min(1, 'Obrigatório').max(20),
  interesse: z.string().max(200).optional().nullable(),
  notas: z.string().max(2000).optional().nullable(),
})

type FormValues = z.infer<typeof schema>

export function FormLead() {
  const router = useRouter()
  const createLead = useCreateLead()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function onSubmit(values: FormValues) {
    const created = await createLead.mutateAsync({
      nome: values.nome,
      whatsapp: values.whatsapp,
      interesse: values.interesse || null,
      notas: values.notas || null,
    })
    router.push(`/leads/${created.id}`)
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Novo Lead</CardTitle>
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
            <Label htmlFor="whatsapp">WhatsApp</Label>
            <Input id="whatsapp" {...register('whatsapp')} placeholder="+55..." className="mt-1" />
            {errors.whatsapp && (
              <p className="mt-1 text-xs text-destructive">{errors.whatsapp.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="interesse">Interesse (opcional)</Label>
            <Input id="interesse" {...register('interesse')} className="mt-1" />
          </div>
          <div>
            <Label htmlFor="notas">Notas (opcional)</Label>
            <Textarea id="notas" {...register('notas')} className="mt-1" />
          </div>
          <Button type="submit" disabled={isSubmitting || createLead.isPending}>
            {isSubmitting || createLead.isPending ? 'Criando…' : 'Criar Lead'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
