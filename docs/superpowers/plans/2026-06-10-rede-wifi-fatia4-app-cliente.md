# Rede WiFi — Fatia 4 (app cliente trocar a própria senha) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que o cliente final troque a senha do WiFi de casa pelo app, com tela bonita, avisando do reboot e mostrando "em construção" quando o roteador ainda não está no GenieACS.

**Architecture:** Endpoints novos exclusivos do cliente sob `/api/v1/cliente-app/rede/*` (auth `get_current_cliente_user`) que derivam o CPF do token e reusam o `RedeService`/`get_rede_service` já existentes (da Fatia 1, app técnico). Cooldown anti-flood de 5 min por `cpf_hash` na tabela `rede_wifi_pedido`. Frontend novo `lib/features/rede/` no padrão visual do `conexao_screen`.

**Tech Stack:** Backend FastAPI + SQLAlchemy async + Pydantic. Frontend Flutter + Riverpod + Dio + go_router. Spec: `docs/superpowers/specs/2026-06-10-rede-wifi-fatia4-app-cliente-design.md`.

> **⚠️ Sem stack local (regra do projeto):** não rodar `pytest`/`flutter`/`alembic`/`docker` nesta máquina. Os passos "Run" de teste acontecem na máquina de deploy / CI **depois do push**. Escrever o código + commitar; a verificação roda no CI. NÃO commitar/pushar sem OK do Robert.

> **⚠️ Fatia 5 é o próximo passo crítico** (hardening: firewall 7547 + TLS + auth por ONU + STUN). É pré-requisito pra apontar a base real de clientes. Cobrar o Robert quando esta Fatia 4 fechar.

---

## File Structure

**Backend (criar):**
- `apps/api/src/ondeline_api/api/schemas/cliente_app_rede.py` — schemas do cliente (sem CPF no input).
- `apps/api/src/ondeline_api/api/v1/cliente_app_rede.py` — 2 endpoints (status + troca com cooldown).
- `apps/api/tests/test_cliente_app_rede.py` — testes E2E.

**Backend (modificar):**
- `apps/api/src/ondeline_api/main.py` — registrar o router novo.

**Frontend (criar):**
- `apps/cliente-mobile/lib/core/api/rede_repository.dart` — DTOs + repo + providers.
- `apps/cliente-mobile/lib/features/rede/rede_screen.dart` — tela "Minha Rede WiFi" (3 estados + fluxo de troca).

**Frontend (modificar):**
- `apps/cliente-mobile/lib/router.dart` — rota `/rede`.
- `apps/cliente-mobile/lib/features/home/home_screen.dart` — QuickAction "Minha rede".
- `apps/cliente-mobile/lib/features/conexao/conexao_screen.dart` — botão "Gerenciar rede WiFi" quando ativo.

---

## Task 1: Schemas do cliente

**Files:**
- Create: `apps/api/src/ondeline_api/api/schemas/cliente_app_rede.py`

- [ ] **Step 1: Escrever o arquivo de schemas**

```python
"""Schemas para /api/v1/cliente-app/rede/* (app do cliente).

Diferente do schema do tecnico (api/schemas/rede.py): aqui o CPF NUNCA vem no
body — e derivado do token do cliente logado. Resposta enxuta (sem device_id/
internals do GenieACS).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class RedeWifiOut(BaseModel):
    ssid: str


class RedeClienteStatusOut(BaseModel):
    # encontrada=False -> app mostra tela "em construcao" (cliente sem ONU no
    # GenieACS ainda).
    encontrada: bool
    online: bool = False
    modelo: str | None = None
    redes: list[RedeWifiOut] = Field(default_factory=list)


class TrocarSenhaClienteIn(BaseModel):
    # SEM cpf: o cliente so pode trocar a propria rede (CPF do token).
    senha: str = Field(min_length=8, max_length=63)


class TrocarSenhaClienteOut(BaseModel):
    status: str  # "enviado"
    reiniciando: bool
    aviso: str
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/src/ondeline_api/api/schemas/cliente_app_rede.py
git commit -m "feat(rede): schemas do app cliente (sem cpf no body)"
```

---

## Task 2: Endpoints do cliente (status + troca com cooldown)

**Files:**
- Create: `apps/api/src/ondeline_api/api/v1/cliente_app_rede.py`
- Modify: `apps/api/src/ondeline_api/main.py`

