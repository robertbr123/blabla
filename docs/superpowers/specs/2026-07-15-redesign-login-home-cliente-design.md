# Redesign Login + Home — cliente-mobile (identidade "Vibrante de marca")

**Data:** 2026-07-15
**Escopo:** apps/cliente-mobile — telas de login, reset de senha e home.
**Status:** aprovado por Robert (brainstorm com mockups visuais; direção C escolhida entre 3 propostas, layout C1+C2 híbrido aprovado).

## Objetivo

Dar identidade própria e mais vibrante ao app do cliente: o ciano da marca Ondeline
vira protagonista, com tipografia grande e confiante. Login mais rápido (biometria +
CPF lembrado) e home com hierarquia clara (status e fatura primeiro), sem remover
nenhum card existente.

## Linguagem visual (direção C)

- **Capa ciano:** gradiente `#14B8B0 → #0F8F89 → tom profundo`, usado no topo do
  login e da home. Elemento decorativo de "onda" sutil (opacity baixa).
- **Tipografia display:** títulos weight 800–900, letter-spacing negativo (-0.5 a
  -1.2), tamanhos grandes (26–34). No login, brinca com a marca: "onde você estiver."
- **Folha:** container claro com cantos superiores 26–28px sobreposto à capa
  (margin-top negativa), onde vive o conteúdo/formulário — perto do dedão.
- **Cards:** brancos, radius 16–18, sombra suave (`shadowCard`/`elevation2`).
- **Modo escuro:** capa ciano permanece igual; a folha usa `backgroundDark`
  (`#051329`) e os cards `surfaceDark` (`#0B1F3A`). Login é visualmente igual nos
  dois modos.
- **Tokens:** novos tokens entram como **adições** em `BrandTokens` (gradiente da
  capa, radius da folha, estilos de display text). Nada existente muda de valor —
  as demais telas não são afetadas nesta fase.

## Tela de login

Layout: capa ciano ocupando o topo (tipografia display + tagline "Ondeline —
internet que acompanha você."), formulário em folha branca ancorada na base.

Funcional:
- Campos CPF (máscara atual) e senha; validação e fluxo `authRepository.login`
  inalterados.
- **Lembrar CPF:** último CPF logado fica salvo localmente e pré-preenche o campo
  (prioridade menor que `initialCpf` vindo do onboarding).
- **Biometria:** via `local_auth`. Após login com senha bem-sucedido, oferece
  ativar Face ID/digital (opt-in). Com biometria ativa, a tela mostra botão
  "Entrar com Face ID/digital" que autentica e reusa a sessão/refresh token
  guardado em storage seguro (`flutter_secure_storage`). Fallback sempre
  disponível pra senha. Logout limpa a opção.
- "Esqueci minha senha" e "Criar conta" permanecem (links na folha).
- `forgot_reset_screen` ganha a mesma roupagem (capa + folha), lógica intacta.

## Tela home

Estrutura (ordem):
1. **Breaking bar de manutenção** (existente) — acima de tudo quando ativa.
2. **Capa ciano:** saudação por horário ("Bom dia/Boa tarde/Boa noite, {nome}"),
   sino de notificações, e **bloco de status integrado**: conexão ativa · nome do
   plano · nº de aparelhos conectados · selo de sinal · atalho "Minha rede →".
   - Dados do `redeAparelhosProvider` (mesma fonte do `RedeDestaqueCard` atual).
   - Degradê gracioso: sem ONU mapeada (`encontrada=false`) ou erro, o bloco
     mostra só status da conexão + plano (dados do `meProvider`), sem a linha de
     aparelhos.
   - O `RedeDestaqueCard` do meio da lista é **absorvido** por este bloco (única
     "remoção", por promoção ao topo).
3. **Folha clara** com, em ordem:
   - **Card de fatura em aberto** com valor, vencimento e CTA "Pagar Pix"
     (navega pra faturas/QR). Some quando não há fatura em aberto. Usa dados já
     disponíveis via providers atuais (sem backend novo).
   - **Ações rápidas** (existente). "Minha rede" permanece aqui mesmo com o
     atalho no topo: é o único acesso quando a ONU não está mapeada e o bloco do
     topo não mostra a linha de rede.
   - **QuickCardsRow** (fidelidade + WhatsApp 24h — existente).
   - **CardDoDia** (existente).
   - **Carrossel de promoções** "Pra você" (existente).
   - **AniversarianteBanner** (existente, condicional).
   - **AvisosList** (existente).
4. Navbar flutuante e comportamentos atuais (NPS auto-popup, pull-to-refresh,
   cache last-known) inalterados.

## Fora de escopo (fases futuras)

- Demais telas (faturas, suporte, rede, perfil...) — herdarão a linguagem depois.
- Navbar/shell.
- Mudanças de backend/API.

## Erros e estados

- Home mantém skeleton de hero + fallback de cache (`_CachedHeroOrError`)
  adaptados ao novo layout da capa.
- Biometria indisponível no aparelho → botão não aparece.
- Falha de biometria → cai pra senha com mensagem discreta.

## Testes

- `flutter analyze` limpo (gate de CI).
- Testes de widget existentes que tocam login/home ajustados; smoke test de
  build das duas telas nos dois temas.
- Validação manual (Robert) no aparelho após deploy — sem dev stack local.
