# Técnico Mobile Offline + Login Design

## Contexto

O app `apps/tecnico-mobile` já possui base de cache local para OS e uma `outbox` para ações offline, mas ainda apresenta lacunas importantes:

- o backoff da sincronização usa `createdAt` e não o instante da última tentativa
- `estoque` e `perfil` dependem 100% da API e quebram sem rede
- ações offline de `iniciar` e `concluir` não atualizam o cache local de forma otimista
- a experiência de login ainda é básica e não oferece reentrada biométrica no iOS

O objetivo desta entrega é transformar essas áreas em um fluxo coerente, mais robusto tecnicamente e melhor para operação em campo.

## Objetivos

- corrigir o algoritmo de retry da `outbox` para evitar rajadas de reenvio e duplicidade
- tornar `estoque` e `perfil` utilizáveis offline com cache persistente
- refletir ações offline de OS imediatamente na UI por meio de atualização otimista do cache local
- redesenhar o login com linguagem visual premium de app nativo
- habilitar reentrada por `Face ID` no iOS após o primeiro login bem-sucedido
- garantir que `logout` manual apague toda a sessão e todos os dados locais
- garantir que `401` invalide a sessão local e force retorno ao login completo

## Fora de Escopo

- refresh token / renovação automática de sessão no backend
- sincronização em background com app morto ou via scheduler nativo
- Android biométrico como parte obrigatória desta entrega
- refatorações grandes fora das áreas tocadas
- redesign completo das demais telas além dos ajustes necessários para coerência visual

## Decisões de Produto

### Reentrada biométrica

- o primeiro acesso continua sendo por `email + senha`
- após um login bem-sucedido, o app pode oferecer reentrada biométrica
- a biometria será usada apenas para desbloquear a sessão já salva no dispositivo
- o fluxo alvo é iOS com `Face ID`
- a tela de reentrada será curta e mostrará:
  - nome do técnico
  - botão principal `Entrar com Face ID`
  - ação secundária `Entrar com email e senha`

### Logout e expiração

- `logout` manual apaga tudo localmente
- o app exige login completo após logout
- qualquer `401` relevante em área autenticada deve invalidar a sessão local e redirecionar para o login completo
- após a sessão ser invalidada, o fluxo biométrico não é mais exibido até um novo login bem-sucedido

### Direção visual do login

A tela de login seguirá a direção visual aprovada `A`:

- hero compacto com presença de marca
- card principal de autenticação com contraste forte e leitura rápida
- sensação premium nativa em vez de “painel web adaptado”
- suporte futuro natural para o estado de reentrada biométrica

## Arquitetura Proposta

## 1. Sincronização offline

### Problema atual

Hoje o cálculo de retry se baseia em `createdAt`, o que faz itens antigos virarem elegíveis repetidamente mesmo após várias falhas. O repositório também não grava o instante da última tentativa.

### Solução

Adicionar rastreamento explícito de última tentativa na `outbox`:

- nova coluna `lastAttemptAt`
- `markAttempt()` passa a incrementar `attempts`, registrar `lastError` e atualizar `lastAttemptAt`
- `_shouldAttempt()` passa a usar `lastAttemptAt ?? createdAt`
- o backoff continua exponencial com limite máximo, mas agora baseado no último envio tentado

### Regras

- sucesso marca `sentAt`
- falha de rede ou timeout mantém item pendente
- falha 4xx continua registrada com erro e respeita backoff
- o sistema não deve entrar em loop agressivo de retry

## 2. Cache offline para estoque e perfil

### Problema atual

`Estoque` e `Perfil` consultam a API diretamente e falham completamente sem conexão.

### Solução

Levar ambos para o banco local com o mesmo modelo já usado em OS:

- `estoque` terá tabela local própria
- `perfil` terá tabela local própria
- providers passam a usar padrão `read-through`

Fluxo `read-through`:

1. UI lê imediatamente do banco local
2. app tenta refresh online em background
3. se a API responder, atualiza o cache
4. se falhar por conectividade, mantém último snapshot funcional

### Regras de consistência

- logout limpa tabelas locais de estoque e perfil
- se não houver cache e a API falhar, a UI mostra erro normal
- se houver cache e a API falhar, a UI continua funcional com dado local

## 3. Atualização otimista de OS

### Problema atual

Quando o técnico inicia ou conclui uma OS offline, a UI continua exibindo o estado anterior até a próxima sync/refetch.

### Solução

Adicionar mutações locais no repositório de OS:

