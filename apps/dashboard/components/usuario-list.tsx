'use client'
import { useMemo, useState } from 'react'
import {
  AlertTriangle,
  Headphones,
  KeyRound,
  Pencil,
  Plus,
  Search,
  ShieldCheck,
  UserCheck,
  UserCog,
  UserX,
} from 'lucide-react'
import { toast } from 'sonner'

import {
  Age,
  Avatar,
  FilterTabs,
  PageHeader,
  SkeletonRows,
  StatusDot,
  TONE_SOFT,
  type FilterTab,
} from '@/components/noc/primitives'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { Input } from '@/components/ui/input'
import { usePatchUsuario, useUsuarios } from '@/lib/api/queries'
import type { UsuarioOut } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { normalizar } from './usuario-cidades-picker'
import { UsuarioFormDialog } from './usuario-form-dialog'
import { UsuarioSenhaDialog } from './usuario-senha-dialog'

type Filtro = 'todos' | 'atendentes' | 'admins' | 'inativos'

type DialogState =
  | { kind: 'criar' }
  | { kind: 'editar'; usuario: UsuarioOut }
  | { kind: 'senha'; usuario: UsuarioOut }
  | null

const MAX_CHIPS = 3

function PerfilPill({ role }: { role: UsuarioOut['role'] }) {
  const admin = role === 'admin'
  const Icon = admin ? ShieldCheck : Headphones
  return (
    <span
      className={cn(
        'inline-flex h-[22px] items-center gap-1 whitespace-nowrap rounded-md px-2 text-xs font-medium ring-1 ring-inset',
        admin ? TONE_SOFT.primary : TONE_SOFT.muted,
      )}
    >
      <Icon aria-hidden className="h-3 w-3" />
      {admin ? 'Administrador' : 'Atendente'}
    </span>
  )
}

function StatusLabel({ ativo }: { ativo: boolean }) {
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap text-xs">
      <StatusDot tone={ativo ? 'success' : 'muted'} />
      <span className={ativo ? undefined : 'text-muted-foreground'}>
        {ativo ? 'Ativo' : 'Inativo'}
      </span>
    </span>
  )
}

function CidadesCell({ u }: { u: UsuarioOut }) {
  if (u.role === 'admin') {
    return (
      <span className="text-muted-foreground" title="Administradores veem todas as cidades">
        <span aria-hidden>—</span>
        <span className="sr-only">Administradores veem todas as cidades</span>
      </span>
    )
  }
  if (u.cidades.length === 0) {
    return <span className="text-xs text-muted-foreground">Todas as cidades</span>
  }
  const visiveis = u.cidades.slice(0, MAX_CHIPS)
  const resto = u.cidades.length - visiveis.length
  return (
    <span className="flex flex-wrap items-center gap-1" title={u.cidades.join(', ')}>
      {visiveis.map((c) => (
        <span
          key={c}
          className={cn(
            'inline-flex h-[22px] max-w-[140px] items-center rounded-md px-2 text-xs ring-1 ring-inset',
            TONE_SOFT.muted,
          )}
        >
          <span className="truncate text-foreground">{c}</span>
        </span>
      ))}
      {resto > 0 && (
        <span className="num text-xs text-muted-foreground">
          +{resto}
          <span className="sr-only"> cidades</span>
        </span>
      )}
    </span>
  )
}

function UltimoAcesso({ iso }: { iso: string | null }) {
  if (!iso) return <span className="text-xs text-muted-foreground">Nunca</span>
  return <Age iso={iso} />
}

