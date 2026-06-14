import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
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

/** Bolinha do sidebar: ha conversa em handoff humano aguardando? */
export function useTemConversaAguardando() {
  return useQuery<boolean>({
    queryKey: ['nav-badge', 'conversas-aguardando'],
    queryFn: async () => {
      const data = await apiFetch<CursorPage<ConversaListItem>>(
        '/api/v1/conversas?status=aguardando&limit=1',
      )
      return (data?.items?.length ?? 0) > 0
    },
    staleTime: 20_000,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
  })
}

/** Bolinha do sidebar: ha chamado do app cliente em aberto? */
export function useTemChamadoAberto() {
  return useQuery<boolean>({
    queryKey: ['nav-badge', 'chamados-aberto'],
    queryFn: async () => {
      const data = await apiFetch<{ counts_by_status?: Record<string, number> }>(
        '/api/v1/admin/cliente-app-os?status=aberto&limit=1',
      )
      return (data?.counts_by_status?.aberto ?? 0) > 0
    },
    staleTime: 20_000,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
  })
}

export function useCanais() {
  return useQuery<import('./types').CanalOut[]>({
    queryKey: ['canais'],
    queryFn: () => apiFetch('/api/v1/canais'),
    staleTime: 60_000,
  })
}

export function useCreateCanal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: import('./types').CanalCreate) =>
      apiFetch<import('./types').CanalOut>('/api/v1/canais', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['canais'] }),
  })
}

export function usePatchCanal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: import('./types').CanalUpdate }) =>
      apiFetch<import('./types').CanalOut>(`/api/v1/canais/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['canais'] }),
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
  categoria: string
  unidade: import('./types').EstoqueUnidade
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
  categoria?: string
  unidade?: import('./types').EstoqueUnidade
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
  unidade: import('./types').EstoqueUnidade
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

export interface DevolverIn {
  item_id: string
  tecnico_id: string
  quantidade: number
  serial?: string | null
  observacao?: string | null
}

export function useDevolver() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: DevolverIn) =>
      apiFetch('/api/v1/estoque/deposito/devolver', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['estoque-deposito-saldo'] })
      qc.invalidateQueries({ queryKey: ['estoque-tecnicos-saldos'] })
      qc.invalidateQueries({ queryKey: ['estoque-saldo'] })
      qc.invalidateQueries({ queryKey: ['estoque-movimentos'] })
      qc.invalidateQueries({ queryKey: ['estoque-seriais-ativos'] })
    },
  })
}

// ── Categorias ───────────────────────────────────────────────

export interface EstoqueCategoria {
  id: string
  slug: string
  nome: string
  ativo: boolean
  created_at: string
}

export interface CategoriaCreate {
  slug: string
  nome: string
  ativo?: boolean
}

export interface CategoriaUpdate {
  nome?: string
  ativo?: boolean
}

export function useEstoqueCategorias(ativosOnly = false) {
  return useQuery<EstoqueCategoria[]>({
    queryKey: ['estoque-categorias', ativosOnly],
    queryFn: () =>
      apiFetch(
        `/api/v1/estoque/categorias${ativosOnly ? '?ativos_only=true' : ''}`,
      ),
    staleTime: 30_000,
  })
}

export function useCreateCategoria() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CategoriaCreate) =>
      apiFetch<EstoqueCategoria>('/api/v1/estoque/categorias', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['estoque-categorias'] }),
  })
}

export function useUpdateCategoria() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: CategoriaUpdate }) =>
      apiFetch<EstoqueCategoria>(`/api/v1/estoque/categorias/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['estoque-categorias'] }),
  })
}

export function useDeleteCategoria() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/v1/estoque/categorias/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['estoque-categorias'] }),
  })
}

export interface TecnicoSaldoResumo {
  tecnico_id: string
  tecnico_nome: string
  item_id: string
  sku: string
  nome: string
  categoria: string
  unidade: import('./types').EstoqueUnidade
  saldo: number
}

export function useTecnicosSaldos() {
  return useQuery<{ linhas: TecnicoSaldoResumo[] }>({
    queryKey: ['estoque-tecnicos-saldos'],
    queryFn: () => apiFetch('/api/v1/estoque/tecnicos/saldos'),
  })
}

export interface SerialAtivo {
  item_id: string
  serial: string
  tecnico_id: string | null
  desde: string
}

