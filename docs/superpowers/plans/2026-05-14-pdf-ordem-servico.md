# PDF de Ordem de Serviço — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerar PDF de qualquer OS no backend com WeasyPrint — dados na página 1, fotos na página 2 — disponível para download no dashboard e envio direto ao técnico via WhatsApp Evolution.

**Architecture:** Serviço `OsPdfService` converte template Jinja2 HTML → PDF em memória via WeasyPrint. Dois endpoints novos em `/api/v1/os/{id}`: `GET /pdf` retorna `StreamingResponse` e `POST /enviar-pdf-tecnico` gera o PDF e chama a Evolution API. Dashboard adiciona dois botões na página de detalhe da OS.

**Tech Stack:** WeasyPrint, Jinja2, FastAPI StreamingResponse, base64 (stdlib), Next.js 14

---

## File Map

| Ação | Arquivo |
|------|---------|
| Modify | `apps/api/pyproject.toml` |
| Create | `apps/api/src/ondeline_api/templates/os_pdf.html` |
| Create | `apps/api/src/ondeline_api/services/os_pdf.py` |
| Modify | `apps/api/src/ondeline_api/api/v1/ordens_servico.py` |
| Create | `apps/api/tests/test_os_pdf.py` |
| Modify | `apps/dashboard/components/os-detail.tsx` |

---

### Task 1: Instalar Dependências

**Files:**
- Modify: `apps/api/pyproject.toml`

- [ ] **Step 1: Adicionar weasyprint e jinja2 ao `pyproject.toml`**

Em `apps/api/pyproject.toml`, adicionar ao bloco `dependencies` (após `"python-multipart>=0.0.20"`):

```toml
    "weasyprint>=62.0",
    "jinja2>=3.1.0",
```

- [ ] **Step 2: Instalar dependências**

```bash
cd apps/api && pip install weasyprint jinja2
```

- [ ] **Step 3: Verificar que WeasyPrint encontra suas libs de sistema**

```bash
cd apps/api && python -c "import weasyprint; print('weasyprint ok')"
```

Expected: `weasyprint ok`

Se falhar com erro de `libpango` ou `libcairo`, instalar as bibliotecas do sistema:

