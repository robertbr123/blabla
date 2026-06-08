import React from 'react'
import { useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion'
import { theme, FONT } from '../theme'

/**
 * Legenda compacta animada no topo da cena (entra com mola). Reforca a
 * mensagem mesmo sem som, sem roubar foco do celular.
 */
export const Caption: React.FC<{
  kicker?: string
  title: string
  accent?: string
  delay?: number
}> = ({ kicker, title, accent = theme.primaryLight, delay = 0 }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()

  const enter = spring({ frame: frame - delay, fps, config: { damping: 200, mass: 0.8 } })
  const y = interpolate(enter, [0, 1], [40, 0])
  const opacity = interpolate(frame - delay, [0, 8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  })

  return (
    <div
      style={{
        transform: `translateY(${y}px)`,
        opacity,
        textAlign: 'center',
        padding: '0 80px',
        fontFamily: FONT,
      }}
    >
      {kicker && (
        <div
          style={{
            display: 'inline-block',
            fontSize: 26,
            fontWeight: 800,
            letterSpacing: 3,
            textTransform: 'uppercase',
            color: accent,
            background: 'rgba(255,255,255,0.08)',
            border: `2px solid ${accent}55`,
            padding: '8px 22px',
            borderRadius: 100,
            marginBottom: 20,
          }}
        >
          {kicker}
        </div>
      )}
      <div
        style={{
          fontSize: 60,
          lineHeight: 1.04,
          fontWeight: 800,
          color: theme.white,
          letterSpacing: -1,
          textShadow: '0 4px 30px rgba(0,0,0,0.45)',
        }}
      >
        {title}
      </div>
    </div>
  )
}
