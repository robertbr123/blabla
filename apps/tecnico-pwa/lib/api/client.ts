import { getAccessToken, refreshAccessToken, setAccessToken } from './token'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? ''

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

function getCsrfToken(): string | undefined {
  if (typeof document === 'undefined') return undefined
  const m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)
  return m?.[1]
}

function isAuthEndpoint(path: string): boolean {
  return (
    path === '/auth/login' ||
    path === '/auth/logout' ||
    path === '/auth/refresh'
  )
}

async function doFetch(
  path: string,
  init: RequestInit,
  bearer: string | null,
): Promise<Response> {
  const headers = new Headers(init.headers)
  if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const csrf = getCsrfToken()
  if (csrf && init.method && init.method !== 'GET') {
    headers.set('X-CSRF', csrf)
  }
  if (bearer && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${bearer}`)
  }
  return fetch(`${API_URL}${path}`, { ...init, headers, credentials: 'include' })
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  let res = await doFetch(path, init, getAccessToken())

  if (res.status === 401 && !isAuthEndpoint(path)) {
    const fresh = await refreshAccessToken(API_URL)
    if (fresh) {
      res = await doFetch(path, init, fresh)
    } else if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
      setAccessToken(null)
      const next = encodeURIComponent(window.location.pathname + window.location.search)
      window.location.href = `/login?next=${next}`
    }
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {}
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}
