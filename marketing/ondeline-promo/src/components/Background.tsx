import React from 'react'
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion'
import { theme } from '../theme'

/**
 * Fundo gradiente navy animado com blobs de luz ciano que se movem devagar.
 */
export const Background: React.FC<{ tint?: string }> = ({ tint }) => {
  const frame = useCurrentFrame()

  const blobA = {
    x: interpolate(frame % 600, [0, 300, 600], [-100, 200, -100]),
    y: interpolate(frame % 600, [0, 300, 600], [200, 500, 200]),
  }
  const blobB = {
    x: interpolate(frame % 720, [0, 360, 720], [800, 600, 800]),
    y: interpolate(frame % 720, [0, 360, 720], [1500, 1200, 1500]),
  }

  const accent = tint ?? theme.primary

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, ${theme.primaryDark} 0%, ${theme.navyDeep} 65%, #04101f 100%)`,
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: blobA.x,
          top: blobA.y,
          width: 720,
          height: 720,
          borderRadius: '50%',
          background: accent,
          filter: 'blur(170px)',
          opacity: 0.32,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: blobB.x,
          top: blobB.y,
          width: 620,
          height: 620,
          borderRadius: '50%',
          background: theme.primaryLight,
          filter: 'blur(180px)',
          opacity: 0.18,
        }}
      />
      <AbsoluteFill
        style={{
          background:
            'radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,0.4) 100%)',
        }}
      />
    </AbsoluteFill>
  )
}
