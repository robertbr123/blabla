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
import { useCreateTecnico } from '@/lib/api/queries'

const schema = z
  .object({
    nome: z.string().min(1, 'Obrigatório').max(200),
    whatsapp: z.string().max(20).optional().nullable(),
    ativo: z.boolean().default(true),
    cria_acesso: z.boolean().default(false),
    email: z.string().email('Email inválido').optional().or(z.literal('')),
    senha: z.string().optional().or(z.literal('')),
    senha_confirm: z.string().optional().or(z.literal('')),
  })
  .superRefine((v, ctx) => {
    if (v.cria_acesso) {
      if (!v.email) {
        ctx.addIssue({ path: ['email'], code: z.ZodIssueCode.custom, message: 'Obrigatório quando acesso é marcado' })
      }
      if (!v.senha || v.senha.length < 8) {
        ctx.addIssue({ path: ['senha'], code: z.ZodIssueCode.custom, message: 'Mínimo 8 caracteres' })
      }
      if (v.senha !== v.senha_confirm) {
        ctx.addIssue({ path: ['senha_confirm'], code: z.ZodIssueCode.custom, message: 'Senhas não conferem' })
      }
    }
  })

type FormValues = z.infer<typeof schema>

export function FormTecnico() {
  const router = useRouter()
  const createTecnico = useCreateTecnico()
  const [showPwd, setShowPwd] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { ativo: true, cria_acesso: false },
  })

  const criaAcesso = watch('cria_acesso')

  async function onSubmit(values: FormValues) {
    setServerError(null)
    try {
      const created = await createTecnico.mutateAsync({
        nome: values.nome,
        whatsapp: values.whatsapp || null,
        ativo: values.ativo,
        ...(values.cria_acesso
          ? { email: values.email || null, password: values.senha || null }
          : {}),
      })
      router.push(`/tecnicos/${created.id}`)
    } catch (e) {
      setServerError(e instanceof Error ? e.message : 'Falha ao criar técnico')
    }
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
            {errors.nome && <p className="mt-1 text-xs text-destructive">{errors.nome.message}</p>}
          </div>
          <div>
            <Label htmlFor="whatsapp">WhatsApp (opcional)</Label>
            <Input id="whatsapp" {...register('whatsapp')} placeholder="+55..." className="mt-1" />
          </div>
          <div className="flex items-center gap-2">
            <input id="ativo" type="checkbox" {...register('ativo')} defaultChecked className="h-4 w-4" />
            <Label htmlFor="ativo">Ativo (disponível para OS)</Label>
          </div>

          <div className="rounded border p-4 space-y-3">
            <div className="flex items-center gap-2">
              <input
                id="cria_acesso"
                type="checkbox"
                {...register('cria_acesso')}
                className="h-4 w-4"
              />
              <Label htmlFor="cria_acesso" className="font-medium">
                Criar acesso ao PWA (login do técnico)
              </Label>
            </div>
            <p className="text-xs text-muted-foreground">
              Marque para o técnico poder entrar em tec.robertbr.dev com email + senha.
              Também pode ser feito depois, na tela de detalhe.
            </p>
            {criaAcesso && (
              <div className="space-y-3 pt-1">
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="off"
                    {...register('email')}
                    className="mt-1"
                  />
                  {errors.email && (
                    <p className="mt-1 text-xs text-destructive">{errors.email.message}</p>
                  )}
                </div>
                <div>
                  <Label htmlFor="senha">Senha (mínimo 8)</Label>
                  <div className="mt-1 flex gap-2">
                    <Input
                      id="senha"
                      type={showPwd ? 'text' : 'password'}
                      autoComplete="new-password"
                      {...register('senha')}
                    />
                    <Button type="button" variant="outline" onClick={() => setShowPwd((v) => !v)}>
                      {showPwd ? 'Ocultar' : 'Mostrar'}
                    </Button>
                  </div>
                  {errors.senha && (
                    <p className="mt-1 text-xs text-destructive">{errors.senha.message}</p>
                  )}
                </div>
                <div>
                  <Label htmlFor="senha_confirm">Confirmar senha</Label>
                  <Input
                    id="senha_confirm"
                    type={showPwd ? 'text' : 'password'}
                    autoComplete="new-password"
                    {...register('senha_confirm')}
                    className="mt-1"
                  />
                  {errors.senha_confirm && (
                    <p className="mt-1 text-xs text-destructive">{errors.senha_confirm.message}</p>
                  )}
                </div>
              </div>
            )}
          </div>

          {serverError && <p className="text-sm text-destructive">{serverError}</p>}
          <Button type="submit" disabled={isSubmitting || createTecnico.isPending}>
            {isSubmitting || createTecnico.isPending ? 'Criando…' : 'Criar Técnico'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
