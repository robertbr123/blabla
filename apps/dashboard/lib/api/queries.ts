import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query'
import { apiFetch } from './client'
import { getAccessToken } from '@/lib/api/token'
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
  PlanoIn,
  PlanoOut,
  RankingTecnicoOut,
  SgpClienteOut,
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
  canal_id?: string
}

export function useConversas(filters: ConversaListFilters = {}) {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.q) params.set('q', filters.q)
  if (filters.canal_id) params.set('canal_id', filters.canal_id)
  const qs = params.toString()
  return useQuery<CursorPage<ConversaListItem>>({
    queryKey: ['conversas', filters],
    queryFn: () => apiFetch(`/api/v1/conversas${qs ? `?${qs}` : ''}`),
    refetchInterval: 15_000,
  })
}

export function useCanais() {
  return useQuery<import('./types').CanalOut[]>({
    queryKey: ['canais'],
    queryFn: () => apiFetch('/api/v1/canais'),
    staleTime: 60_000,
  })
}

// F6 — Estoque
export function useEstoqueItens(ativosOnly = false) {
  return useQuery<import('./types').EstoqueItem[]>({
    queryKey: ['estoque-itens', ativosOnly],
    queryFn: () => apiFetch(`/api/v1/estoque/itens${ativosOnly ? '?ativos_only=true' : ''}`),
    staleTime: 30_000,
  })
}

export function useEstoqueSaldo(tecnicoId: string | null) {
  return useQuery<import('./types').EstoqueSaldo>({
    queryKey: ['estoque-saldo', tecnicoId],
    queryFn: () => apiFetch(`/api/v1/estoque/saldo?tecnico_id=${tecnicoId}`),
    enabled: !!tecnicoId,
  })
}

export interface EstoqueItemCreate {
  sku: string
  nome: string
  categoria: 'onu' | 'roteador' | 'cabo' | 'conector' | 'outro'
  serializado: boolean
  ativo: boolean
}

export function useCreateEstoqueItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: EstoqueItemCreate) =>
      apiFetch<import('./types').EstoqueItem>('/api/v1/estoque/itens', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['estoque-itens'] }),
  })
}

export interface EstoqueItemUpdate {
  nome?: string
  categoria?: 'onu' | 'roteador' | 'cabo' | 'conector' | 'outro'
  ativo?: boolean
}

