import React from 'react'
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
} from 'remotion'
import { theme, FONT } from '../theme'
import { Caption } from '../components/Caption'
import { PhoneStage } from '../components/Stage'
import {
  HomeScreen,
  FaturasScreen,
  SuporteScreen,
  FidelidadeScreen,
  LogoMark,
} from '../components/Screens'

// ============================================================ 1. HOOK
export const HookScene: React.FC = () => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()

  const logoIn = spring({ frame, fps, config: { damping: 12, mass: 0.9 } })
  const logoScale = interpolate(logoIn, [0, 1], [0.2, 1])
  const ring = interpolate(frame, [6, 40], [0, 1], { extrapolateRight: 'clamp' })
  const textIn = spring({ frame: frame - 22, fps, config: { damping: 200 } })
  const textY = interpolate(textIn, [0, 1], [50, 0])
  const textOp = interpolate(frame - 22, [0, 10], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })

  return (
    <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', fontFamily: FONT }}>
      <div
        style={{
          position: 'absolute',
          width: 520,
          height: 520,
          borderRadius: '50%',
          border: `4px solid ${theme.primary}`,
          opacity: (1 - ring) * 0.6,
          transform: `scale(${0.6 + ring * 1.4})`,
        }}
      />
      <div style={{ transform: `scale(${logoScale})` }}>
        <LogoMark size={320} />
      </div>
      <div style={{ transform: `translateY(${textY}px)`, opacity: textOp, marginTop: 60, textAlign: 'center' }}>
        <div style={{ fontSize: 60, fontWeight: 800, color: 'white', letterSpacing: -1 }}>Chegou o app da</div>
        <div
          style={{
            fontSize: 104,
            fontWeight: 900,
            letterSpacing: -2,
            background: `linear-gradient(90deg, ${theme.primaryLight}, ${theme.primary})`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          Ondeline
        </div>
      </div>
    </AbsoluteFill>
  )
}

// ====================================================== 2. INTRO HOME
export const IntroHomeScene: React.FC = () => (
  <PhoneStage caption={<Caption title="Tudo na palma da sua mão" />}>
    <HomeScreen />
  </PhoneStage>
)

// ========================================================= 3. FATURAS
export const FaturasScene: React.FC = () => {
  const frame = useCurrentFrame()
  const qr = interpolate(frame, [40, 75], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
  const paid = interpolate(frame, [210, 225], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
  return (
    <PhoneStage caption={<Caption kicker="Faturas" title="Pague com Pix na hora" accent={theme.primaryLight} />}>
      <FaturasScreen qr={qr} paid={paid} />
    </PhoneStage>
  )
}

// ========================================================= 4. SUPORTE
export const SuporteScene: React.FC = () => {
  const frame = useCurrentFrame()
  const bubbles = Math.min(4, 1 + Math.floor(interpolate(frame, [40, 200], [0, 3], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })))
  return (
    <PhoneStage caption={<Caption kicker="Suporte" title="Abra um chamado e acompanhe" accent={theme.primaryLight} />}>
      <SuporteScreen bubbles={bubbles} />
    </PhoneStage>
  )
}

// ====================================================== 5. FIDELIDADE
export const FidelidadeScene: React.FC = () => {
  const frame = useCurrentFrame()
  const points = interpolate(frame, [35, 110], [0, 1250], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
  return (
    <PhoneStage caption={<Caption kicker="Fidelidade" title="Junte pontos, troque por prêmios" accent="#F2C66B" />}>
      <FidelidadeScreen points={points} />
    </PhoneStage>
  )
}

// ========================================================== 6. AVISOS
export const AvisosScene: React.FC = () => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()

  const toastIn = spring({ frame: frame - 30, fps, config: { damping: 14 } })
  const toastY = interpolate(toastIn, [0, 1], [-200, 0])
  const pulse = 1 + Math.sin(frame / 6) * 0.05

  return (
    <PhoneStage caption={<Caption kicker="Notificações" title="Você fica sabendo na hora" accent={theme.primaryLight} />}>
      <HomeScreen />
      {/* toast deslizando do topo */}
      <div
        style={{
          position: 'absolute',
          top: 96,
          left: 26,
          right: 26,
          transform: `translateY(${toastY}px)`,
          opacity: interpolate(frame - 30, [0, 8], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          background: 'rgba(255,255,255,0.98)',
          borderRadius: 28,
          padding: '22px 26px',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          boxShadow: '0 24px 56px rgba(0,0,0,0.32)',
          zIndex: 90,
          fontFamily: FONT,
        }}
      >
        <div style={{ width: 64, height: 64, borderRadius: 18, background: theme.primaryDark, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 32 }}>🔔</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 900, fontSize: 26, color: theme.text }}>Ondeline</div>
          <div style={{ fontSize: 23, color: theme.muted, fontWeight: 600 }}>Sua fatura vence em 3 dias</div>
        </div>
      </div>
      {/* FAB WhatsApp pulsando, acima da navbar */}
      <div
        style={{
          position: 'absolute',
          bottom: 175,
          right: 40,
          width: 100,
          height: 100,
          borderRadius: 50,
          background: theme.whatsapp,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 50,
          transform: `scale(${pulse})`,
          boxShadow: `0 0 0 ${(pulse - 1) * 320}px ${theme.whatsapp}22, 0 16px 40px rgba(0,0,0,0.3)`,
          zIndex: 90,
        }}
      >
        💬
      </div>
    </PhoneStage>
  )
}

// ============================================================= 7. CTA
export const CTAScene: React.FC = () => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()

  const logoIn = spring({ frame, fps, config: { damping: 13 } })
  const logoScale = interpolate(logoIn, [0, 1], [0.4, 1])

  const badgeIn = spring({ frame: frame - 25, fps, config: { damping: 200 } })
  const badgeY = interpolate(badgeIn, [0, 1], [60, 0])
  const badgeOp = interpolate(frame - 25, [0, 10], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
  const ctaIn = interpolate(frame, [12, 28], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })

  return (
    <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', fontFamily: FONT, gap: 16 }}>
      <div style={{ transform: `scale(${logoScale})` }}>
        <LogoMark size={250} />
      </div>
      <div style={{ opacity: ctaIn, textAlign: 'center', marginTop: 10 }}>
        <div style={{ fontSize: 88, fontWeight: 900, color: 'white', letterSpacing: -2 }}>Baixe agora</div>
        <div style={{ fontSize: 36, fontWeight: 700, color: theme.primaryLight }}>e tenha tudo na mão</div>
      </div>
      <div style={{ display: 'flex', gap: 20, marginTop: 30, transform: `translateY(${badgeY}px)`, opacity: badgeOp }}>
        <StoreBadge top="Baixe na" bottom="App Store" icon={<AppleIcon />} />
        <StoreBadge top="Disponível no" bottom="Google Play" icon={<PlayIcon />} />
      </div>
    </AbsoluteFill>
  )
}