- [ ] **Step 1: Escrever o router**

```python
"""GET/POST /api/v1/cliente-app/rede/* - cliente troca a propria senha WiFi.

Reusa RedeService + get_rede_service (a dependency NAO forca role; o role do
tecnico fica nas rotas de /api/v1/rede). O CPF vem do token (decrypt_pii), nunca
do body: o cliente so mexe na propria ONU. Cooldown anti-flood de reboots.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.genieacs.base import GenieAcsUnavailableError
from ondeline_api.api.schemas.cliente_app_rede import (
    RedeClienteStatusOut,
    RedeWifiOut,
    TrocarSenhaClienteIn,
    TrocarSenhaClienteOut,
)
from ondeline_api.api.v1.rede import get_rede_service
from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.db.crypto import decrypt_pii, hash_pii
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.db.models.rede import RedeWifiPedido
from ondeline_api.deps import get_db
from ondeline_api.services.rede_service import (
    CpfInvalidoError,
    OnuNaoEncontradaError,
    RedeService,
    SenhaInvalidaError,
)

router = APIRouter(prefix="/api/v1/cliente-app/rede", tags=["cliente-app:rede"])

COOLDOWN_MINUTOS = 5
AVISO_REBOOT = "Sua internet vai reiniciar e voltar em cerca de 2 minutos."


def _so_digitos(cpf: str) -> str:
    return "".join(ch for ch in (cpf or "") if ch.isdigit())


async def _minutos_cooldown_restante(session: AsyncSession, cpf_digits: str) -> int:
    """Minutos que faltam pro cliente poder trocar de novo (0 = liberado).

    Olha a troca mais recente do mesmo cpf_hash dentro da janela. cpf_hash e
    escrito pelo RedeService como hash_pii(_so_digitos(cpf)); replicamos igual.
    """
    since = datetime.now(timezone.utc) - timedelta(minutes=COOLDOWN_MINUTOS)
    stmt = select(func.max(RedeWifiPedido.created_at)).where(
        RedeWifiPedido.cpf_hash == hash_pii(cpf_digits),
        RedeWifiPedido.created_at >= since,
    )
    last = (await session.execute(stmt)).scalar_one_or_none()
    if last is None:
        return 0
    libera = last + timedelta(minutes=COOLDOWN_MINUTOS)
    restante = (libera - datetime.now(timezone.utc)).total_seconds()
    return max(0, math.ceil(restante / 60))


@router.get("/status", response_model=RedeClienteStatusOut)
async def status_rede_cliente(
    user: Annotated[ClienteAppUser, Depends(get_current_cliente_user)],
    service: Annotated[RedeService, Depends(get_rede_service)],
) -> RedeClienteStatusOut:
    cpf = decrypt_pii(user.cpf_encrypted)
    try:
        st = await service.status_rede(cpf)
    except CpfInvalidoError:
        # Cliente logado deveria ter CPF valido; trata defensivamente como
        # "sem ONU" (mostra em construcao) em vez de 500.
        return RedeClienteStatusOut(encontrada=False)
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    if not st.encontrada or st.device is None:
        return RedeClienteStatusOut(encontrada=False)
    d = st.device
    # SSIDs distintos, preservando ordem (uma ONU repete o SSID em 2.4 e 5G).
    vistos: list[str] = []
    for r in d.redes:
        if r.ssid and r.ssid not in vistos:
            vistos.append(r.ssid)
    return RedeClienteStatusOut(
        encontrada=True,
        online=d.online,
        modelo=d.modelo,
        redes=[RedeWifiOut(ssid=s) for s in vistos],
    )


@router.post("/wifi/senha", response_model=TrocarSenhaClienteOut)
async def trocar_senha_cliente(
    payload: TrocarSenhaClienteIn,
    user: Annotated[ClienteAppUser, Depends(get_current_cliente_user)],
    service: Annotated[RedeService, Depends(get_rede_service)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TrocarSenhaClienteOut:
    cpf = decrypt_pii(user.cpf_encrypted)
    cpf_digits = _so_digitos(cpf)

    restante = await _minutos_cooldown_restante(session, cpf_digits)
    if restante > 0:
        raise HTTPException(
            status_code=429,
            detail={"erro": "cooldown", "minutos_restantes": restante},
        )

    try:
        res = await service.trocar_senha_wifi(
            cpf=cpf,
            nova_senha=payload.senha,
            serial=None,
            ator_user_id=user.id,
        )
    except (SenhaInvalidaError, CpfInvalidoError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except OnuNaoEncontradaError as e:
        raise HTTPException(status_code=404, detail="ONU nao encontrada") from e
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e

    aviso = AVISO_REBOOT if res.reiniciando else "Senha enviada."
    return TrocarSenhaClienteOut(
        status="enviado", reiniciando=res.reiniciando, aviso=aviso
    )
```

