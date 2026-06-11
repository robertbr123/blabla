# Rede WiFi — Fatia 3: Rede do cliente na conversa (dashboard) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao atendente, dentro da conversa do WhatsApp na dashboard, um painel de rede (online/sinal/IP/aparelhos) + trocar senha + reiniciar ONU, derivando o cliente da própria conversa (sem digitar CPF).

**Architecture:** Endpoints novos escopados por conversa (`/api/v1/conversas/{id}/rede/*`, role ADMIN/ATENDENTE/TÉCNICO) que derivam o CPF do `conversa.cliente_id` server-side e reusam o `RedeService` da Fatia 2. Dashboard ganha uma aba "Rede" + selo no header + botão "colar diagnóstico" (pré-preenche a resposta).

**Tech Stack:** FastAPI + Alembic + pytest (backend); Next.js + react-query + Tailwind (dashboard).

**Spec:** `docs/superpowers/specs/2026-06-11-rede-wifi-fatia3-dashboard-conversa-design.md`

**Convenção do projeto:** testes (`pytest`), `ruff`, `mypy` e `flutter`/`pnpm` rodam na **máquina de deploy/CI depois do push**, não no ambiente local. Os passos "Run" são os comandos a executar lá; respeitar a ordem TDD ao escrever. **IMPORTANTE (lição da Fatia 2):** com `from __future__ import annotations`, NUNCA use anotação entre aspas (`"Tipo"`) — o ruff `UP037` quebra o CI. Escreva o tipo sem aspas.

---

### Task 1: Coluna `tipo` em `rede_wifi_pedido` (model + migração)

**Files:**
- Modify: `apps/api/src/ondeline_api/db/models/rede.py`
- Create: `apps/api/alembic/versions/0046_rede_wifi_pedido_tipo.py`

- [ ] **Step 1: Adicionar o campo no model**

Em `db/models/rede.py`, dentro de `class RedeWifiPedido`, depois do campo `reiniciou` (linha 38), adicione:

```python
    tipo: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="senha", default="senha"
    )
```

(`String` já está importado no arquivo.)

- [ ] **Step 2: Criar a migração**

Crie `apps/api/alembic/versions/0046_rede_wifi_pedido_tipo.py`:

```python
"""rede_wifi_pedido: coluna tipo ('senha'|'reboot') pra auditar reboots.

A Fatia 3 (dashboard) permite reiniciar a ONU como acao de suporte. A auditoria
reusa rede_wifi_pedido com tipo='reboot' (a troca de senha continua 'senha').

Revision ID: 0046_rede_wifi_pedido_tipo
Revises: 0045_rede_wifi_pedido_cpf
Create Date: 2026-06-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0046_rede_wifi_pedido_tipo"
down_revision: str | None = "0045_rede_wifi_pedido_cpf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rede_wifi_pedido",
        sa.Column("tipo", sa.String(16), nullable=False, server_default="senha"),
    )


def downgrade() -> None:
    op.drop_column("rede_wifi_pedido", "tipo")
```

- [ ] **Step 3: Verificar (na máquina de deploy)**

Run: `cd apps/api && alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
Expected: sobe e desce sem erro; a coluna `tipo` existe com default `'senha'`.

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/ondeline_api/db/models/rede.py apps/api/alembic/versions/0046_rede_wifi_pedido_tipo.py
git commit -m "feat(rede): coluna tipo (senha|reboot) em rede_wifi_pedido + migracao 0046"
```

---

### Task 2: `RedeService.reiniciar_onu` (reboot auditado)

**Files:**
- Modify: `apps/api/src/ondeline_api/services/rede_service.py`
- Test: `apps/api/tests/test_rede_service.py`

- [ ] **Step 1: Escrever os testes (falhando)**

Em `test_rede_service.py`, adicione (o `_FakeGenie` já tem `reboot` registrando em `self.reboots`):

```python
async def test_reiniciar_onu_reboota_e_audita(db_session: AsyncSession) -> None:
    genie = _FakeGenie(by_pppoe=_dev())
    svc = _svc(db_session, genie)
    ator = uuid4()
    res = await svc.reiniciar_onu(cpf=CPF, serial=None, ator_user_id=ator)
    assert res.device_id == "30E1F1-AX1800-X"
    assert genie.reboots == ["30E1F1-AX1800-X"]
    pedido = (await db_session.execute(select(RedeWifiPedido))).scalar_one()
    assert pedido.tipo == "reboot"
    assert pedido.reiniciou is True
    assert pedido.status == "enviado"
    assert pedido.ator_user_id == ator
    assert pedido.cpf_hash == hash_pii(CPF)


async def test_reiniciar_onu_sem_device_levanta(db_session: AsyncSession) -> None:
    genie = _FakeGenie(by_pppoe=None, by_serial=None)
    svc = _svc(db_session, genie)
    with pytest.raises(OnuNaoEncontradaError):
        await svc.reiniciar_onu(cpf=CPF, serial=None, ator_user_id=uuid4())
```

