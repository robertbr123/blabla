# Offline Bloco B — Cadastro de cliente offline — Design

**Data:** 2026-06-11
**App:** `apps/tecnico-mobile`

## Objetivo
Permitir o técnico **cadastrar cliente sem internet** (rascunho local) e **enviar com 1 toque** quando a rede voltar. Só app (CPF como idempotência), sem mudança de backend.

## Descoberta que simplifica
O cadastro **não tem fotos no fluxo** (`cliente_novo` só faz `criar(body)` → vai pro detalhe; fotos são anexadas depois, online, na tela de detalhe). Então:
- O cadastro é **1 POST** (`/api/v1/clientes-campo`, cria cliente + baixa estoque atômica).
- O **rascunho é só o payload JSON** (sem copiar fotos).

## Componentes

### 1. Planos offline (pré-requisito do form)
- `PrefetchService` (Bloco A) passa a cachear os **planos SGP**: GET `/api/v1/sgp/planos` → grava num arquivo `planos_cache.json` (helper em `lib/core/sync/planos_cache.dart`: `writePlanos(raw)` / `readPlanos()`).
- `planosProvider` (`cliente_form_data.dart`): mantém o fluxo atual (SGP → fallback `/planos`); adiciona um **último fallback** pro `planos_cache.json` quando dá erro de rede. Sucesso online também atualiza o cache.

### 2. `CadastroDraftRepo` (file-based, sem Drift/codegen)
`lib/core/sync/cadastro_draft_repo.dart`. Cada rascunho = um arquivo JSON em `<appDocs>/cadastro_drafts/<draftId>.json`:
```json
{ "id": "...", "created_at": "ISO", "cpf": "...", "nome": "...", "payload": { <CreateClienteCampoIn.toJson()> } }
```
- `draftId` = `DateTime.now().microsecondsSinceEpoch` em string (único por device).
- Métodos: `Future<void> save({required Map<String,dynamic> payload, required String cpf, required String nome})`, `Future<List<CadastroDraft>> list()` (ordenado por created_at desc), `Future<void> delete(String id)`.
- Model `CadastroDraft { id, createdAt, cpf, nome, payload }`.
- Provider `cadastroDraftRepoProvider` + `cadastroDraftsProvider` (FutureProvider<List<CadastroDraft>>).

### 3. Submit offline (`cliente_novo_screen._enviar`)
- Monta o `body` como hoje. Decisão:
  - **Offline** (`connectivityStatusProvider.value == false`): salva rascunho (`repo.save(payload: body.toJson(), cpf, nome)`) → toast "Cadastro salvo offline. Envie quando tiver sinal." → `context.go('/clientes')`. NÃO tenta o POST.
  - **Online**: fluxo atual (`criar` → `pushReplacement('/clientes/$id')`). Se o `criar` falhar com **erro de rede** (timeout/connection) → fallback: salva rascunho + toast + volta. Outros erros (409/validação) → mostra o erro como hoje (não vira rascunho).

### 4. Pendentes + envio (lista de Clientes)
- **Banner** (sliver) na lista de Clientes, logo após o header/chip-offline, quando `cadastroDraftsProvider` tem itens: "N cadastro(s) pendente(s) de envio" → abre um **sheet**.
- **Sheet** (`cadastro_drafts_sheet.dart`): lista cada rascunho (nome · CPF · "há X"), com **Enviar** (habilitado só online) e **Descartar** (confirma).
- **Envio (1 toque):** `ClienteFormActions.criar(payload)` (reusa o existente, recebendo o Map do payload):
  - **Sucesso** → `repo.delete(id)` + invalida `cadastroDraftsProvider` + `clientesListProvider` + toast "Cliente cadastrado.".
  - **409 "CPF já existe"** (detail contém "CPF") → trata como já criado → `repo.delete(id)` + toast "Cliente já estava cadastrado.".
  - **409 saldo insuficiente / outros / rede** → mantém o rascunho + erro claro (ex: "Estoque insuficiente — ajuste e tente de novo.").

## Não muda
- Backend; fluxo online de cadastro; fotos (seguem pós-criação na tela de detalhe); providers cache-first/prefetch do Bloco A (só estendidos p/ planos).

## Critérios de sucesso
1. Offline (após prefetch): abrir "Novo cliente", preencher (planos do cache, materiais do cache), salvar → vira rascunho; toast; volta pra lista com o banner "1 pendente".
2. Online: banner → sheet → Enviar → cliente criado, rascunho some, lista atualiza.
3. Reenvio do mesmo CPF (já criado) → tratado como sucesso (rascunho some, sem duplicar).
4. Saldo insuficiente no envio → rascunho permanece + erro claro.
5. Online normal de cadastro inalterado.
6. `flutter analyze` limpo (deploy).

## Riscos
- `ClienteFormActions.criar` hoje recebe `CreateClienteCampoIn`; pro envio do rascunho precisa aceitar o **Map** do payload (adicionar `criarFromJson(Map)` ou refatorar `criar` p/ receber Map). Manter compat.
- Planos cache pode ficar velho (planos do SGP mudam pouco) — aceitável; atualiza a cada prefetch online.
- Sem teste automatizado (file IO + network/UI sem harness) — validar via analyze + on-device.
- ViaCEP offline não autocompleta (o técnico digita endereço na mão) — comportamento atual já tolera (campos manuais).
