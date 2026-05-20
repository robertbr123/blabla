# Técnico Mobile iPhone Visual Refresh Design

## Contexto

O `apps/tecnico-mobile` já avançou em robustez funcional com offline, biometria e sessão local, mas a linguagem visual ainda transmite um app utilitário simples. No iPhone isso pesa ainda mais, porque o usuário compara o app com padrões nativos mais refinados de ritmo, hierarquia, tipografia, superfícies e navegação.

Hoje o maior incômodo está na dashboard, mas a intenção é refinar o app inteiro, começando pela tela principal e estendendo o sistema visual para `OS`, `Clientes`, `Estoque` e `Perfil`.

## Objetivo

Evoluir o app para uma experiência `premium proprietária com iOS nativo refinado`, em que:

- a home responde rapidamente o que o técnico precisa fazer agora
- a lista de OS continua sendo o centro da operação
- o visual parece produto pensado, não um CRUD adaptado
- a navegação e os componentes ficam consistentes entre todas as telas
- o iPhone ganha acabamento visual superior sem perder velocidade operacional

## Fora de Escopo

- reconstrução completa da arquitetura do app
- redesign para Android com linguagem divergente nesta fase
- animações complexas ou efeitos pesados que prejudiquem performance
- mudança de regras de negócio de OS, estoque, clientes ou perfil
- refatorações técnicas não relacionadas ao sistema visual e à hierarquia das telas

## Decisões de Produto

### Direção visual aprovada

A direção escolhida é:

- premium proprietária
- com comportamento visual inspirado em iOS refinado
- sem copiar o padrão Apple de forma literal

Isso significa:

- superfícies claras e sofisticadas
- contraste mais nobre do que “branco + azul padrão”
- cards com função clara e menos repetição visual
- tipografia com mais presença editorial
- navegação mais calma, limpa e confiante

### Hierarquia de navegação

O app passa a seguir um modelo `home-first`.

- a primeira experiência deixa de ser apenas uma lista crua de OS
- a home vira o centro operacional do dia
- a lista de OS continua dominante dentro da home
- `Estoque`, `Clientes` e `Perfil` continuam existindo como áreas de trabalho

No iPhone, a pergunta principal da primeira tela deve ser:

> “O que eu preciso fazer agora?”

e não:

> “Em qual módulo eu entro?”

### Dashboard prioriza OS

A dashboard não será um painel executivo pesado. Ela terá:

- resumo curto do dia
- contexto operacional
- filtros rápidos
- lista de OS prioritárias como conteúdo principal

As métricas existem, mas entram como apoio, não como protagonista.

## Abordagem Recomendada

Entre três caminhos possíveis:

1. `Home-first`
2. `OS-first refinado`
3. `Hybrid iPhone`

foi aprovada a opção `3`.

### O que isso significa

A home será uma tela híbrida:

- topo curto e premium
- resumo operacional do dia
- filtros/chips contextuais
- lista de OS como corpo dominante
- blocos secundários de status e atalhos em volta da lista, sem competir com ela

Essa abordagem preserva produtividade de campo e melhora fortemente a percepção de qualidade.

## Linguagem Visual

## 1. Paleta

A base visual deve fugir do aspecto “Flutter genérico”.

### Base

- fundo principal quente e claro
- branco quebrado / marfim para superfícies
- tons neutros levemente minerais para divisórias e planos secundários

### Cor de comando

- azul petróleo profundo ou marinho acinzentado como cor principal de ação

### Cor de destaque

- dourado discreto / âmbar elegante para prioridade, progresso e microênfase

### Resultado esperado

- contraste premium
- menos sensação hospitalar ou corporativa fria
- identidade própria sem ficar chamativa demais

## 2. Tipografia

A tipografia precisa comunicar confiança e clareza.

### Regras

- títulos maiores e mais fortes
- números com mais destaque nas áreas operacionais
- labels pequenos com bom espaçamento e uso controlado de caixa alta
- textos secundários menos “lavados”

### Sensação buscada

- mais editorial
- menos tabela administrativa

## 3. Superfícies e cards

Os cards deixam de ser apenas blocos repetidos com borda suave.

### Tipos de card

- card de resumo do dia
- card de métrica secundária
- card de OS prioritária
- card de atalho/contexto
- card de estado vazio

### Regras

- raio maior e mais consistente
- sombra curta e limpa
- bordas discretas
- mais respiro interno
- diferenciação por função, não só por texto

## 4. Movimento e estados

O comportamento precisa parecer iPhone refinado.

### Incluir

- transições suaves entre abas
- skeletons elegantes em carregamento
- estados offline e erro com aparência premium
- feedback visual sutil em ações principais

### Evitar

- animações longas
- excesso de blur
- microefeitos sem valor operacional

## Arquitetura de Navegação

## 1. Home principal

A primeira aba vira uma home operacional.

### Estrutura

1. header premium compacto
2. resumo do dia
3. filtros rápidos
4. lista de OS prioritárias
5. bloco opcional de atalhos/contexto

### Conteúdo do topo

- saudação curta ou marcador do dia
- total de OS do turno
- estado operacional resumido
- possível CTA discreto para ação principal

O topo deve ser forte, mas curto. A home não pode gastar altura demais antes de mostrar a lista de OS.

## 2. Abas inferiores

As quatro áreas principais continuam:

