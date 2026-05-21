# Cliente App — Fase 3: Home + Plano + Perfil

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Checkboxes `- [ ]` para tracking.

**Goal:** Cliente loga e vê plano vigente + dados pessoais. App passa a ser útil — primeiro valor real. 4 tabs no NavigationBar (Home/Faturas/Suporte/Perfil), sendo Faturas/Suporte stubs até Fase 4/5.

**Architecture:** Backend adiciona endpoints autenticados como cliente (`/me`, `/plano`, `/avisos`, `PATCH /me`, `POST /me/password`). Reaproveita `SgpCacheService` (já cacheia plano por 1h). Flutter ganha shell com NavigationBar, telas reais de Home + Perfil + editar dados + mudar senha. Cache curto em SharedPreferences pra last-known.

**Tech Stack:** mesma da Fase 2 + `shared_preferences`.

**Spec:** `docs/superpowers/specs/2026-05-21-cliente-mobile-app-design.md` (seções 4 tab 1 + tab 4, seção 6).
**Plano anterior:** Fase 1 (auth backend) + Fase 2 (scaffold Flutter).

---

## Decisões

1. **Sem tabela `avisos` nessa fase.** `/avisos` retorna lista vazia placeholder. Fase 7 adiciona tabela + UI admin pra postar. Home renderiza "sem avisos" gracefully.
2. **PATCH /me restringido:** edita só `telefone` e `email`. Nome/CPF/endereço **não** — exige fluxo de OS de mudança (Fase 5).
3. **`POST /me/password`** exige senha atual + nova. Sem forgot-flow (forgot já existe na Fase 1).
4. **Cache last-known:** Home grava `last_me_json` e `last_plano_json` em SharedPreferences. Em erro de rede, mostra cache. Cliente sempre vê algo.
5. **Tema controlado pelo perfil:** toggle claro/escuro/auto persistido em SharedPreferences. Vira `ThemeMode` em `main.dart`.

---

## File Structure

**Backend (modificar/criar):**
- Create: `apps/api/src/ondeline_api/api/v1/cliente_app_me.py`
- Modify: `apps/api/src/ondeline_api/api/schemas/cliente_app_auth.py` (adicionar MeOut, PlanoOut, etc)
- Modify: `apps/api/src/ondeline_api/main.py` (registrar novo router)
- Create: `apps/api/tests/test_cliente_app_me.py`

**Flutter (criar):**
- Create: `apps/cliente-mobile/lib/core/api/dto.dart` — Me, Plano, Aviso models
- Create: `apps/cliente-mobile/lib/core/api/me_repository.dart`
- Create: `apps/cliente-mobile/lib/core/cache/last_known_cache.dart`
- Create: `apps/cliente-mobile/lib/core/theme/theme_mode_controller.dart`
- Create: `apps/cliente-mobile/lib/features/shell/main_shell.dart`
- Replace: `apps/cliente-mobile/lib/features/home/home_screen.dart` (renomeia placeholder)
- Create: `apps/cliente-mobile/lib/features/home/widgets/hero_card.dart`
- Create: `apps/cliente-mobile/lib/features/home/widgets/quick_actions.dart`
- Create: `apps/cliente-mobile/lib/features/home/widgets/avisos_list.dart`
- Create: `apps/cliente-mobile/lib/features/perfil/perfil_screen.dart`
- Create: `apps/cliente-mobile/lib/features/perfil/editar_perfil_screen.dart`
- Create: `apps/cliente-mobile/lib/features/perfil/mudar_senha_screen.dart`
- Create: `apps/cliente-mobile/lib/features/faturas/faturas_stub_screen.dart`
- Create: `apps/cliente-mobile/lib/features/suporte/suporte_stub_screen.dart`
- Modify: `apps/cliente-mobile/lib/router.dart` (substitui /home pelo MainShell + sub-rotas)
- Modify: `apps/cliente-mobile/lib/main.dart` (theme controlado por provider)
- Modify: `apps/cliente-mobile/pubspec.yaml` (+shared_preferences)

---

## Task 1: Schemas Pydantic novos

**File:** `apps/api/src/ondeline_api/api/schemas/cliente_app_auth.py` (adicionar — não duplicar arquivo).

Adicionar no fim:

```python
from datetime import date as _Date
from datetime import datetime as _Dt


class MeOut(BaseModel):
    id: str
    nome: str
    cpf_last4: str
    telefone: str
    email: str | None = None
    biometric_enabled: bool
    plano_nome: str | None = None  # resumo — detalhe via /plano
    status_conexao: str | None = None  # "online" | "offline" | None


class EnderecoOut(BaseModel):
    logradouro: str = ""
    numero: str = ""
    bairro: str = ""
    cidade: str = ""
    uf: str = ""
    cep: str = ""


class ContratoOut(BaseModel):
    id: str
    plano: str
    status: str
    cidade: str = ""
    endereco: EnderecoOut = EnderecoOut()


class PlanoOut(BaseModel):
    nome_titular: str
    contratos: list[ContratoOut]
    endereco_principal: EnderecoOut


class AvisoOut(BaseModel):
    id: str
    titulo: str
    corpo: str
    severidade: str  # info|warning|danger
    publicado_em: _Dt


class AvisosOut(BaseModel):
    items: list[AvisoOut]


class UpdateMeIn(BaseModel):
    telefone: str | None = None
    email: str | None = None

    @field_validator("telefone")
    @classmethod
    def _check_tel(cls, v: str | None) -> str | None:
        if v is None:
            return None
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) < 10 or len(digits) > 13:
            raise ValueError("telefone invalido")
        return digits


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
```

- [ ] Commit:
```bash
git add apps/api/src/ondeline_api/api/schemas/cliente_app_auth.py
git commit -m "feat(cliente-app): schemas MeOut/PlanoOut/AvisoOut/UpdateMeIn/ChangePasswordIn"
```

