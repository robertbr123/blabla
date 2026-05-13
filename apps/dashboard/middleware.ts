import { NextResponse, type NextRequest } from 'next/server'

const PROTECTED_PREFIXES = [
  '/conversas',
  '/os',
  '/leads',
  '/clientes',
  '/tecnicos',
  '/manutencoes',
  '/config',
  '/metricas',
]

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl
  const needsAuth = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p))
  if (!needsAuth) return NextResponse.next()

  // The M2 backend sets two cookies on login:
  //   - refresh_token (httpOnly, Path=/auth) — used by /auth/refresh only
  //   - csrf_token    (readable,  Path=/)    — double-submit CSRF token
  // We probe csrf_token here because the refresh_token's Path=/auth scope
  // means it isn't sent to /conversas (or any non-/auth path), so the
  // middleware never sees it. csrf_token is set by /auth/login and cleared
  // by /auth/logout, so its presence is the right "user is logged in" signal
  // at the edge. The API still validates the JWT on every protected call.
  const token = req.cookies.get('csrf_token')
  if (!token) {
    const url = req.nextUrl.clone()
    url.pathname = '/login'
    url.searchParams.set('next', pathname)
    return NextResponse.redirect(url)
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api).*)'],
}