- `markStartedOptimistic(osId, location?)`
- `markConcludedOptimistic(osId, payload, location?)`

Essas mutações atualizam o `payloadJson` persistido e campos derivados da OS local.

### Regras de UI

- `iniciar` deve mover a OS para `em_andamento` imediatamente
- `concluir` deve mover a OS para `concluida` imediatamente
- a tela de detalhe e a lista devem refletir o novo status sem esperar rede
- a UI deve deixar de oferecer ações incompatíveis com o novo estado

### Relação com a sync

- a `outbox` continua sendo a fonte do envio posterior
- a mutação otimista cuida apenas da experiência local
- a próxima leitura online pode reconciliar o estado real do backend

## 4. Sessão local e biometria

### Modelo de sessão

Separar duas preocupações:

- token e sessão autenticada
- preferência/capacidade de reentrada biométrica

### Estado salvo

Após login com sucesso, salvar:

- token atual
- identificadores básicos do usuário
- nome do técnico para a tela curta de reentrada
- flag de sessão elegível para biometria

### Fluxo de abertura do app

1. app inicia
2. se não houver sessão salva, abre login completo
3. se houver sessão salva e biometria disponível/ativada, abre tela curta de reentrada
4. ao autenticar por `Face ID`, o app libera a navegação principal
5. se o usuário escolher fallback, vai para login completo

### Falhas

- falha de biometria não deve apagar a sessão imediatamente
- cancelamento da biometria mantém a tela curta disponível
- `401` da API apaga sessão e volta para login completo
- logout manual apaga sessão, biometria e cache

## 5. Login premium

### Estrutura visual

A nova tela de login terá:

- fundo com hero compacto e identidade da marca
- card de autenticação central como elemento primário
- hierarquia clara para email, senha, erro e ação principal
- espaço reservado para mensagem de reentrada biométrica no estado futuro

### Requisitos funcionais

- loading claro durante autenticação
- mensagens de erro menos genéricas quando possível
- foco em rapidez operacional
- preparação para alternar entre:
  - login completo
  - tela curta de reentrada biométrica

### Requisitos de UX

- visual premium, mas não carregado
- leitura excelente em aparelhos modestos
- contraste forte
- nada de depender de animações pesadas

## Componentes e Arquivos Esperados

### Banco e repositórios

- expandir schema Drift atual
- adicionar repositórios locais de estoque e perfil
- adicionar mutações otimistas no repositório de OS

### Sync

- ajustar `outbox_repo` e `sync_service`
- revisar cálculo de elegibilidade para retry

### Auth e sessão

- evoluir `auth_storage` para armazenar dados mínimos de reentrada
- adicionar serviço/controlador de biometria
- ajustar bootstrap e roteamento inicial para suportar:
  - login completo
  - reentrada biométrica

### UI

- redesign de `login_screen`
- nova tela curta de reentrada
- pequenos ajustes nas telas de OS para refletir estado otimista

## Tratamento de Erros

- falha de refresh online com cache disponível não derruba a UI
- falha de biometria não deve causar logout automático
- `401` limpa sessão e navega para login
- falha no cache local deve ser tratada como erro operacional da feature, sem corromper as demais

## Estratégia de Testes

### Unidade

- cálculo de backoff usando `lastAttemptAt`
- `markAttempt()` atualizando timestamp e tentativas
- mutações otimistas de OS
- serialização e leitura de cache local para estoque e perfil
- regras de sessão biométrica e fallback

### Widget

- login premium em estados:
  - idle
  - loading
  - erro
- tela curta de reentrada com nome do técnico
- mudança de ações visíveis após mutação otimista de status

### Integração local

- provider de estoque funcionando com cache sem rede
- provider de perfil funcionando com cache sem rede
- OS iniciada offline reaparecendo como `em_andamento`
- OS concluída offline reaparecendo como `concluida`

## Impacto em Documentação

Atualizar README do app para refletir:

- o que já é realmente offline
- o que passa a ter cache local
- o novo fluxo biométrico no iOS
- o comportamento de logout e expiração de sessão

## Critérios de Aceite

- itens da `outbox` respeitam backoff baseado na última tentativa
- `estoque` funciona com último snapshot local sem conexão
- `perfil` funciona com último snapshot local sem conexão
- `iniciar` e `concluir` offline atualizam a UI imediatamente
- app mostra tela curta de reentrada após primeiro login salvo
- `Face ID` libera a entrada no app no iOS quando disponível
- fallback para login completo permanece acessível
- logout manual apaga todos os dados locais
- `401` leva para login completo e remove a sessão salva
