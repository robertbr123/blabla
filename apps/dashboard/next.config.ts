import type { NextConfig } from 'next'

// `INTERNAL_API_URL` is the backend URL as reachable from the Next.js server process
// (server-side rendering + the rewrite proxy below). Set this even when
// `NEXT_PUBLIC_API_URL` is empty so the browser can use relative paths.
const INTERNAL = process.env.INTERNAL_API_URL
  ?? process.env.NEXT_PUBLIC_API_URL
  ?? 'http://localhost:8000'

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${INTERNAL}/api/:path*`,
      },
      {
        source: '/auth/:path*',
        destination: `${INTERNAL}/auth/:path*`,
      },
    ]
  },
}

export default nextConfig