---

## Task 2: Router `/cliente-app/me` + `/plano` + `/avisos`

**File:** `apps/api/src/ondeline_api/api/v1/cliente_app_me.py`

```python
"""Router /api/v1/cliente-app/* — endpoints de me, plano e avisos.

Todos exigem token cliente (kind=cliente). Reaproveita SgpCacheService
ja existente do dashboard.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.sgp.base import ClienteSgp
from ondeline_api.api.schemas.cliente_app_auth import (
    AvisoOut,
    AvisosOut,
    ChangePasswordIn,
    ContratoOut,
    EnderecoOut,
    MeOut,
    PlanoOut,
    UpdateMeIn,
)
from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.auth.passwords import hash_password, verify_password
from ondeline_api.db.crypto import decrypt_pii, encrypt_pii
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.deps import get_db

router = APIRouter(prefix="/api/v1/cliente-app", tags=["cliente-app:me"])


async def _sgp_cliente(session: AsyncSession, cpf_encrypted: str) -> ClienteSgp | None:
    """Reaproveita _sgp_lookup_by_cpf do router de auth pra nao duplicar."""
    from ondeline_api.api.v1.cliente_app_auth import _sgp_lookup_by_cpf

    cpf = decrypt_pii(cpf_encrypted)
    return await _sgp_lookup_by_cpf(session, cpf)


@router.get("/me", response_model=MeOut)
async def me(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> MeOut:
    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    plano_nome = None
    if sgp and sgp.contratos:
        plano_nome = sgp.contratos[0].plano

    return MeOut(
        id=str(user.id),
        nome=decrypt_pii(user.nome_encrypted),
        cpf_last4=user.cpf_last4,
        telefone=decrypt_pii(user.telefone_encrypted),
        email=decrypt_pii(user.email_encrypted) if user.email_encrypted else None,
        biometric_enabled=user.biometric_enabled,
        plano_nome=plano_nome,
        status_conexao=None,  # Fase futura
    )


def _endereco_out(e: object) -> EnderecoOut:
    return EnderecoOut(
        logradouro=getattr(e, "logradouro", "") or "",
        numero=getattr(e, "numero", "") or "",
        bairro=getattr(e, "bairro", "") or "",
        cidade=getattr(e, "cidade", "") or "",
        uf=getattr(e, "uf", "") or "",
        cep=getattr(e, "cep", "") or "",
    )


@router.get("/plano", response_model=PlanoOut)
async def plano(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PlanoOut:
    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    if sgp is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado no SGP")

    contratos = [
        ContratoOut(
            id=c.id,
            plano=c.plano,
            status=c.status,
            cidade=c.cidade,
            endereco=_endereco_out(c.endereco),
        )
        for c in sgp.contratos
    ]
    return PlanoOut(
        nome_titular=sgp.nome,
        contratos=contratos,
        endereco_principal=_endereco_out(sgp.endereco),
    )


@router.get("/avisos", response_model=AvisosOut)
async def avisos(
    _user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
) -> AvisosOut:
    # Fase 7 adiciona tabela + admin posting. Por ora vazio.
    return AvisosOut(items=[])


@router.patch("/me", response_model=MeOut)
async def update_me(
    body: UpdateMeIn,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> MeOut:
    if body.telefone is not None:
        user.telefone_encrypted = encrypt_pii(body.telefone)
    if body.email is not None:
        user.email_encrypted = encrypt_pii(body.email) if body.email else None
    await session.flush()
    await session.commit()
    return await me(user=user, session=session)  # type: ignore[arg-type]


@router.post("/me/password", status_code=204)
async def change_password(
    body: ChangePasswordIn,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    if user.password_hash is None or not verify_password(
        body.current_password, user.password_hash
    ):
        raise HTTPException(status_code=401, detail="senha atual incorreta")
    user.password_hash = hash_password(body.new_password)
    await session.flush()
    await session.commit()
```

- [ ] Commit:
```bash
git add apps/api/src/ondeline_api/api/v1/cliente_app_me.py
git commit -m "feat(cliente-app): endpoints /me, /plano, /avisos, PATCH /me, POST /me/password"
```

---

## Task 3: Wire router no main.py

**File:** `apps/api/src/ondeline_api/main.py`

- [ ] Adicionar import junto com `cliente_app_auth`:
```python
from ondeline_api.api.v1 import cliente_app_me as v1_cliente_app_me
```

- [ ] Adicionar include depois do `cliente_app_auth.router`:
```python
app.include_router(v1_cliente_app_me.router)
```

- [ ] Commit:
```bash
git add apps/api/src/ondeline_api/main.py
git commit -m "feat(cliente-app): registra router /me/plano/avisos no main"
```

---

## Task 4: Teste E2E backend

**File:** `apps/api/tests/test_cliente_app_me.py`

