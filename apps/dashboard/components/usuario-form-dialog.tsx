'use client'
import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Headphones, Loader2, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ApiError } from '@/lib/api/client'
import { useCreateUsuario, usePatchUsuario } from '@/lib/api/queries'
import type { UsuarioOut, UsuarioPatch } from '@/lib/api/types'
import { UsuarioCidadesPicker } from './usuario-cidades-picker'
import { UsuarioDialogShell } from './usuario-dialog-shell'
import { SENHA_MIN, UsuarioSenhaField, gerarSenha } from './usuario-senha-field'

function buildSchema(isEdit: boolean) {
  return z.object({
    name: z.string().trim().min(2, 'Informe o nome'),
    email: z.string().trim().min(1, 'Informe o email').email('Email inválido'),
    role: z.enum(['admin', 'atendente']),
    // Na edicao a senha nao aparece (troca pelo dialog "Redefinir senha").
    password: isEdit
      ? z.string()
      : z.string().min(SENHA_MIN, `A senha precisa ter pelo menos ${SENHA_MIN} caracteres`),
    cidades: z.array(z.string()),
  })
}
type FormValues = z.infer<ReturnType<typeof buildSchema>>

const PERFIS: ReadonlyArray<{
  value: FormValues['role']
  label: string
  descricao: string
  icon: React.ComponentType<{ className?: string }>
}> = [
  {
    value: 'atendente',
    label: 'Atendente',
    descricao: 'Atende conversas e ordens de serviço das cidades liberadas.',
    icon: Headphones,
  },
  {
    value: 'admin',
    label: 'Administrador',
    descricao: 'Acesso total: todas as cidades, usuários e configurações.',
    icon: ShieldCheck,
  },
]

function mesmasCidades(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false
  const set = new Set(a)
  return b.every((c) => set.has(c))
}

/** Criar (usuario = null) ou editar um usuario do dashboard. */
export function UsuarioFormDialog({
  usuario,
  onClose,
}: {
  usuario: UsuarioOut | null
  onClose: () => void
}) {
  const isEdit = usuario !== null
  const create = useCreateUsuario()
  const patch = usePatchUsuario()
  const saving = create.isPending || patch.isPending
  const [showPwd, setShowPwd] = useState(false)

  const schema = useMemo(() => buildSchema(isEdit), [isEdit])
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    getValues,
    setError,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: usuario?.name ?? '',
      email: usuario?.email ?? '',
      role: usuario?.role ?? 'atendente',
      password: '',
      cidades: usuario?.cidades ?? [],
    },
  })

  const role = watch('role')
  const cidades = watch('cidades')

  async function onSubmit(values: FormValues) {
    try {
      if (usuario) {
        // So manda o que mudou — evita esbarrar nas travas de "ultimo admin"
        // quando o perfil nem foi tocado.
        const body: UsuarioPatch = {}
        if (values.name !== usuario.name) body.name = values.name
        if (values.role !== usuario.role) body.role = values.role
        if (values.role === 'atendente' && !mesmasCidades(values.cidades, usuario.cidades)) {
          body.cidades = values.cidades
        }
        if (Object.keys(body).length > 0) {
          await patch.mutateAsync({ id: usuario.id, body })
          toast.success('Usuário atualizado')
        }
      } else {
        const criado = await create.mutateAsync({
          name: values.name,
          email: values.email,
          role: values.role,
          password: values.password,
          ...(values.role === 'atendente' ? { cidades: values.cidades } : {}),
        })
        toast.success(`Usuário ${criado.name} criado`)
      }
      onClose()
    } catch (e) {
      // O toast sai no onError do hook; aqui so marca o campo quando da pra saber qual.
      if (e instanceof ApiError && e.status === 409) {
        setError('email', { message: e.message }, { shouldFocus: true })
      }
    }
  }

  return (
    <UsuarioDialogShell
      title={isEdit ? 'Editar usuário' : 'Novo usuário'}
      description={
        usuario
          ? usuario.email
          : 'Crie o acesso de um atendente ou de outro administrador ao painel.'
      }
      onClose={onClose}
    >
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="space-y-1.5">
          <Label htmlFor="usuario-nome">Nome</Label>
          <Input
            id="usuario-nome"
            autoComplete="off"
            autoFocus
            aria-invalid={errors.name ? true : undefined}
            aria-describedby={errors.name ? 'usuario-nome-erro' : undefined}
            {...register('name')}
          />
          {errors.name && (
            <p id="usuario-nome-erro" className="text-xs text-destructive">
              {errors.name.message}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="usuario-email">Email</Label>
          <Input
            id="usuario-email"
            type="email"
            inputMode="email"
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
            readOnly={isEdit}
            aria-invalid={errors.email ? true : undefined}
            aria-describedby="usuario-email-ajuda"
            className={isEdit ? 'bg-muted text-muted-foreground' : undefined}
            {...register('email')}
          />
          <div id="usuario-email-ajuda" className="space-y-1">
            {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
            <p className="text-xs text-muted-foreground">
              {isEdit
                ? 'O email é o login e não pode ser alterado.'
                : 'É com este email que a pessoa entra no painel.'}
            </p>
          </div>
        </div>

        <fieldset className="min-w-0 space-y-1.5">
          <legend className="text-sm font-medium leading-none">Perfil</legend>
          <div className="grid gap-2 pt-1.5 sm:grid-cols-2">
            {PERFIS.map((p) => {
              const Icon = p.icon
              return (
                <label key={p.value} className="relative block cursor-pointer">
                  <input
                    type="radio"
                    value={p.value}
                    className="peer sr-only"
                    {...register('role')}
                  />
                  <span className="flex h-full items-start gap-2.5 rounded-md border border-input bg-card p-3 transition-colors hover:bg-elevated peer-checked:border-primary peer-checked:bg-primary/[0.08] peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-background">
                    <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="min-w-0">
                      <span className="block text-sm font-medium">{p.label}</span>
                      <span className="mt-0.5 block text-xs text-muted-foreground">
                        {p.descricao}
                      </span>
                    </span>
                  </span>
                </label>
              )
            })}
          </div>
        </fieldset>

        {!isEdit && (
          <UsuarioSenhaField
            id="usuario-senha"
            label="Senha"
            registration={register('password')}
            error={errors.password?.message}
            show={showPwd}
            onShowChange={setShowPwd}
            onGerar={() => {
              setValue('password', gerarSenha(), { shouldValidate: true, shouldDirty: true })
              setShowPwd(true)
            }}
            getValue={() => getValues('password')}
            hint={`Mínimo de ${SENHA_MIN} caracteres. Copie e envie à pessoa antes de salvar — a senha não é exibida de novo.`}
          />
        )}

        {role === 'atendente' ? (
          <UsuarioCidadesPicker
            value={cidades}
            onChange={(next) => setValue('cidades', next, { shouldDirty: true })}
          />
        ) : (
          <p className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
            Administradores veem todas as cidades — não há restrição a configurar.
          </p>
        )}

        <div className="flex flex-col-reverse gap-2 border-t pt-4 sm:flex-row sm:justify-end">
          <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button type="submit" disabled={saving}>
            {saving ? (
              <>
                <Loader2 aria-hidden className="animate-spin" /> Salvando…
              </>
            ) : isEdit ? (
              'Salvar alterações'
            ) : (
              'Criar usuário'
            )}
          </Button>
        </div>
      </form>
    </UsuarioDialogShell>
  )
}
