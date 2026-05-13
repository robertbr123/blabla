import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
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
      const headers: HeadersInit = {}
      if (csrf) headers['X-CSRF'] = csrf
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
