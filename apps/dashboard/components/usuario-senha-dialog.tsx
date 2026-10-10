'use client'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Info, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { usePatchUsuario } from '@/lib/api/queries'
import type { UsuarioOut } from '@/lib/api/types'
import { UsuarioDialogShell } from './usuario-dialog-shell'
import { SENHA_MIN, UsuarioSenhaField, gerarSenha } from './usuario-senha-field'

const schema = z.object({
  password: z
    .string()
    .min(SENHA_MIN, `A senha precisa ter pelo menos ${SENHA_MIN} caracteres`),
})
type FormValues = z.infer<typeof schema>

export function UsuarioSenhaDialog({
  usuario,
  onClose,
}: {
  usuario: UsuarioOut
  onClose: () => void
}) {
  const patch = usePatchUsuario()
  const [showPwd, setShowPwd] = useState(false)
  const {
    register,
    handleSubmit,
    setValue,
    getValues,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { password: '' } })

  async function onSubmit(values: FormValues) {
    try {
      await patch.mutateAsync({ id: usuario.id, body: { password: values.password } })
      toast.success(`Senha de ${usuario.name} redefinida`)
      onClose()
    } catch {
      /* toast no onError do hook */
    }
  }

  return (
    <UsuarioDialogShell
      title="Redefinir senha"
      description={`${usuario.name} · ${usuario.email}`}
      onClose={onClose}
    >
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <UsuarioSenhaField
          id="usuario-nova-senha"
          label="Nova senha"
          autoFocus
          registration={register('password')}
          error={errors.password?.message}
          show={showPwd}
          onShowChange={setShowPwd}
          onGerar={() => {
            setValue('password', gerarSenha(), { shouldValidate: true, shouldDirty: true })
            setShowPwd(true)
          }}
          getValue={() => getValues('password')}
          hint={`Mínimo de ${SENHA_MIN} caracteres. Copie antes de salvar — a senha não é exibida de novo.`}
        />

        <div className="flex items-start gap-2 rounded-md bg-info/[0.10] px-3 py-2 text-xs ring-1 ring-inset ring-info/25">
          <Info aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0 text-info" />
          <p>
            Ao salvar, o usuário é desconectado das sessões ativas e precisa entrar de novo com a
            nova senha.
          </p>
        </div>

        <div className="flex flex-col-reverse gap-2 border-t pt-4 sm:flex-row sm:justify-end">
          <Button type="button" variant="outline" onClick={onClose} disabled={patch.isPending}>
            Cancelar
          </Button>
          <Button type="submit" disabled={patch.isPending}>
            {patch.isPending ? (
              <>
                <Loader2 aria-hidden className="animate-spin" /> Salvando…
              </>
            ) : (
              'Redefinir senha'
            )}
          </Button>
        </div>
      </form>
    </UsuarioDialogShell>
  )
}
