# Cliente App — Fase 4: Faturas

> **For agentic workers:** subagent-driven-development. Checkboxes `- [ ]`.

**Goal:** Cliente vê faturas abertas/pagas, copia PIX, abre boleto PDF e compartilha — sem falar com ninguém. Esse é o entregável-chave do app.

**Architecture:** Backend expõe 3 endpoints autenticados como cliente — lista de faturas (do cache SGP existente), PIX copia-e-cola por título, URL do boleto PDF por título. Flutter ganha Tab Faturas com lista filtrada (abertas | pagas), tap → bottom sheet com PIX copiável + abrir PDF + compartilhar.

**Tech Stack:** + `url_launcher` (abrir PDF/compartilhar), + `flutter/services` Clipboard (copiar PIX).

**Spec:** seção 4 tab 2 + seção 6.

---

## Decisões

1. **Sem proxy do PDF.** Backend retorna a `link_pdf` do SGP direto; app abre no browser via `url_launcher`. Reduz superfície e código. Se SGP mudar URLs assinadas, Fase 7 troca pra proxy stream.
2. **Lista vem do `ClienteSgp.titulos`** que já chega no cache. Sem chamada adicional ao SGP.
3. **PIX no clipboard** — `flutter/services` Clipboard sem dep extra.
4. **Filtros:** abertas (default) + pagas (últimos 12 meses). Sem paginação — SGP não devolve histórico longo, lista normalmente pequena (~20 itens).

---

## File Structure

**Backend:**
- Modify: `apps/api/src/ondeline_api/api/schemas/cliente_app_auth.py` — FaturaOut, FaturasOut, PixOut, BoletoUrlOut
- Modify: `apps/api/src/ondeline_api/api/v1/cliente_app_me.py` — 3 novos endpoints
- Modify: `apps/api/tests/test_cliente_app_me.py` — testes

**Flutter:**
- Modify: `apps/cliente-mobile/pubspec.yaml` — url_launcher
- Modify: `apps/cliente-mobile/lib/core/api/dto.dart` — FaturaDto
- Create: `apps/cliente-mobile/lib/core/api/faturas_repository.dart`
- Replace: `apps/cliente-mobile/lib/features/faturas/faturas_stub_screen.dart` → `faturas_screen.dart`
- Create: `apps/cliente-mobile/lib/features/faturas/widgets/fatura_card.dart`
- Create: `apps/cliente-mobile/lib/features/faturas/widgets/fatura_bottom_sheet.dart`
- Modify: `apps/cliente-mobile/lib/features/shell/main_shell.dart` — usar FaturasScreen

---

## Task 1: Schemas backend

Adicionar em `cliente_app_auth.py`:

```python
class FaturaOut(BaseModel):
    id: str
    valor: float
    vencimento: str  # YYYY-MM-DD
    status: str  # "aberto" | "pago" | etc
    dias_atraso: int = 0
    tem_pdf: bool
    tem_pix: bool


class FaturasOut(BaseModel):
    items: list[FaturaOut]


class PixOut(BaseModel):
    codigo: str


class BoletoUrlOut(BaseModel):
    url: str
```

## Task 2: Endpoints `/faturas` no router me

Adicionar em `cliente_app_me.py`:

```python
from ondeline_api.api.schemas.cliente_app_auth import (
    BoletoUrlOut,
    FaturaOut,
    FaturasOut,
    PixOut,
)


def _fatura_out(f) -> FaturaOut:
    return FaturaOut(
        id=f.id,
        valor=float(f.valor),
        vencimento=f.vencimento,
        status=f.status,
        dias_atraso=int(f.dias_atraso),
        tem_pdf=bool(f.link_pdf),
        tem_pix=bool(f.codigo_pix),
    )


@router.get("/faturas", response_model=FaturasOut)
async def faturas(
    status: str | None = None,  # "abertas" | "pagas" | None (todas)
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> FaturasOut:
    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    if sgp is None:
        return FaturasOut(items=[])
    titulos = list(sgp.titulos)
    if status == "abertas":
        titulos = [t for t in titulos if t.status == "aberto"]
    elif status == "pagas":
        titulos = [t for t in titulos if t.status != "aberto"]
    # Mais recente primeiro
    titulos.sort(key=lambda t: t.vencimento, reverse=True)
    return FaturasOut(items=[_fatura_out(t) for t in titulos])


@router.get("/faturas/{titulo_id}/pix", response_model=PixOut)
async def fatura_pix(
    titulo_id: str,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PixOut:
    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    if sgp is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")
    for t in sgp.titulos:
        if t.id == titulo_id:
            if not t.codigo_pix:
                raise HTTPException(status_code=404, detail="fatura sem pix")
            return PixOut(codigo=t.codigo_pix)
    raise HTTPException(status_code=404, detail="fatura nao encontrada")


@router.get("/faturas/{titulo_id}/boleto", response_model=BoletoUrlOut)
async def fatura_boleto(
    titulo_id: str,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> BoletoUrlOut:
    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    if sgp is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")
    for t in sgp.titulos:
        if t.id == titulo_id:
            if not t.link_pdf:
                raise HTTPException(status_code=404, detail="fatura sem pdf")
            return BoletoUrlOut(url=t.link_pdf)
    raise HTTPException(status_code=404, detail="fatura nao encontrada")
```

## Task 3: Testes backend

Adicionar fixture com `titulos` no `fake_sgp` do test_cliente_app_me.py + testes de cada endpoint.

## Task 4-7: Flutter — DTO, repo, screen, widgets

Padrão dos anteriores. `FaturaDto`, `FaturasRepository`, `FaturasScreen` com `TabBar` (Abertas | Pagas), `FaturaCard` com chip de status colorido, `FaturaBottomSheet` com 3 botões (PIX/PDF/Compartilhar) + Clipboard + url_launcher.
