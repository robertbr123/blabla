/**
 * Landing fallback do `clientes.ondeline.com.br`.
 *
 * Quando o usuario toca num link de template WhatsApp com URL
 * `https://clientes.ondeline.com.br/...` (ex.: /faturas, /suporte,
 * /notificacoes):
 * - App **instalado**: o SO intercepta via App Links/Universal Links
 *   antes do browser carregar esta pagina.
 * - App **nao instalado**: o browser cai aqui — esta pagina convida a
 *   baixar o app.
 *
 * Reusado pela raiz (`app/page.tsx`) e pelo catch-all 404
 * (`app/not-found.tsx`), pra que qualquer path desconhecido caia na
 * landing em vez do 404 padrao do Next.
 *
 * Server component puro (sem JS no client). Detecta o aparelho pelo
 * User-Agent (server-side) pra destacar a loja certa: Android ve a
 * Google Play, iOS ve a App Store, desktop/desconhecido ve as duas.
 * Ler `headers()` torna a rota dinamica — irrelevante p/ esta landing.
 */
import { headers } from 'next/headers'
import AutoRedirect from './AutoRedirect'

const PLAY_URL =
  'https://play.google.com/store/apps/details?id=dev.robertbr.cliente_mobile'
const APP_STORE_URL = 'https://apps.apple.com/br/app/ondeline/id6776840056'

const NAVY = '#0B1F3A'
const BG = '#F4F6FA'
const TEXT = '#1A2540'
const MUTED = '#5B6884'

type Platform = 'ios' | 'android' | 'desktop'

/** Detecta a plataforma pelo User-Agent. Cobre o browser interno do WhatsApp. */
function detectPlatform(ua: string): Platform {
  const s = ua.toLowerCase()
  if (/android/.test(s)) return 'android'
  if (/iphone|ipad|ipod/.test(s)) return 'ios'
  return 'desktop'
}

export default async function AppLanding() {
  const ua = (await headers()).get('user-agent') ?? ''
  const platform = detectPlatform(ua)
  return (
    <main
      style={{
        minHeight: '100vh',
        background: BG,
        color: TEXT,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
      }}
    >
      <section
        style={{
          background: 'white',
          borderRadius: 24,
          padding: '40px 32px',
          maxWidth: 420,
          width: '100%',
          boxShadow: '0 20px 60px rgba(11, 31, 58, 0.08)',
          textAlign: 'center',
        }}
      >
        {/* Logo do cliente-mobile (256x256, mesmo PNG do app). */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/logo.png"
          alt="Ondeline"
          width={88}
          height={88}
          style={{
            display: 'block',
            margin: '0 auto 20px',
            borderRadius: 20,
            boxShadow: '0 8px 24px rgba(11, 31, 58, 0.15)',
          }}
        />
        <h1 style={{ fontSize: 24, margin: '0 0 8px', letterSpacing: '-0.02em' }}>
          Aplicativo Ondeline
        </h1>
        <p
          style={{
            color: MUTED,
            fontSize: 15,
            lineHeight: 1.5,
            margin: '0 0 28px',
          }}
        >
          Acompanhe seu plano, suas faturas, abra chamados e copie o PIX em
          poucos toques.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Android: Play em destaque. iOS: App Store em destaque.
              Desktop/desconhecido: os dois. Sempre ha um fallback p/ a
              outra loja (link discreto) caso o UA seja mal detectado. */}
          {platform === 'android' && (
            <>
              <PlayButton />
              <StoreFallbackLink store="ios" />
            </>
          )}
          {platform === 'ios' && (
            <>
              <AppStoreButton />
              <StoreFallbackLink store="android" />
            </>
          )}
          {platform === 'desktop' && (
            <>
              <PlayButton />
              <AppStoreButton />
            </>
          )}
        </div>
        {/* Mobile: se nao tocar em ~3s, abre a loja certa sozinho. */}
        {platform === 'android' && <AutoRedirect url={PLAY_URL} />}
        {platform === 'ios' && <AutoRedirect url={APP_STORE_URL} />}
        <p style={{ marginTop: 28, fontSize: 12, color: MUTED }}>
          Já é cliente?{' '}
          <a
            href="https://ondeline.com.br"
            target="_blank"
            rel="noopener"
            style={{ color: MUTED, textDecoration: 'underline' }}
          >
            Site oficial
          </a>
        </p>
      </section>
    </main>
  )
}

const buttonBase = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 12,
  textDecoration: 'none',
  padding: '14px 20px',
  borderRadius: 12,
  fontWeight: 600,
  fontSize: 15,
} as const

function PlayButton() {
  return (
    <a href={PLAY_URL} style={{ ...buttonBase, background: NAVY, color: 'white' }}>
      {/* Google Play — triangulo oficial 4 cores */}
      <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M3.609 1.814L13.792 12 3.61 22.186a.996.996 0 01-.61-.92V2.734a1 1 0 01.609-.92z" fill="#00C2FF" />
        <path d="M16.81 8.99l2.964 1.706a1.5 1.5 0 010 2.608l-2.964 1.706L13.792 12l3.018 3.01z" fill="#FFC000" />
        <path d="M3.609 1.814a1 1 0 01.39-.078c.18 0 .36.046.518.137l11.293 6.517L13.792 12 3.61 1.814z" fill="#00DE7A" />
        <path d="M16.81 15.01L4.517 22.127a1 1 0 01-.908.06L13.792 12l3.018 3.01z" fill="#FF3A44" />
      </svg>
      Baixar na Google Play
    </a>
  )
}

function AppStoreButton() {
  return (
    <a
      href={APP_STORE_URL}
      style={{ ...buttonBase, background: 'white', color: NAVY, border: '1.5px solid #E2E8F2' }}
    >
      {/* Apple logo — versao monocromatica preta (padrao oficial) */}
      <svg width="20" height="22" viewBox="0 0 384 512" aria-hidden="true" fill={NAVY}>
        <path d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7-15 0-49.4-19.7-76.4-19.7C63.3 141.2 4 184.8 4 273.5q0 39.3 14.4 81.2c12.8 36.7 59 126.7 107.2 125.2 25.2-.6 43-17.9 75.8-17.9 31.8 0 48.3 17.9 76.4 17.9 48.6-.7 90.4-82.5 102.6-119.3-65.2-30.7-61.7-90-61.7-91.9zm-56.6-164.2c27.3-32.4 24.8-61.9 24-72.5-24.1 1.4-52 16.4-67.9 34.9-17.5 19.8-27.8 44.3-25.6 71.9 26.1 2 49.9-11.4 69.5-34.3z" />
      </svg>
      Baixar na App Store
    </a>
  )
}

/** Link discreto pra outra loja, caso a deteccao de aparelho falhe. */
function StoreFallbackLink({ store }: { store: 'ios' | 'android' }) {
  const isIos = store === 'ios'
  return (
    <a
      href={isIos ? APP_STORE_URL : PLAY_URL}
      style={{ marginTop: 4, fontSize: 13, color: MUTED, textDecoration: 'underline' }}
    >
      {isIos ? 'Usa iPhone? Baixar na App Store' : 'Usa Android? Baixar na Google Play'}
    </a>
  )
}
