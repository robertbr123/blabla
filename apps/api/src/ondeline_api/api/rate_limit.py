"""Rate limit por CPF nas rotas de /api/v1/cliente-app/auth/*.

Atras do nginx, todo request vem do mesmo IP (bridge Docker) — entao o
limite padrao por IP vira global. A ``cpf_or_ip_key`` extrai o CPF do body
(via middleware) e usa como chave; rotas sem CPF caem em IP automaticamente.

Mitigacao parcial: ataque que pulveriza N CPFs do mesmo IP ainda passa
(cada CPF tem seu balde). Resolver no futuro com limit dupla (CPF + IP global
mais permissivo) ou usando X-Forwarded-For real do header do nginx.
"""
from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from fastapi import Request
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import Message

_AUTH_PREFIX = "/api/v1/cliente-app/auth/"


def cpf_or_ip_key(request: Request) -> str:
    """``key_func`` do slowapi: usa CPF se houver no ``request.state``; senao IP.

    Os endpoints que tem CPF no body sao tagueados pela ``CpfExtractorMiddleware``.
    Endpoints como ``/register/password`` (que nao tem CPF, so setup_token)
    caem no fallback de IP — comportamento aceitavel.
    """
    cpf = getattr(request.state, "cpf", None)
    if isinstance(cpf, str) and cpf:
        return f"cpf:{cpf}"
    return get_remote_address(request)


class CpfExtractorMiddleware(BaseHTTPMiddleware):
    """Le o body uma vez nas rotas de auth, extrai CPF e RE-INJETA o body.

    Sem o replay do body via ``request._receive``, o handler downstream nao
    consegue ler o body de novo (Starlette consume o ASGI ``receive`` uma vez
    so). Esse padrao e o documentado pra inspecionar body em middleware.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not request.url.path.startswith(_AUTH_PREFIX):
            return await call_next(request)

        body = await request.body()
        if body:
            try:
                data = json.loads(body)
                cpf_raw = str(data.get("cpf", "")) if isinstance(data, dict) else ""
                cpf = "".join(c for c in cpf_raw if c.isdigit())
                if len(cpf) == 11:
                    request.state.cpf = cpf
            except (json.JSONDecodeError, ValueError, AttributeError):
                # Body nao e JSON ou nao tem cpf — segue sem tagear
                pass

            # Re-injetar body pra handler conseguir ler. Starlette consome o
            # ASGI receive na primeira leitura; sobrescrever volta o stream.
            async def receive() -> Message:
                return {"type": "http.request", "body": body, "more_body": False}

            request._receive = receive

        return await call_next(request)