```python
"""E2E /cliente-app/me + plano + avisos + PATCH/me + change-password."""
from __future__ import annotations

import collections.abc
import os
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
    SgpProviderEnum,
)
from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.auth.passwords import hash_password
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.deps import get_db
from ondeline_api.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession


TEST_CPF = "11144477735"


@pytest_asyncio.fixture
async def existing_cliente(db_session: AsyncSession) -> ClienteAppUser:
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


@pytest.fixture
def fake_sgp() -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="12345",
        nome="Cliente Teste",
        cpf_cnpj=TEST_CPF,
        whatsapp="92981234567",
        contratos=[
            Contrato(id="c1", plano="Fibra 600", status="ativo", cidade="Manaus"),
        ],
        endereco=EnderecoSgp(cidade="Manaus", uf="AM"),
    )


@pytest.fixture
def app(
    db_session: AsyncSession,
    fake_sgp: ClienteSgp,
    monkeypatch: pytest.MonkeyPatch,
) -> FastAPI:
    async def _fake_lookup(_s, _cpf):
        return fake_sgp

    monkeypatch.setattr(
        "ondeline_api.api.v1.cliente_app_auth._sgp_lookup_by_cpf", _fake_lookup
    )

    app = create_app()

    async def _override_db() -> collections.abc.AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> collections.abc.AsyncIterator[Any]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _auth(user: ClienteAppUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {jwt_mod.encode_cliente_access_token(user.id)}"}


@pytest.mark.asyncio
async def test_me_returns_data(client, existing_cliente: ClienteAppUser) -> None:
    r = await client.get("/api/v1/cliente-app/me", headers=_auth(existing_cliente))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["cpf_last4"] == TEST_CPF[-4:]
    assert data["nome"] == "Cliente Teste"
    assert data["plano_nome"] == "Fibra 600"


@pytest.mark.asyncio
async def test_plano_returns_contratos(client, existing_cliente: ClienteAppUser) -> None:
    r = await client.get("/api/v1/cliente-app/plano", headers=_auth(existing_cliente))
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["contratos"]) == 1
    assert data["contratos"][0]["plano"] == "Fibra 600"


@pytest.mark.asyncio
async def test_avisos_empty(client, existing_cliente: ClienteAppUser) -> None:
    r = await client.get("/api/v1/cliente-app/avisos", headers=_auth(existing_cliente))
    assert r.status_code == 200
    assert r.json() == {"items": []}


@pytest.mark.asyncio
async def test_patch_me_updates_phone(client, existing_cliente: ClienteAppUser) -> None:
    r = await client.patch(
        "/api/v1/cliente-app/me",
        headers=_auth(existing_cliente),
        json={"telefone": "92987654321"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["telefone"] == "92987654321"


@pytest.mark.asyncio
async def test_change_password_requires_current(
    client, existing_cliente: ClienteAppUser
) -> None:
    r = await client.post(
        "/api/v1/cliente-app/me/password",
        headers=_auth(existing_cliente),
        json={"current_password": "errada1234", "new_password": "NovaSenha456!"},
    )
    assert r.status_code == 401

    r = await client.post(
        "/api/v1/cliente-app/me/password",
        headers=_auth(existing_cliente),
        json={"current_password": "SenhaForte123!", "new_password": "NovaSenha456!"},
    )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_me_rejects_staff_token(client) -> None:
    from uuid import uuid4

    staff_token = jwt_mod.encode_access_token(uuid4(), role="admin")
    r = await client.get(
        "/api/v1/cliente-app/me",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 401
```

- [ ] Commit:
```bash
git add apps/api/tests/test_cliente_app_me.py
git commit -m "test(cliente-app): E2E /me + /plano + /avisos + patch + change-password"
```

---

## Task 5: Flutter — pubspec + DTOs

**Files:**
- Modify: `apps/cliente-mobile/pubspec.yaml` (adicionar shared_preferences)
- Create: `apps/cliente-mobile/lib/core/api/dto.dart`

- [ ] Adicionar em deps do pubspec:
```yaml
  shared_preferences: ^2.3.3
```

- [ ] `dto.dart`:
```dart
class MeDto {
  MeDto({
    required this.id,
    required this.nome,
    required this.cpfLast4,
    required this.telefone,
    this.email,
    required this.biometricEnabled,
    this.planoNome,
    this.statusConexao,
  });

  factory MeDto.fromJson(Map<String, dynamic> j) => MeDto(
        id: j['id'] as String,
        nome: j['nome'] as String,
        cpfLast4: j['cpf_last4'] as String,
        telefone: j['telefone'] as String,
        email: j['email'] as String?,
        biometricEnabled: j['biometric_enabled'] as bool,
        planoNome: j['plano_nome'] as String?,
        statusConexao: j['status_conexao'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'nome': nome,
        'cpf_last4': cpfLast4,
        'telefone': telefone,
        'email': email,
        'biometric_enabled': biometricEnabled,
        'plano_nome': planoNome,
        'status_conexao': statusConexao,
      };

  final String id;
  final String nome;
  final String cpfLast4;
  final String telefone;
  final String? email;
  final bool biometricEnabled;
  final String? planoNome;
  final String? statusConexao;
}

class EnderecoDto {
  EnderecoDto({
    this.logradouro = '',
    this.numero = '',
    this.bairro = '',
    this.cidade = '',
    this.uf = '',
    this.cep = '',
  });
  factory EnderecoDto.fromJson(Map<String, dynamic> j) => EnderecoDto(
        logradouro: (j['logradouro'] ?? '') as String,
        numero: (j['numero'] ?? '') as String,
        bairro: (j['bairro'] ?? '') as String,
        cidade: (j['cidade'] ?? '') as String,
        uf: (j['uf'] ?? '') as String,
        cep: (j['cep'] ?? '') as String,
      );
  Map<String, dynamic> toJson() => {
        'logradouro': logradouro,
        'numero': numero,
        'bairro': bairro,
        'cidade': cidade,
        'uf': uf,
        'cep': cep,
      };

  final String logradouro;
  final String numero;
  final String bairro;
  final String cidade;
  final String uf;
  final String cep;

  String get linhaUnica {
    final partes = [
      if (logradouro.isNotEmpty) logradouro,
      if (numero.isNotEmpty) numero,
      if (bairro.isNotEmpty) bairro,
      if (cidade.isNotEmpty) cidade,
      if (uf.isNotEmpty) uf,
    ];
    return partes.join(', ');
  }
}

class ContratoDto {
  ContratoDto({
    required this.id,
    required this.plano,
    required this.status,
    this.cidade = '',
    required this.endereco,
  });
  factory ContratoDto.fromJson(Map<String, dynamic> j) => ContratoDto(
        id: j['id'] as String,
        plano: j['plano'] as String,
        status: j['status'] as String,
        cidade: (j['cidade'] ?? '') as String,
        endereco: EnderecoDto.fromJson(j['endereco'] as Map<String, dynamic>),
      );
  Map<String, dynamic> toJson() => {
        'id': id,
        'plano': plano,
        'status': status,
        'cidade': cidade,
        'endereco': endereco.toJson(),
      };

  final String id;
  final String plano;
  final String status;
  final String cidade;
  final EnderecoDto endereco;
}

class PlanoDto {
  PlanoDto({
    required this.nomeTitular,
    required this.contratos,
    required this.enderecoPrincipal,
  });
  factory PlanoDto.fromJson(Map<String, dynamic> j) => PlanoDto(
        nomeTitular: j['nome_titular'] as String,
        contratos: ((j['contratos'] as List?) ?? const [])
            .map((c) => ContratoDto.fromJson(c as Map<String, dynamic>))
            .toList(),
        enderecoPrincipal: EnderecoDto.fromJson(
            j['endereco_principal'] as Map<String, dynamic>),
      );
  Map<String, dynamic> toJson() => {
        'nome_titular': nomeTitular,
        'contratos': contratos.map((c) => c.toJson()).toList(),
        'endereco_principal': enderecoPrincipal.toJson(),
      };

  final String nomeTitular;
  final List<ContratoDto> contratos;
  final EnderecoDto enderecoPrincipal;
}

class AvisoDto {
  AvisoDto({
    required this.id,
    required this.titulo,
    required this.corpo,
    required this.severidade,
    required this.publicadoEm,
  });
  factory AvisoDto.fromJson(Map<String, dynamic> j) => AvisoDto(
        id: j['id'] as String,
        titulo: j['titulo'] as String,
        corpo: j['corpo'] as String,
        severidade: j['severidade'] as String,
        publicadoEm: DateTime.parse(j['publicado_em'] as String),
      );
  final String id;
  final String titulo;
  final String corpo;
  final String severidade;
  final DateTime publicadoEm;
}
```