export function useUpdateEstoqueItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: EstoqueItemUpdate }) =>
      apiFetch<import('./types').EstoqueItem>(`/api/v1/estoque/itens/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['estoque-itens'] }),
  })
}

export function useDeleteEstoqueItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/v1/estoque/itens/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['estoque-itens'] }),
  })
}

export interface EstoqueMovimentoCreate {
  item_id: string
  tipo: 'entrada' | 'saida' | 'recolhido' | 'devolucao' | 'perda' | 'ajuste_positivo' | 'ajuste_negativo'
  quantidade: number
  tecnico_id?: string | null
  serial?: string | null
  ordem_servico_id?: string | null
  observacao?: string | null
}

export function useCreateEstoqueMovimento() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: EstoqueMovimentoCreate) =>
      apiFetch<import('./types').EstoqueMovimento>('/api/v1/estoque/movimentos', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['estoque-saldo'] })
      qc.invalidateQueries({ queryKey: ['estoque-movimentos'] })
    },
  })
}

// ── Depósito (estoque central) ─────────────────────────────────

export interface SaldoLinha {
  item_id: string
  sku: string
  nome: string
  categoria: string
  serializado: boolean
  saldo: number
}

export function useDepositoSaldo() {
  return useQuery<{ linhas: SaldoLinha[] }>({
    queryKey: ['estoque-deposito-saldo'],
    queryFn: () => apiFetch('/api/v1/estoque/deposito/saldo'),
  })
}

export interface DepositoEntradaIn {
  item_id: string
  quantidade: number
  serial?: string | null
  observacao?: string | null
}

export function useDepositoEntrada() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: DepositoEntradaIn) =>
      apiFetch('/api/v1/estoque/deposito/entrada', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['estoque-deposito-saldo'] })
      qc.invalidateQueries({ queryKey: ['estoque-movimentos'] })
    },
  })
}

export interface DepositoBaixaIn {
  item_id: string
  quantidade: number
  tipo: 'perda' | 'ajuste_negativo'
  serial?: string | null
  observacao?: string | null
}

export function useDepositoBaixa() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: DepositoBaixaIn) =>
      apiFetch('/api/v1/estoque/deposito/baixa', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['estoque-deposito-saldo'] })
      qc.invalidateQueries({ queryKey: ['estoque-movimentos'] })
    },
  })
}

export interface TransferirIn {
  item_id: string
  tecnico_id: string
  quantidade: number
  serial?: string | null
  observacao?: string | null
}

export function useTransferir() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: TransferirIn) =>
      apiFetch('/api/v1/estoque/deposito/transferir', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['estoque-deposito-saldo'] })
      qc.invalidateQueries({ queryKey: ['estoque-tecnicos-saldos'] })
      qc.invalidateQueries({ queryKey: ['estoque-saldo'] })
      qc.invalidateQueries({ queryKey: ['estoque-movimentos'] })
    },
  })
}

export interface TecnicoSaldoResumo {
  tecnico_id: string
  tecnico_nome: string
  item_id: string
  sku: string
  nome: string
  categoria: string
  saldo: number
}

export function useTecnicosSaldos() {
  return useQuery<{ linhas: TecnicoSaldoResumo[] }>({
    queryKey: ['estoque-tecnicos-saldos'],
    queryFn: () => apiFetch('/api/v1/estoque/tecnicos/saldos'),
  })
}

export function useEstoqueMovimentos(filters: { tecnico_id?: string; item_id?: string; limit?: number } = {}) {
  const params = new URLSearchParams()
  if (filters.tecnico_id) params.set('tecnico_id', filters.tecnico_id)
  if (filters.item_id) params.set('item_id', filters.item_id)
  if (filters.limit) params.set('limit', String(filters.limit))
  const qs = params.toString()
  return useQuery<import('./types').EstoqueMovimento[]>({
    queryKey: ['estoque-movimentos', filters],
    queryFn: () => apiFetch(`/api/v1/estoque/movimentos${qs ? `?${qs}` : ''}`),
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

export function useEnviarMidia(conversaId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ file, caption }: { file: File; caption: string }) => {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('caption', caption)
      const token = getAccessToken()
      const res = await fetch(`/api/v1/conversas/${conversaId}/enviar-midia`, {
        method: 'POST',
        body: fd,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: 'include',
      })
      if (!res.ok) {
        const txt = await res.text().catch(() => '')
        throw new Error(txt || `HTTP ${res.status}`)
      }
      return res.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['conversa', conversaId] }),
  })
}

export function useVincularCliente(conversaId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (cpf: string) =>
      apiFetch(`/api/v1/conversas/${conversaId}/vincular-cliente`, {
        method: 'POST',
        body: JSON.stringify({ cpf }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conversa', conversaId] })
      qc.invalidateQueries({ queryKey: ['conversas'] })
    },
  })
}

export function useDeleteConversa(conversaId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<void>(`/api/v1/conversas/${conversaId}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conversas'] })
    },
  })
}

export function useSgpLookup() {
  return useMutation({
    mutationFn: (cpf: string) =>
      apiFetch<SgpClienteOut>(`/api/v1/clientes/sgp?cpf=${encodeURIComponent(cpf)}`),
  })
}

// ── OS ──────────────────────────────────────────────────────────────────────

export interface OsListFilters {
  status?: string
  tecnico?: string
  cliente_id?: string
  enabled?: boolean
}