const AppleIcon: React.FC = () => (
  <svg width="44" height="44" viewBox="0 0 24 24" fill="white">
    <path d="M16.36 1.43c0 1.14-.42 2.22-1.18 3.02-.79.85-2.05 1.5-3.13 1.42-.13-1.1.43-2.27 1.13-3 .79-.83 2.16-1.46 3.18-1.44zM20.9 17.1c-.55 1.27-.82 1.84-1.53 2.97-.99 1.57-2.39 3.53-4.12 3.55-1.54.01-1.93-1-4.02-.99-2.09.01-2.52 1.01-4.06.99-1.73-.02-3.05-1.79-4.04-3.36C.36 16.49.07 11.4 1.86 8.7c1.05-1.61 2.71-2.55 4.28-2.55 1.6 0 2.6 1.05 3.92 1.05 1.28 0 2.06-1.05 3.91-1.05 1.4 0 2.88.76 3.94 2.07-3.46 1.9-2.9 6.84.99 8.83z" />
  </svg>
)

const PlayIcon: React.FC = () => (
  <svg width="40" height="40" viewBox="0 0 24 24">
    <path d="M3 2.5v19l11-9.5L3 2.5z" fill="#5FE3DC" />
    <path d="M14 12L3 2.5l13.5 7.2L14 12z" fill="#14B8B0" />
    <path d="M14 12l2.5 2.3L3 21.5 14 12z" fill="#E8A33D" />
    <path d="M16.5 9.7L20 11.6c.9.5.9 1.3 0 1.8l-3.5 1.9L14 12l2.5-2.3z" fill="#E0455A" />
  </svg>
)

const StoreBadge: React.FC<{ top: string; bottom: string; icon: React.ReactNode }> = ({ top, bottom, icon }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 16, background: '#000', border: '2px solid rgba(255,255,255,0.25)', borderRadius: 22, padding: '18px 28px', color: 'white' }}>
    <div style={{ display: 'flex', alignItems: 'center' }}>{icon}</div>
    <div style={{ textAlign: 'left' }}>
      <div style={{ fontSize: 22, opacity: 0.85 }}>{top}</div>
      <div style={{ fontSize: 34, fontWeight: 800, lineHeight: 1 }}>{bottom}</div>
    </div>
  </div>
)