- [ ] Commit:
```bash
git add apps/cliente-mobile/pubspec.yaml apps/cliente-mobile/lib/core/api/dto.dart
git commit -m "feat(cliente-app): dto Me/Plano/Endereco/Contrato/Aviso + shared_preferences"
```

---

## Task 6: Flutter — me_repository + last_known_cache + theme controller

**Files:**
- Create: `apps/cliente-mobile/lib/core/api/me_repository.dart`
- Create: `apps/cliente-mobile/lib/core/cache/last_known_cache.dart`
- Create: `apps/cliente-mobile/lib/core/theme/theme_mode_controller.dart`

- [ ] `me_repository.dart`:
```dart
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'dto.dart';

class MeRepository {
  MeRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app';

  Future<MeDto> getMe() async {
    final r = await _dio.get('$_base/me');
    return MeDto.fromJson(r.data as Map<String, dynamic>);
  }

  Future<PlanoDto> getPlano() async {
    final r = await _dio.get('$_base/plano');
    return PlanoDto.fromJson(r.data as Map<String, dynamic>);
  }

  Future<List<AvisoDto>> getAvisos() async {
    final r = await _dio.get('$_base/avisos');
    final items = ((r.data as Map)['items'] as List? ?? const [])
        .map((j) => AvisoDto.fromJson(j as Map<String, dynamic>))
        .toList();
    return items;
  }

  Future<MeDto> patchMe({String? telefone, String? email}) async {
    final body = <String, dynamic>{};
    if (telefone != null) body['telefone'] = telefone;
    if (email != null) body['email'] = email;
    final r = await _dio.patch('$_base/me', data: body);
    return MeDto.fromJson(r.data as Map<String, dynamic>);
  }

  Future<bool> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    try {
      await _dio.post('$_base/me/password', data: {
        'current_password': currentPassword,
        'new_password': newPassword,
      });
      return true;
    } on DioException {
      return false;
    }
  }
}

final meRepositoryProvider = Provider<MeRepository>(
  (ref) => MeRepository(ref.watch(apiClientProvider)),
);

final meProvider = FutureProvider<MeDto>(
  (ref) => ref.watch(meRepositoryProvider).getMe(),
);

final planoProvider = FutureProvider<PlanoDto>(
  (ref) => ref.watch(meRepositoryProvider).getPlano(),
);

final avisosProvider = FutureProvider<List<AvisoDto>>(
  (ref) => ref.watch(meRepositoryProvider).getAvisos(),
);
```

- [ ] `last_known_cache.dart`:
```dart
import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../api/dto.dart';

class LastKnownCache {
  static const _kMe = 'last_me_json';
  static const _kPlano = 'last_plano_json';

  Future<void> writeMe(MeDto me) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_kMe, jsonEncode(me.toJson()));
  }

  Future<MeDto?> readMe() async {
    final p = await SharedPreferences.getInstance();
    final s = p.getString(_kMe);
    if (s == null) return null;
    return MeDto.fromJson(jsonDecode(s) as Map<String, dynamic>);
  }

  Future<void> writePlano(PlanoDto plano) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_kPlano, jsonEncode(plano.toJson()));
  }

  Future<PlanoDto?> readPlano() async {
    final p = await SharedPreferences.getInstance();
    final s = p.getString(_kPlano);
    if (s == null) return null;
    return PlanoDto.fromJson(jsonDecode(s) as Map<String, dynamic>);
  }

  Future<void> clear() async {
    final p = await SharedPreferences.getInstance();
    await p.remove(_kMe);
    await p.remove(_kPlano);
  }
}
```

