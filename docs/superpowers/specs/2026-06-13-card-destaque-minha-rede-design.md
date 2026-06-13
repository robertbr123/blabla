# Card de destaque "Minha Rede" na home

**Data:** 2026-06-13
**Status:** Design aprovado em conversa com Robert.

## Contexto

A feature "Minha Rede" (ver dispositivos conectados + trocar senha do WiFi via GenieACS, rota `/rede`) é uma das de maior valor pro cliente, mas hoje está pouco descoberta: é só um ícone entre vários na seção "Ações rápidas" (perto do fim da home) + um botão na tela Conexão. Objetivo: dar destaque de primeira classe na home.

## Decisões do brainstorming

1. **Abordagem:** card de destaque "vivo" na home (não 5ª aba na navbar, não promover no HeroCard). Mostra estado da rede ao vivo e leva pra tela completa.
2. **Dados ao vivo, estados graciosos:** cliente sem ONU mapeada → card some; com ONU → sempre aparece (skeleton no load; `—` + selo neutro se dados falharem mas ONU existe).
3. **Manter o ícone "Minha rede" nas "Ações rápidas"** (decisão do Robert) — card de destaque + atalho coexistem, sem remoção.

## Design

### Componente
`RedeDestaqueCard` — novo widget em `apps/cliente-mobile/lib/features/home/widgets/rede_destaque_card.dart` (ConsumerWidget).

### Posição
Na home (`home_screen.dart`), inserido **logo abaixo do bloco do HeroCard** e **antes do `QuickCardsRow`** (Fidelidade/Fale conosco).

### Dados — uma única chamada
- Observa `redeAparelhosProvider` (já existe; usado pela tela `/rede` e pela triagem da v3), **contrato-aware** via `contratoAtualProvider`.
- Esse endpoint (`GET /cliente-app/rede/aparelhos`) já devolve `encontrada`, `total` (dispositivos), `aparelhos` (lista) e `saude` (selo do sinal: excelente/boa/fraca/indisponivel) — tudo numa chamada só. Não adiciona segunda chamada GenieACS no load da home.

### Estados
- **`encontrada: false`** (sem ONU mapeada) → `SizedBox.shrink()` (some, igual aos mini-cards condicionais).
- **Loading** → skeleton shimmer do card; independente dos outros providers (não trava a home).
- **ONU existe, dados parciais/erro** → card aparece com `—` no número de dispositivos e selo neutro; atalho "trocar senha" continua funcionando.
- **Data OK** → cabeçalho `📶 Minha Rede` + selo de sinal; `{total} aparelhos conectados`; linha `🔑 Trocar senha do WiFi →`.
- **Pull-to-refresh** da home invalida `redeAparelhosProvider` junto com os demais providers.

### Navegação
Tocar em qualquer parte do card → `context.push('/rede')` (a tela Minha Rede é a casa dos dispositivos e da troca de senha). Reusa `PressableScale` (feedback de toque já padronizado).

### Visual
Card largo no estilo do design system, seguindo o padrão visual de `QuickCardsRow` (gradiente/superfície, raio, sombra). Selo de saúde reaproveita o estilo do `_SaudeBadge`/selo já presente em `rede_screen.dart` (extrair pra widget compartilhado se facilitar; senão replicar o estilo). `BrandTokens` + `withValues(alpha:)`. Claro e escuro corretos.

### Sem mudança de backend
Tudo consome endpoints/providers existentes. Sem migration, sem mudança de API/dashboard.

### Não-objetivos (YAGNI)
- Não vira aba na navbar.
- Não mostra status online/offline (evita 2ª chamada; o HeroCard já tem a pílula de conexão).
- Não remove o ícone das "Ações rápidas" nem o botão da Conexão.

## Testes
- Widget test do `RedeDestaqueCard`: some quando `encontrada: false`; mostra total + leva pra `/rede` no data; skeleton no loading. (Mock do provider via override do Riverpod.)
- `flutter analyze` + `flutter test`; smoke manual no device.
