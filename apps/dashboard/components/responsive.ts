/**
 * Classes utilitárias de responsividade compartilhadas entre telas.
 * (Arquivo em `components/` pra entrar no `content` do Tailwind.)
 */

/**
 * `FilterTabs` em uma linha só no celular: abaixo de `md` as abas rolam na
 * horizontal (sem barra de rolagem visível) em vez de quebrar em várias linhas.
 * De `md` pra cima nada muda.
 */
export const TABS_SCROLL =
  'max-w-full [&>button]:shrink-0 [&>button]:whitespace-nowrap ' +
  'max-md:flex-nowrap max-md:overflow-x-auto max-md:[scrollbar-width:none] max-md:[&::-webkit-scrollbar]:hidden'

/**
 * `PanelHeader` com ações largas (segmentado + botão): deixa as ações caírem
 * pra segunda linha em vez de espremer/truncar o título. Em telas largas a
 * altura continua a mesma (44px).
 */
export const PANEL_HEADER_WRAP = 'h-auto min-h-11 flex-wrap gap-y-1.5 py-2'

/**
 * `StatTile` em grade de 2 colunas no celular: o rótulo quebra em duas linhas
 * em vez de truncar ("CONVERSAS A…").
 */
export const TILE_LABEL_WRAP = 'max-sm:[&_.eyebrow]:whitespace-normal'