- [ ] `theme_mode_controller.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ThemeModeNotifier extends StateNotifier<ThemeMode> {
  ThemeModeNotifier() : super(ThemeMode.system) {
    _load();
  }
  static const _key = 'theme_mode';

  Future<void> _load() async {
    final p = await SharedPreferences.getInstance();
    final v = p.getString(_key);
    state = switch (v) {
      'light' => ThemeMode.light,
      'dark' => ThemeMode.dark,
      _ => ThemeMode.system,
    };
  }

  Future<void> set(ThemeMode m) async {
    state = m;
    final p = await SharedPreferences.getInstance();
    await p.setString(_key, m.name);
  }
}

final themeModeProvider =
    StateNotifierProvider<ThemeModeNotifier, ThemeMode>((ref) => ThemeModeNotifier());
```

- [ ] Commit:
```bash
git add apps/cliente-mobile/lib/core/api/me_repository.dart apps/cliente-mobile/lib/core/cache/ apps/cliente-mobile/lib/core/theme/
git commit -m "feat(cliente-app): me_repository + last_known_cache + theme_mode_controller"
```

---

## Task 7: MainShell com NavigationBar + stubs

**Files:**
- Create: `apps/cliente-mobile/lib/features/shell/main_shell.dart`
- Create: `apps/cliente-mobile/lib/features/faturas/faturas_stub_screen.dart`
- Create: `apps/cliente-mobile/lib/features/suporte/suporte_stub_screen.dart`

- [ ] `main_shell.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/branding/brand_tokens.dart';
import '../faturas/faturas_stub_screen.dart';
import '../home/home_screen.dart';
import '../perfil/perfil_screen.dart';
import '../suporte/suporte_stub_screen.dart';

class MainShell extends ConsumerStatefulWidget {
  const MainShell({super.key});

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell> {
  int _index = 0;

  static const _tabs = [
    HomeScreen(),
    FaturasStubScreen(),
    SuporteStubScreen(),
    PerfilScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _index, children: _tabs),
      bottomNavigationBar: NavigationBarTheme(
        data: NavigationBarThemeData(
          indicatorColor: BrandTokens.primary.withOpacity(0.10),
          labelTextStyle: WidgetStatePropertyAll(
            Theme.of(context).textTheme.labelSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
        ),
        child: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (i) => setState(() => _index = i),
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home_rounded),
              label: 'Inicio',
            ),
            NavigationDestination(
              icon: Icon(Icons.receipt_long_outlined),
              selectedIcon: Icon(Icons.receipt_long),
              label: 'Faturas',
            ),
            NavigationDestination(
              icon: Icon(Icons.support_agent_outlined),
              selectedIcon: Icon(Icons.support_agent),
              label: 'Suporte',
            ),
            NavigationDestination(
              icon: Icon(Icons.person_outline),
              selectedIcon: Icon(Icons.person),
              label: 'Perfil',
            ),
          ],
        ),
      ),
    );
  }
}
```

- [ ] `faturas_stub_screen.dart`:
```dart
import 'package:flutter/material.dart';

import '../../core/branding/brand_tokens.dart';

class FaturasStubScreen extends StatelessWidget {
  const FaturasStubScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Faturas')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceXl),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.receipt_long_outlined,
                  size: 64, color: BrandTokens.textSecondary),
              const SizedBox(height: BrandTokens.spaceMd),
              Text(
                'Em breve',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                'Suas faturas, codigo PIX e boleto PDF chegam aqui na proxima atualizacao.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: BrandTokens.textSecondary,
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] `suporte_stub_screen.dart`: copia exata do faturas, troca ícone pra `Icons.support_agent_outlined` e título pra "Suporte".

- [ ] Commit:
```bash
git add apps/cliente-mobile/lib/features/shell/ apps/cliente-mobile/lib/features/faturas/ apps/cliente-mobile/lib/features/suporte/
git commit -m "feat(cliente-app): MainShell com NavigationBar + stubs Faturas/Suporte"
```

---

## Task 8: Home screen real

**Files:**
- Create: `apps/cliente-mobile/lib/features/home/home_screen.dart`
- Create: `apps/cliente-mobile/lib/features/home/widgets/hero_card.dart`
- Create: `apps/cliente-mobile/lib/features/home/widgets/quick_actions.dart`
- Create: `apps/cliente-mobile/lib/features/home/widgets/avisos_list.dart`
- Delete: `apps/cliente-mobile/lib/features/home/home_placeholder_screen.dart` (substituido)

- [ ] `hero_card.dart`:
```dart
import 'package:flutter/material.dart';

import '../../../core/api/dto.dart';
import '../../../core/branding/brand_tokens.dart';

