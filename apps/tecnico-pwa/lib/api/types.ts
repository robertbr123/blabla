export type CursorPage<T> = { items: T[]; next_cursor: string | null }
export interface MeOut { user_id: string; email: string; role: 'admin' | 'atendente' | 'tecnico'; name: string }
