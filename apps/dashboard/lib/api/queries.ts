import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import type {
  AreaCreate,
  AreaOut,
  ClienteDetail,
  ClienteListItem,
  ConfigOut,
  ConversaDetail,
  ConversaListItem,
  CursorPage,
  LeadCreate,
  LeadOut,
  LeadPatch,
  ManutencaoCreate,
  ManutencaoOut,
  ManutencaoPatch,
  MetricasOut,
  OsConcluirIn,
  OsCreate,
  OsDeleteOut,
  OsListItem,
  OsOut,
  OsPatch,
  OsReatribuirIn,
  TecnicoCreate,
  TecnicoListItem,
  TecnicoOut,
  TecnicoPatch,
  TecnicoUserCreate,
  TecnicoUserOut,
  TecnicoUserPatch,
  TecnicoUserResetPassword,
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
  cliente_id?: string
}

export function useOsList(filters: OsListFilters = {}) {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.tecnico) params.set('tecnico', filters.tecnico)
  if (filters.cliente_id) params.set('cliente_id', filters.cliente_id)
  const qs = params.toString()
  return useQuery<CursorPage<OsListItem>>({
    queryKey: ['os', filters],
    queryFn: () => apiFetch(`/api/v1/os${qs ? `?${qs}` : ''}`),
    refetchInterval: 30_000,
    enabled: filters.cliente_id !== undefined ? Boolean(filters.cliente_id) : true,
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

export function useReatribuirOs(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: OsReatribuirIn) =>
      apiFetch<OsOut>(`/api/v1/os/${id}/reatribuir`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['os-detail', id] })
      qc.invalidateQueries({ queryKey: ['os'] })
    },
  })
}

export function useDeleteOs(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<OsDeleteOut>(`/api/v1/os/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['os'] }),
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

// ----- Leads -----
export function useLeads(filters: { status?: string; q?: string } = {}) {
  const p = new URLSearchParams()
  if (filters.status) p.set('status', filters.status)
  if (filters.q) p.set('q', filters.q)
  const qs = p.toString()
  return useQuery<CursorPage<LeadOut>>({
    queryKey: ['leads', filters],
    queryFn: () => apiFetch(`/api/v1/leads${qs ? `?${qs}` : ''}`),
  })
}

export function useLead(id: string) {
  return useQuery<LeadOut>({
    queryKey: ['lead', id],
    queryFn: () => apiFetch(`/api/v1/leads/${id}`),
    enabled: Boolean(id),
  })
}

export function useCreateLead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: LeadCreate) =>
      apiFetch<LeadOut>('/api/v1/leads', { method: 'POST', body: JSON.stringify(b) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leads'] }),
  })
}

export function usePatchLead(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: LeadPatch) =>
      apiFetch<LeadOut>(`/api/v1/leads/${id}`, { method: 'PATCH', body: JSON.stringify(b) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead', id] })
      qc.invalidateQueries({ queryKey: ['leads'] })
    },
  })
}

export function useDeleteLead(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch<void>(`/api/v1/leads/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leads'] }),
  })
}

// ----- Clientes -----
export function useClientes(filters: { q?: string; cidade?: string } = {}) {
  const p = new URLSearchParams()
  if (filters.q) p.set('q', filters.q)
  if (filters.cidade) p.set('cidade', filters.cidade)
  const qs = p.toString()
  return useQuery<CursorPage<ClienteListItem>>({
    queryKey: ['clientes', filters],
    queryFn: () => apiFetch(`/api/v1/clientes${qs ? `?${qs}` : ''}`),
  })
}

export function useCliente(id: string) {
  return useQuery<ClienteDetail>({
    queryKey: ['cliente', id],
    queryFn: () => apiFetch(`/api/v1/clientes/${id}`),
    enabled: Boolean(id),
  })
}

export function useDeleteCliente(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch<void>(`/api/v1/clientes/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['clientes'] }),
  })
}

export function exportClienteUrl(clienteId: string): string {
  const base = process.env.NEXT_PUBLIC_API_URL ?? ''
  return `${base}/api/v1/clientes/${clienteId}/export`
}

// ----- Tecnicos -----
export function useTecnicos(filters: { ativo?: boolean } = {}) {
  const p = new URLSearchParams()
  if (filters.ativo !== undefined) p.set('ativo', String(filters.ativo))
  const qs = p.toString()
  return useQuery<CursorPage<TecnicoListItem>>({
    queryKey: ['tecnicos', filters],
    queryFn: () => apiFetch(`/api/v1/tecnicos${qs ? `?${qs}` : ''}`),
  })
}

export function useTecnico(id: string) {
  return useQuery<TecnicoOut>({
    queryKey: ['tecnico', id],
    queryFn: () => apiFetch(`/api/v1/tecnicos/${id}`),
    enabled: Boolean(id),
  })
}

export function useCreateTecnico() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: TecnicoCreate) =>
      apiFetch<TecnicoOut>('/api/v1/tecnicos', { method: 'POST', body: JSON.stringify(b) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tecnicos'] }),
  })
}

export function usePatchTecnico(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: TecnicoPatch) =>
      apiFetch<TecnicoOut>(`/api/v1/tecnicos/${id}`, { method: 'PATCH', body: JSON.stringify(b) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tecnico', id] })
      qc.invalidateQueries({ queryKey: ['tecnicos'] })
    },
  })
}

export function useDeleteTecnico(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch<void>(`/api/v1/tecnicos/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tecnicos'] }),
  })
}