function RowActions({
  u,
  busy,
  onEditar,
  onSenha,
  onToggleAtivo,
}: {
  u: UsuarioOut
  busy: boolean
  onEditar: () => void
  onSenha: () => void
  onToggleAtivo: () => void
}) {
  const btn = 'h-8 w-8 text-muted-foreground hover:text-foreground md:h-7 md:w-7'
  return (
    <div className="flex items-center justify-end gap-0.5">
      <Button
        variant="ghost"
        size="icon"
        className={btn}
        onClick={onEditar}
        title="Editar"
        aria-label={`Editar ${u.name}`}
      >
        <Pencil className="h-3.5 w-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className={btn}
        onClick={onSenha}
        title="Redefinir senha"
        aria-label={`Redefinir senha de ${u.name}`}
      >
        <KeyRound className="h-3.5 w-3.5" />
      </Button>
      {u.is_active ? (
        <Button
          variant="ghost"
          size="icon"
          className={cn(btn, 'hover:bg-destructive/10 hover:text-destructive')}
          onClick={onToggleAtivo}
          disabled={busy}
          title="Desativar"
          aria-label={`Desativar ${u.name}`}
        >
          <UserX className="h-3.5 w-3.5" />
        </Button>
      ) : (
        <Button
          variant="ghost"
          size="icon"
          className={btn}
          onClick={onToggleAtivo}
          disabled={busy}
          title="Ativar"
          aria-label={`Ativar ${u.name}`}
        >
          <UserCheck className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  )
}

export function UsuarioList() {
  const { data, isLoading, error } = useUsuarios()
  const patch = usePatchUsuario()
  const [filtro, setFiltro] = useState<Filtro>('todos')
  const [busca, setBusca] = useState('')
  const [dialog, setDialog] = useState<DialogState>(null)

  const usuarios = useMemo(() => data ?? [], [data])

  const tabs = useMemo<ReadonlyArray<FilterTab<Filtro>>>(
    () => [
      { value: 'todos', label: 'Todos', count: usuarios.length },
      {
        value: 'atendentes',
        label: 'Atendentes',
        count: usuarios.filter((u) => u.role === 'atendente').length,
      },
      { value: 'admins', label: 'Admins', count: usuarios.filter((u) => u.role === 'admin').length },
      { value: 'inativos', label: 'Inativos', count: usuarios.filter((u) => !u.is_active).length },
    ],
    [usuarios],
  )

  const termo = normalizar(busca)
  const filtrados = useMemo(
    () =>
      usuarios.filter((u) => {
        if (filtro === 'atendentes' && u.role !== 'atendente') return false
        if (filtro === 'admins' && u.role !== 'admin') return false
        if (filtro === 'inativos' && u.is_active) return false
        if (!termo) return true
        return normalizar(u.name).includes(termo) || normalizar(u.email).includes(termo)
      }),
    [usuarios, filtro, termo],
  )

  const filtrando = filtro !== 'todos' || termo !== ''
  const togglingId = patch.isPending ? patch.variables?.id : undefined

  function toggleAtivo(u: UsuarioOut) {
    if (
      u.is_active &&
      !confirm(
        `Desativar ${u.name}? A pessoa perde o acesso ao painel até ser reativada.`,
      )
    ) {
      return
    }
    patch.mutate(
      { id: u.id, body: { is_active: !u.is_active } },
      {
        onSuccess: () =>
          toast.success(u.is_active ? `${u.name} foi desativado` : `${u.name} foi reativado`),
        // erro (ex.: ultimo admin ativo) sai no toast do onError do hook
      },
    )
  }

  const novoBtn = (
    <Button size="sm" onClick={() => setDialog({ kind: 'criar' })}>
      <Plus aria-hidden /> Novo usuário
    </Button>
  )

  return (
    <div className="min-w-0 space-y-4">
      <PageHeader
        title="Usuários"
        description="Quem acessa o painel e quais cidades cada atendente enxerga."
        actions={novoBtn}
      />

      {dialog?.kind === 'criar' && (
        <UsuarioFormDialog usuario={null} onClose={() => setDialog(null)} />
      )}
      {dialog?.kind === 'editar' && (
        <UsuarioFormDialog
          key={dialog.usuario.id}
          usuario={dialog.usuario}
          onClose={() => setDialog(null)}
        />
      )}
      {dialog?.kind === 'senha' && (
        <UsuarioSenhaDialog
          key={dialog.usuario.id}
          usuario={dialog.usuario}
          onClose={() => setDialog(null)}
        />
      )}

      <div className="flex flex-wrap items-center gap-3">
        <FilterTabs
          tabs={tabs}
          value={filtro}
          onChange={setFiltro}
          ariaLabel="Filtrar usuários"
        />
        <div className="relative w-full sm:ml-auto sm:w-72">
          <Search
            aria-hidden
            className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            type="search"
            aria-label="Buscar usuários"
            placeholder="Buscar por nome ou email…"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="pl-8"
          />
        </div>
      </div>

      {isLoading && (
        <div className="overflow-hidden rounded-lg border bg-card">
          <SkeletonRows rows={6} />
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/[0.08] p-4"
        >
          <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
          <div className="min-w-0">
            <p className="text-sm font-medium">Não foi possível carregar os usuários</p>
            <p className="mt-0.5 break-words text-xs text-muted-foreground">
              {error instanceof Error ? error.message : 'Erro ao carregar'}
            </p>
          </div>
        </div>
      )}

      {!isLoading && !error && filtrados.length === 0 && (
        <EmptyState
          icon={UserCog}
          className="rounded-lg"
          title={filtrando ? 'Nenhum usuário encontrado' : 'Nenhum usuário cadastrado'}
          description={
            filtrando
              ? 'Tente outro filtro ou limpe a busca.'
              : 'Crie o primeiro acesso de atendente ou administrador.'
          }
          action={filtrando ? undefined : novoBtn}
        />
      )}

      {filtrados.length > 0 && (
        <>
          {/* md+: tabela */}
          <div className="hidden overflow-hidden rounded-lg border bg-card md:block">
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Usuário</th>
                    <th scope="col">Perfil</th>
                    <th scope="col">Cidades</th>
                    <th scope="col">Último acesso</th>
                    <th scope="col">Status</th>
                    <th scope="col" className="text-right">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {filtrados.map((u) => (
                    <tr key={u.id}>
                      <td>
                        <span className="flex min-w-0 items-center gap-2.5">
                          <Avatar name={u.name} className={u.is_active ? undefined : 'opacity-60'} />
                          <span className="min-w-0">
                            <span
                              className={cn(
                                'block max-w-[240px] truncate font-medium',
                                !u.is_active && 'text-muted-foreground',
                              )}
                              title={u.name}
                            >
                              {u.name}
                            </span>
                            <span
                              className="block max-w-[240px] truncate text-xs text-muted-foreground"
                              title={u.email}
                            >
                              {u.email}
                            </span>
                          </span>
                        </span>
                      </td>
                      <td>
                        <PerfilPill role={u.role} />
                      </td>
                      <td className="min-w-[180px] max-w-[360px]">
                        <CidadesCell u={u} />
                      </td>
                      <td className="whitespace-nowrap">
                        <UltimoAcesso iso={u.last_login_at} />
                      </td>
                      <td>
                        <StatusLabel ativo={u.is_active} />
                      </td>
                      <td>
                        <RowActions
                          u={u}
                          busy={togglingId === u.id}
                          onEditar={() => setDialog({ kind: 'editar', usuario: u })}
                          onSenha={() => setDialog({ kind: 'senha', usuario: u })}
                          onToggleAtivo={() => toggleAtivo(u)}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* < md: cartoes empilhados */}
          <ul className="space-y-2 md:hidden">
            {filtrados.map((u) => (
              <li key={u.id} className="rounded-lg border bg-card p-3">
                <div className="flex items-start gap-2.5">
                  <Avatar name={u.name} className={u.is_active ? undefined : 'opacity-60'} />
                  <div className="min-w-0 flex-1">
                    <p
                      className={cn(
                        'truncate text-sm font-medium',
                        !u.is_active && 'text-muted-foreground',
                      )}
                    >
                      {u.name}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">{u.email}</p>
                  </div>
                  <StatusLabel ativo={u.is_active} />
                </div>

                <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5">
                  <PerfilPill role={u.role} />
                  <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                    Último acesso
                    <UltimoAcesso iso={u.last_login_at} />
                  </span>
                </div>

                {u.role === 'atendente' && (
                  <div className="mt-2.5">
                    <p className="eyebrow mb-1">Cidades</p>
                    <CidadesCell u={u} />
                  </div>
                )}

                <div className="mt-2 border-t pt-2">
                  <RowActions
                    u={u}
                    busy={togglingId === u.id}
                    onEditar={() => setDialog({ kind: 'editar', usuario: u })}
                    onSenha={() => setDialog({ kind: 'senha', usuario: u })}
                    onToggleAtivo={() => toggleAtivo(u)}
                  />
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
