import React from 'react'
import { Img, staticFile, interpolate } from 'remotion'
import { theme, FONT } from '../theme'
import { StatusBar } from './PhoneFrame'
import { NavBar } from './NavBar'

const screen: React.CSSProperties = {
  position: 'absolute',
  inset: 0,
  fontFamily: FONT,
  color: theme.text,
  background: theme.bg,
  display: 'flex',
  flexDirection: 'column',
}

const body: React.CSSProperties = {
  padding: '6px 30px 0',
  display: 'flex',
  flexDirection: 'column',
  gap: 22,
}

const card: React.CSSProperties = {
  background: theme.surface,
  borderRadius: 30,
  border: `1px solid ${theme.divider}`,
  boxShadow: '0 6px 20px rgba(11,31,58,0.06)',
}

// ---- pequenos blocos reutilizaveis ----
const Avatar: React.FC = () => (
  <div
    style={{
      width: 84,
      height: 84,
      borderRadius: 42,
      background: `linear-gradient(135deg, ${theme.primary}, ${theme.primaryDark})`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: 'white',
      fontWeight: 900,
      fontSize: 36,
      boxShadow: `0 8px 20px ${theme.primary}55`,
    }}
  >
    RA
  </div>
)

const ConnPill: React.FC = () => (
  <div
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 9,
      background: `${theme.primary}1A`,
      color: theme.primary,
      fontWeight: 800,
      fontSize: 22,
      padding: '9px 18px',
      borderRadius: 100,
    }}
  >
    <span style={{ width: 13, height: 13, borderRadius: 7, background: theme.primary }} />
    Online
  </div>
)

const Bell: React.FC = () => (
  <div
    style={{
      width: 70,
      height: 70,
      borderRadius: 22,
      background: theme.surface,
      border: `1px solid ${theme.divider}`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
    }}
  >
    <svg width="34" height="34" viewBox="0 0 24 24" fill={theme.text}>
      <path d="M12 2a6 6 0 0 0-6 6c0 5-2 6-2 8h16c0-2-2-3-2-8a6 6 0 0 0-6-6z" />
      <path d="M9.5 20a2.5 2.5 0 0 0 5 0" stroke={theme.text} strokeWidth="1.6" fill="none" />
    </svg>
    <span style={{ position: 'absolute', top: 16, right: 16, width: 14, height: 14, borderRadius: 7, background: theme.danger, border: '2px solid white' }} />
  </div>
)