- [ ] **Step 2: Rodar e confirmar que falham**

Run: `cd apps/api && pytest tests/test_rede_service.py -k reiniciar_onu -v`
Expected: FAIL (`reiniciar_onu` não existe).

- [ ] **Step 3: Implementar em `rede_service.py`**

Adicione o DTO perto de `ResultadoTroca`:

```python
@dataclass(frozen=True, slots=True)
class ResultadoReboot:
    device_id: str
```

Adicione o método na classe `RedeService`, depois de `trocar_senha_wifi`:

```python
    async def reiniciar_onu(
        self, *, cpf: str, serial: str | None, ator_user_id: UUID
    ) -> ResultadoReboot:
        """Reinicia a ONU (acao de suporte). Audita em rede_wifi_pedido com
        tipo='reboot' (mesma tabela da troca de senha, PII-safe)."""
        cpf = _so_digitos(cpf)
        if not cpf:
            raise CpfInvalidoError("CPF invalido")
        res = await self._resolver_por_cpf(cpf, serial)
        if res.device is None:
            raise OnuNaoEncontradaError("ONU nao encontrada por PPPoE nem serial")
        pedido = RedeWifiPedido(
            cpf_hash=hash_pii(cpf),
            contrato_id=res.contrato_id,
            pppoe_login=res.pppoe,
            device_id=res.device.device_id,
            ator_user_id=ator_user_id,
            status="pendente",
            reiniciou=True,
            tipo="reboot",
        )
        self._session.add(pedido)
        await self._session.flush()
        await self._genie.reboot(res.device.device_id)
        pedido.status = "enviado"
        await self._session.flush()
        log.info("rede.onu_reiniciada", device_id=res.device.device_id)
        return ResultadoReboot(device_id=res.device.device_id)
```

- [ ] **Step 4: Rodar e confirmar que passam**

Run: `cd apps/api && pytest tests/test_rede_service.py -k reiniciar_onu -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/services/rede_service.py apps/api/tests/test_rede_service.py
git commit -m "feat(rede): RedeService.reiniciar_onu (reboot auditado tipo=reboot)"
```

---

### Task 3: Mappers reutilizáveis + schemas da conversa

**Files:**
- Modify: `apps/api/src/ondeline_api/api/v1/rede.py`
- Create: `apps/api/src/ondeline_api/api/schemas/conversa_rede.py`

Extrai a montagem de `StatusRedeOut`/`DiagnosticoOut` pra funções reutilizáveis (o endpoint da conversa vai reusar) e cria os schemas novos.

- [ ] **Step 1: Extrair os mappers em `rede.py`**

Em `api/v1/rede.py`, adicione `StatusRede` e `DiagnosticoRede` ao import existente de `services.rede_service` (junto de `CpfInvalidoError, OnuNaoEncontradaError, RedeService, SenhaInvalidaError`). Adicione `StatusRedeOut` ao import de schemas (se ainda não estiver). Logo após o helper `_sinal_out`, adicione dois mappers module-level:

```python
def status_out(st: StatusRede) -> StatusRedeOut:
    if not st.encontrada or st.device is None:
        return StatusRedeOut(
            encontrada=False, pppoe_login=st.pppoe_login, motivo=st.motivo
        )
    d = st.device
    return StatusRedeOut(
        encontrada=True,
        device_id=d.device_id,
        fabricante=d.fabricante,
        modelo=d.modelo,
        online=d.online,
        last_inform=d.last_inform,
        redes=[
            RedeWlanOut(instancia=r.instancia, ssid=r.ssid, enabled=r.enabled)
            for r in d.redes
        ],
        pppoe_login=st.pppoe_login,
    )


def diagnostico_out(diag: DiagnosticoRede) -> DiagnosticoOut:
    if not diag.encontrada or diag.device is None:
        return DiagnosticoOut(encontrada=False, motivo=diag.motivo)
    d = diag.device
    return DiagnosticoOut(
        encontrada=True,
        last_inform=d.last_inform,
        aparelhos=[
            AparelhoOut(nome=a.nome, ip=a.ip, mac=a.mac, ativo=a.ativo, interface=a.interface)
            for a in d.aparelhos
        ],
        sinal=_sinal_out(d.sinal),
    )
```

