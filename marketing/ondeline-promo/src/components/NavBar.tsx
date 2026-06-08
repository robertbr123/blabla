import React from 'react'
import { theme, FONT } from '../theme'

/**
 * Réplica da FloatingNavBar do app: pílula branca flutuante com 4 tabs e
 * uma "bolha" ciano atrás da tab ativa. Ícones desenhados em SVG pra bater
 * com os Material Icons usados (home, receipt_long, support_agent, person).
 */
type Tab = { label: string; icon: React.FC<{ color: string }> }

const TABS: Tab[] = [
  { label: 'Início', icon: HomeIcon },
  { label: 'Faturas', icon: ReceiptIcon },
  { label: 'Suporte', icon: SupportIcon },
  { label: 'Perfil', icon: PersonIcon },
]

export const NavBar: React.FC<{ active: number }> = ({ active }) => {
  return (
    <div
      style={{
        position: 'absolute',
        left: 22,
        right: 22,
        bottom: 26,
        height: 104,
        background: theme.surface,
        borderRadius: 40,
        border: `1px solid ${theme.divider}`,
        boxShadow: '0 14px 34px rgba(11,31,58,0.16)',
        display: 'flex',
        alignItems: 'center',
        padding: 10,
        fontFamily: FONT,
        zIndex: 40,
      }}
    >
      {/* bolha ativa */}
      <div
        style={{
          position: 'absolute',
          top: 10,
          bottom: 10,
          left: `calc(${(active * 100) / TABS.length}% + 6px)`,
          width: `calc(${100 / TABS.length}% - 12px)`,
          borderRadius: 26,
          background: `linear-gradient(135deg, ${theme.primary}28, ${theme.primary}10)`,
          transition: 'left 0.3s',
        }}
      />
      {TABS.map((t, i) => {
        const on = i === active
        const color = on ? theme.primary : theme.muted
        const Icon = t.icon
        return (
          <div
            key={t.label}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 6,
              zIndex: 1,
              transform: on ? 'scale(1.06)' : 'scale(1)',
            }}
          >
            <Icon color={color} />
            <span style={{ fontSize: 19, fontWeight: on ? 800 : 600, color }}>{t.label}</span>
          </div>
        )
      })}
    </div>
  )
}

// ---- Ícones (Material-ish) em SVG, ~28px ----
function HomeIcon({ color }: { color: string }) {
  return (
    <svg width="30" height="30" viewBox="0 0 24 24" fill={color}>
      <path d="M12 3l9 8h-2.5v9h-5v-6h-3v6h-5v-9H3l9-8z" />
    </svg>
  )
}
function ReceiptIcon({ color }: { color: string }) {
  return (
    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 3v18l2-1.2 2 1.2 2-1.2 2 1.2 2-1.2 2 1.2V3l-2 1.2L17 3l-2 1.2L13 3l-2 1.2L9 3 7 4.2 5 3z" />
      <path d="M8 8h8M8 12h8M8 16h5" />
    </svg>
  )
}
function SupportIcon({ color }: { color: string }) {
  return (
    <svg width="30" height="30" viewBox="0 0 24 24" fill={color}>
      <path d="M12 2a9 9 0 0 0-9 9v5a3 3 0 0 0 3 3h1v-7H5v-1a7 7 0 0 1 14 0v1h-2v7h1a3 3 0 0 0 3-3v-5a9 9 0 0 0-9-9z" />
      <path d="M9 20a3 3 0 0 0 6 0" stroke={color} strokeWidth="1.6" fill="none" />
    </svg>
  )
}
function PersonIcon({ color }: { color: string }) {
  return (
    <svg width="30" height="30" viewBox="0 0 24 24" fill={color}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4 3.6-7 8-7s8 3 8 7" />
    </svg>
  )
}