export function useSeriaisAtivos() {
  return useQuery<{ linhas: SerialAtivo[] }>({
    queryKey: ['estoque-seriais-ativos'],
    queryFn: () => apiFetch('/api/v1/estoque/seriais'),
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

export function useConversa(
  id: string,
  opts?: { refetchInterval?: number | false },
) {
  return useQuery<ConversaDetail>({
    queryKey: ['conversa', id],
    queryFn: () => apiFetch(`/api/v1/conversas/${id}`),
    enabled: Boolean(id),
    refetchInterval: opts?.refetchInterval ?? false,
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
    onError: (err) =>
      toast.error(
        err instanceof Error ? `Falha ao enviar: ${err.message}` : 'Falha ao enviar mensagem',
      ),
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
    onError: (err) =>
      toast.error(
        err instanceof Error ? `Falha ao assumir conversa: ${err.message}` : 'Falha ao assumir conversa',
      ),
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
    onError: (err) =>
      toast.error(
        err instanceof Error ? `Falha ao encerrar: ${err.message}` : 'Falha ao encerrar',
      ),
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
    onError: (err) =>
      toast.error(
        err instanceof Error ? `Falha ao excluir: ${err.message}` : 'Falha ao excluir',
      ),
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

export function useOsConsumo(id: string) {
  return useQuery<import('./types').OsConsumoOut>({
    queryKey: ['os-consumo', id],
    queryFn: () => apiFetch(`/api/v1/os/${id}/consumo`),
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

// ════════ Cliente App Chat (admin) ════════

export function useClienteAppChatThread(userId: string | null) {
  return useQuery<import('./types').ClienteAppChatThread>({
    queryKey: ['cliente-app-chat', userId],
    enabled: !!userId,
    queryFn: () => apiFetch(`/api/v1/admin/cliente-app-chat/${userId}`),
    refetchInterval: 5000, // polling 5s
  })
}

export function useClienteAppChatSend(userId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (text: string) =>
      apiFetch<import('./types').ClienteAppChatMessage>(
        `/api/v1/admin/cliente-app-chat/${userId}/send`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text }),
        },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cliente-app-chat', userId] })
    },
  })
}

export function useClienteAppChatTake(userId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<import('./types').ClienteAppChatThread>(
        `/api/v1/admin/cliente-app-chat/${userId}/take`,
        { method: 'POST' },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cliente-app-chat', userId] })
    },
  })
}

export function useClienteAppChatRelease(userId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<import('./types').ClienteAppChatThread>(
        `/api/v1/admin/cliente-app-chat/${userId}/release`,
        { method: 'POST' },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cliente-app-chat', userId] })
    },
  })
}

// ════════ Promoções (admin) ════════

export function usePromocoesAdmin() {
  return useQuery<import('./types').PromocaoAdmin[]>({
    queryKey: ['promocoes-admin'],
    queryFn: () => apiFetch('/api/v1/admin/promocoes'),
  })
}

export function useCreatePromocao() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: import('./types').PromocaoCreate) =>
      apiFetch<import('./types').PromocaoAdmin>('/api/v1/admin/promocoes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['promocoes-admin'] }),
  })
}

export function usePatchPromocao(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (patch: import('./types').PromocaoPatch) =>
      apiFetch<import('./types').PromocaoAdmin>(`/api/v1/admin/promocoes/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['promocoes-admin'] }),
  })
}

export function useDeletePromocao() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/admin/promocoes/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['promocoes-admin'] }),
  })
}

export function useSeedPromocoesTemplates() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<import('./types').PromocaoAdmin[]>(
        '/api/v1/admin/promocoes/seed-templates',
        { method: 'POST' },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['promocoes-admin'] }),
  })
}

export function useReorderPromocoes() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ids: string[]) =>
      apiFetch<import('./types').PromocaoAdmin[]>(
        '/api/v1/admin/promocoes/reorder',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids }),
        },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['promocoes-admin'] }),
  })
}

export function useIndicacoesStats() {
  return useQuery<{
    shares_app: number
    leads_whatsapp: number
    convertidos: number
  }>({
    queryKey: ['indicacoes-stats'],
    queryFn: () => apiFetch('/api/v1/indicacoes/stats'),
  })
}

export function usePromocaoIndicacaoAtiva() {
  return useQuery<import('./types').PromocaoAdmin | null>({
    queryKey: ['promocao-indicacao-ativa'],
    queryFn: async () => {
      const all = await apiFetch<import('./types').PromocaoAdmin[]>(
        '/api/v1/admin/promocoes',
      )
      return all.find((p) => p.tipo === 'indicacao' && p.ativa) ?? null
    },
  })
}

export function useUploadPromocaoImagem(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      const token = await getAccessToken()
      const r = await fetch(`/api/v1/admin/promocoes/${id}/imagem`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: fd,
        credentials: 'include',
      })
      if (!r.ok) {
        const msg = await r.text().catch(() => 'erro upload')
        throw new Error(msg || `upload ${r.status}`)
      }
      return (await r.json()) as import('./types').PromocaoAdmin
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['promocoes-admin'] }),
  })
}

export function usePromocaoLeads(filtros?: {
  promocaoId?: string
  status?: import('./types').PromocaoLeadStatus
}) {
  const params = new URLSearchParams()
  if (filtros?.promocaoId) params.set('promocao_id', filtros.promocaoId)
  if (filtros?.status) params.set('status_filtro', filtros.status)
  const qs = params.toString()
  return useQuery<import('./types').PromocaoLeadAdmin[]>({
    queryKey: ['promocoes-leads', filtros?.promocaoId ?? '', filtros?.status ?? ''],
    queryFn: () => apiFetch(`/api/v1/admin/promocoes/leads${qs ? `?${qs}` : ''}`),
  })
}

export function usePatchPromocaoLead(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (patch: { status: import('./types').PromocaoLeadStatus }) =>
      apiFetch<import('./types').PromocaoLeadAdmin>(
        `/api/v1/admin/promocoes/leads/${id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch),
        },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['promocoes-leads'] })
      qc.invalidateQueries({ queryKey: ['promocoes-admin'] })
    },
  })
}

