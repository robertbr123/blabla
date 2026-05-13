import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import type { ConversaDetail, ConversaListItem, CursorPage } from './types'

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
