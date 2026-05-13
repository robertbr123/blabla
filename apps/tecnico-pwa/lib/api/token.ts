// In-memory access token store. We never persist the JWT to localStorage to
// avoid XSS exfiltration; the durable session lives in the httpOnly
// refresh_token cookie, and /auth/refresh mints a fresh access token whenever
// we need one (page reload, expired token, etc.).
let accessToken: string | null = null
let refreshing: Promise<string | null> | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export async function refreshAccessToken(apiUrl: string): Promise<string | null> {
  if (refreshing) return refreshing
  refreshing = (async () => {
    try {
      const res = await fetch(`${apiUrl}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      })
      if (!res.ok) {
        accessToken = null
        return null
      }
      const body = (await res.json()) as { access_token: string }
      accessToken = body.access_token
      return accessToken
    } catch {
      accessToken = null
      return null
    } finally {
      refreshing = null
    }
  })()
  return refreshing
}
