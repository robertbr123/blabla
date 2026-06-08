import React from 'react'
import { Composition } from 'remotion'
import { Promo, PromoStatus, FULL_DURATION, STATUS_DURATION } from './Promo'
import { FPS, WIDTH, HEIGHT } from './theme'

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Promo"
        component={Promo}
        durationInFrames={FULL_DURATION}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="PromoStatus"
        component={PromoStatus}
        durationInFrames={STATUS_DURATION}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
    </>
  )
}
