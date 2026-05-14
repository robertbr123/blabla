'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  useCreateTecnicoUser,
  usePatchTecnicoUser,
  useResetTecnicoUserPassword,
} from '@/lib/api/queries'
import type { TecnicoUserOut } from '@/lib/api/types'

interface Props {
  tecnicoId: string
  user: TecnicoUserOut | null
}

export function TecnicoUserCard({ tecnicoId, user }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Acesso (login PWA)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {user ? <ExistingUser tecnicoId={tecnicoId} user={user} /> : <NewUserForm tecnicoId={tecnicoId} />}
      </CardContent>
    </Card>
  )
}

function NewUserForm({ tecnicoId }: { tecnicoId: string }) {
  const create = useCreateTecnicoUser(tecnicoId)
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [confirm, setConfirm] = useState('')
  const [show, setShow] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)

  async function submit() {
    setError(null)
    setOk(null)
    if (!email || !email.includes('@')) return setError('Informe um email válido')
    if (senha.length < 8) return setError('Senha precisa de 8+ caracteres')
    if (senha !== confirm) return setError('Senhas não conferem')
    try {
      await create.mutateAsync({ email, password: senha })
      setOk('Acesso criado. Técnico já pode logar.')
      setEmail('')
      setSenha('')
      setConfirm('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Falha ao criar acesso')
    }
  }

  return (
    <>
      <p className="text-xs text-muted-foreground">
        Sem acesso. Crie email + senha para o técnico entrar no PWA.
      </p>
      <div>
        <Label htmlFor="user-email">Email</Label>
        <Input
          id="user-email"
          type="email"
          autoComplete="off"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1"
        />
      </div>
      <div>
        <Label htmlFor="user-senha">Senha (mínimo 8)</Label>
        <div className="mt-1 flex gap-2">
          <Input
            id="user-senha"
            type={show ? 'text' : 'password'}
            autoComplete="new-password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
          />
          <Button type="button" variant="outline" onClick={() => setShow((v) => !v)}>
            {show ? 'Ocultar' : 'Mostrar'}
          </Button>
        </div>
      </div>
      <div>
        <Label htmlFor="user-confirm">Confirmar senha</Label>
        <Input
          id="user-confirm"
          type={show ? 'text' : 'password'}
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className="mt-1"
        />
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
      {ok && <p className="text-xs text-emerald-600">{ok}</p>}
      <Button className="w-full" onClick={submit} disabled={create.isPending}>
        {create.isPending ? 'Criando…' : 'Criar acesso'}
      </Button>
    </>
  )
}

function ExistingUser({ tecnicoId, user }: { tecnicoId: string; user: TecnicoUserOut }) {
  const patch = usePatchTecnicoUser(tecnicoId)
  const reset = useResetTecnicoUserPassword(tecnicoId)
  const [resetMode, setResetMode] = useState(false)
  const [nova, setNova] = useState('')
  const [show, setShow] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)

  async function toggleActive() {
    setError(null)
    setOk(null)
    try {
      await patch.mutateAsync({ is_active: !user.is_active })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Falha ao atualizar')
    }
  }

  async function doReset() {
    setError(null)
    setOk(null)
    if (nova.length < 8) return setError('Senha precisa de 8+ caracteres')
    try {
      await reset.mutateAsync({ password: nova })
      setOk('Senha alterada.')
      setNova('')
      setResetMode(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Falha ao resetar senha')
    }
  }

  return (
    <>
      <div className="space-y-1 text-sm">
        <div>
          <span className="text-muted-foreground">Email: </span>
          <span className="font-medium">{user.email}</span>
        </div>
        <div>
          <span className="text-muted-foreground">Login: </span>
          <span className={user.is_active ? 'text-emerald-600' : 'text-amber-600'}>
            {user.is_active ? 'ativo' : 'desativado'}
          </span>
        </div>
        <div className="text-xs text-muted-foreground">
          Último login: {user.last_login_at ? new Date(user.last_login_at).toLocaleString('pt-BR') : '—'}
        </div>
      </div>

      {!resetMode ? (
        <div className="space-y-2 pt-2">
          <Button
            variant="outline"
            className="w-full"
            onClick={() => {
              setOk(null)
              setError(null)
              setResetMode(true)
            }}
          >
            Resetar senha
          </Button>
          <Button
            variant="outline"
            className="w-full"
            onClick={toggleActive}
            disabled={patch.isPending}
          >
            {user.is_active ? 'Desativar login' : 'Reativar login'}
          </Button>
        </div>
      ) : (
        <div className="space-y-2 pt-2">
          <Label htmlFor="nova">Nova senha (mínimo 8)</Label>
          <div className="flex gap-2">
            <Input
              id="nova"
              type={show ? 'text' : 'password'}
              autoComplete="new-password"
              value={nova}
              onChange={(e) => setNova(e.target.value)}
            />
            <Button type="button" variant="outline" onClick={() => setShow((v) => !v)}>
              {show ? 'Ocultar' : 'Mostrar'}
            </Button>
          </div>
          <div className="flex gap-2">
            <Button onClick={doReset} disabled={reset.isPending} className="flex-1">
              {reset.isPending ? 'Salvando…' : 'Salvar nova senha'}
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setResetMode(false)
                setNova('')
              }}
            >
              Cancelar
            </Button>
          </div>
        </div>
      )}

      {error && <p className="text-xs text-destructive">{error}</p>}
      {ok && <p className="text-xs text-emerald-600">{ok}</p>}
    </>
  )
}