class HeroCard extends StatelessWidget {
  const HeroCard({super.key, required this.me});
  final MeDto me;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [BrandTokens.primary, BrandTokens.primaryDark],
        ),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        boxShadow: BrandTokens.shadowSoft,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            _saudacao(),
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: BrandTokens.spaceXs),
          Text(
            _primeiroNome(me.nome),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 24,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: BrandTokens.spaceLg),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: BrandTokens.spaceMd,
              vertical: BrandTokens.spaceSm,
            ),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.12),
              borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
            ),
            child: Row(
              children: [
                const Icon(Icons.wifi, color: Colors.white, size: 18),
                const SizedBox(width: BrandTokens.spaceSm),
                Expanded(
                  child: Text(
                    me.planoNome ?? 'Sem plano vinculado',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w600,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _saudacao() {
    final h = DateTime.now().hour;
    if (h < 12) return 'Bom dia,';
    if (h < 18) return 'Boa tarde,';
    return 'Boa noite,';
  }

  String _primeiroNome(String full) {
    final t = full.trim();
    if (t.isEmpty) return 'Cliente';
    return t.split(' ').first;
  }
}
```

- [ ] `quick_actions.dart`:
```dart
import 'package:flutter/material.dart';

import '../../../core/branding/brand_tokens.dart';

class QuickAction {
  const QuickAction({
    required this.icon,
    required this.label,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final VoidCallback onTap;
}

class QuickActions extends StatelessWidget {
  const QuickActions({super.key, required this.actions});
  final List<QuickAction> actions;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 110,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: actions.length,
        separatorBuilder: (_, __) => const SizedBox(width: BrandTokens.spaceMd),
        itemBuilder: (_, i) {
          final a = actions[i];
          return GestureDetector(
            onTap: a.onTap,
            child: Container(
              width: 100,
              padding: const EdgeInsets.all(BrandTokens.spaceMd),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surface,
                borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
                boxShadow: BrandTokens.shadowCard,
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(a.icon, color: BrandTokens.primary, size: 28),
                  const SizedBox(height: BrandTokens.spaceSm),
                  Text(
                    a.label,
                    textAlign: TextAlign.center,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
```

- [ ] `avisos_list.dart`:
```dart
import 'package:flutter/material.dart';

import '../../../core/api/dto.dart';
import '../../../core/branding/brand_tokens.dart';

class AvisosList extends StatelessWidget {
  const AvisosList({super.key, required this.avisos});
  final List<AvisoDto> avisos;

  @override
  Widget build(BuildContext context) {
    if (avisos.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Avisos',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w800,
              ),
        ),
        const SizedBox(height: BrandTokens.spaceSm),
        ...avisos.map(_card),
      ],
    );
  }

  Widget _card(AvisoDto a) {
    return Builder(
      builder: (ctx) {
        final color = switch (a.severidade) {
          'danger' => BrandTokens.danger,
          'warning' => BrandTokens.warning,
          _ => BrandTokens.info,
        };
        return Container(
          margin: const EdgeInsets.only(bottom: BrandTokens.spaceSm),
          padding: const EdgeInsets.all(BrandTokens.spaceMd),
          decoration: BoxDecoration(
            color: color.withOpacity(0.08),
            borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
            border: Border.all(color: color.withOpacity(0.25)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                a.titulo,
                style: TextStyle(fontWeight: FontWeight.w700, color: color),
              ),
              const SizedBox(height: BrandTokens.spaceXs),
              Text(a.corpo),
            ],
          ),
        );
      },
    );
  }
}
```

- [ ] `home_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/dto.dart';
import '../../core/api/me_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/cache/last_known_cache.dart';
import 'widgets/avisos_list.dart';
import 'widgets/hero_card.dart';
import 'widgets/quick_actions.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final meAsync = ref.watch(meProvider);
    final avisosAsync = ref.watch(avisosProvider);

    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(meProvider);
            ref.invalidate(avisosProvider);
            await ref.read(meProvider.future);
          },
          child: ListView(
            padding: const EdgeInsets.all(BrandTokens.spaceLg),
            children: [
              meAsync.when(
                data: (me) {
                  _persistMe(me);
                  return HeroCard(me: me);
                },
                loading: () => const _HeroSkeleton(),
                error: (_, __) => _CachedHeroOrError(ref),
              ),
              const SizedBox(height: BrandTokens.spaceLg),
              QuickActions(
                actions: [
                  QuickAction(
                    icon: Icons.receipt_long_outlined,
                    label: '2a via',
                    onTap: () => _todo(context, 'Faturas chega na Fase 4'),
                  ),
                  QuickAction(
                    icon: Icons.support_agent_outlined,
                    label: 'Falar conosco',
                    onTap: () => _todo(context, 'Chat chega na Fase 6'),
                  ),
                  QuickAction(
                    icon: Icons.wifi_off_outlined,
                    label: 'Sem internet',
                    onTap: () => _todo(context, 'Abrir OS chega na Fase 5'),
                  ),
                  QuickAction(
                    icon: Icons.swap_horiz,
                    label: 'Mudar plano',
                    onTap: () => _todo(context, 'Abrir OS chega na Fase 5'),
                  ),
                ],
              ),
              const SizedBox(height: BrandTokens.spaceLg),
              avisosAsync.when(
                data: (a) => AvisosList(avisos: a),
                loading: () => const SizedBox.shrink(),
                error: (_, __) => const SizedBox.shrink(),
              ),
              const SizedBox(height: BrandTokens.spaceXl),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _persistMe(MeDto me) async {
    await LastKnownCache().writeMe(me);
  }

  void _todo(BuildContext ctx, String s) =>
      ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text(s)));
}

class _HeroSkeleton extends StatelessWidget {
  const _HeroSkeleton();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 160,
      decoration: BoxDecoration(
        color: BrandTokens.primary.withOpacity(0.08),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
      ),
      child: const Center(child: CircularProgressIndicator()),
    );
  }
}

class _CachedHeroOrError extends StatelessWidget {
  const _CachedHeroOrError(this.ref);
  final WidgetRef ref;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<MeDto?>(
      future: LastKnownCache().readMe(),
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const _HeroSkeleton();
        }
        final me = snap.data;
        if (me != null) return HeroCard(me: me);
        return Container(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          decoration: BoxDecoration(
            color: BrandTokens.danger.withOpacity(0.08),
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
          ),
          child: Column(
            children: [
              const Icon(Icons.error_outline, color: BrandTokens.danger),
              const SizedBox(height: BrandTokens.spaceSm),
              const Text('Nao conseguimos carregar seus dados.'),
              TextButton(
                onPressed: () => ref.invalidate(meProvider),
                child: const Text('Tentar de novo'),
              ),
            ],
          ),
        );
      },
    );
  }
}
```

- [ ] Delete `home_placeholder_screen.dart`:
```bash
git rm apps/cliente-mobile/lib/features/home/home_placeholder_screen.dart
```

- [ ] Commit:
```bash
git add apps/cliente-mobile/lib/features/home/
git commit -m "feat(cliente-app): home real com hero card + quick actions + avisos + cache last-known"
```

---

## Task 9: Perfil + editar + mudar senha

**Files:**
- Create: `apps/cliente-mobile/lib/features/perfil/perfil_screen.dart`
- Create: `apps/cliente-mobile/lib/features/perfil/editar_perfil_screen.dart`
- Create: `apps/cliente-mobile/lib/features/perfil/mudar_senha_screen.dart`

- [ ] `perfil_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/me_repository.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/theme/theme_mode_controller.dart';

