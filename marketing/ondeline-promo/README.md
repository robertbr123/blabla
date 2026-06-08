# Ondeline — Vídeo promocional (Remotion)

Vídeo motion 9:16 (1080×1920) pra divulgar o app da Ondeline no Instagram,
Stories e status do WhatsApp.

## Rodar / editar
```bash
npm install
npm run dev        # abre o Remotion Studio pra editar e pré-visualizar
```

## Renderizar
```bash
npm run render         # versão completa ~50s -> out/ondeline-promo.mp4
npm run render:status  # corte ~30s p/ status -> out/ondeline-status-30s.mp4
```

## Estrutura
- `src/theme.ts` — cores da marca e specs (fps, tamanho)
- `src/components/` — `Background`, `PhoneFrame`, `Caption`, `Stage`, `Screens` (mockups das telas)
- `src/scenes/Scenes.tsx` — as 7 cenas
- `src/Promo.tsx` — timeline (durações de cada cena) das versões 50s e 30s
- `src/Root.tsx` — registra as composições `Promo` e `PromoStatus`
- `public/logo.png` — logo da Ondeline

## Locução
Script + dicas de ElevenLabs em [`LOCUCAO.md`](./LOCUCAO.md).

## Adicionar a voz no próprio vídeo (opcional)
Coloque `public/voiceover.mp3` e adicione um `<Audio src={staticFile('voiceover.mp3')} />`
no topo de `Timeline` em `src/Promo.tsx`, depois re-renderize.