// ════════ Cliente App Contatos da Operadora (admin) ════════

export function useContatosOperadora() {
  return useQuery<import('./types').AdminContatoOperadora[]>({
    queryKey: ['contatos-operadora'],
    queryFn: () => apiFetch(`/api/v1/admin/cliente-app-contatos`),
  })
}

export function useCreateContatoOperadora() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: import('./types').ContatoOperadoraIn) =>
      apiFetch<import('./types').AdminContatoOperadora>(
        `/api/v1/admin/cliente-app-contatos`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['contatos-operadora'] }),
  })
}

export function usePatchContatoOperadora(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (patch: import('./types').ContatoOperadoraPatch) =>
      apiFetch<import('./types').AdminContatoOperadora>(
        `/api/v1/admin/cliente-app-contatos/${id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch),
        },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['contatos-operadora'] }),
  })
}

export function useDeleteContatoOperadora() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/admin/cliente-app-contatos/${id}`, {
        method: 'DELETE',
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['contatos-operadora'] }),
  })
}

// ════════ Cliente App Cards do Dia (admin) ════════

export function useCardsDia() {
  return useQuery<import('./types').AdminCardDia[]>({
    queryKey: ['cliente-app-cards-dia'],
    queryFn: () => apiFetch(`/api/v1/admin/cliente-app-cards-dia`),
  })
}

export function useCreateCardDia() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: import('./types').CardDiaIn) =>
      apiFetch<import('./types').AdminCardDia>(
        `/api/v1/admin/cliente-app-cards-dia`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cliente-app-cards-dia'] }),
  })
}

export function usePatchCardDia(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (patch: import('./types').CardDiaPatch) =>
      apiFetch<import('./types').AdminCardDia>(
        `/api/v1/admin/cliente-app-cards-dia/${id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch),
        },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cliente-app-cards-dia'] }),
  })
}

export function useDeleteCardDia() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/admin/cliente-app-cards-dia/${id}`, {
        method: 'DELETE',
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cliente-app-cards-dia'] }),
  })
}

// ════════ Cliente App Fidelidade (admin) ════════

export function useFidelidadeResgates() {
  return useQuery<import('./types').AdminFidelidadeResgate[]>({
    queryKey: ['fidelidade-resgates'],
    queryFn: () => apiFetch(`/api/v1/admin/cliente-app-fidelidade`),
  })
}

