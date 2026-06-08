import React from 'react'
import { theme, FONT } from '../theme'

/**
 * Moldura de iPhone (bezel + dynamic island) com a tela como children.
 * Maior que antes pra dar foco na UI do app.
 */
export const PhoneFrame: React.FC<{
  children: React.ReactNode
  scale?: number
}> = ({ children, scale = 1 }) => {
  const W = 600
  const H = 1248
  return (
    <div
      style={{
        width: W,
        height: H,
        borderRadius: 88,
        background: '#070707',
        padding: 18,
        boxShadow:
          '0 60px 130px rgba(0,0,0,0.6), inset 0 0 2px 2px rgba(255,255,255,0.08)',
        transform: `scale(${scale})`,
      }}
    >
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          borderRadius: 72,
          overflow: 'hidden',
          background: theme.bg,
        }}
      >
        {/* Dynamic Island */}
        <div
          style={{
            position: 'absolute',
            top: 24,
            left: '50%',
            transform: 'translateX(-50%)',
            width: 150,
            height: 40,
            borderRadius: 24,
            background: '#070707',
            zIndex: 80,
          }}
        />
        {children}
      </div>
    </div>
  )
}

/** Barra de status fake (hora + icones). */
export const StatusBar: React.FC = () => (
  <div
    style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '28px 46px 6px',
      fontSize: 28,
      fontWeight: 800,
      color: theme.text,
      fontFamily: FONT,
    }}
  >
    <span>9:41</span>
    <span style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      <SignalIcon />
      <span style={{ fontSize: 24 }}>100%</span>
      <BatteryIcon />
    </span>
  </div>
)

const SignalIcon: React.FC = () => (
  <svg width="34" height="24" viewBox="0 0 34 24" fill={theme.text}>
    <rect x="0" y="14" width="6" height="8" rx="1.5" />
    <rect x="9" y="10" width="6" height="12" rx="1.5" />
    <rect x="18" y="6" width="6" height="16" rx="1.5" />
    <rect x="27" y="2" width="6" height="20" rx="1.5" />
  </svg>
)

const BatteryIcon: React.FC = () => (
  <svg width="40" height="22" viewBox="0 0 40 22">
    <rect x="1" y="3" width="33" height="16" rx="5" fill="none" stroke={theme.text} strokeWidth="2" opacity="0.5" />
    <rect x="4" y="6" width="27" height="10" rx="2.5" fill={theme.text} />
    <rect x="36" y="8" width="3" height="6" rx="1.5" fill={theme.text} opacity="0.5" />
  </svg>
)
