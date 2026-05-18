import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import { getAccessToken } from './token'
import type {
  ConcluirIn,
  GpsUpdate,
  IniciarIn,
  OsListItem,
  OsOut,
} from './types'

export function useMyOs(statusFilter?: string) {
  const qs = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : ''
  return useQuery<OsListItem[]>({
    queryKey: ['my-os', statusFilter],
    queryFn: () => apiFetch(`/api/v1/tecnico/me/os${qs}`),
    refetchInterval: 60_000,
  })
}

export function useMyOsDetail(id: string) {
  return useQuery<OsOut>({
    queryKey: ['my-os-detail', id],
    queryFn: () => apiFetch(`/api/v1/tecnico/me/os/${id}`),
    enabled: Boolean(id),
  })
}

export function useUpdateGps() {
  return useMutation({
    mutationFn: (body: GpsUpdate) =>
      apiFetch<void>('/api/v1/tecnico/me/gps', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  })
}

export function useIniciarOs(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: IniciarIn) =>
      apiFetch<OsOut>(`/api/v1/tecnico/me/os/${id}/iniciar`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['my-os-detail', id] })
      qc.invalidateQueries({ queryKey: ['my-os'] })
    },
  })
}

export function useConcluirMyOs(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ConcluirIn) =>
      apiFetch<OsOut>(`/api/v1/tecnico/me/os/${id}/concluir`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['my-os-detail', id] })
      qc.invalidateQueries({ queryKey: ['my-os'] })
    },
  })
}

export function useUploadFotoMy(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      const csrf =
        typeof document !== 'undefined'
          ? document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)?.[1]
          : undefined
      const headers: Record<string, string> = {}
      if (csrf) headers['X-CSRF'] = csrf
      const token = getAccessToken()
      if (token) headers['Authorization'] = `Bearer ${token}`
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ''}/api/v1/tecnico/me/os/${id}/foto`,
        {
          method: 'POST',
          body: fd,
          headers,
          credentials: 'include',
        },
      )
      if (!res.ok) throw new Error(`upload failed: ${res.status}`)
      return (await res.json()) as OsOut
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['my-os-detail', id] }),
  })
}

// F6 — Meu estoque
export function useMyEstoqueSaldo() {
  return useQuery<import('./types').EstoqueSaldo>({
    queryKey: ['me-estoque-saldo'],
    queryFn: () => apiFetch('/api/v1/tecnico/me/estoque/saldo'),
    staleTime: 30_000,
  })
}

// F6+ — Catálogo (read-only) + criar movimento próprio
export function useEstoqueCatalogo() {
  return useQuery<import('./types').EstoqueItemInfo[]>({
    queryKey: ['estoque-catalogo'],
    queryFn: () => apiFetch('/api/v1/estoque/itens?ativos_only=true'),
    staleTime: 60_000,
  })
}

export function useMyEstoqueMovimentos(osId?: string) {
  const qs = osId ? `?ordem_servico_id=${osId}` : ''
  return useQuery<import('./types').EstoqueMovimento[]>({
    queryKey: ['me-estoque-movimentos', osId ?? ''],
    queryFn: () => apiFetch(`/api/v1/tecnico/me/estoque/movimentos${qs}`),
  })
}

export function useCreateMyMovimento() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: import('./types').TecMovimentoCreate) =>
      apiFetch<import('./types').EstoqueMovimento>(
        '/api/v1/tecnico/me/estoque/movimentos',
        { method: 'POST', body: JSON.stringify(body) },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['me-estoque-saldo'] })
      qc.invalidateQueries({ queryKey: ['me-estoque-movimentos'] })
    },
  })
}