export function useOsList(filters: OsListFilters = {}) {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.tecnico) params.set('tecnico', filters.tecnico)
  if (filters.cliente_id) params.set('cliente_id', filters.cliente_id)
  const qs = params.toString()
  // Quando cliente_id eh passado como undefined/null explicitamente
  // (ex.: conversa sem cliente vinculado), tratamos como "nao buscar".
  // `enabled: false` permite override manual.
  const hasClienteFilter = 'cliente_id' in filters
  const enabled =
    filters.enabled === false
      ? false
      : hasClienteFilter
        ? Boolean(filters.cliente_id)
        : true
  return useQuery<CursorPage<OsListItem>>({
    queryKey: ['os', filters],
    queryFn: () => apiFetch(`/api/v1/os${qs ? `?${qs}` : ''}`),
    refetchInterval: 30_000,
    enabled,
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

export function useReabrirOs(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (motivo: string) =>
      apiFetch<OsOut>(`/api/v1/os/${id}/reabrir`, {
        method: 'POST',
        body: JSON.stringify({ motivo }),
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

export function useTimeseries(days: number) {
  return useQuery<import('./types').TimeseriesOut>({
    queryKey: ['metricas', 'timeseries', days],
    queryFn: () => apiFetch(`/api/v1/metricas/timeseries?days=${days}`),
  })
}

export async function downloadTimeseriesCsv(days: number): Promise<void> {
  const token = getAccessToken()
  const res = await fetch(`/api/v1/metricas/timeseries/export?days=${days}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    credentials: 'include',
  })
  if (!res.ok) throw new Error('Erro ao exportar CSV')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `timeseries-${days}d-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
}

// ── Ranking de Técnicos ─────────────────────────────────────────────

export function useRankingTecnicos(mes?: string) {
  const qs = mes ? `?mes=${mes}` : ''
  return useQuery<RankingTecnicoOut[]>({
    queryKey: ['ranking-tecnicos', mes],
    queryFn: () => apiFetch(`/api/v1/metricas/tecnicos${qs}`),
  })
}

export async function downloadRankingCsv(mes?: string): Promise<void> {
  const qs = mes ? `?mes=${mes}` : ''
  const token = getAccessToken()
  const res = await fetch(`/api/v1/metricas/tecnicos/export${qs}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    credentials: 'include',
  })
  if (!res.ok) throw new Error('Erro ao exportar CSV')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `ranking-tecnicos-${mes ?? new Date().toISOString().slice(0, 7)}.csv`
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
}

// ── Planos ──────────────────────────────────────────────────────────

export function usePlanos() {
  return useQuery<PlanoOut[]>({
    queryKey: ['planos'],
    queryFn: () => apiFetch('/api/v1/planos'),
  })
}

export function useCreatePlano() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: PlanoIn) =>
      apiFetch<PlanoOut>('/api/v1/planos', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['planos'] }),
  })
}

export function useUpdatePlano(index: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: PlanoIn) =>
      apiFetch<PlanoOut>(`/api/v1/planos/${index}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['planos'] }),
  })
}

export function useDeletePlano() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (index: number) =>
      apiFetch<void>(`/api/v1/planos/${index}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['planos'] }),
  })
}

// F8 — Equipamentos do cliente
export function useClienteEquipamentos(clienteId: string, ativosOnly = false) {
  const qs = ativosOnly ? '?ativos_only=true' : ''
  return useQuery<import('./types').ClienteEquipamentoOut[]>({
    queryKey: ['cliente-equipamentos', clienteId, ativosOnly],
    queryFn: () => apiFetch(`/api/v1/clientes/${clienteId}/equipamentos${qs}`),
    enabled: !!clienteId,
  })
}

// F9 — Produtividade
export function useProdutividade(mes?: string) {
  const qs = mes ? `?mes=${mes}` : ''
  return useQuery<import('./types').ProdutividadeResponse>({
    queryKey: ['produtividade', mes ?? 'current'],
    queryFn: () => apiFetch(`/api/v1/metricas/tecnicos/produtividade${qs}`),
  })
}

// F10 — Indicacoes
export function useIndicacoes() {
  return useQuery<import('./types').IndicacaoOut[]>({
    queryKey: ['indicacoes'],
    queryFn: () => apiFetch('/api/v1/indicacoes'),
  })
}

export function useIndicacaoUsos() {
  return useQuery<import('./types').IndicacaoUsoOut[]>({
    queryKey: ['indicacao-usos'],
    queryFn: () => apiFetch('/api/v1/indicacoes/usos'),
  })
}

export function useRankingIndicadores() {
  return useQuery<import('./types').RankingIndicadorOut[]>({
    queryKey: ['ranking-indicadores'],
    queryFn: () => apiFetch('/api/v1/indicacoes/ranking'),
  })
}

export function useMarcarConvertido() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ usoId, observacao, cliente_indicado_id }: { usoId: string; observacao?: string; cliente_indicado_id?: string }) =>
      apiFetch<import('./types').IndicacaoUsoOut>(`/api/v1/indicacoes/usos/${usoId}/converter`, {
        method: 'POST',
        body: JSON.stringify({ observacao, cliente_indicado_id }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['indicacao-usos'] })
      qc.invalidateQueries({ queryKey: ['ranking-indicadores'] })
    },
  })
}

export function useMarcarCredito() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ usoId, observacao }: { usoId: string; observacao?: string }) =>
      apiFetch<import('./types').IndicacaoUsoOut>(`/api/v1/indicacoes/usos/${usoId}/credito`, {
        method: 'POST',
        body: JSON.stringify({ observacao }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['indicacao-usos'] }),
  })
}

// F11 — Cliente: dados frescos do SGP (plano, valor próxima fatura, atraso)
export function useClienteSgpInfo(cpf: string | null) {
  return useQuery<SgpClienteOut>({
    queryKey: ['cliente-sgp-info', cpf],
    queryFn: () =>
      apiFetch<SgpClienteOut>(`/api/v1/clientes/sgp?cpf=${encodeURIComponent(cpf ?? '')}`),
    enabled: !!cpf,
    staleTime: 60_000,
    retry: false,
  })
}

// ── Clientes cadastrados em campo (Fase 10) ───────────────────

export interface ClientesCampoFilter {
  q?: string
  city?: string
  sgp_status?: 'synced' | 'pending'
  cursor?: string
}

export function useClientesCampo(filter: ClientesCampoFilter = {}) {
  const params = new URLSearchParams()
  if (filter.q) params.set('q', filter.q)
  if (filter.city) params.set('city', filter.city)
  if (filter.sgp_status) params.set('sgp_status', filter.sgp_status)
  params.set('limit', '50')
  if (filter.cursor) params.set('cursor', filter.cursor)
  const qs = params.toString()
  return useQuery<import('./types').CursorPage<import('./types').ClienteCampoListItem>>({
    queryKey: ['clientes-campo', filter],
    queryFn: () => apiFetch(`/api/v1/clientes-campo?${qs}`),
    placeholderData: (prev) => prev,  // segura UI ao mudar página
  })
}

export function useClientesCampoStats() {
  return useQuery<{ total: number; synced: number; pending: number }>({
    queryKey: ['clientes-campo-stats'],
    queryFn: () => apiFetch('/api/v1/clientes-campo/stats'),
  })
}

export function useClienteCampoDetail(id: string | null) {
  return useQuery<import('./types').ClienteCampoOut>({
    queryKey: ['cliente-campo', id],
    queryFn: () => apiFetch(`/api/v1/clientes-campo/${id}`),
    enabled: !!id,
  })
}

export function useMarcarSyncSgp() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, sgp_id }: { id: string; sgp_id: string }) =>
      apiFetch<import('./types').ClienteCampoOut>(
        `/api/v1/clientes-campo/${id}/sync-sgp`,
        {
          method: 'POST',
          body: JSON.stringify({ sgp_id }),
        },
      ),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['clientes-campo'] })
      qc.invalidateQueries({ queryKey: ['clientes-campo-stats'] })
      qc.invalidateQueries({ queryKey: ['cliente-campo', vars.id] })
    },
  })
}

export function usePatchClienteCampo(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (patch: Partial<import('./types').ClienteCampoOut>) =>
      apiFetch<import('./types').ClienteCampoOut>(
        `/api/v1/clientes-campo/${id}`,
        {
          method: 'PATCH',
          body: JSON.stringify(patch),
        },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clientes-campo'] })
      qc.invalidateQueries({ queryKey: ['clientes-campo-stats'] })
      qc.invalidateQueries({ queryKey: ['cliente-campo', id] })
    },
  })
}

export function useDeleteClienteCampo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/v1/clientes-campo/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clientes-campo'] })
      qc.invalidateQueries({ queryKey: ['clientes-campo-stats'] })
    },
  })
}

export interface ImportCsvOptions {
  file: File
  dryRun: boolean
  markAsSynced: boolean
}

export function useImportClientesCsv() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (opts: ImportCsvOptions) => {
      const fd = new FormData()
      fd.append('file', opts.file)
      fd.append('dry_run', String(opts.dryRun))
      fd.append('mark_as_synced', String(opts.markAsSynced))
      const token = getAccessToken()
      const res = await fetch(`/api/v1/clientes-campo/import/csv`, {
        method: 'POST',
        body: fd,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: 'include',
      })
      if (!res.ok) {
        const txt = await res.text().catch(() => '')
        throw new Error(txt || `HTTP ${res.status}`)
      }
      return (await res.json()) as import('./types').ImportResultOut
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clientes-campo'] })
      qc.invalidateQueries({ queryKey: ['clientes-campo-stats'] })
    },
  })
}

// ════════ Cliente App OS (admin) ════════

export interface ClienteAppOsFilter {
  status?: import('./types').ClienteAppOsAdminItem['status']
  tipo?: import('./types').ClienteAppOsAdminItem['tipo']
  limit?: number
  offset?: number
}

export function useClienteAppOsList(filter: ClienteAppOsFilter = {}) {
  const qs = new URLSearchParams()
  if (filter.status) qs.set('status', filter.status)
  if (filter.tipo) qs.set('tipo', filter.tipo)
  if (filter.limit) qs.set('limit', String(filter.limit))
  if (filter.offset) qs.set('offset', String(filter.offset))
  return useQuery<import('./types').ClienteAppOsAdminList>({
    queryKey: ['cliente-app-os', filter],
    queryFn: () => apiFetch(`/api/v1/admin/cliente-app-os?${qs}`),
    refetchInterval: 30000, // pega novas a cada 30s
  })
}

export function useClienteAppOsDetail(id: string | null) {
  return useQuery<import('./types').ClienteAppOsAdminItem>({
    queryKey: ['cliente-app-os', 'detail', id],
    enabled: !!id,
    queryFn: () => apiFetch(`/api/v1/admin/cliente-app-os/${id}`),
  })
}

export function usePatchClienteAppOs(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (patch: import('./types').ClienteAppOsPatch) =>
      apiFetch<import('./types').ClienteAppOsAdminItem>(
        `/api/v1/admin/cliente-app-os/${id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch),
        },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cliente-app-os'] })
    },
  })
}