export function usePatchFidelidadeResgate(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (patch: import('./types').FidelidadeResgatePatch) =>
      apiFetch<import('./types').AdminFidelidadeResgate>(
        `/api/v1/admin/cliente-app-fidelidade/${id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch),
        },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['fidelidade-resgates'] }),
  })
}

/** OTP métricas (Cloud vs Evolution) — Fase 2.3 do plano de evolução. */
export function useOtpMetricas() {
  return useQuery<import('./types').OtpMetricasOut>({
    queryKey: ['otp-metricas'],
    queryFn: () => apiFetch('/api/v1/admin/otp-metricas'),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}

/** Métricas de templates WhatsApp (entrega/leitura/falha) — Fase 2.2 do plano. */
export function useWhatsAppMetricas(days: number = 7) {
  return useQuery<import('./types').WhatsAppMetricasOut>({
    queryKey: ['whatsapp-metricas', days],
    queryFn: () => apiFetch(`/api/v1/admin/whatsapp-metricas?days=${days}`),
    staleTime: 60_000,
    refetchInterval: 120_000,
  })
}

// ════════ Rede WiFi (GenieACS) — por conversa ════════

export function useRedeStatusConversa(conversaId: string, enabled: boolean) {
  return useQuery<import('./types').RedeStatus>({
    queryKey: ['rede-status', conversaId],
    queryFn: () => apiFetch(`/api/v1/conversas/${conversaId}/rede/status`),
    enabled,
    staleTime: 30_000,
  })
}

export function useRedeDiagnostico(conversaId: string, enabled: boolean) {
  return useQuery<import('./types').RedeDiagnostico>({
    queryKey: ['rede-diagnostico', conversaId],
    queryFn: () => apiFetch(`/api/v1/conversas/${conversaId}/rede/diagnostico`),
    enabled,
    staleTime: 30_000,
  })
}

export function useTrocarSenhaConversa(conversaId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (senha: string) =>
      apiFetch<import('./types').TrocarSenhaResult>(
        `/api/v1/conversas/${conversaId}/rede/wifi/senha`,
        { method: 'POST', body: JSON.stringify({ senha }) },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rede-diagnostico', conversaId] })
      qc.invalidateQueries({ queryKey: ['rede-status', conversaId] })
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : 'Falha ao trocar a senha'),
  })
}

export function useReiniciarOnu(conversaId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<import('./types').RebootResult>(
        `/api/v1/conversas/${conversaId}/rede/reboot`,
        { method: 'POST' },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rede-status', conversaId] }),
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : 'Falha ao reiniciar'),
  })
}

// ════════ Comunicados (campanhas broadcast) ════════

export function useBroadcastTemplates() {
  return useQuery<import('./types').BroadcastTemplate[]>({
    queryKey: ['broadcast-templates'],
    queryFn: () => apiFetch('/api/v1/admin/comunicados/templates'),
    staleTime: 300_000,
  })
}

export function useCampanhas() {
  return useQuery<import('./types').CampanhaListItem[]>({
    queryKey: ['campanhas'],
    queryFn: () => apiFetch('/api/v1/admin/comunicados'),
  })
}

export function useCampanha(id: string) {
  return useQuery<import('./types').CampanhaDetail>({
    queryKey: ['campanha', id],
    queryFn: () => apiFetch(`/api/v1/admin/comunicados/${id}`),
    enabled: Boolean(id),
    refetchInterval: (query) =>
      query.state.data?.status === 'enviando' ? 3000 : false,
  })
}

export function useCreateCampanha() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: import('./types').CampanhaCreate) =>
      apiFetch<import('./types').CampanhaListItem>('/api/v1/admin/comunicados', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campanhas'] }),
  })
}

export function usePreviewSegmento() {
  return useMutation({
    mutationFn: (filtros: import('./types').SegmentoFiltros) =>
      apiFetch<import('./types').PreviewResult>('/api/v1/admin/comunicados/preview', {
        method: 'POST',
        body: JSON.stringify(filtros),
      }),
  })
}

export function useSendCampanha() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<{ status: string }>(`/api/v1/admin/comunicados/${id}/send`, {
        method: 'POST',
      }),
    onSuccess: (_d, id) => {
      qc.invalidateQueries({ queryKey: ['campanhas'] })
      qc.invalidateQueries({ queryKey: ['campanha', id] })
    },
  })
}

export function useTestCampanha(id: string) {
  return useMutation({
    mutationFn: (whatsapp: string) =>
      apiFetch<{ status: string }>(`/api/v1/admin/comunicados/${id}/test`, {
        method: 'POST',
        body: JSON.stringify({ whatsapp }),
      }),
  })
}

export function exportClientesUrl(f: import('./types').SegmentoFiltros, fmt: 'csv' | 'xlsx') {
  const p = new URLSearchParams()
  if (f.cidade) p.set('cidade', f.cidade)
  if (f.status) p.set('status', f.status)
  if (f.plano) p.set('plano', f.plano)
  p.set('format', fmt)
  return `/api/v1/admin/comunicados/export/clientes?${p.toString()}`
}

export function useSegmentoValores() {
  return useQuery<import('./types').SegmentoValores>({
    queryKey: ['comunicados-valores'],
    queryFn: () => apiFetch('/api/v1/admin/comunicados/segmento/valores'),
    staleTime: 300_000,
  })
}

export function useSyncTemplates() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<{ sincronizados: number; canais: number }>(
        '/api/v1/admin/comunicados/templates/sincronizar',
        { method: 'POST' },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['broadcast-templates'] }),
  })
}

export function useImportDestinatarios(campanhaId: string) {
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      const base = process.env.NEXT_PUBLIC_API_URL ?? ''
      const res = await fetch(
        `${base}/api/v1/admin/comunicados/${campanhaId}/destinatarios/importar`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getAccessToken() ?? ''}` },
          credentials: 'include',
          body: fd,
        },
      )
      if (!res.ok) throw new Error('Falha ao importar CSV')
      return (await res.json()) as import('./types').ImportResult
    },
  })
}
