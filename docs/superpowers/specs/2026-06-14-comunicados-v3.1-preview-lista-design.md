# Comunicados v3.1 — CSV exemplo só-audiência + lista de quem vai receber

**Data:** 2026-06-14
**Status:** Aprovado (seguindo direto pro plano)
**Base:** ajustes sobre Comunicados v3 (`2026-06-13-comunicados-v3-import-filtravel-tracking-design.md`).

## Contexto

Dois ajustes pedidos no uso real:
1. O CSV de exemplo empurrava `link`/`nome` como coluna — mas o link/variável o operador prefere **digitar no formulário** (valor igual pra todos). CSV deve ser só a **audiência**.
2. Antes de disparar, ver só a **contagem** não basta — quer ver a **lista de quem vai receber** (nome/telefone/cidade) conforme o filtro, igual deveria ser nos dois modos (segmento e import).

## Decisões
- Lista pré-disparo = **amostra (até 30) + total** ("mostrando 30 de X"). Lista completa fica na tela da campanha (já existe, com status + export).
- CSV de exemplo = `telefone;cidade;status;plano` (sem colunas de variável). Colunas de variável seguem **suportadas** (opcionais), só não aparecem no exemplo/ajuda.
- Sem mudança de banco.

## Bloco 1 — CSV exemplo só-audiência (frontend)
No `comunicado-form.tsx`:
- `baixarExemplo()` gera:
  ```
  telefone;cidade;status;plano
  5592991112222;Manaus;Ativo;100MB
  559784272884;Eirunepe;Ativo;50MB
  ```
- Texto de ajuda: "CSV com a coluna de telefone + (opcional) cidade, status, plano para filtrar. O conteúdo da mensagem (links etc.) você preenche no formulário."

## Bloco 2 — Lista de quem vai receber (amostra + total)

### Segmento da base
- `/preview` já retorna `{total, amostra}` com `amostra = [{id, nome, whatsapp, cidade}]`. Subir o limite da amostra de 10 → **30** (chamar `amostra_segmento(..., limite=30)` no endpoint).
- Form: abaixo do "X clientes vão receber", renderizar tabela **nome · telefone · cidade** da `preview.data.amostra` + rodapé "mostrando N de X".

### Importar CSV
- `POST /{id}/destinatarios/contagem` passa a retornar `{total, amostra}` onde `amostra = [{whatsapp, cidade, status}]` (até 30) dos `pendente` que casam o filtro.
  - Novo método `CampanhaRepo.amostra_selecionados(campanha_id, filtros, limite=30)` → lista de `CampanhaDestinatario` (pendente + match), do qual o endpoint extrai `{whatsapp, cidade=csv_cidade, status=csv_status}`.
- Schema `ContagemOut` ganha `amostra: list[AmostraDestinatario]` (campos `whatsapp, cidade, status` — todos opcionais p/ cidade/status).
- Form: tabela **telefone · cidade · status** da amostra + "mostrando N de X".

## API
- `ContagemOut` → `{ total: int, amostra: list[{whatsapp, cidade, status}] }`.
- `/preview` inalterado no contrato (amostra já existe); só muda o limite interno p/ 30.

## Frontend (tipos/hooks)
- `PreviewResult.amostra` já existe (`{id, nome, whatsapp, cidade}`).
- `useContagemImport` passa a retornar `{ total, amostra }`; tipo novo `AmostraImport {whatsapp, cidade, status}`.

## Testes (CI/deploy)
- `amostra_selecionados`: respeita filtro (só os que casam), respeita limite, só `pendente`.

## Fora de escopo
- Lista completa/paginada pré-disparo (fica na tela da campanha pós-disparo, já existente).
