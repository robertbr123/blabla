# Comunicados — Editar e Excluir

**Data:** 2026-06-15
**Status:** Aprovado (pendente implementação)

## Problema

No sistema de Comunicados (disparo em massa WhatsApp Cloud), uma campanha em
`rascunho` fica "presa": dá pra enviar, cancelar ou testar, mas **não dá pra
editar** (corrigir título/template/params) nem **excluir** (jogar fora um
rascunho de teste). Os endpoints atuais cobrem criar/listar/ver/enviar/cancelar/
testar/importar/reenviar/exportar — falta `DELETE` e `PATCH`.

## Decisões

- **Excluir:** hard delete, permitido em **qualquer status exceto `enviando`**.
  - `enviando` é bloqueado (HTTP 409): apagar no meio do disparo derruba o
    worker Celery, que itera os destinatários enquanto o cascade os apaga. Fluxo
    correto: `/cancel` primeiro, depois excluir.
  - Concluída/cancelada/erro/rascunho: apagáveis. (Robert priorizou limpeza do
    histórico sobre retenção de auditoria — decisão de produto consciente.)
  - O `ondelete="CASCADE"` em `campanha_destinatarios.campanha_id` já apaga os
    destinatários junto. Sem migration.
- **Editar:** permitido em `{"rascunho", "erro"}` — espelha os guards de
  `send`/`import` que já existem (`comunicados.py:292,387`). Permite corrigir e
  reenviar uma campanha que falhou.

## API — 2 endpoints novos (`api/v1/comunicados.py`)

### `DELETE /api/v1/admin/comunicados/{campanha_id}` → 204

- 404 se não existe.
- 409 se `status == "enviando"` (detail: "cancele a campanha antes de excluir").
- Senão: `session.delete(camp)` + commit. Cascade remove os destinatários.
- RBAC: `require_role(ADMIN)` (igual aos demais).

### `PATCH /api/v1/admin/comunicados/{campanha_id}` → CampanhaDetail

- 404 se não existe.
- 409 se `status not in {"rascunho", "erro"}` (detail: "campanha já está '<status>'").
- Body: `CampanhaUpdate` (todos os campos opcionais). Aplica só os campos
  enviados (`model_dump(exclude_unset=True)`).
- Campos editáveis: `titulo`, `template_name`, `template_language`,
  `body_params`, `header_media_url`, `segmentacao`, `button_param`.
- **Não** re-seleciona destinatários automaticamente ao trocar template/canal —
  isso continua sendo ação explícita via `/selecionar` ou `/importar`.
- Retorna o `CampanhaDetail` atualizado (mesma forma do `GET /{id}`).

## Schema (`api/schemas/comunicado.py`)

`CampanhaUpdate` — todos os campos `Optional`, reaproveita `SegmentoFiltros`
para `segmentacao`. `model_config` permite `exclude_unset` no endpoint.

```python
class CampanhaUpdate(BaseModel):
    titulo: str | None = None
    template_name: str | None = None
    template_language: str | None = None
    body_params: list[str] | None = None
    header_media_url: str | None = None
    segmentacao: SegmentoFiltros | None = None
    button_param: str | None = None
```

## Dashboard (`apps/dashboard/.../comunicados`)

- **Excluir:** botão na `comunicado-detail.tsx` (e/ou ação na `comunicado-list.tsx`)
  com confirmação. Some quando `status === "enviando"`. Após excluir, volta pra
  lista e remove o item.
- **Editar:** botão visível quando `status` é `rascunho` ou `erro`. Abre o
  `comunicado-form.tsx` em modo edição (PATCH em vez de POST), pré-preenchido.

## Testes (`tests/test_comunicados_api.py`)

- excluir rascunho → 204; some do banco (e destinatários via cascade).
- excluir concluída → 204 (permitido).
- excluir `enviando` → 409.
- excluir inexistente → 404.
- editar rascunho (muda título) → 200, persistiu.
- editar `concluida` / `enviando` → 409.
- editar inexistente → 404.

## Fora de escopo

- Sem migration (cascade já existe).
- Sem soft delete / lixeira.
- Sem re-seleção automática de destinatários ao editar.