- [ ] **Step 2: Registrar o router no main.py**

Em `apps/api/src/ondeline_api/main.py`, na seção de imports (perto de `from ondeline_api.api.v1 import cliente_app_conexao as v1_cliente_app_conexao`), adicionar:

```python
from ondeline_api.api.v1 import cliente_app_rede as v1_cliente_app_rede
```

E na seção de `app.include_router(...)` (perto de `app.include_router(v1_cliente_app_os.router)`), adicionar:

```python
    app.include_router(v1_cliente_app_rede.router)
```

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/cliente_app_rede.py apps/api/src/ondeline_api/main.py
git commit -m "feat(rede): endpoints do app cliente (status + troca + cooldown 5min)"
```

---

## Task 3: Testes E2E dos endpoints do cliente

**Files:**
- Create: `apps/api/tests/test_cliente_app_rede.py`

- [ ] **Step 1: Escrever os testes**

```python
"""E2E /api/v1/cliente-app/rede/* (app do cliente).

Reusa o get_rede_service fake (igual test_v1_rede), mas autentica como
ClienteAppUser e roda o cooldown contra a sessao real.
"""
from __future__ import annotations

import collections.abc
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.adapters.genieacs.base import GenieAcsDevice, RedeWlan
from ondeline_api.api.v1.rede import get_rede_service
from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.auth.passwords import hash_password
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.db.models.rede import RedeWifiPedido
from ondeline_api.deps import get_db
from ondeline_api.main import create_app
from ondeline_api.services.rede_service import (
    OnuNaoEncontradaError,
    ResultadoTroca,
    StatusRede,
)
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

TEST_CPF = "11144477735"


class _FakeService:
    def __init__(
        self,
        *,
        status: StatusRede | None = None,
        troca: ResultadoTroca | None = None,
        raise_troca: Exception | None = None,
    ) -> None:
        self._status = status
        self._troca = troca
        self._raise = raise_troca

    async def status_rede(self, cpf: str, serial: str | None = None) -> StatusRede:
        assert self._status is not None
        return self._status

    async def trocar_senha_wifi(
        self, *, cpf: str, nova_senha: str, serial: str | None, ator_user_id: UUID
    ) -> ResultadoTroca:
        if self._raise:
            raise self._raise
        assert self._troca is not None
        return self._troca


def _dev() -> GenieAcsDevice:
    return GenieAcsDevice(
        device_id="30E1F1-AX1800-X",
        modelo="AX1800",
        fabricante="INTELBRAS",
        online=True,
        redes=[
            RedeWlan(instancia=1, ssid="CASA", enabled=True),
            RedeWlan(instancia=6, ssid="CASA", enabled=True),  # 2.4 + 5G mesmo SSID
        ],
    )


def _make_app(db_session: AsyncSession, fake: _FakeService) -> FastAPI:
    app = create_app()

    async def _override_db() -> collections.abc.AsyncIterator[AsyncSession]:
        yield db_session

    async def _override_rede_service() -> collections.abc.AsyncIterator[_FakeService]:
        yield fake

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_rede_service] = _override_rede_service
    return app


async def _make_cliente(db_session: AsyncSession) -> ClienteAppUser:
    u = ClienteAppUser(
        cpf_hash=hash_pii(TEST_CPF),
        cpf_last4=TEST_CPF[-4:],
        cpf_encrypted=encrypt_pii(TEST_CPF),
        nome_encrypted=encrypt_pii("Cliente Teste"),
        telefone_encrypted=encrypt_pii("92981234567"),
        password_hash=hash_password("SenhaForte123!"),
        sgp_id="12345",
        status="active",
    )
    db_session.add(u)
    await db_session.commit()
    return u


