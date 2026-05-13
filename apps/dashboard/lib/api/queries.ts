import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import type {
  ConversaDetail,
  ConversaListItem,
  CursorPage,
  OsConcluirIn,
  OsCreate,
  OsListItem,
  OsOut,
  OsPatch,
} from './types'

export interface ConversaListFilters {
  status?: string
  q?: string
}

export function useConversas(filters: ConversaListFilters = {}) {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.q) params.set('q', filters.q)
  const qs = params.toString()
  return useQuery<CursorPage<ConversaListItem>>({
    queryKey: ['conversas', filters],
    queryFn: () => apiFetch(`/api/v1/conversas${qs ? `?${qs}` : ''}`),
    refetchInterval: 15_000,
  })
}

export function useConversa(id: string) {
  return useQuery<ConversaDetail>({
    queryKey: ['conversa', id],
    queryFn: () => apiFetch(`/api/v1/conversas/${id}`),
    enabled: Boolean(id),
  })
}

export function useResponder(conversaId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (text: string) =>
      apiFetch(`/api/v1/conversas/${conversaId}/responder`, {
        method: 'POST',
        body: JSON.stringify({ text }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['conversa', conversaId] }),
  })
}

export function useAtender(conversaId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch(`/api/v1/conversas/${conversaId}/atender`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conversa', conversaId] })
      qc.invalidateQueries({ queryKey: ['conversas'] })
    },
  })
}

export function useEncerrar(conversaId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch(`/api/v1/conversas/${conversaId}/encerrar`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conversa', conversaId] })
      qc.invalidateQueries({ queryKey: ['conversas'] })
    },
  })
}

// ── OS ──────────────────────────────────────────────────────────────────────

export interface OsListFilters {
  status?: string
  tecnico?: string
}

export function useOsList(filters: OsListFilters = {}) {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.tecnico) params.set('tecnico', filters.tecnico)
  const qs = params.toString()
  return useQuery<CursorPage<OsListItem>>({
    queryKey: ['os', filters],
    queryFn: () => apiFetch(`/api/v1/os${qs ? `?${qs}` : ''}`),
    refetchInterval: 30_000,
  })
}

export function useOs(id: string) {
  return useQuery<OsOut>({
    queryKey: ['os-detail', id],
    queryFn: () => apiFetch(`/api/v1/os/${id}`),
    enabled: Boolean(id),
  })
}

export function useCreateOs() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: OsCreate) =>
      apiFetch<OsOut>('/api/v1/os', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['os'] }),
  })
}

export function usePatchOs(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: OsPatch) =>
      apiFetch<OsOut>(`/api/v1/os/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['os-detail', id] })
      qc.invalidateQueries({ queryKey: ['os'] })
    },
  })
}

export function useConcluirOs(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: OsConcluirIn) =>
      apiFetch<OsOut>(`/api/v1/os/${id}/concluir`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['os-detail', id] })
      qc.invalidateQueries({ queryKey: ['os'] })
    },
  })
}

export function useUploadFoto(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      // Custom fetch — apiFetch sets Content-Type: application/json; we need multipart
      const csrf =
        typeof document !== 'undefined'
          ? document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)?.[1]
          : undefined
      const headers: HeadersInit = {}
      if (csrf) headers['X-CSRF'] = csrf
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ''}/api/v1/os/${id}/foto`,
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ['os-detail', id] }),
  })
}