// ================================================================ HOME
export const HomeScreen: React.FC = () => (
  <div style={screen}>
    <StatusBar />
    <div style={body}>
      {/* header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 6 }}>
        <div>
          <div style={{ fontSize: 26, color: theme.muted, fontWeight: 600 }}>Bom dia 👋</div>
          <div style={{ fontSize: 40, fontWeight: 900, letterSpacing: -0.5 }}>Início</div>
        </div>
        <Bell />
      </div>

      {/* HERO CARD (replica do app) */}
      <div style={{ ...card }}>
        {/* linha 1 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 18, padding: 22 }}>
          <Avatar />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 30, fontWeight: 900, letterSpacing: -0.3 }}>Robert</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginTop: 4 }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill={theme.primary}><path d="M12 18a2 2 0 1 1 0 4 2 2 0 0 1 0-4zM4.5 11.5a10 10 0 0 1 15 0l-2.3 2.3a6.8 6.8 0 0 0-10.4 0L4.5 11.5zM1 8a15 15 0 0 1 22 0l-2.3 2.3a11.8 11.8 0 0 0-17.4 0L1 8z" /></svg>
              <span style={{ color: theme.muted, fontSize: 23, fontWeight: 700, whiteSpace: 'nowrap' }}>Plano Fibra 600MB</span>
            </div>
          </div>
          <ConnPill />
        </div>
        {/* endereço */}
        <div style={{ borderTop: `1px solid ${theme.divider}`, padding: '14px 22px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={theme.muted} strokeWidth="2"><path d="M12 21s-7-5.5-7-11a7 7 0 0 1 14 0c0 5.5-7 11-7 11z" /><circle cx="12" cy="10" r="2.5" /></svg>
          <span style={{ color: theme.muted, fontSize: 22, fontWeight: 600 }}>Rua das Flores, 123 — Centro</span>
        </div>
        {/* streak */}
        <div style={{ borderTop: `1px solid ${theme.divider}`, padding: '14px 22px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 26 }}>🔥</span>
          <span style={{ fontSize: 22, fontWeight: 700, color: theme.muted }}>
            <span style={{ color: theme.amber, fontWeight: 900 }}>8 </span>meses pagando em dia
          </span>
        </div>
        {/* footer fatura */}
        <div style={{ background: `${theme.amber}10`, borderTop: `1px solid ${theme.divider}`, borderRadius: '0 0 30px 30px', padding: '18px 22px', display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 52, height: 52, borderRadius: 14, background: `${theme.amber}29`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill={theme.amber}><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 5h-2v6h6v-2h-4V7z" /></svg>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ color: theme.amber, fontWeight: 800, fontSize: 24 }}>Fatura vence em 3 dias</div>
            <div style={{ color: theme.muted, fontSize: 21, fontWeight: 600 }}>R$ 99,90 · vence 10/06</div>
          </div>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={theme.amber} strokeWidth="2.5"><path d="M9 6l6 6-6 6" /></svg>
        </div>
      </div>

      {/* QUICK CARDS */}
      <div style={{ display: 'flex', gap: 18 }}>
        <div style={{ ...card, flex: 1, background: `${theme.amber}14`, border: `1px solid ${theme.amber}33`, padding: 22 }}>
          <div style={{ fontSize: 44 }}>🏆</div>
          <div style={{ fontWeight: 900, fontSize: 30, marginTop: 8 }}>1.250 pts</div>
          <div style={{ color: theme.muted, fontSize: 22, fontWeight: 600 }}>Fidelidade</div>
        </div>
        <div style={{ ...card, flex: 1, background: `${theme.whatsapp}14`, border: `1px solid ${theme.whatsapp}33`, padding: 22 }}>
          <div style={{ fontSize: 44 }}>💬</div>
          <div style={{ fontWeight: 900, fontSize: 30, marginTop: 8 }}>Fale conosco</div>
          <div style={{ color: theme.muted, fontSize: 22, fontWeight: 600 }}>WhatsApp</div>
        </div>
      </div>
    </div>
    <NavBar active={0} />
  </div>
)

// ============================================================= FATURAS
export const FaturasScreen: React.FC<{ qr?: number; paid?: number }> = ({ qr = 1, paid = 0 }) => (
  <div style={screen}>
    <StatusBar />
    <div style={body}>
      <div style={{ fontSize: 44, fontWeight: 900, marginTop: 6 }}>Faturas</div>
      {/* fatura aberta */}
      <div style={{ ...card, padding: 26 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 24, color: theme.muted, fontWeight: 700 }}>Junho • 2026</span>
          <span style={{ background: paid > 0.5 ? `${theme.primary}1A` : `${theme.amber}1F`, color: paid > 0.5 ? theme.primary : theme.amber, fontWeight: 800, fontSize: 21, padding: '8px 16px', borderRadius: 100 }}>
            {paid > 0.5 ? '✓ Pago' : 'Em aberto'}
          </span>
        </div>
        <div style={{ fontSize: 62, fontWeight: 900, marginTop: 8, whiteSpace: 'nowrap' }}>R$ 99,90</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 2 }}>
          <span style={{ color: theme.muted, fontSize: 22, fontWeight: 600 }}>Vence em 10/06</span>
          <span style={{ background: `${theme.amber}1F`, color: theme.amber, fontWeight: 800, fontSize: 19, padding: '5px 12px', borderRadius: 100 }}>★ Ganhe +50 pts</span>
        </div>
        {/* Pix */}
        <div style={{ marginTop: 22, display: 'flex', gap: 22, alignItems: 'center', opacity: qr, transform: `scale(${interpolate(qr, [0, 1], [0.9, 1])})`, transformOrigin: 'left center' }}>
          <QrPix />
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 900, fontSize: 30, color: theme.primary }}>Pague com Pix</div>
            <div style={{ color: theme.muted, fontSize: 22, marginTop: 4, lineHeight: 1.3, fontWeight: 600 }}>Escaneie o QR e<br />pague na hora</div>
          </div>
        </div>
        <div style={{ marginTop: 22, background: theme.primary, color: 'white', textAlign: 'center', fontWeight: 800, fontSize: 26, padding: '20px', borderRadius: 20, boxShadow: `0 10px 24px ${theme.primary}66` }}>
          Copiar código Pix
        </div>
      </div>
      {/* paga */}
      <div style={{ ...card, padding: 22, display: 'flex', justifyContent: 'space-between', alignItems: 'center', opacity: 0.7 }}>
        <span style={{ fontSize: 24, color: theme.muted, fontWeight: 700 }}>Maio • 2026</span>
        <span style={{ color: theme.primary, fontWeight: 800, fontSize: 22 }}>✓ Pago</span>
      </div>
    </div>
    <NavBar active={1} />
  </div>
)

const QrPix: React.FC = () => (
  <div style={{ width: 170, height: 170, borderRadius: 20, background: 'white', border: `4px solid ${theme.primary}`, display: 'grid', gridTemplateColumns: 'repeat(9, 1fr)', gap: 3, padding: 14 }}>
    {Array.from({ length: 81 }).map((_, i) => {
      const r = Math.floor(i / 9)
      const c = i % 9
      const corner = (r < 3 && c < 3) || (r < 3 && c > 5) || (r > 5 && c < 3)
      const on = corner ? (r === 0 || r === 2 || c === 0 || c === 2 || (r === 1 && c === 1) || r === 6 || r === 8 || c === 6 || c === 8 || (r === 7 && c === 7)) : (i * 7 + ((i * 13) % 5)) % 3 === 0
      return <div key={i} style={{ background: on ? theme.primaryDark : 'transparent', borderRadius: 2 }} />
    })}
  </div>
)

// ============================================================= SUPORTE
export const SuporteScreen: React.FC<{ bubbles?: number }> = ({ bubbles = 4 }) => {
  const msgs = [
    { me: false, t: 'Oi! Minha internet caiu 😕' },
    { me: true, t: 'Já abrimos seu chamado! Um técnico vai até você.' },
    { me: false, t: 'Dá pra acompanhar pelo app?' },
    { me: true, t: 'Sim! Status: técnico a caminho 🛠️' },
  ]
  return (
    <div style={screen}>
      <StatusBar />
      <div style={{ ...body, gap: 16, flex: 1, paddingBottom: 172 }}>
        <div style={{ fontSize: 44, fontWeight: 900, marginTop: 6 }}>Suporte</div>
        <div style={{ background: `${theme.primary}14`, color: theme.primary, fontWeight: 800, fontSize: 23, padding: '16px 22px', borderRadius: 18, textAlign: 'center' }}>
          Chamado #A1B2 • Em andamento
        </div>
        {msgs.slice(0, bubbles).map((m, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: m.me ? 'flex-end' : 'flex-start' }}>
            <div
              style={{
                maxWidth: '80%',
                background: m.me ? theme.primary : theme.surface,
                color: m.me ? 'white' : theme.text,
                padding: '20px 24px',
                borderRadius: 28,
                borderBottomRightRadius: m.me ? 8 : 28,
                borderBottomLeftRadius: m.me ? 28 : 8,
                fontSize: 25,
                fontWeight: 600,
                border: m.me ? 'none' : `1px solid ${theme.divider}`,
                boxShadow: '0 4px 14px rgba(11,31,58,0.06)',
                lineHeight: 1.32,
              }}
            >
              {m.t}
            </div>
          </div>
        ))}
        {/* campo de digitar */}
        <div style={{ marginTop: 'auto', display: 'flex', gap: 12, alignItems: 'center', padding: '6px 0 4px' }}>
          <div style={{ flex: 1, background: theme.surface, border: `1px solid ${theme.divider}`, borderRadius: 100, padding: '18px 24px', color: theme.muted, fontSize: 22 }}>Escreva uma mensagem…</div>
          <div style={{ width: 64, height: 64, borderRadius: 32, background: theme.primary, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="30" height="30" viewBox="0 0 24 24" fill="white"><path d="M3 20l18-8L3 4v6l12 2-12 2v6z" /></svg>
          </div>
        </div>
      </div>
      <NavBar active={2} />
    </div>
  )
}

// ========================================================== FIDELIDADE
export const FidelidadeScreen: React.FC<{ points?: number }> = ({ points = 1250 }) => {
  const rewards = [
    { i: '🎁', t: '5% de desconto', p: '500 pts', ok: true },
    { i: '⚡', t: 'Upgrade temporário', p: '2.000 pts', ok: false },
    { i: '🎉', t: 'Mês grátis', p: '5.000 pts', ok: false },
  ]
  return (
    <div style={screen}>
      <StatusBar />
      <div style={body}>
        <div style={{ fontSize: 44, fontWeight: 900, marginTop: 6 }}>Fidelidade</div>
        <div style={{ ...card, background: `linear-gradient(135deg, ${theme.amber}, #F2C66B)`, border: 'none', color: 'white', textAlign: 'center', padding: 30, boxShadow: `0 16px 36px ${theme.amber}55` }}>
          <div style={{ fontSize: 25, fontWeight: 700, opacity: 0.95 }}>Seu saldo</div>
          <div style={{ fontSize: 92, fontWeight: 900, lineHeight: 1.05 }}>{Math.round(points).toLocaleString('pt-BR')}</div>
          <div style={{ fontSize: 28, fontWeight: 800, opacity: 0.95 }}>pontos</div>
        </div>
        {rewards.map((r, i) => (
          <div key={i} style={{ ...card, display: 'flex', alignItems: 'center', gap: 18, padding: 22, opacity: r.ok ? 1 : 0.5 }}>
            <div style={{ fontSize: 44 }}>{r.i}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 800, fontSize: 28 }}>{r.t}</div>
              <div style={{ color: theme.muted, fontSize: 22, fontWeight: 600 }}>{r.p}</div>
            </div>
            {r.ok && <div style={{ background: theme.primary, color: 'white', fontWeight: 800, fontSize: 22, padding: '12px 22px', borderRadius: 100 }}>Resgatar</div>}
          </div>
        ))}
      </div>
      <NavBar active={0} />
    </div>
  )
}

// ================================================================ LOGO
export const LogoMark: React.FC<{ size?: number }> = ({ size = 220 }) => (
  <Img src={staticFile('logo.png')} style={{ width: size, height: size, borderRadius: size * 0.22 }} />
)
