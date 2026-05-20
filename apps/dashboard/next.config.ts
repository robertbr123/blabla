import path from 'path'
import type { NextConfig } from 'next'

const INTERNAL = process.env.INTERNAL_API_URL
  || process.env.NEXT_PUBLIC_API_URL
  || 'http://localhost:8000'

const nextConfig: NextConfig = {
  output: 'standalone',
  outputFileTracingRoot: path.join(__dirname, '../../'),
  reactStrictMode: true,
  // CPU do servidor não suporta SIMD/AVX usado pelo sharp → SIGILL (exit 132).
  // Logos são pequenos e já otimizados; servir cru evita o otimizador.
  images: { unoptimized: true },
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
