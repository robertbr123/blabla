import { apiFetch } from './api/client'
import { setAccessToken } from './api/token'

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
  const out = await apiFetch<LoginOut>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  setAccessToken(out.access_token)
  return out
}

export async function logout(): Promise<void> {
  try {
    await apiFetch<void>('/auth/logout', { method: 'POST' })
  } finally {
    setAccessToken(null)
  }
}

export async function getMe(): Promise<MeOut | null> {
  try {
    return await apiFetch<MeOut>('/auth/me')
  } catch {
    return null
  }
}

/** Server-side getMe helper. Two-hop because /auth/me needs Bearer:
 *   refresh (cookie -> access_token), then /auth/me (Bearer -> MeOut).
 */
export async function getMeServer(): Promise<MeOut | null> {
  const { cookies } = await import('next/headers')
  const c = await cookies()
  const all = c
    .getAll()
    .map(({ name, value }) => `${name}=${value}`)
    .join('; ')
  if (!all) return null
  const apiUrl =
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://127.0.0.1:8000'
  try {
    const refreshRes = await fetch(`${apiUrl}/auth/refresh`, {
      method: 'POST',
      headers: { cookie: all },
      cache: 'no-store',
    })
    if (!refreshRes.ok) return null
    const { access_token } = (await refreshRes.json()) as { access_token: string }
    const meRes = await fetch(`${apiUrl}/auth/me`, {
      headers: { Authorization: `Bearer ${access_token}` },
      cache: 'no-store',
    })
    if (!meRes.ok) return null
    return (await meRes.json()) as MeOut
  } catch {
    return null
  }
}