Troque o corpo dos endpoints `status_rede` e `diagnostico_rede` em `rede.py` pra usar os mappers (mantendo o try/except de erro). O `status_rede` retorna `status_out(st)`; o `diagnostico_rede` retorna `diagnostico_out(diag)`. (Garante DRY e que o novo router produza o MESMO shape.)

- [ ] **Step 2: Criar os schemas da conversa**

Crie `apps/api/src/ondeline_api/api/schemas/conversa_rede.py`:

```python
"""Schemas dos endpoints de rede escopados por conversa (dashboard)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TrocarSenhaConversaIn(BaseModel):
    senha: str = Field(min_length=8, max_length=63)


class RebootOut(BaseModel):
    status: str  # "enviado"
    device_id: str
    aviso: str
```

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/rede.py apps/api/src/ondeline_api/api/schemas/conversa_rede.py
git commit -m "refactor(rede): mappers status_out/diagnostico_out reutilizaveis + schemas da conversa"
```

---

### Task 4: Endpoints `/api/v1/conversas/{id}/rede/*` (read) + registro

**Files:**
- Create: `apps/api/src/ondeline_api/api/v1/conversas_rede.py`
- Modify: `apps/api/src/ondeline_api/main.py`
- Test: `apps/api/tests/test_v1_conversas_rede.py`

- [ ] **Step 1: Escrever os testes dos GETs (falhando)**

Crie `apps/api/tests/test_v1_conversas_rede.py`:

```python
"""Endpoints /api/v1/conversas/{id}/rede/* (rede na conversa, dashboard)."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.adapters.genieacs.base import GenieAcsDevice
from ondeline_api.api.v1.rede import get_rede_service
from ondeline_api.auth.passwords import hash_password
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Cliente, Conversa
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from ondeline_api.services.rede_service import (
    DiagnosticoRede,
    ResultadoReboot,
    ResultadoTroca,
    StatusRede,
)
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

CPF = "01882354265"


class _FakeService:
    def __init__(self) -> None:
        self.cpf_recebido: str | None = None

    async def status_rede(self, cpf: str, serial: str | None = None) -> StatusRede:
        self.cpf_recebido = cpf
        return StatusRede(encontrada=True, device=_dev())

    async def diagnostico_rede(
        self, cpf: str, serial: str | None = None
    ) -> DiagnosticoRede:
        self.cpf_recebido = cpf
        return DiagnosticoRede(encontrada=True, device=_dev())

    async def trocar_senha_wifi(
        self, *, cpf: str, nova_senha: str, serial: str | None, ator_user_id: UUID
    ) -> ResultadoTroca:
        self.cpf_recebido = cpf
        return ResultadoTroca(device_id="DEV-X", reiniciando=True)

    async def reiniciar_onu(
        self, *, cpf: str, serial: str | None, ator_user_id: UUID
    ) -> ResultadoReboot:
        self.cpf_recebido = cpf
        return ResultadoReboot(device_id="DEV-X")


def _dev() -> GenieAcsDevice:
    return GenieAcsDevice(device_id="DEV-X", modelo="AX1800", online=True)


def _make_app(db_session: AsyncSession, redis_client: Any, fake: _FakeService) -> FastAPI:
    app = create_app()

    async def _db() -> Any:
        yield db_session

    async def _redis() -> Any:
        return redis_client

    async def _svc() -> AsyncIterator[_FakeService]:
        yield fake

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_redis] = _redis
    app.dependency_overrides[get_rede_service] = _svc
    return app


async def _login(c: AsyncClient, email: str, password: str) -> str:
    r = await c.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


def _auth(t: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {t}"}


async def _make_user(db_session: AsyncSession, role: Role) -> dict[str, Any]:
    email = f"u-{uuid4().hex[:8]}@example.com"
    password = "Pa$$word123"
    u = User(email=email, password_hash=hash_password(password), role=role,
             name="T", is_active=True)
    db_session.add(u)
    await db_session.flush()
    return {"email": email, "password": password, "id": u.id}


async def _make_conversa(db_session: AsyncSession, *, com_cliente: bool) -> UUID:
    cliente_id = None
    if com_cliente:
        cli = Cliente(
            cpf_cnpj_encrypted=encrypt_pii(CPF),
            cpf_hash=hash_pii(CPF),
            nome_encrypted=encrypt_pii("Fulano"),
            whatsapp="559900000000",
        )
        db_session.add(cli)
        await db_session.flush()
        cliente_id = cli.id
    conv = Conversa(whatsapp="559900000000", cliente_id=cliente_id)
    db_session.add(conv)
    await db_session.flush()
    return conv.id


@pytest_asyncio.fixture
async def redis_client() -> Any:
    client: Any = Redis.from_url(str(get_settings().redis_url), decode_responses=True)
    yield client
    await client.aclose()


async def test_diagnostico_da_conversa_resolve_cpf(
    db_session: AsyncSession, redis_client: Any
) -> None:
    fake = _FakeService()
    app = _make_app(db_session, redis_client, fake)
    user = await _make_user(db_session, Role.ATENDENTE)
    conv_id = await _make_conversa(db_session, com_cliente=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, user["email"], user["password"])
        r = await c.get(f"/api/v1/conversas/{conv_id}/rede/diagnostico", headers=_auth(token))
    assert r.status_code == 200, r.text
    assert r.json()["encontrada"] is True
    assert fake.cpf_recebido == CPF  # CPF derivado da conversa, nao do body


async def test_status_da_conversa_atendente_ok(
    db_session: AsyncSession, redis_client: Any
) -> None:
    fake = _FakeService()
    app = _make_app(db_session, redis_client, fake)
    user = await _make_user(db_session, Role.ATENDENTE)
    conv_id = await _make_conversa(db_session, com_cliente=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, user["email"], user["password"])
        r = await c.get(f"/api/v1/conversas/{conv_id}/rede/status", headers=_auth(token))
    assert r.status_code == 200, r.text  # ATENDENTE liberado (nao 403)


async def test_conversa_sem_cliente_vinculado_409(
    db_session: AsyncSession, redis_client: Any
) -> None:
    fake = _FakeService()
    app = _make_app(db_session, redis_client, fake)
    user = await _make_user(db_session, Role.ATENDENTE)
    conv_id = await _make_conversa(db_session, com_cliente=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, user["email"], user["password"])
        r = await c.get(f"/api/v1/conversas/{conv_id}/rede/diagnostico", headers=_auth(token))
    assert r.status_code == 409, r.text
```

- [ ] **Step 2: Rodar e confirmar que falham**

Run: `cd apps/api && pytest tests/test_v1_conversas_rede.py -v`
Expected: FAIL (rota não existe → 404).

- [ ] **Step 3: Criar `api/v1/conversas_rede.py` (helper + GETs)**

```python
"""GET/POST /api/v1/conversas/{id}/rede/* - rede do cliente DENTRO da conversa.

O CPF e derivado do cliente VINCULADO a conversa (conversa.cliente_id -> Cliente
-> decrypt), nunca do body: o atendente so age no cliente daquela conversa.
Reusa o RedeService (Fatia 2) e os mappers de api/v1/rede.py. Liberado pra
ADMIN/ATENDENTE/TECNICO (os /api/v1/rede/* continuam TECNICO/ADMIN).
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.genieacs.base import GenieAcsUnavailableError
from ondeline_api.api.schemas.conversa_rede import RebootOut, TrocarSenhaConversaIn
from ondeline_api.api.schemas.rede import DiagnosticoOut, StatusRedeOut, TrocarSenhaOut
from ondeline_api.api.v1.rede import (
    AVISO_REBOOT,
    diagnostico_out,
    get_rede_service,
    status_out,
)
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import Cliente, Conversa
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.services.rede_service import (
    CpfInvalidoError,
    OnuNaoEncontradaError,
    RedeService,
    SenhaInvalidaError,
)

router = APIRouter(prefix="/api/v1/conversas", tags=["conversas:rede"])
_role_dep = Depends(require_role(Role.ADMIN, Role.ATENDENTE, Role.TECNICO))


class ConversaSemClienteError(Exception):
    """Conversa nao tem cliente vinculado -> nao da pra resolver a ONU."""


async def _cpf_da_conversa(session: AsyncSession, conversa_id: UUID) -> str:
    conv = await session.get(Conversa, conversa_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversa nao encontrada")
    if conv.cliente_id is None:
        raise ConversaSemClienteError()
    cli = (
        await session.execute(select(Cliente).where(Cliente.id == conv.cliente_id))
    ).scalar_one_or_none()
    if cli is None or not cli.cpf_cnpj_encrypted:
        raise ConversaSemClienteError()
    return decrypt_pii(cli.cpf_cnpj_encrypted)


def _sem_cliente_http() -> HTTPException:
    return HTTPException(status_code=409, detail="conversa sem cliente vinculado")


@router.get(
    "/{conversa_id}/rede/status", response_model=StatusRedeOut, dependencies=[_role_dep]
)
async def status_conversa(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[RedeService, Depends(get_rede_service)],
) -> StatusRedeOut:
    try:
        cpf = await _cpf_da_conversa(session, conversa_id)
    except ConversaSemClienteError as e:
        raise _sem_cliente_http() from e
    try:
        st = await service.status_rede(cpf)
    except CpfInvalidoError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    return status_out(st)


@router.get(
    "/{conversa_id}/rede/diagnostico",
    response_model=DiagnosticoOut,
    dependencies=[_role_dep],
)
async def diagnostico_conversa(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[RedeService, Depends(get_rede_service)],
) -> DiagnosticoOut:
    try:
        cpf = await _cpf_da_conversa(session, conversa_id)
    except ConversaSemClienteError as e:
        raise _sem_cliente_http() from e
    try:
        diag = await service.diagnostico_rede(cpf)
    except CpfInvalidoError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    return diagnostico_out(diag)
```

(Os POSTs de senha/reboot entram na Task 5, no MESMO arquivo.)

- [ ] **Step 4: Registrar o router em `main.py`**

Em `main.py`, junto dos imports `from ondeline_api.api.v1 import ...`, adicione:
`from ondeline_api.api.v1 import conversas_rede as v1_conversas_rede`
E na seção de `app.include_router(...)`, logo após `app.include_router(v1_conversas_stream.router)`:
`app.include_router(v1_conversas_rede.router)`

- [ ] **Step 5: Rodar e confirmar que passam**

Run: `cd apps/api && pytest tests/test_v1_conversas_rede.py -v`
Expected: PASS (3 testes: diagnostico resolve cpf, status atendente ok, sem cliente 409).

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/conversas_rede.py apps/api/src/ondeline_api/main.py apps/api/tests/test_v1_conversas_rede.py
git commit -m "feat(rede): GET /conversas/{id}/rede/{status,diagnostico} (CPF da conversa)"
```

---

### Task 5: Endpoints POST senha + reboot da conversa

**Files:**
- Modify: `apps/api/src/ondeline_api/api/v1/conversas_rede.py`
- Test: `apps/api/tests/test_v1_conversas_rede.py`

- [ ] **Step 1: Escrever os testes (falhando)**

Adicione a `test_v1_conversas_rede.py`:

```python
async def test_trocar_senha_da_conversa(
    db_session: AsyncSession, redis_client: Any
) -> None:
    fake = _FakeService()
    app = _make_app(db_session, redis_client, fake)
    user = await _make_user(db_session, Role.ATENDENTE)
    conv_id = await _make_conversa(db_session, com_cliente=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, user["email"], user["password"])
        r = await c.post(
            f"/api/v1/conversas/{conv_id}/rede/wifi/senha",
            json={"senha": "senhaboa123"}, headers=_auth(token),
        )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "enviado"
    assert fake.cpf_recebido == CPF


async def test_reboot_da_conversa(
    db_session: AsyncSession, redis_client: Any
) -> None:
    fake = _FakeService()
    app = _make_app(db_session, redis_client, fake)
    user = await _make_user(db_session, Role.ATENDENTE)
    conv_id = await _make_conversa(db_session, com_cliente=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, user["email"], user["password"])
        r = await c.post(f"/api/v1/conversas/{conv_id}/rede/reboot", headers=_auth(token))
    assert r.status_code == 200, r.text
    assert r.json()["device_id"] == "DEV-X"
    assert fake.cpf_recebido == CPF
```

- [ ] **Step 2: Rodar e confirmar que falham**

Run: `cd apps/api && pytest tests/test_v1_conversas_rede.py -k "trocar_senha_da_conversa or reboot_da_conversa" -v`
Expected: FAIL (404, rotas não existem).

- [ ] **Step 3: Implementar os POSTs em `conversas_rede.py`**

Adicione `get_current_user`/`User` já estão importados. Acrescente ao fim do arquivo:

```python
@router.post(
    "/{conversa_id}/rede/wifi/senha",
    response_model=TrocarSenhaOut,
    dependencies=[_role_dep],
)
async def trocar_senha_conversa(
    conversa_id: UUID,
    payload: TrocarSenhaConversaIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[RedeService, Depends(get_rede_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> TrocarSenhaOut:
    try:
        cpf = await _cpf_da_conversa(session, conversa_id)
    except ConversaSemClienteError as e:
        raise _sem_cliente_http() from e
    try:
        res = await service.trocar_senha_wifi(
            cpf=cpf, nova_senha=payload.senha, serial=None, ator_user_id=user.id
        )
    except (SenhaInvalidaError, CpfInvalidoError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except OnuNaoEncontradaError as e:
        raise HTTPException(status_code=404, detail="ONU nao encontrada") from e
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    aviso = AVISO_REBOOT if res.reiniciando else "Senha enviada."
    return TrocarSenhaOut(
        status="enviado", device_id=res.device_id, reiniciando=res.reiniciando, aviso=aviso
    )


@router.post(
    "/{conversa_id}/rede/reboot", response_model=RebootOut, dependencies=[_role_dep]
)
async def reboot_conversa(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[RedeService, Depends(get_rede_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> RebootOut:
    try:
        cpf = await _cpf_da_conversa(session, conversa_id)
    except ConversaSemClienteError as e:
        raise _sem_cliente_http() from e
    try:
        res = await service.reiniciar_onu(cpf=cpf, serial=None, ator_user_id=user.id)
    except CpfInvalidoError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except OnuNaoEncontradaError as e:
        raise HTTPException(status_code=404, detail="ONU nao encontrada") from e
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    return RebootOut(status="enviado", device_id=res.device_id, aviso=AVISO_REBOOT)
```

- [ ] **Step 4: Rodar e confirmar (suíte inteira do arquivo)**

Run: `cd apps/api && pytest tests/test_v1_conversas_rede.py tests/test_rede_service.py -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/conversas_rede.py apps/api/tests/test_v1_conversas_rede.py
git commit -m "feat(rede): POST /conversas/{id}/rede/{wifi/senha,reboot}"
```

---

### Task 6: Dashboard — tipos + hooks react-query

**Files:**
- Modify: `apps/dashboard/lib/api/types.ts`
- Modify: `apps/dashboard/lib/api/queries.ts`

- [ ] **Step 1: Adicionar os tipos em `types.ts`**

No fim de `apps/dashboard/lib/api/types.ts`:

```typescript
export interface RedeAparelho {
  nome: string
  ip: string
  mac: string
  ativo: boolean
  interface: string
}

export interface RedeSinal {
  rx_power: number | null
  tx_power: number | null
  status_gpon: string | null
  conexao_pppoe: string | null
  ip_externo: string | null
  uptime_s: number | null
  ultimo_erro: string | null
}

export interface RedeStatus {
  encontrada: boolean
  device_id?: string | null
  modelo?: string | null
  online: boolean
  motivo?: string | null
}

export interface RedeDiagnostico {
  encontrada: boolean
  last_inform: string | null
  aparelhos: RedeAparelho[]
  sinal: RedeSinal | null
  motivo: string | null
}

export interface TrocarSenhaResult {
  status: string
  device_id: string
  reiniciando: boolean
  aviso: string
}

export interface RebootResult {
  status: string
  device_id: string
  aviso: string
}
```

- [ ] **Step 2: Adicionar os hooks em `queries.ts`**

No fim de `apps/dashboard/lib/api/queries.ts` (segue o padrão `useQuery`/`useMutation` + `apiFetch` + `toast` já usados no arquivo; `toast` já é importado lá — confirme e reuse o mesmo import):

```typescript
export function useRedeStatusConversa(conversaId: string, enabled: boolean) {
  return useQuery<import('./types').RedeStatus>({
    queryKey: ['rede-status', conversaId],
    queryFn: () => apiFetch(`/api/v1/conversas/${conversaId}/rede/status`),
    enabled,
    staleTime: 30_000,
  })
}

export function useRedeDiagnostico(conversaId: string, enabled: boolean) {
  return useQuery<import('./types').RedeDiagnostico>({
    queryKey: ['rede-diagnostico', conversaId],
    queryFn: () => apiFetch(`/api/v1/conversas/${conversaId}/rede/diagnostico`),
    enabled,
  })
}

export function useTrocarSenhaConversa(conversaId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (senha: string) =>
      apiFetch<import('./types').TrocarSenhaResult>(
        `/api/v1/conversas/${conversaId}/rede/wifi/senha`,
        { method: 'POST', body: JSON.stringify({ senha }) },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rede-diagnostico', conversaId] })
      qc.invalidateQueries({ queryKey: ['rede-status', conversaId] })
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : 'Falha ao trocar a senha'),
  })
}

export function useReiniciarOnu(conversaId: string) {
  return useMutation({
    mutationFn: () =>
      apiFetch<import('./types').RebootResult>(
        `/api/v1/conversas/${conversaId}/rede/reboot`,
        { method: 'POST' },
      ),
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : 'Falha ao reiniciar'),
  })
}
```

- [ ] **Step 3: Verificar (typecheck)**

Run: `cd apps/dashboard && pnpm typecheck` (ou `pnpm tsc --noEmit`)
Expected: sem erros nos arquivos alterados.

- [ ] **Step 4: Commit**

```bash
git add apps/dashboard/lib/api/types.ts apps/dashboard/lib/api/queries.ts
git commit -m "feat(rede/dashboard): tipos + hooks react-query da rede na conversa"
```

---

### Task 7: Dashboard — painel "Rede" + selo + colar diagnóstico

**Files:**
- Create: `apps/dashboard/components/conversa-rede-panel.tsx`
- Modify: `apps/dashboard/components/conversa-chat.tsx`

- [ ] **Step 1: Criar `conversa-rede-panel.tsx`**

```tsx
'use client'
import { Loader2, RotateCw, Wifi, WifiOff } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  useRedeDiagnostico,
  useReiniciarOnu,
  useTrocarSenhaConversa,
} from '@/lib/api/queries'
import type { RedeDiagnostico } from '@/lib/api/types'

/** Cor do RX power (GPON, dBm): verde -8..-25, amarelo -25..-27, vermelho fora. */
export function corRx(rx: number | null | undefined): string {
  if (rx == null) return 'text-muted-foreground'
  if (rx > -8 || rx < -27) return 'text-red-500'
  if (rx < -25) return 'text-amber-500'
  return 'text-green-500'
}

