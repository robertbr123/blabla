import React from 'react'
import { AbsoluteFill, Sequence, Audio, staticFile } from 'remotion'
import { Background } from './components/Background'
import {
  HookScene,
  IntroHomeScene,
  FaturasScene,
  SuporteScene,
  FidelidadeScene,
  AvisosScene,
  CTAScene,
} from './scenes/Scenes'

/**
 * Sequencia de cenas (30fps). A versao completa esta cronometrada pra casar
 * com a narracao do Gabriel (~47,5s = 1424 frames). A soma das duracoes bate
 * com durationInFrames em Root.tsx.
 */
type Block = { Comp: React.FC; dur: number }

// Duracoes ajustadas (x0.95) pra fechar em 1424 frames ~= 47,46s (locucao).
const FULL: Block[] = [
  { Comp: HookScene, dur: 142 },
  { Comp: IntroHomeScene, dur: 171 },
  { Comp: FaturasScene, dur: 256 },
  { Comp: SuporteScene, dur: 256 },
  { Comp: FidelidadeScene, dur: 228 },
  { Comp: AvisosScene, dur: 199 },
  { Comp: CTAScene, dur: 172 },
]

// Corte de ~30s para o status do WhatsApp (sem locucao embutida).
const STATUS: Block[] = [
  { Comp: HookScene, dur: 90 },
  { Comp: IntroHomeScene, dur: 120 },
  { Comp: FaturasScene, dur: 240 },
  { Comp: SuporteScene, dur: 150 },
  { Comp: FidelidadeScene, dur: 150 },
  { Comp: CTAScene, dur: 150 },
]

const Timeline: React.FC<{ blocks: Block[]; voiced?: boolean }> = ({ blocks, voiced }) => {
  let cursor = 0
  return (
    <AbsoluteFill>
      <Background />
      {blocks.map(({ Comp, dur }, i) => {
        const from = cursor
        cursor += dur
        return (
          <Sequence key={i} from={from} durationInFrames={dur}>
            <Comp />
          </Sequence>
        )
      })}
      {voiced && (
        <>
          {/* Narração do Gabriel (ElevenLabs) — volume cheio */}
          <Audio src={staticFile('voiceover.mp3')} />
          {/* Trilha de fundo — bem baixa pra não competir com a voz */}
          <Audio src={staticFile('music.mp3')} volume={0.16} />
        </>
      )}
    </AbsoluteFill>
  )
}

export const FULL_DURATION = FULL.reduce((a, b) => a + b.dur, 0) // 1424
export const STATUS_DURATION = STATUS.reduce((a, b) => a + b.dur, 0) // 900

export const Promo: React.FC = () => <Timeline blocks={FULL} voiced />
export const PromoStatus: React.FC = () => <Timeline blocks={STATUS} />