class PerfilScreen extends ConsumerWidget {
  const PerfilScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final meAsync = ref.watch(meProvider);
    final themeMode = ref.watch(themeModeProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Perfil')),
      body: meAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Center(child: Text('Erro carregando perfil')),
        data: (me) => ListView(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          children: [
            _Avatar(nome: me.nome),
            const SizedBox(height: BrandTokens.spaceMd),
            Text(
              me.nome.isEmpty ? 'Cliente' : me.nome,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            Text(
              'CPF ***.***.***-${me.cpfLast4}',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: BrandTokens.textSecondary,
                  ),
            ),
            const SizedBox(height: BrandTokens.spaceXl),
            _Section(title: 'Dados de contato', children: [
              _Tile(
                icon: Icons.phone_outlined,
                label: 'Telefone',
                value: me.telefone,
                onTap: () => context.push('/perfil/editar', extra: {
                  'campo': 'telefone',
                  'valor': me.telefone,
                }),
              ),
              _Tile(
                icon: Icons.mail_outline,
                label: 'Email',
                value: me.email ?? 'Nao informado',
                onTap: () => context.push('/perfil/editar', extra: {
                  'campo': 'email',
                  'valor': me.email ?? '',
                }),
              ),
            ]),
            _Section(title: 'Seguranca', children: [
              _Tile(
                icon: Icons.lock_outline,
                label: 'Mudar senha',
                onTap: () => context.push('/perfil/mudar-senha'),
              ),
            ]),
            _Section(title: 'Aparencia', children: [
              ListTile(
                leading: const Icon(Icons.brightness_6_outlined),
                title: const Text('Tema'),
                trailing: DropdownButton<ThemeMode>(
                  value: themeMode,
                  underline: const SizedBox.shrink(),
                  onChanged: (m) {
                    if (m != null) {
                      ref.read(themeModeProvider.notifier).set(m);
                    }
                  },
                  items: const [
                    DropdownMenuItem(
                        value: ThemeMode.system, child: Text('Automatico')),
                    DropdownMenuItem(
                        value: ThemeMode.light, child: Text('Claro')),
                    DropdownMenuItem(
                        value: ThemeMode.dark, child: Text('Escuro')),
                  ],
                ),
              ),
            ]),
            const SizedBox(height: BrandTokens.spaceLg),
            OutlinedButton.icon(
              icon: const Icon(Icons.logout),
              label: const Text('Sair'),
              onPressed: () async {
                await ref.read(authRepositoryProvider).logout();
                ref.read(authRefreshProvider).bump();
                if (context.mounted) context.go('/onboarding/cpf');
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _Avatar extends StatelessWidget {
  const _Avatar({required this.nome});
  final String nome;

  @override
  Widget build(BuildContext context) {
    final initials = _initials(nome);
    return Center(
      child: Container(
        width: 96,
        height: 96,
        decoration: BoxDecoration(
          color: BrandTokens.primary.withOpacity(0.10),
          borderRadius: BorderRadius.circular(BrandTokens.radiusXl),
        ),
        alignment: Alignment.center,
        child: Text(
          initials,
          style: const TextStyle(
            fontSize: 32,
            fontWeight: FontWeight.w800,
            color: BrandTokens.primary,
          ),
        ),
      ),
    );
  }

  String _initials(String full) {
    final parts = full.trim().split(' ').where((s) => s.isNotEmpty).toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) return parts.first[0].toUpperCase();
    return (parts.first[0] + parts.last[0]).toUpperCase();
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.children});
  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(
            top: BrandTokens.spaceLg,
            bottom: BrandTokens.spaceSm,
          ),
          child: Text(
            title,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: BrandTokens.textSecondary,
                  fontWeight: FontWeight.w700,
                ),
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          ),
          child: Column(children: children),
        ),
      ],
    );
  }
}

class _Tile extends StatelessWidget {
  const _Tile({
    required this.icon,
    required this.label,
    this.value,
    this.onTap,
  });
  final IconData icon;
  final String label;
  final String? value;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon),
      title: Text(label),
      subtitle: value == null ? null : Text(value!),
      trailing: const Icon(Icons.chevron_right),
      onTap: onTap,
    );
  }
}
```

- [ ] `editar_perfil_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/me_repository.dart';
import '../../core/branding/brand_tokens.dart';

class EditarPerfilScreen extends ConsumerStatefulWidget {
  const EditarPerfilScreen({super.key, required this.campo, required this.valor});
  final String campo; // 'telefone' | 'email'
  final String valor;

  @override
  ConsumerState<EditarPerfilScreen> createState() => _EditarPerfilScreenState();
}

