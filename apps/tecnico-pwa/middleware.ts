import { NextResponse, type NextRequest } from 'next/server'

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl
  if (pathname.startsWith('/_next') || pathname.startsWith('/api') || pathname === '/login' || pathname === '/manifest.json' || pathname === '/sw.js' || pathname.startsWith('/icon-')) {
    return NextResponse.next()
  }
  const token = req.cookies.get('refresh_token')
  if (!token) {
    const url = req.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