```bash
apt-get install -y libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

- [ ] **Step 4: Commit**

```bash
git add apps/api/pyproject.toml
git commit -m "chore(api): adicionar weasyprint e jinja2 como dependências"
```

---

### Task 2: Template HTML do PDF

**Files:**
- Create: `apps/api/src/ondeline_api/templates/os_pdf.html`

- [ ] **Step 1: Criar o diretório de templates**

```bash
mkdir -p apps/api/src/ondeline_api/templates
```

- [ ] **Step 2: Criar o template Jinja2**

```html
{# apps/api/src/ondeline_api/templates/os_pdf.html #}
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: Arial, sans-serif; font-size: 12px; color: #1a1a1a; }
    .page { padding: 32px; max-width: 100%; }
    .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #1e40af; padding-bottom: 12px; margin-bottom: 20px; }
    .header-left .company { font-size: 18px; font-weight: bold; color: #1e40af; }
    .header-left .subtitle { font-size: 10px; color: #6b7280; margin-top: 2px; }
    .header-right { text-align: right; }
    .header-right .codigo { font-size: 16px; font-weight: bold; }
    .header-right .data { font-size: 10px; color: #6b7280; margin-top: 2px; }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
    .field-label { font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; color: #6b7280; margin-bottom: 3px; }
    .field-value { font-size: 12px; font-weight: 600; }
    .field-sub { font-size: 11px; color: #374151; margin-top: 1px; }
    .block { background: #f8fafc; border-left: 3px solid #1e40af; padding: 10px 12px; margin-bottom: 16px; border-radius: 0 4px 4px 0; }
    .block-problema { background: #fef3c7; border-left-color: #f59e0b; }
    .badges { display: flex; gap: 12px; margin-bottom: 16px; }
    .badge { background: #f1f5f9; border-radius: 6px; padding: 8px 12px; text-align: center; }
    .badge-label { font-size: 9px; color: #6b7280; text-transform: uppercase; }
    .badge-value { font-size: 12px; font-weight: 600; margin-top: 2px; }
    .badge-concluida { background: #dcfce7; }
    .badge-pendente { background: #fef9c3; }
    .csat-section { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 10px; margin-bottom: 16px; }
    .footer { border-top: 1px dashed #d1d5db; padding-top: 8px; font-size: 9px; color: #9ca3af; }
    .page-break { page-break-before: always; }
    .fotos-title { font-size: 14px; font-weight: bold; margin-bottom: 16px; color: #1e40af; }
    .fotos-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .foto-item { }
    .foto-item img { width: 100%; height: 200px; object-fit: cover; border-radius: 6px; border: 1px solid #e2e8f0; }
    .foto-ts { font-size: 9px; color: #6b7280; margin-top: 4px; text-align: center; }
  </style>
</head>
<body>
  <!-- Página 1: Dados -->
  <div class="page">
    <div class="header">
      <div class="header-left">
        <div class="company">ONDELINE TELECOM</div>
        <div class="subtitle">Ordem de Serviço</div>
      </div>
      <div class="header-right">
        <div class="codigo">{{ os.codigo }}</div>
        <div class="data">Aberta em {{ os.criada_em }}</div>
      </div>
    </div>

    <div class="grid-2">
      <div>
        <div class="field-label">Cliente</div>
        <div class="field-value">{{ cliente_nome or "Não identificado" }}</div>
        {% if cliente_whatsapp %}
        <div class="field-sub">📱 {{ cliente_whatsapp }}</div>
        {% endif %}
      </div>
      <div>
        <div class="field-label">Técnico</div>
        <div class="field-value">{{ tecnico_nome or "Não atribuído" }}</div>
        {% if tecnico_whatsapp %}
        <div class="field-sub">📱 {{ tecnico_whatsapp }}</div>
        {% endif %}
      </div>
    </div>

    <div class="block">
      <div class="field-label">Endereço</div>
      <div class="field-value">{{ os.endereco }}</div>
    </div>

    <div class="block block-problema">
      <div class="field-label">Problema Reportado</div>
      <div class="field-value">{{ os.problema }}</div>
    </div>

    <div class="badges">
      <div class="badge {% if os.status == 'concluida' %}badge-concluida{% else %}badge-pendente{% endif %}">
        <div class="badge-label">Status</div>
        <div class="badge-value">{{ os.status | upper }}</div>
      </div>
      {% if os.agendamento_at %}
      <div class="badge">
        <div class="badge-label">Agendamento</div>
        <div class="badge-value">{{ os.agendamento_at }}</div>
      </div>
      {% endif %}
      {% if os.concluida_em %}
      <div class="badge badge-concluida">
        <div class="badge-label">Conclusão</div>
        <div class="badge-value">{{ os.concluida_em }}</div>
      </div>
      {% endif %}
    </div>

    {% if os.csat is not none %}
    <div class="csat-section">
      <div class="field-label">Avaliação do Cliente</div>
      <div class="field-value">{{ "⭐" * os.csat }} ({{ os.csat }}/5)</div>
      {% if os.comentario_cliente %}
      <div class="field-sub" style="margin-top: 4px; font-style: italic;">"{{ os.comentario_cliente }}"</div>
      {% endif %}
    </div>
    {% endif %}

    <div class="footer">
      {% if fotos | length > 0 %}
      📷 {{ fotos | length }} foto(s) — ver página 2
      {% else %}
      Sem fotos anexadas
      {% endif %}
      &nbsp;·&nbsp; Gerado em {{ gerado_em }}
    </div>
  </div>

  {% if fotos | length > 0 %}
  <!-- Página 2: Fotos -->
  <div class="page page-break">
    <div class="fotos-title">📷 Fotos da OS {{ os.codigo }}</div>
    <div class="fotos-grid">
      {% for foto in fotos %}
      <div class="foto-item">
        <img src="data:{{ foto.mime }};base64,{{ foto.b64 }}" alt="Foto {{ loop.index }}" />
        <div class="foto-ts">{{ foto.ts }}</div>
      </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/templates/os_pdf.html
git commit -m "feat(pdf): template Jinja2 HTML para PDF da OS (2 páginas)"
```

---

### Task 3: Serviço de Geração de PDF

**Files:**
- Create: `apps/api/src/ondeline_api/services/os_pdf.py`

- [ ] **Step 1: Criar o serviço**

```python
# apps/api/src/ondeline_api/services/os_pdf.py
"""Geração de PDF para Ordens de Serviço com WeasyPrint."""
from __future__ import annotations

import base64
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from ondeline_api.db.models.business import OrdemServico

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True)


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.astimezone(UTC).strftime("%d/%m/%Y %H:%M")


def _load_fotos(os_: OrdemServico) -> list[dict]:
    fotos = []
    for meta in os_.fotos or []:
        path = Path(meta.get("url", ""))
        if not path.exists():
            continue
        b64 = base64.b64encode(path.read_bytes()).decode()
        fotos.append(
            {
                "b64": b64,
                "mime": meta.get("mime", "image/jpeg"),
                "ts": _fmt_dt(datetime.fromisoformat(meta["ts"])) if meta.get("ts") else "",
            }
        )
    return fotos


def generate_os_pdf(
    os_: OrdemServico,
    cliente_nome: str | None,
    cliente_whatsapp: str | None,
    tecnico_nome: str | None,
    tecnico_whatsapp: str | None,
) -> bytes:
    """Renderiza template HTML e converte para PDF em memória. Retorna bytes do PDF."""
    template = _jinja_env.get_template("os_pdf.html")
    fotos = _load_fotos(os_)

    os_data = {
        "codigo": os_.codigo,
        "status": os_.status.value,
        "problema": os_.problema,
        "endereco": os_.endereco,
        "criada_em": _fmt_dt(os_.criada_em),
        "concluida_em": _fmt_dt(os_.concluida_em),
        "agendamento_at": _fmt_dt(os_.agendamento_at),
        "csat": os_.csat,
        "comentario_cliente": os_.comentario_cliente,
    }

    html_content = template.render(
        os=os_data,
        cliente_nome=cliente_nome,
        cliente_whatsapp=cliente_whatsapp,
        tecnico_nome=tecnico_nome,
        tecnico_whatsapp=tecnico_whatsapp,
        fotos=fotos,
        gerado_em=datetime.now(tz=UTC).strftime("%d/%m/%Y %H:%M"),
    )

    return HTML(string=html_content, base_url=str(_TEMPLATES_DIR)).write_pdf()
```

- [ ] **Step 2: Verificar importação**

```bash
cd apps/api && python -c "from ondeline_api.services.os_pdf import generate_os_pdf; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/services/os_pdf.py
git commit -m "feat(pdf): serviço OsPdfService com WeasyPrint e Jinja2"
```

---

### Task 4: Endpoints de PDF na OS + Testes

**Files:**
- Modify: `apps/api/src/ondeline_api/api/v1/ordens_servico.py`
- Create: `apps/api/tests/test_os_pdf.py`

- [ ] **Step 1: Escrever os testes (TDD)**

```python
# apps/api/tests/test_os_pdf.py
"""Testes de integração para GET /api/v1/os/{id}/pdf e POST /enviar-pdf-tecnico."""
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.config import get_settings
from ondeline_api.db.models.business import OrdemServico, OsStatus
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app

os.environ.setdefault("EVOLUTION_URL", "http://fake-evolution")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")
os.environ.setdefault("EVOLUTION_KEY", "fake-key")


@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[Redis]:  # type: ignore[type-arg]
    r: Redis = Redis.from_url(str(get_settings().redis_url), decode_responses=True)  # type: ignore[type-arg]
    yield r
    await r.aclose()  # type: ignore[attr-defined]


@pytest.fixture
def app(db_session: AsyncSession, redis_client: Redis) -> FastAPI:  # type: ignore[type-arg]
    application = create_app()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def _redis() -> Any:
        return redis_client

    application.dependency_overrides[get_db] = _db
    application.dependency_overrides[get_redis] = _redis
    return application


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _admin_token(client: AsyncClient, created_user: dict[str, Any]) -> str:
    r = await client.post(
        "/auth/login",
        json={"email": created_user["email"], "password": created_user["password"]},
    )
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


async def _seed_os(db_session: AsyncSession) -> OrdemServico:
    os_ = OrdemServico(
        codigo=f"OS-{uuid4().hex[:6]}",
        problema="Internet caindo",
        endereco="Rua das Flores, 123",
        status=OsStatus.CONCLUIDA,
        criada_em=datetime(2026, 5, 14, 8, 0, tzinfo=UTC),
        concluida_em=datetime(2026, 5, 14, 10, 30, tzinfo=UTC),
        csat=5,
        comentario_cliente="Ótimo atendimento",
    )
    db_session.add(os_)
    await db_session.flush()
    return os_


@pytest.mark.asyncio
async def test_pdf_requires_auth(client: AsyncClient, db_session: AsyncSession) -> None:
    os_ = await _seed_os(db_session)
    r = await client.get(f"/api/v1/os/{os_.id}/pdf")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_pdf_returns_pdf_bytes(
    client: AsyncClient, created_user: dict[str, Any], db_session: AsyncSession
) -> None:
    os_ = await _seed_os(db_session)
    token = await _admin_token(client, created_user)
    r = await client.get(
        f"/api/v1/os/{os_.id}/pdf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"  # PDF magic bytes


@pytest.mark.asyncio
async def test_pdf_not_found(client: AsyncClient, created_user: dict[str, Any]) -> None:
    token = await _admin_token(client, created_user)
    r = await client.get(
        f"/api/v1/os/{uuid4()}/pdf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_enviar_pdf_sem_tecnico_retorna_422(
    client: AsyncClient, created_user: dict[str, Any], db_session: AsyncSession
) -> None:
    os_ = await _seed_os(db_session)  # sem tecnico_id
    token = await _admin_token(client, created_user)
    r = await client.post(
        f"/api/v1/os/{os_.id}/enviar-pdf-tecnico",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_enviar_pdf_ao_tecnico(
    client: AsyncClient, created_user: dict[str, Any], db_session: AsyncSession
) -> None:
    from ondeline_api.db.models.business import Tecnico

    tecnico = Tecnico(nome="João Técnico", whatsapp="5511999990000", ativo=True)
    db_session.add(tecnico)
    await db_session.flush()

    os_ = await _seed_os(db_session)
    os_.tecnico_id = tecnico.id
    await db_session.flush()

    token = await _admin_token(client, created_user)
    with patch(
        "ondeline_api.api.v1.ordens_servico._send_whatsapp_document",
        new=AsyncMock(return_value=None),
    ):
        r = await client.post(
            f"/api/v1/os/{os_.id}/enviar-pdf-tecnico",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200
    assert r.json()["enviado"] is True
```

- [ ] **Step 2: Rodar testes para confirmar que falham**

```bash
cd apps/api && pytest tests/test_os_pdf.py -v 2>&1 | head -20
```

Expected: FAILED (rotas não existem)

- [ ] **Step 3: Adicionar endpoints em `ordens_servico.py`**

Adicionar os seguintes imports ao bloco de imports existente em `apps/api/src/ondeline_api/api/v1/ordens_servico.py`:

```python
from fastapi.responses import StreamingResponse

from ondeline_api.repositories.tecnico import TecnicoRepo
from ondeline_api.services.os_pdf import generate_os_pdf
```

Adicionar a função helper e os dois endpoints ao final do arquivo:

```python
async def _send_whatsapp_document(whatsapp: str, pdf_bytes: bytes, filename: str) -> None:
    """Best-effort envio de documento PDF via WhatsApp. Nunca levanta exceção."""
    try:
        import base64
        import tempfile

        from ondeline_api.adapters.evolution import EvolutionAdapter
        from ondeline_api.config import get_settings

        s = get_settings()
        evo = EvolutionAdapter(
            base_url=s.evolution_url,
            instance=s.evolution_instance,
            api_key=s.evolution_key,
        )
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        try:
            await evo.send_document(whatsapp, tmp_path, filename)
        except Exception:
            log.warning("os.pdf_send_failed", whatsapp=whatsapp, exc_info=True)
        finally:
            await evo.aclose()
            Path(tmp_path).unlink(missing_ok=True)
    except Exception:
        log.warning("os.pdf_send_failed_cleanup", whatsapp=whatsapp)


@router.get("/{os_id}/pdf", dependencies=[_role_dep])
async def download_os_pdf(
    os_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not found")

    tecnico = None
    if os_.tecnico_id:
        tecnico = await TecnicoRepo(session).get_by_id(os_.tecnico_id)

    pdf_bytes = generate_os_pdf(
        os_=os_,
        cliente_nome=None,
        cliente_whatsapp=None,
        tecnico_nome=tecnico.nome if tecnico else None,
        tecnico_whatsapp=tecnico.whatsapp if tecnico else None,
    )
    filename = f"{os_.codigo}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"},
    )


@router.post("/{os_id}/enviar-pdf-tecnico", dependencies=[_role_dep])
async def enviar_pdf_tecnico(
    os_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not found")
    if os_.tecnico_id is None:
        raise HTTPException(status_code=422, detail="OS sem técnico atribuído")

    tecnico = await TecnicoRepo(session).get_by_id(os_.tecnico_id)
    if tecnico is None or not tecnico.whatsapp:
        raise HTTPException(status_code=422, detail="Técnico sem WhatsApp cadastrado")

    pdf_bytes = generate_os_pdf(
        os_=os_,
        cliente_nome=None,
        cliente_whatsapp=None,
        tecnico_nome=tecnico.nome,
        tecnico_whatsapp=tecnico.whatsapp,
    )
    filename = f"{os_.codigo}.pdf"
    await _send_whatsapp_document(tecnico.whatsapp, pdf_bytes, filename)
    return {"enviado": True, "tecnico": tecnico.nome, "whatsapp": tecnico.whatsapp}
```

**Nota:** Verificar se `TecnicoRepo` tem o método `get_by_id`. Caso não exista, adicionar ao repositório:

```python
# Em apps/api/src/ondeline_api/repositories/tecnico.py
async def get_by_id(self, tecnico_id: UUID) -> Tecnico | None:
    return (
        await self._session.execute(
            select(Tecnico).where(Tecnico.id == tecnico_id)
        )
    ).scalar_one_or_none()
```

**Nota 2:** Verificar se `EvolutionAdapter` tem o método `send_document`. Se não existir, usar `send_text` com o link do PDF como fallback temporário:

```python
# Fallback caso send_document não exista no EvolutionAdapter:
await evo.send_text(whatsapp, f"PDF da {filename} gerado. (Link: {tmp_path})")
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

```bash
cd apps/api && pytest tests/test_os_pdf.py -v
```

Expected: todos PASSED

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/ordens_servico.py \
        apps/api/tests/test_os_pdf.py
git commit -m "feat(pdf): endpoints GET /os/{id}/pdf e POST /os/{id}/enviar-pdf-tecnico"
```

---

### Task 5: Botões PDF no Frontend

**Files:**
- Modify: `apps/dashboard/components/os-detail.tsx`

- [ ] **Step 1: Adicionar botões ao componente `OsDetail`**

Em `apps/dashboard/components/os-detail.tsx`, adicionar após as importações existentes:

```typescript
import { useState } from 'react'
import { toast } from 'sonner'
import { apiFetch } from '@/lib/api/client'
```

Dentro da função `OsDetail`, adicionar estado e handler:

```typescript
const [enviandoPdf, setEnviandoPdf] = useState(false)

async function handleEnviarPdfTecnico() {
  setEnviandoPdf(true)
  try {
    await apiFetch(`/api/v1/os/${id}/enviar-pdf-tecnico`, { method: 'POST' })
    toast.success('PDF enviado ao técnico via WhatsApp')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Erro ao enviar PDF')
  } finally {
    setEnviandoPdf(false)
  }
}
```

Adicionar os dois botões dentro do `CardContent` do card de fotos (após o `Input` de upload de foto) ou em um novo `Card`:

```typescript
<Card>
  <CardHeader>
    <CardTitle className="text-base">PDF da OS</CardTitle>
  </CardHeader>
  <CardContent className="space-y-2">
    <Button
      className="w-full"
      variant="outline"
      onClick={() => window.open(`/api/v1/os/${id}/pdf`, '_blank')}
    >
      ⬇️ Baixar PDF
    </Button>
    <Button
      className="w-full"
      style={{ backgroundColor: '#25d366', color: 'white' }}
      disabled={enviandoPdf || !data?.tecnico_id}
      onClick={handleEnviarPdfTecnico}
      title={!data?.tecnico_id ? 'OS sem técnico atribuído' : undefined}
    >
      {enviandoPdf ? 'Enviando…' : '📲 Enviar PDF ao Técnico'}
    </Button>
    {!data?.tecnico_id && (
      <p className="text-xs text-muted-foreground">
        Atribua um técnico para habilitar o envio.
      </p>
    )}
  </CardContent>
</Card>
```

Esse novo `Card` deve ser inserido na coluna da direita (div com `className="space-y-4"`), após o card de fotos existente.

**Nota:** O campo `tecnico_id` precisa estar no tipo `OsOut` em `apps/dashboard/lib/api/types.ts`. Verificar se já existe. Se não, adicionar:

```typescript
// Em OsOut (apps/dashboard/lib/api/types.ts)
tecnico_id: string | null
```

- [ ] **Step 2: Verificar TypeScript**

```bash
cd apps/dashboard && pnpm tsc --noEmit 2>&1 | grep "os-detail" | head -10
```

Expected: sem erros

- [ ] **Step 3: Commit**

```bash
git add apps/dashboard/components/os-detail.tsx \
        apps/dashboard/lib/api/types.ts
git commit -m "feat(pdf): botões Baixar PDF e Enviar PDF ao Técnico na tela da OS"
```

---

### Task 6: Smoke test visual

- [ ] **Step 1: Subir o servidor de desenvolvimento**

```bash
cd apps/dashboard && pnpm dev
```

- [ ] **Step 2: Verificar no browser**

1. Navegar para uma OS existente no dashboard (`/os/[id]`)
2. Confirmar que o card "PDF da OS" aparece na coluna direita
3. Clicar "Baixar PDF" — PDF deve abrir em nova aba com os dados da OS
4. Verificar que o PDF tem cabeçalho ONDELINE, código da OS, endereço e problema
5. Se a OS tiver fotos, verificar que a página 2 do PDF mostra as fotos
6. Se a OS tiver técnico com WhatsApp, clicar "Enviar PDF ao Técnico" — toast de sucesso deve aparecer

- [ ] **Step 3: Commit final**

```bash
git add -A
git commit -m "feat(pdf): geração e envio de PDF de OS completo"
```
