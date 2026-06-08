import React from 'react'
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion'
import { PhoneFrame } from './PhoneFrame'

/**
 * Layout das cenas de feature: caption compacta no topo, celular GRANDE
 * dominando o quadro. O foco e a tela do app.
 */
export const PhoneStage: React.FC<{
  caption: React.ReactNode
  children: React.ReactNode
  scale?: number
}> = ({ caption, children, scale = 1 }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()

  const enter = spring({ frame, fps, config: { damping: 200, mass: 1.1 } })
  const y = interpolate(enter, [0, 1], [620, 0])
  const opacity = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: 'clamp' })

  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', top: 96, left: 0, right: 0, zIndex: 5 }}>{caption}</div>
      <div
        style={{
          position: 'absolute',
          top: 360,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
          transform: `translateY(${y}px)`,
          opacity,
        }}
      >
        <PhoneFrame scale={scale}>{children}</PhoneFrame>
      </div>
    </AbsoluteFill>
  )
}
