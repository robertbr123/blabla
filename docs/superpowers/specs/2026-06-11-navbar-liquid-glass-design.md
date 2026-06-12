# Navbar Liquid Glass — Design

**Data:** 2026-06-11
**App:** `apps/tecnico-mobile` (Flutter — técnico em campo)
**Componente:** `lib/core/branding/brand_bottom_nav.dart` (`BrandBottomNav`)

## Objetivo

Transformar o bottom nav atual (pill flutuante com bolha emerald sólida sobre
`surfaceContainer` opaco) num visual **liquid glass** estilo iOS 26: cápsula
flutuante translúcida com blur e uma "lente" de vidro especular que desliza pro
item ativo. Tema claro é o foco (default do app); o tema escuro recebe um
tratamento grafite equivalente porque o app tem toggle light/dark.

Direção escolhida via mockups: **Opção C — liquid glass com lente especular**
(não a barra full-width estilo WhatsApp puro nem o pill frosted simples).

## Escopo

**Muda:** apenas o widget `BrandBottomNav` e seus internos (`_NavSlot`).

**NÃO muda:**
- API pública do componente: `selectedIndex` (int), `onSelect` (ValueChanged<int>),
  `items` (List<BrandNavItem>). Logo `MainShell` permanece intacto.
- `BrandNavItem` (icon / selectedIcon / label).
- Número de tabs (4), ícones, labels.
- `MainShell`: `extendBody: true`, PageView, FAB "Novo" (tab Clientes), animação
  de troca de página.
- Animação de troca de aba (220ms easeOutCubic no PageController).

## Layout

- Pill flutuante mantém posição atual: `SafeArea(top:false)` + `Padding` lateral
  (~14) e bottom (~10–12).
- Altura ~60–62, cantos ~26 (hoje 22 — sobe um pouco pro look glass).
- O conteúdo da tela passa por trás (já garantido por `extendBody: true`).

## Vidro (estrutura de camadas)

Ordem de empilhamento, de baixo pra cima, **tudo dentro de um `ClipRRect`** com o
mesmo raio (obrigatório — sem o clip o `BackdropFilter` vaza pra tela toda):

1. `BackdropFilter(filter: ImageFilter.blur(sigmaX: ~20, sigmaY: ~20))` —
   desfoca o conteúdo atrás. Aplicar `saturation`/tint via a camada de cor acima.
2. Camada de cor translúcida com gradiente vertical:
   - **Claro:** branco `rgba(255,255,255,0.55)` → `0.32`.
   - **Escuro:** grafite `rgba(40,46,50,0.55)` → `rgba(28,32,36,0.42)`.
3. Borda hairline (`Border.all`):
   - **Claro:** branco `0.7`. **Escuro:** branco `0.14`.
4. Sombra externa (boxShadow no Container externo, fora do ClipRRect) +
   *inset highlight* no topo simulando a borda de vidro:
   - Externa claro: preto `0.22`, blur ~34, offset (0,12).
   - Externa escuro: preto `0.5`, blur ~36, offset (0,14).
   - Inset highlight: linha clara no topo (branco `0.9` claro / `0.18` escuro).

> Nota de implementação: `boxShadow` precisa ficar no Container **externo** ao
> `ClipRRect` (o clip corta a sombra). A borda e o inset-highlight ficam na
> camada de cor interna.

## Lente de seleção (substitui a bolha atual)

- Mantém `AnimatedPositioned` deslizando entre slots, curve `Curves.easeOutBack`,
  duração 420ms (igual hoje). `left = selectedIndex * slotW + inset`.
- Visual da lente:
  - **Claro:** gradiente branco `0.9 → 0.4`, borda branca `0.95`, glow emerald
    sutil (`shadow emerald 0.30`, blur ~12) + inset highlight branco no topo.
  - **Escuro:** gradiente emerald `0.30 → 0.12`, borda emerald `0.5`, glow emerald.
- Cantos da lente ~22.

## Item (ícone + label) — `_NavSlot`

Mantém o comportamento de microinteração atual:
- Ícone troca outlined→filled via `AnimatedSwitcher` com "pulinho" (scale
  easeOutBack, 220ms).
- Label com `AnimatedDefaultTextStyle` (peso w500→w700, 220ms).
- Haptic `HapticFeedback.selectionClick()` na troca (já existe em `_handleTap`).
- Cores:
  - Ativo: ícone/label emerald — claro `#047857`, escuro `#34d399`.
  - Inativo: cinza com peso suficiente pra contraste sobre vidro
    (`onSurfaceVariant` ou cinza explícito ~`rgba(70,80,80,0.9)` claro).

## Acessibilidade

- Mantém `Semantics(button: true, selected: ..., label: item.label)` por slot.
- Garantir contraste do label inativo sobre o vidro (não usar cinza claro demais).
- Tap target: cada slot ocupa 1/N da largura × 60px de altura — acima do mínimo.

## Performance / fallback

- `BackdropFilter` é aplicado só nessa barra de ~60px de altura, GPU-acelerado —
  custo baixo mesmo rolando a lista atrás.
- **Fallback** (decidir só se algum aparelho antigo de campo engasgar no teste
  real): reduzir `sigma` do blur, ou trocar por fundo semi-opaco sem
  `BackdropFilter`. Não implementar fallback agora (YAGNI até haver evidência).

## Critérios de sucesso

1. Nav aparece translúcido com blur visível do conteúdo atrás (claro e escuro).
2. Lente desliza suavemente entre as 4 abas ao trocar.
3. `MainShell` e a API do componente não precisaram de nenhuma alteração.
4. `flutter analyze` limpo (validado na máquina de deploy — sem stack local aqui).
5. Sem regressão de haptic, ícone-pop ou label weight.