- Home
- Estoque
- Clientes
- Perfil

### Ajustes visuais

- `NavigationBar` mais leve
- ícones mais equilibrados
- label ativa mais refinada
- área ativa com mais sofisticação e menos “pill genérica”

### Observação

Se a lista completa de OS precisar existir separadamente no futuro, ela pode nascer como desdobramento da home e não obrigatoriamente como aba dedicada.

## Prioridades Tela por Tela

## 1. Home / Dashboard

Essa é a tela de maior impacto visual e deve ser o primeiro foco.

### Objetivo

Fazer o técnico sentir imediatamente:

- contexto
- prioridade
- ritmo do dia
- controle da operação

### Estrutura proposta

- hero operacional compacto
- chips de filtro premium (`pendentes`, `em andamento`, `prioridade`, `concluídas hoje`)
- lista de OS com card mais nobre e informativo
- agrupamentos claros por urgência ou estado

### Melhorias na lista de OS

- hierarquia melhor entre cliente, endereço, status e horário
- status com aparência mais proprietária
- CTA de ação mais claro
- menos ruído visual por card
- possibilidade de destacar 1 ou 2 OS prioritárias com tratamento especial

## 2. Detalhe da OS

Hoje a tela precisa parecer mais importante e menos utilitária.

### Melhorias

- cabeçalho de status mais forte
- blocos separados para dados, ações, fotos e observações
- ações primárias com destaque real
- leitura melhor para endereço, problema e conclusão
- área de fotos com mais presença visual

### Sensação desejada

O detalhe da OS precisa parecer “centro da missão”, não apenas formulário técnico.

## 3. Clientes

`Clientes` deve passar confiança e organização.

### Lista

- busca mais elegante
- cards menos secos
- melhor leitura de nome, endereço e situação

### Detalhe

- agrupamento mais claro das informações
- fotos com apresentação melhor
- email, endereço, plano e instalação com mais hierarquia

### Novo cliente

- fluxo continua eficiente
- visual do stepper e dos blocos deve parecer mais premium
- menos cara de formulário genérico

## 4. Estoque

`Estoque` hoje corre risco de parecer tabela improvisada.

### Melhorias

- cards ou linhas com melhor hierarquia
- saldo e categoria mais legíveis
- filtros e busca mais nobres
- movimentos e contexto operacional mais claros

### Meta

Manter rapidez sem sacrificar acabamento.

## 5. Perfil

`Perfil` deve ficar mais limpo e maduro.

### Melhorias

- foto do técnico melhor integrada
- sessão e biometria com aparência confiável
- agrupamento visual das ações de conta
- menos dispersão entre blocos

## Sistema de Componentes

Para que o redesign escale bem, a fase seguinte deve introduzir ou consolidar:

- tokens de cor
- tokens de espaçamento
- tokens de raio
- variantes de card
- variantes de chips/status
- padrões consistentes de header por tela

Sem isso, o redesign corre o risco de virar melhoria pontual da dashboard apenas.

## Requisitos de UX

- o primeiro viewport da home deve mostrar contexto e começar a lista de OS sem exigir rolagem exagerada
- o app deve continuar rápido em aparelhos modestos
- os estados offline precisam parecer parte do produto, não fallback improvisado
- ações frequentes precisam continuar acessíveis com uma mão
- cada tela deve ter um foco visual evidente

## Critérios de Sucesso

Consideraremos essa evolução bem-sucedida quando:

- a home parecer claramente uma tela principal premium
- a lista de OS continuar rápida, mas visualmente superior
- `Clientes`, `Estoque` e `Perfil` seguirem a mesma linguagem visual
- o app no iPhone parecer mais próximo de um produto nativo sofisticado do que de um painel administrativo mobile
- a melhoria visual acontecer sem regressão perceptível de performance

## Sequenciamento Recomendado

### Fase 1

- tokens visuais base
- nova home/dashboard
- refinamento da navegação inferior
- ajustes dos cards de OS

### Fase 2

- detalhe de OS
- clientes lista/detalhe/novo cliente

### Fase 3

- estoque
- perfil
- estados vazios, loading, erro e offline

## Arquivos e Áreas Esperadas

As mudanças devem se concentrar principalmente em:

- `apps/tecnico-mobile/lib/features/shell/main_shell.dart`
- `apps/tecnico-mobile/lib/features/os/os_list_screen.dart`
- `apps/tecnico-mobile/lib/features/os/widgets/*`
- `apps/tecnico-mobile/lib/features/os/os_detail_screen.dart`
- `apps/tecnico-mobile/lib/features/clientes/*`
- `apps/tecnico-mobile/lib/features/estoque/*`
- `apps/tecnico-mobile/lib/features/perfil/*`
- tema/tokens compartilhados do app

## Riscos e Cuidados

- exagerar no hero e empurrar a lista de OS para baixo
- introduzir um visual premium genérico sem identidade própria
- aumentar complexidade visual e prejudicar velocidade operacional
- criar inconsistência entre a nova home e as demais telas
- usar efeitos pesados demais para aparelhos de campo

## Decisão Final

O redesign do `tecnico-mobile` para iPhone seguirá a direção:

- `Hybrid iPhone`
- base visual `A / Command Center`
- foco principal em lista de OS
- refinamento premium proprietário com comportamento nativo de iOS

Essa decisão serve como base para o próximo plano de implementação tela por tela.
