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

  // The M2 backend sets an httpOnly `refresh_token` cookie on login.
  // We cannot validate the JWT here (edge runtime), so we treat its presence
  // as a sufficient signal. The API will reject stale tokens independently.
  const token = req.cookies.get('refresh_token')
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