export function fmtUptime(s: number | null | undefined): string {
  if (s == null) return '—'
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (d > 0) return `${d}d ${h}h`
  if (h > 0) return `${h}h ${m}min`
  return `${m}min`
}

/** Resumo amigável pra colar na conversa. */
export function resumoDiagnostico(d: RedeDiagnostico): string {
  if (!d.encontrada) return 'Não localizei o equipamento deste cliente na rede.'
  const partes: string[] = []
  if (d.sinal?.rx_power != null) partes.push(`sinal ${d.sinal.rx_power} dBm`)
  if (d.sinal?.conexao_pppoe) partes.push(`conexão ${d.sinal.conexao_pppoe}`)
  if (d.sinal?.uptime_s != null) partes.push(`estável há ${fmtUptime(d.sinal.uptime_s)}`)
  partes.push(`${d.aparelhos.length} aparelho(s) conectado(s)`)
  return `Diagnóstico da sua rede: ${partes.join(', ')}.`
}

interface Props {
  conversaId: string
  temCliente: boolean
  onColarDiagnostico: (texto: string) => void
}

export function ConversaRedePanel({ conversaId, temCliente, onColarDiagnostico }: Props) {
  const diag = useRedeDiagnostico(conversaId, temCliente)
  const trocar = useTrocarSenhaConversa(conversaId)
  const reboot = useReiniciarOnu(conversaId)
  const [senha, setSenha] = useState('')

  if (!temCliente) {
    return (
      <p className="text-sm text-muted-foreground">
        Vincule o cliente à conversa para ver e gerenciar a rede.
      </p>
    )
  }
  if (diag.isLoading) {
    return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
  }
  if (diag.isError || !diag.data) {
    return <p className="text-sm text-destructive">Não foi possível carregar a rede.</p>
  }
  const d = diag.data
  if (!d.encontrada) {
    return (
      <p className="text-sm text-muted-foreground">
        Cliente sem equipamento gerenciável na rede.
      </p>
    )
  }

  async function confirmarEReboot() {
    if (!window.confirm('A internet do cliente vai reiniciar e volta em ~2min. Continuar?')) return
    const r = await reboot.mutateAsync()
    if (r) window.alert(r.aviso)
  }

  async function confirmarETrocar() {
    if (senha.length < 8 || senha.length > 63) {
      window.alert('A senha deve ter de 8 a 63 caracteres.')
      return
    }
    if (!window.confirm('A internet do cliente pode reiniciar (~2min) ao trocar a senha. Continuar?')) return
    const r = await trocar.mutateAsync(senha)
    if (r) {
      window.alert(r.aviso)
      setSenha('')
    }
  }

  return (
    <div className="space-y-4 text-sm">
      {/* Sinal */}
      <div>
        <p className="font-semibold">Sinal da fibra</p>
        {d.sinal == null ? (
          <p className="text-muted-foreground">
            Ainda não disponível — atualize em ~5min.
          </p>
        ) : (
          <div className="space-y-0.5">
            <p>
              <span className={corRx(d.sinal.rx_power)}>● </span>
              RX: {d.sinal.rx_power ?? '—'} dBm · TX: {d.sinal.tx_power ?? '—'} dBm
            </p>
            <p>
              GPON: {d.sinal.status_gpon ?? '—'} · PPPoE: {d.sinal.conexao_pppoe ?? '—'}
            </p>
            {d.sinal.ip_externo && <p>IP: {d.sinal.ip_externo}</p>}
            <p>Uptime: {fmtUptime(d.sinal.uptime_s)}</p>
          </div>
        )}
      </div>

      {/* Aparelhos */}
      <div>
        <p className="font-semibold">Aparelhos conectados ({d.aparelhos.length})</p>
        {d.aparelhos.length === 0 ? (
          <p className="text-muted-foreground">Nenhum aparelho no momento.</p>
        ) : (
          <ul className="space-y-0.5">
            {d.aparelhos.map((a) => (
              <li key={a.mac} className="font-mono text-xs">
                {a.nome || a.ip} · {a.ip} · {a.mac}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Ações */}
      <div className="space-y-2 border-t pt-3">
        <Input
          placeholder="Nova senha do WiFi (8–63)"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={confirmarETrocar} disabled={trocar.isPending}>
            {trocar.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Trocar senha'}
          </Button>
          <Button size="sm" variant="outline" onClick={confirmarEReboot} disabled={reboot.isPending}>
            <RotateCw className="mr-1 h-4 w-4" /> Reiniciar ONU
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onColarDiagnostico(resumoDiagnostico(d))}>
            Colar diagnóstico na resposta
          </Button>
        </div>
      </div>
    </div>
  )
}

/** Selo de saúde pro header da conversa. */
export function RedeBadge({ conversaId, temCliente }: { conversaId: string; temCliente: boolean }) {
  const st = useRedeStatusBadge(conversaId, temCliente)
  if (!temCliente || !st.data?.encontrada) return null
  return st.data.online ? (
    <span className="inline-flex items-center gap-1 text-xs text-green-600">
      <Wifi className="h-3 w-3" /> online
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
      <WifiOff className="h-3 w-3" /> offline
    </span>
  )
}
```

Adicione o import do hook de status no topo do arquivo:
`import { useRedeStatusConversa as useRedeStatusBadge } from '@/lib/api/queries'`
(junto dos outros imports de `@/lib/api/queries`).

- [ ] **Step 2: Plugar na `conversa-chat.tsx`**

(a) No topo, importe o painel e o selo:
```tsx
import { ConversaRedePanel, RedeBadge } from './conversa-rede-panel'
```

(b) Inclua o tipo da aba: troque a linha 38
`type Tab = 'mensagens' | 'cliente' | 'nova-os'`
por
`type Tab = 'mensagens' | 'cliente' | 'nova-os' | 'rede'`

(c) Adicione a aba "Rede" ao array `TABS` (perto da linha 281):
```tsx
  const TABS: { id: Tab; label: string }[] = [
    { id: 'mensagens', label: 'Mensagens' },
    { id: 'cliente', label: 'Cliente SGP' },
    { id: 'rede', label: 'Rede' },
    { id: 'nova-os', label: '+ Nova OS' },
  ]
```

(d) Renderize o conteúdo da aba. Logo após o bloco `{tab === 'cliente' && (...)}` (que termina por volta da linha 506), adicione:
```tsx
        {tab === 'rede' && (
          <div className="p-4">
            <ConversaRedePanel
              conversaId={conversaId}
              temCliente={!!data.cliente_id}
              onColarDiagnostico={(texto) => {
                setText(texto)
                setTab('mensagens')
              }}
            />
          </div>
        )}
```
(`conversaId`, `data`, `setText` e `setTab` já existem no escopo do componente — linhas 61/70/71.)

(e) Selo no header: encontre onde o nome/título da conversa é renderizado no cabeçalho do componente (perto do `ConversaSlaTimer`/topo do painel central) e adicione ao lado:
```tsx
            <RedeBadge conversaId={conversaId} temCliente={!!data.cliente_id} />
```

- [ ] **Step 3: Verificar (typecheck + build)**

Run: `cd apps/dashboard && pnpm typecheck && pnpm build`
Expected: sem erros; build passa.

- [ ] **Step 4: Commit**

```bash
git add apps/dashboard/components/conversa-rede-panel.tsx apps/dashboard/components/conversa-chat.tsx
git commit -m "feat(rede/dashboard): aba Rede na conversa + selo de saude + colar diagnostico"
```

---

## Self-review notes / follow-up

- **Selo com cor do sinal:** nesta fatia o selo mostra só online/offline (via `/status`, leve). A cor do sinal aparece no painel (aba Rede). Subir a cor pro selo exigiria carregar o diagnóstico (que bate na ONU) de toda conversa aberta — evitado de propósito.
- **HG6145D:** o sinal óptico depende do path GPON por modelo (mapa em `GPON_CFG_PATHS`, backend Fatia 2). No parque FiberHome o sinal pode vir "—" até mapear — pendência herdada da Fatia 2, não bloqueia a Fatia 3.
- **Confirmações via `window.confirm/alert`:** mínimo viável; se o projeto tiver um componente de Dialog/AlertDialog padronizado, trocar por ele numa polish futura (não bloqueia).