export function useAddArea(tecnicoId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: AreaCreate) =>
      apiFetch<AreaOut>(`/api/v1/tecnicos/${tecnicoId}/areas`, {
        method: 'POST',
        body: JSON.stringify(b),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tecnico', tecnicoId] }),
  })
}

export function useRemoveArea(tecnicoId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (a: { cidade: string; rua: string }) =>
      apiFetch<void>(
        `/api/v1/tecnicos/${tecnicoId}/areas/${encodeURIComponent(a.cidade)}/${encodeURIComponent(a.rua)}`,
        { method: 'DELETE' },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tecnico', tecnicoId] }),
  })
}

export function useCreateTecnicoUser(tecnicoId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: TecnicoUserCreate) =>
      apiFetch<TecnicoUserOut>(`/api/v1/tecnicos/${tecnicoId}/user`, {
        method: 'POST',
        body: JSON.stringify(b),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tecnico', tecnicoId] }),
  })
}

export function useResetTecnicoUserPassword(tecnicoId: string) {
  return useMutation({
    mutationFn: (b: TecnicoUserResetPassword) =>
      apiFetch<void>(`/api/v1/tecnicos/${tecnicoId}/user/reset-password`, {
        method: 'POST',
        body: JSON.stringify(b),
      }),
  })
}

export function usePatchTecnicoUser(tecnicoId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: TecnicoUserPatch) =>
      apiFetch<TecnicoUserOut>(`/api/v1/tecnicos/${tecnicoId}/user`, {
        method: 'PATCH',
        body: JSON.stringify(b),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tecnico', tecnicoId] }),
  })
}

// ----- Manutencoes -----
export function useManutencoes(filters: { ativas?: boolean } = {}) {
  const p = new URLSearchParams()
  if (filters.ativas !== undefined) p.set('ativas', String(filters.ativas))
  const qs = p.toString()
  return useQuery<CursorPage<ManutencaoOut>>({
    queryKey: ['manutencoes', filters],
    queryFn: () => apiFetch(`/api/v1/manutencoes${qs ? `?${qs}` : ''}`),
  })
}
export function useManutencao(id: string) {
  return useQuery<ManutencaoOut>({
    queryKey: ['manutencao', id],
    queryFn: () => apiFetch(`/api/v1/manutencoes/${id}`),
    enabled: Boolean(id),
  })
}
export function useCreateManutencao() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: ManutencaoCreate) =>
      apiFetch<ManutencaoOut>('/api/v1/manutencoes', {
        method: 'POST',
        body: JSON.stringify(b),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['manutencoes'] }),
  })
}
export function usePatchManutencao(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: ManutencaoPatch) =>
      apiFetch<ManutencaoOut>(`/api/v1/manutencoes/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(b),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['manutencao', id] })
      qc.invalidateQueries({ queryKey: ['manutencoes'] })
    },
  })
}
export function useDeleteManutencao(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch<void>(`/api/v1/manutencoes/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['manutencoes'] }),
  })
}

// ----- Config -----
export function useConfigKey(key: string) {
  return useQuery<ConfigOut>({
    queryKey: ['config', key],
    queryFn: () => apiFetch(`/api/v1/config/${encodeURIComponent(key)}`),
    enabled: Boolean(key),
    retry: false,
  })
}
export function useSetConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: unknown }) =>
      apiFetch<ConfigOut>(`/api/v1/config/${encodeURIComponent(key)}`, {
        method: 'PUT',
        body: JSON.stringify({ value }),
      }),
    onSuccess: (_, vars) => qc.invalidateQueries({ queryKey: ['config', vars.key] }),
  })
}

// ----- Metricas -----
export function useMetricas() {
  return useQuery<MetricasOut>({
    queryKey: ['metricas'],
    queryFn: () => apiFetch('/api/v1/metricas'),
    refetchInterval: 30_000,
  })
}
