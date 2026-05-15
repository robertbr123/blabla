export type CursorPage<T> = { items: T[]; next_cursor: string | null }
export interface MeOut { user_id: string; email: string; role: 'admin' | 'atendente' | 'tecnico'; name: string }

export interface OsListItem {
  id: string
  codigo: string
  cliente_id: string
  tecnico_id: string | null
  status: string
  problema: string
  endereco: string
  plano: string | null
  agendamento_at: string | null
  criada_em: string
  concluida_em: string | null
}

export interface OsFoto {
  url: string
  ts: string
  size: number
  mime: string
}

export interface OsOut extends OsListItem {
  fotos: OsFoto[] | null
  csat: number | null
  comentario_cliente: string | null
  pppoe_login: string | null
  pppoe_senha: string | null
  relatorio: string | null
  houve_visita: boolean | null
  materiais: string | null
}

export interface IniciarIn {
  lat?: number | null
  lng?: number | null
}

export interface ConcluirIn {
  csat?: number | null
  comentario?: string | null
  relatorio?: string | null
  houve_visita?: boolean
  materiais?: string | null
  lat?: number | null
  lng?: number | null
}

export interface GpsUpdate {
  lat: number
  lng: number
}
