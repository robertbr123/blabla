/**
 * Landing fallback do `clientes.ondeline.com.br`.
 *
 * Quando o usuario toca num botao de template WhatsApp com URL
 * `https://clientes.ondeline.com.br/...`:
 * - App **instalado**: o SO intercepta via App Links/Universal Links
 *   antes do browser carregar esta pagina.
 * - App **nao instalado**: o browser cai aqui — esta pagina convida a
 *   baixar o app.
 *
 * Server component puro (sem JS no client) pra ser leve e rapido.
 * Detalhe de plataforma (Android vs iOS) e feito em CSS via media query.
 */

const PLAY_URL =
  'https://play.google.com/store/apps/details?id=dev.robertbr.cliente_mobile'
const APP_STORE_URL = 'https://apps.apple.com/app/id000000000'

const NAVY = '#0B1F3A'
const TEAL = '#00C2A8'
const BG = '#F4F6FA'
const TEXT = '#1A2540'
const MUTED = '#5B6884'

export default function Page() {
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
        <div
          style={{
            width: 72,
            height: 72,
            background: NAVY,
            borderRadius: 18,
            margin: '0 auto 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
            <path
              d="M20 70 Q50 30 80 70"
              stroke={TEAL}
              strokeWidth="8"
              fill="none"
              strokeLinecap="round"
            />
            <circle cx="50" cy="80" r="6" fill={TEAL} />
          </svg>
        </div>
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
          <a
            href={PLAY_URL}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 10,
              textDecoration: 'none',
              padding: '14px 20px',
              borderRadius: 12,
              fontWeight: 600,
              fontSize: 15,
              background: NAVY,
              color: 'white',
            }}
          >
            Baixar na Google Play
          </a>
          <a
            href={APP_STORE_URL}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 10,
              textDecoration: 'none',
              padding: '14px 20px',
              borderRadius: 12,
              fontWeight: 600,
              fontSize: 15,
              background: 'white',
              color: NAVY,
              border: '1.5px solid #E2E8F2',
            }}
          >
            Baixar na App Store
          </a>
        </div>
        <p style={{ marginTop: 28, fontSize: 12, color: MUTED }}>
          Já é cliente?{' '}
          <a
            href="https://ondelinetelecom.com.br"
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
