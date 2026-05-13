import { NextResponse, type NextRequest } from 'next/server'

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl
  if (pathname.startsWith('/_next') || pathname.startsWith('/api') || pathname === '/login' || pathname === '/manifest.json' || pathname === '/sw.js' || pathname.startsWith('/icon-')) {
    return NextResponse.next()
  }
  // csrf_token (Path=/) is the right cookie to probe here — refresh_token's
  // Path=/auth scope means it isn't sent to /os, /, etc.
  const token = req.cookies.get('csrf_token')
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