def _auth(u: ClienteAppUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {jwt_mod.encode_cliente_access_token(u.id)}"}


async def test_status_encontrada(db_session: AsyncSession) -> None:
    fake = _FakeService(status=StatusRede(encontrada=True, device=_dev()))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/cliente-app/rede/status", headers=_auth(u))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["encontrada"] is True
    assert body["modelo"] == "AX1800"
    assert body["online"] is True
    # SSID repetido (2.4 + 5G) vira 1 so na resposta do cliente.
    assert [x["ssid"] for x in body["redes"]] == ["CASA"]


async def test_status_nao_encontrada(db_session: AsyncSession) -> None:
    """encontrada=False vira o gatilho da tela 'em construcao'."""
    fake = _FakeService(status=StatusRede(encontrada=False, motivo="onu_nao_encontrada"))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/cliente-app/rede/status", headers=_auth(u))
    assert r.status_code == 200, r.text
    assert r.json()["encontrada"] is False


async def test_trocar_senha_ok(db_session: AsyncSession) -> None:
    fake = _FakeService(troca=ResultadoTroca(device_id="30E1F1-AX1800-X", reiniciando=True))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/v1/cliente-app/rede/wifi/senha",
            json={"senha": "senhaboa123"},
            headers=_auth(u),
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "enviado"
    assert body["reiniciando"] is True


async def test_trocar_sem_token_401(db_session: AsyncSession) -> None:
    fake = _FakeService(troca=ResultadoTroca(device_id="X", reiniciando=False))
    app = _make_app(db_session, fake)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/cliente-app/rede/wifi/senha", json={"senha": "senhaboa123"})
    assert r.status_code == 401, r.text


async def test_trocar_onu_nao_encontrada_404(db_session: AsyncSession) -> None:
    fake = _FakeService(raise_troca=OnuNaoEncontradaError("sem device"))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/v1/cliente-app/rede/wifi/senha",
            json={"senha": "senhaboa123"},
            headers=_auth(u),
        )
    assert r.status_code == 404, r.text


async def test_cooldown_429(db_session: AsyncSession) -> None:
    """Troca recente do mesmo cpf_hash -> 429 com minutos_restantes."""
    fake = _FakeService(troca=ResultadoTroca(device_id="X", reiniciando=False))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    # Registra uma troca AGORA (default created_at = now()).
    db_session.add(
        RedeWifiPedido(
            cpf_hash=hash_pii(TEST_CPF),
            device_id="30E1F1-AX1800-X",
            ator_user_id=u.id,
            status="enviado",
            reiniciou=True,
        )
    )
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/v1/cliente-app/rede/wifi/senha",
            json={"senha": "senhaboa123"},
            headers=_auth(u),
        )
    assert r.status_code == 429, r.text
    assert r.json()["detail"]["minutos_restantes"] >= 1
```

- [ ] **Step 2: Rodar os testes (no CI/deploy — sem stack local)**

Run: `cd apps/api && pytest tests/test_cliente_app_rede.py -v`
Expected: 6 PASS.

- [ ] **Step 3: Commit**

```bash
git add apps/api/tests/test_cliente_app_rede.py
git commit -m "test(rede): E2E dos endpoints do app cliente (status/troca/cooldown)"
```

---

## Task 4: Repository + DTOs no Flutter

**Files:**
- Create: `apps/cliente-mobile/lib/core/api/rede_repository.dart`

- [ ] **Step 1: Escrever o repository**

```dart
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

class RedeWifiInfo {
  RedeWifiInfo({required this.ssid});
  factory RedeWifiInfo.fromJson(Map<String, dynamic> j) =>
      RedeWifiInfo(ssid: j['ssid'] as String);
  final String ssid;
}

class RedeStatusDto {
  RedeStatusDto({
    required this.encontrada,
    required this.online,
    this.modelo,
    required this.redes,
  });

