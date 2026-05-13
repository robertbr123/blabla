import { apiFetch } from './api/client'

/** Shape returned by the backend /auth/me endpoint. */
export interface MeOut {
  user_id: string
  email: string
  name: string
  role: 'admin' | 'atendente' | 'tecnico'
  is_active: boolean
}

/** Shape returned by the backend /auth/login endpoint. */
export interface LoginOut {
  access_token: string
  token_type: string
  user_id: string
  role: string
}

export async function login(email: string, password: string): Promise<LoginOut> {
  return apiFetch<LoginOut>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function logout(): Promise<void> {
  await apiFetch<void>('/auth/logout', { method: 'POST' })
}

export async function getMe(): Promise<MeOut | null> {
  try {
    return await apiFetch<MeOut>('/auth/me')
  } catch {
    return null
  }
}

/** Server-side getMe helper. Reads cookies from the incoming request. */
export async function getMeServer(): Promise<MeOut | null> {
  const { cookies } = await import('next/headers')
  const c = await cookies()
  const all = c
    .getAll()
    .map(({ name, value }) => `${name}=${value}`)
    .join('; ')
  if (!all) return null
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
  try {
    const res = await fetch(`${apiUrl}/auth/me`, {
      headers: { cookie: all },
      cache: 'no-store',
    })
    if (!res.ok) return null
    return (await res.json()) as MeOut
  } catch {
    return null
  }
}
