import path from 'path'
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Necessario pra Docker (standalone output reduz a imagem em ~90%).
  output: 'standalone',
  outputFileTracingRoot: path.join(__dirname, '../../'),
  reactStrictMode: true,
  // iOS Universal Links: o `apple-app-site-association` NAO tem extensao,
  // entao o Next serve sem Content-Type — Apple exige `application/json`.
  // Android `assetlinks.json` ja sai como JSON pela extensao .json.
  async headers() {
    return [
      {
        source: '/.well-known/apple-app-site-association',
        headers: [
          { key: 'Content-Type', value: 'application/json' },
          { key: 'Cache-Control', value: 'public, max-age=3600' },
        ],
      },
      {
        source: '/.well-known/assetlinks.json',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=3600' },
        ],
      },
    ]
  },
}

export default nextConfig