class _EditarPerfilScreenState extends ConsumerState<EditarPerfilScreen> {
  late final TextEditingController _ctrl;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _ctrl = TextEditingController(text: widget.valor);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _loading = true);
    try {
      final repo = ref.read(meRepositoryProvider);
      if (widget.campo == 'telefone') {
        await repo.patchMe(telefone: _ctrl.text);
      } else {
        await repo.patchMe(email: _ctrl.text);
      }
      ref.invalidate(meProvider);
      if (!mounted) return;
      context.pop();
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Falha ao salvar')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final label = widget.campo == 'telefone' ? 'Telefone' : 'Email';
    final keyboardType =
        widget.campo == 'telefone' ? TextInputType.phone : TextInputType.emailAddress;
    return Scaffold(
      appBar: AppBar(title: Text(label)),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          child: Column(
            children: [
              TextField(
                controller: _ctrl,
                keyboardType: keyboardType,
                autofocus: true,
                decoration: InputDecoration(labelText: label),
              ),
              const Spacer(),
              FilledButton(
                onPressed: _loading ? null : _save,
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Salvar'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] `mudar_senha_screen.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/me_repository.dart';
import '../../core/branding/brand_tokens.dart';

class MudarSenhaScreen extends ConsumerStatefulWidget {
  const MudarSenhaScreen({super.key});

  @override
  ConsumerState<MudarSenhaScreen> createState() => _MudarSenhaScreenState();
}

class _MudarSenhaScreenState extends ConsumerState<MudarSenhaScreen> {
  final _atual = TextEditingController();
  final _nova = TextEditingController();
  final _conf = TextEditingController();
  bool _loading = false;
  bool _hide = true;

  @override
  void dispose() {
    _atual.dispose();
    _nova.dispose();
    _conf.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_nova.text.length < 8) {
      _toast('Senha nova precisa ter ao menos 8 caracteres');
      return;
    }
    if (_nova.text != _conf.text) {
      _toast('Senhas nao conferem');
      return;
    }
    setState(() => _loading = true);
    final ok = await ref.read(meRepositoryProvider).changePassword(
          currentPassword: _atual.text,
          newPassword: _nova.text,
        );
    if (!mounted) return;
    setState(() => _loading = false);
    if (ok) {
      _toast('Senha atualizada');
      context.pop();
    } else {
      _toast('Senha atual incorreta');
    }
  }

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mudar senha')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          child: Column(
            children: [
              TextField(
                controller: _atual,
                obscureText: _hide,
                decoration: InputDecoration(
                  labelText: 'Senha atual',
                  suffixIcon: IconButton(
                    icon: Icon(_hide ? Icons.visibility : Icons.visibility_off),
                    onPressed: () => setState(() => _hide = !_hide),
                  ),
                ),
              ),
              const SizedBox(height: BrandTokens.spaceMd),
              TextField(
                controller: _nova,
                obscureText: _hide,
                decoration: const InputDecoration(labelText: 'Nova senha'),
              ),
              const SizedBox(height: BrandTokens.spaceMd),
              TextField(
                controller: _conf,
                obscureText: _hide,
                decoration: const InputDecoration(labelText: 'Confirme a nova senha'),
              ),
              const Spacer(),
              FilledButton(
                onPressed: _loading ? null : _save,
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Atualizar senha'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] Commit:
```bash
git add apps/cliente-mobile/lib/features/perfil/
git commit -m "feat(cliente-app): tela Perfil + editar tel/email + mudar senha"
```

---

## Task 10: Atualizar router e main para usar MainShell + ThemeMode

**Files:**
- Modify: `apps/cliente-mobile/lib/router.dart`
- Modify: `apps/cliente-mobile/lib/main.dart`

- [ ] `router.dart` — trocar:
```dart
// Remove import:
import 'features/home/home_placeholder_screen.dart';

// Adicione imports:
import 'features/perfil/editar_perfil_screen.dart';
import 'features/perfil/mudar_senha_screen.dart';
import 'features/shell/main_shell.dart';

// Substitua a rota /home pela MainShell + subrotas de perfil:
GoRoute(path: '/home', builder: (_, __) => const MainShell()),
GoRoute(
  path: '/perfil/editar',
  builder: (_, state) {
    final extra = state.extra as Map<String, String>?;
    return EditarPerfilScreen(
      campo: extra?['campo'] ?? 'telefone',
      valor: extra?['valor'] ?? '',
    );
  },
),
GoRoute(
  path: '/perfil/mudar-senha',
  builder: (_, __) => const MudarSenhaScreen(),
),
```

- [ ] `main.dart` — substituir `ClienteApp`:
```dart
class ClienteApp extends ConsumerWidget {
  const ClienteApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    final themeMode = ref.watch(themeModeProvider);
    return MaterialApp.router(
      title: 'Ondeline',
      debugShowCheckedModeBanner: false,
      theme: BrandTheme.light(),
      darkTheme: BrandTheme.dark(),
      themeMode: themeMode,
      routerConfig: router,
    );
  }
}
```

(adicionar import: `import 'core/theme/theme_mode_controller.dart';`)

- [ ] Analyze:
```bash
cd apps/cliente-mobile && flutter pub get && flutter analyze
```

- [ ] Commit:
```bash
git add apps/cliente-mobile/lib/router.dart apps/cliente-mobile/lib/main.dart
git commit -m "feat(cliente-app): wire MainShell + rotas perfil + theme controlado por provider"
```

---

## Pontos de atenção

1. **`_endereco_out` na seção 2:** o `getattr` defensivo é porque `EnderecoSgp` é dataclass frozen — campos podem estar vazios mas não None. Manter assim por segurança.

2. **`async def update_me`:** chama `me()` de volta passando os mesmos kwargs — não é elegante mas funciona. Alternativa: extrair a lógica pra função pura. Mantém como tá pra reduzir surface area.

3. **Imports nos schemas:** o `from datetime import date as _Date, datetime as _Dt` é só pra não conflitar com nada existente no arquivo (não tem, mas defensivo).

4. **`shared_preferences` no iOS:** precisa de `cd ios && pod install` após o `flutter pub get`. Sem isso, app crasha em runtime ao acessar.

5. **Cache last-known:** só Home grava. Perfil sempre vai pra API (não tem fallback). Se quiser fallback no Perfil, mesma técnica.

6. **Rota `/perfil/*` fora do shell:** push em cima da tab Perfil. Botão back volta pro shell — funciona naturalmente.

7. **Theme dropdown:** usa `DropdownButton` direto. Se ficar feio, trocar pra `SegmentedButton` (Material 3) na Fase 7.
