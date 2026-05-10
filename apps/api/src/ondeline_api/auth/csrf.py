"""Double-submit cookie CSRF middleware.

Para qualquer metodo nao-safe, exige que o header `X-CSRF` tenha o mesmo
valor do cookie `csrf_token`. Bypass para `exempt_paths`.

O cookie `csrf_token` nao e HttpOnly (cliente JS precisa ler para devolver
no header), mas o JWT que importa fica no cookie HttpOnly separado.
"""
from __future__ import annotations

import hmac
from collections.abc import Awaitable, Callable, Sequence

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
COOKIE_NAME = "csrf_token"
HEADER_NAME = "x-csrf"


class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        exempt_paths: Sequence[str] = (),
    ) -> None:
        super().__init__(app)
        self._exempt = tuple(exempt_paths)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method in SAFE_METHODS:
            return await call_next(request)
        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in self._exempt):
            return await call_next(request)

        cookie = request.cookies.get(COOKIE_NAME, "")
        header = request.headers.get(HEADER_NAME, "")
        if not cookie or not header or not hmac.compare_digest(cookie, header):
            return JSONResponse({"detail": "csrf check failed"}, status_code=403)

        return await call_next(request)