  factory RedeStatusDto.fromJson(Map<String, dynamic> j) => RedeStatusDto(
        encontrada: j['encontrada'] as bool,
        online: (j['online'] as bool?) ?? false,
        modelo: j['modelo'] as String?,
        redes: ((j['redes'] as List?) ?? const [])
            .map((e) => RedeWifiInfo.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  final bool encontrada;
  final bool online;
  final String? modelo;
  final List<RedeWifiInfo> redes;

  /// Nome amigavel da rede pro hero (primeiro SSID, ou fallback).
  String get nomeRede => redes.isNotEmpty ? redes.first.ssid : 'Sua rede WiFi';
}

class TrocaResultDto {
  TrocaResultDto({
    required this.status,
    required this.reiniciando,
    required this.aviso,
  });

  factory TrocaResultDto.fromJson(Map<String, dynamic> j) => TrocaResultDto(
        status: j['status'] as String,
        reiniciando: (j['reiniciando'] as bool?) ?? false,
        aviso: (j['aviso'] as String?) ?? '',
      );

  final String status;
  final bool reiniciando;
  final String aviso;
}

/// Lancada quando o backend responde 429 (cooldown anti-flood).
class CooldownException implements Exception {
  CooldownException(this.minutosRestantes);
  final int minutosRestantes;
}

class RedeRepository {
  RedeRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app/rede';

  Future<RedeStatusDto> status() async {
    final r = await _dio.get('$_base/status');
    return RedeStatusDto.fromJson(r.data as Map<String, dynamic>);
  }

  Future<TrocaResultDto> trocarSenha(String senha) async {
    try {
      final r = await _dio.post('$_base/wifi/senha', data: {'senha': senha});
      return TrocaResultDto.fromJson(r.data as Map<String, dynamic>);
    } on DioException catch (e) {
      if (e.response?.statusCode == 429) {
        throw CooldownException(_minutosFrom(e.response?.data));
      }
      rethrow;
    }
  }

  int _minutosFrom(Object? data) {
    if (data is Map && data['detail'] is Map) {
      final m = (data['detail'] as Map)['minutos_restantes'];
      if (m is int) return m;
    }
    return 5;
  }
}

final redeRepositoryProvider = Provider<RedeRepository>(
  (ref) => RedeRepository(ref.watch(apiClientProvider)),
);

/// Status da rede do cliente. O backend resolve a ONU iterando TODOS os
/// contratos do CPF, entao nao precisa de contrato_id aqui (MVP).
final redeStatusProvider = FutureProvider<RedeStatusDto>(
  (ref) => ref.watch(redeRepositoryProvider).status(),
);
```

- [ ] **Step 2: Commit**

```bash
git add apps/cliente-mobile/lib/core/api/rede_repository.dart
git commit -m "feat(rede/app): repository + DTOs de rede WiFi do cliente"
```

---

## Task 5: Tela "Minha Rede WiFi"

**Files:**
- Create: `apps/cliente-mobile/lib/features/rede/rede_screen.dart`

- [ ] **Step 1: Escrever a tela**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/rede_repository.dart';
import '../../core/branding/brand_tokens.dart';

enum _Fase { editando, enviando, reconectando, pronto }

class RedeScreen extends ConsumerStatefulWidget {
  const RedeScreen({super.key});

  @override
  ConsumerState<RedeScreen> createState() => _RedeScreenState();
}

class _RedeScreenState extends ConsumerState<RedeScreen> {
  final _senha = TextEditingController();
  final _confirma = TextEditingController();
  bool _obscure = true;
  _Fase _fase = _Fase.editando;
  String? _erro;

  @override
  void dispose() {
    _senha.dispose();
    _confirma.dispose();
    super.dispose();
  }

  String? _validar() {
    final s = _senha.text;
    if (s.length < 8 || s.length > 63) {
      return 'A senha precisa ter de 8 a 63 caracteres.';
    }
    if (s != _confirma.text) return 'As senhas não são iguais.';
    return null;
  }

  Future<void> _confirmarTroca() async {
    final erro = _validar();
    if (erro != null) {
      setState(() => _erro = erro);
      return;
    }
    setState(() => _erro = null);

    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const _ConfirmSheet(),
    );
    if (ok != true || !mounted) return;

    setState(() => _fase = _Fase.enviando);
    try {
      final res = await ref.read(redeRepositoryProvider).trocarSenha(_senha.text);
      if (!mounted) return;
      setState(() => _fase = res.reiniciando ? _Fase.reconectando : _Fase.pronto);
    } on CooldownException catch (e) {
      if (!mounted) return;
      setState(() => _fase = _Fase.editando);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Você trocou a senha há pouco. Aguarde ~${e.minutosRestantes} min pra trocar de novo.',
          ),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      setState(() => _fase = _Fase.editando);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Não conseguimos trocar a senha agora. Tente mais tarde.'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(redeStatusProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Minha Rede WiFi'), elevation: 0),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(redeStatusProvider);
          await ref.read(redeStatusProvider.future);
        },
        child: async.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => _EmConstrucao(
            titulo: 'Não conseguimos carregar agora',
            texto: 'Tente novamente em instantes.',
          ),
          data: (st) {
            if (!st.encontrada) {
              return const _EmConstrucao(
                titulo: 'Gerenciamento do WiFi a caminho 🛠️',
                texto:
                    'Estamos preparando o controle do seu WiFi por aqui. Em breve '
                    'você vai poder trocar a senha da sua rede direto pelo app.',
              );
            }
            if (_fase == _Fase.reconectando) return _Reconectando(rede: st);
            if (_fase == _Fase.pronto) {
              return _Sucesso(onVoltar: () => context.pop());
            }
            return _FormTroca(
              rede: st,
              senha: _senha,
              confirma: _confirma,
              obscure: _obscure,
              erro: _erro,
              enviando: _fase == _Fase.enviando,
              onToggleObscure: () => setState(() => _obscure = !_obscure),
              onTrocar: _confirmarTroca,
            );
          },
        ),
      ),
    );
  }
}

class _FormTroca extends StatelessWidget {
  const _FormTroca({
    required this.rede,
    required this.senha,
    required this.confirma,
    required this.obscure,
    required this.erro,
    required this.enviando,
    required this.onToggleObscure,
    required this.onTrocar,
  });

  final RedeStatusDto rede;
  final TextEditingController senha;
  final TextEditingController confirma;
  final bool obscure;
  final String? erro;
  final bool enviando;
  final VoidCallback onToggleObscure;
  final VoidCallback onTrocar;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return ListView(
      physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      children: [
        _HeroRede(rede: rede),
        const SizedBox(height: BrandTokens.spaceLg),
        Container(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          decoration: BoxDecoration(
            color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
            border: Border.all(color: isDark ? Colors.white12 : BrandTokens.divider),
            boxShadow: BrandTokens.elevation1,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Trocar senha do WiFi',
                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
              ),
              const SizedBox(height: BrandTokens.spaceMd),
              TextField(
                controller: senha,
                obscureText: obscure,
                decoration: InputDecoration(
                  labelText: 'Nova senha',
                  suffixIcon: IconButton(
                    icon: Icon(obscure ? Icons.visibility_off : Icons.visibility),
                    onPressed: onToggleObscure,
                  ),
                ),
              ),
              const SizedBox(height: BrandTokens.spaceMd),
              TextField(
                controller: confirma,
                obscureText: obscure,
                decoration: const InputDecoration(labelText: 'Confirmar senha'),
              ),
              if (erro != null) ...[
                const SizedBox(height: BrandTokens.spaceSm),
                Text(erro!, style: const TextStyle(color: BrandTokens.danger, fontSize: 13)),
              ],
              const SizedBox(height: BrandTokens.spaceSm),
              const Text(
                'De 8 a 63 caracteres. Ao trocar, sua internet reinicia por ~2 min.',
                style: TextStyle(color: BrandTokens.textSecondary, fontSize: 12),
              ),
              const SizedBox(height: BrandTokens.spaceMd),
              FilledButton.icon(
                onPressed: enviando ? null : onTrocar,
                icon: enviando
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.lock_reset_rounded, size: 18),
                label: Text(enviando ? 'Enviando…' : 'Trocar senha do WiFi'),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _HeroRede extends StatelessWidget {
  const _HeroRede({required this.rede});
  final RedeStatusDto rede;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF14B8B0), Color(0xFF22E0A1)],
        ),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        boxShadow: BrandTokens.elevation2,
      ),
      child: Row(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.18),
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white.withOpacity(0.3), width: 2),
            ),
            child: const Icon(Icons.wifi_rounded, color: Colors.white, size: 32),
          ),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  rede.nomeRede,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.3,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Text(
                  rede.online ? 'Sua rede está online' : 'Rede fora do ar no momento',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ConfirmSheet extends StatelessWidget {
  const _ConfirmSheet();

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(BrandTokens.radiusXl)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Icon(Icons.warning_amber_rounded, color: BrandTokens.warning, size: 40),
            const SizedBox(height: BrandTokens.spaceMd),
            const Text(
              'Sua internet vai reiniciar',
              textAlign: TextAlign.center,
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
            ),
            const SizedBox(height: BrandTokens.spaceSm),
            const Text(
              'Ao trocar a senha, sua conexão reinicia e volta em cerca de 2 minutos. '
              'Depois, reconecte seus aparelhos (celular, TV, etc.) com a nova senha.',
              textAlign: TextAlign.center,
              style: TextStyle(color: BrandTokens.textSecondary, fontSize: 14, height: 1.4),
            ),
            const SizedBox(height: BrandTokens.spaceLg),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Trocar agora'),
            ),
            const SizedBox(height: BrandTokens.spaceSm),
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancelar'),
            ),
          ],
        ),
      ),
    );
  }
}

class _Reconectando extends StatelessWidget {
  const _Reconectando({required this.rede});
  final RedeStatusDto rede;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(BrandTokens.spaceLg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: BrandTokens.spaceLg),
            const Text(
              'Reconectando sua rede…',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
            ),
            const SizedBox(height: BrandTokens.spaceSm),
            const Text(
              'Senha enviada! Sua internet está reiniciando e volta em ~2 minutos. '
              'Seus aparelhos vão pedir a nova senha pra reconectar.',
              textAlign: TextAlign.center,
              style: TextStyle(color: BrandTokens.textSecondary, fontSize: 14, height: 1.4),
            ),
          ],
        ),
      ),
    );
  }
}

class _Sucesso extends StatelessWidget {
  const _Sucesso({required this.onVoltar});
  final VoidCallback onVoltar;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(BrandTokens.spaceLg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle_rounded, color: BrandTokens.success, size: 56),
            const SizedBox(height: BrandTokens.spaceMd),
            const Text(
              'Senha enviada!',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
            ),
            const SizedBox(height: BrandTokens.spaceSm),
            const Text(
              'Use a nova senha pra reconectar seus aparelhos.',
              textAlign: TextAlign.center,
              style: TextStyle(color: BrandTokens.textSecondary, fontSize: 14),
            ),
            const SizedBox(height: BrandTokens.spaceLg),
            FilledButton(onPressed: onVoltar, child: const Text('Voltar')),
          ],
        ),
      ),
    );
  }
}

class _EmConstrucao extends StatelessWidget {
  const _EmConstrucao({required this.titulo, required this.texto});
  final String titulo;
  final String texto;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
      padding: const EdgeInsets.all(BrandTokens.spaceXl),
      children: [
        const SizedBox(height: BrandTokens.spaceXxl),
        Center(
          child: Container(
            width: 96,
            height: 96,
            decoration: BoxDecoration(
              color: BrandTokens.primary.withOpacity(0.12),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.wifi_rounded, color: BrandTokens.primary, size: 48),
          ),
        ),
        const SizedBox(height: BrandTokens.spaceLg),
        Text(
          titulo,
          textAlign: TextAlign.center,
          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 20),
        ),
        const SizedBox(height: BrandTokens.spaceSm),
        Text(
          texto,
          textAlign: TextAlign.center,
          style: const TextStyle(color: BrandTokens.textSecondary, fontSize: 15, height: 1.4),
        ),
      ],
    );
  }
}
```

- [ ] **Step 2: Analisar (no CI/deploy — sem stack local)**

Run: `cd apps/cliente-mobile && flutter analyze lib/features/rede/rede_screen.dart lib/core/api/rede_repository.dart`
Expected: No issues.

- [ ] **Step 3: Commit**

```bash
git add apps/cliente-mobile/lib/features/rede/rede_screen.dart
git commit -m "feat(rede/app): tela Minha Rede WiFi (3 estados + fluxo de troca com reboot)"
```

---

## Task 6: Pontos de entrada (rota + Home + Conexão)

**Files:**
- Modify: `apps/cliente-mobile/lib/router.dart`
- Modify: `apps/cliente-mobile/lib/features/home/home_screen.dart`
- Modify: `apps/cliente-mobile/lib/features/conexao/conexao_screen.dart`

- [ ] **Step 1: Rota `/rede` no router.dart**

Adicionar o import (perto de `import 'features/conexao/conexao_screen.dart';`):

```dart
import 'features/rede/rede_screen.dart';
```

Adicionar a rota (perto do bloco `GoRoute(path: '/conexao', ...)`):

```dart
      GoRoute(
        path: '/rede',
        builder: (_, __) => const RedeScreen(),
      ),
```

- [ ] **Step 2: QuickAction "Minha rede" na Home**

Em `apps/cliente-mobile/lib/features/home/home_screen.dart`, dentro de `QuickActions(actions: [ ... ])` (perto da linha 114), adicionar como primeira ação da lista:

```dart
                  QuickAction(
                    icon: Icons.wifi_rounded,
                    label: 'Minha rede',
                    color: BrandTokens.primary,
                    onTap: () => context.push('/rede'),
                  ),
```

- [ ] **Step 3: Botão "Gerenciar rede WiFi" na tela Conexão**

Em `apps/cliente-mobile/lib/features/conexao/conexao_screen.dart`, no `ListView` do estado `data` (linhas ~40-43), trocar:

```dart
              if (c.status != 'ativo')
                _CtaSuporte(status: c.status)
              else
                const _DicaPanel(),
```

por:

```dart
              if (c.status != 'ativo')
                _CtaSuporte(status: c.status)
              else ...[
                const _GerenciarRedeButton(),
                const SizedBox(height: BrandTokens.spaceLg),
                const _DicaPanel(),
              ],
```

E adicionar o widget novo no fim do arquivo (antes de `class _Error`):

```dart
class _GerenciarRedeButton extends StatelessWidget {
  const _GerenciarRedeButton();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        color: BrandTokens.primary.withOpacity(0.08),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(color: BrandTokens.primary.withOpacity(0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Row(
            children: [
              Icon(Icons.wifi_rounded, color: BrandTokens.primary),
              SizedBox(width: BrandTokens.spaceSm),
              Expanded(
                child: Text(
                  'Quer trocar a senha do seu WiFi? Faça por aqui, na hora.',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                ),
              ),
            ],
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          FilledButton.icon(
            icon: const Icon(Icons.settings_rounded, size: 18),
            label: const Text('Gerenciar rede WiFi'),
            onPressed: () => context.push('/rede'),
          ),
        ],
      ),
    );
  }
}
```

> Nota: `conexao_screen.dart` já importa `go_router` e `BrandTokens`; sem imports novos.

- [ ] **Step 4: Analisar (no CI/deploy — sem stack local)**

Run: `cd apps/cliente-mobile && flutter analyze`
Expected: No issues.

- [ ] **Step 5: Commit**

```bash
git add apps/cliente-mobile/lib/router.dart apps/cliente-mobile/lib/features/home/home_screen.dart apps/cliente-mobile/lib/features/conexao/conexao_screen.dart
git commit -m "feat(rede/app): pontos de entrada (rota /rede + QuickAction Home + botao Conexao)"
```

---

## Self-Review (feita ao escrever o plano)

- **Cobertura do spec:** status (Task 2/4/5) ✓, troca com reboot+confirmação (Task 2/5) ✓, tela "em construção" via `encontrada=false` (Task 2 retorna, Task 5 renderiza) ✓, cooldown 5min (Task 2 + teste Task 3) ✓, CPF do token / nunca no body (Task 2) ✓, entradas Home+Conexão+rota (Task 6) ✓, testes backend (Task 3) ✓.
- **Consistência de tipos:** `RedeStatusDto`/`TrocaResultDto`/`CooldownException` definidos na Task 4 e usados na Task 5; `redeStatusProvider`/`redeRepositoryProvider` idem. Backend: `RedeClienteStatusOut`/`TrocarSenhaClienteIn`/`Out` da Task 1 usados na Task 2; `_FakeService` da Task 3 casa com a assinatura real de `RedeService` (`status_rede`, `trocar_senha_wifi`).
- **Decisão de implementação confirmada no código:** `ClienteAppUser.id` é UUID → passa direto em `ator_user_id=user.id` (sem ajuste de coluna). `cpf_hash` do cooldown = `hash_pii(_so_digitos(cpf))`, igual o `RedeService` grava.
- **Desvio consciente do spec:** o `redeStatusProvider` NÃO observa `contratoAtualProvider` — o backend (`status_rede`) já resolve iterando todos os contratos do CPF, então passar `contrato_id` seria parâmetro morto no MVP. Multi-contrato real fica pra quando o backend aceitar o filtro.

---

## Out of scope (Fatia 5 / futuro)

Ver aparelhos conectados, sinal óptico, aplicar instantâneo (STUN), TLS/firewall na 7547, trocar nome do SSID. **Fatia 5 (hardening) é o próximo passo crítico antes da base real.**
