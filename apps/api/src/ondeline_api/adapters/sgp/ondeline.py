"""SgpOndelineProvider — POST /api/ura/clientes/ form-encoded."""
from __future__ import annotations

import re
from typing import Any

import httpx
import structlog

from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
    Fatura,
    SgpProvider,
)
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum

log = structlog.get_logger(__name__)

_DIGITS_RE = re.compile(r"\D+")


def _clean_cpf(cpf: str) -> str:
    return _DIGITS_RE.sub("", cpf or "")


def _build_endereco(raw: dict[str, Any] | None) -> EnderecoSgp:
    raw = raw or {}
    return EnderecoSgp(
        logradouro=raw.get("logradouro", "") or "",
        numero=raw.get("numero", "") or "",
        bairro=raw.get("bairro", "") or "",
        cidade=raw.get("cidade", "") or "",
        uf=raw.get("uf", "") or "",
        cep=raw.get("cep", "") or "",
        complemento=raw.get("complemento", "") or "",
    )


def _build_fatura(raw: dict[str, Any]) -> Fatura:
    return Fatura(
        id=str(raw.get("id", "")),
        valor=float(raw.get("valorCorrigido") or raw.get("valor") or 0),
        vencimento=str(raw.get("dataVencimento") or ""),
        status=str(raw.get("status") or ""),
        link_pdf=raw.get("link") or None,
        codigo_pix=raw.get("codigoPix") or None,
        dias_atraso=int(raw.get("diasAtraso") or 0),
    )


class SgpOndelineProvider(SgpProvider):
    name = SgpProviderEnum.ONDELINE

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        app: str = "mikrotik",
        timeout: float = 20.0,
        verify_ssl: bool = True,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._token = token
        self._app = app
        self._client = httpx.AsyncClient(timeout=timeout, verify=verify_ssl)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def buscar_por_cpf(self, cpf: str) -> ClienteSgp | None:
        clean = _clean_cpf(cpf)
        if not clean:
            return None
        try:
            r = await self._client.post(
                f"{self._base}/api/ura/clientes/",
                data={"token": self._token, "app": self._app, "cpfcnpj": clean},
            )
        except httpx.HTTPError as e:
            log.warning("sgp.ondeline.network_error", error=str(e))
            return None
        if r.status_code != 200:
            log.warning("sgp.ondeline.http_error", status=r.status_code)
            return None
        try:
            data = r.json()
        except Exception:
            log.warning("sgp.ondeline.json_decode_error")
            return None
        clientes = data if isinstance(data, list) else (data.get("clientes") or [])
        if not clientes:
            return None
        # match exato por cpf
        c = next(
            (cl for cl in clientes if _clean_cpf(cl.get("cpfcnpj", "")) == clean),
            clientes[0],
        )
        contratos_raw = c.get("contratos") or []
        contratos: list[Contrato] = []
        for ct in contratos_raw:
            sv = (ct.get("servicos") or [{}])[0]
            plano = ((sv.get("plano") or {}).get("descricao", "")) or ""
            cidade = (
                (sv.get("endereco") or {}).get("cidade")
                or (ct.get("endereco") or {}).get("cidade")
                or ""
            )
            contratos.append(
                Contrato(
                    id=str(ct.get("id", "")),
                    plano=plano,
                    status=str(ct.get("status", "")),
                    motivo_status=str(ct.get("motivo_status", "") or ""),
                    cidade=cidade,
                )
            )
        titulos = [_build_fatura(t) for t in (c.get("titulos") or [])]
        return ClienteSgp(
            provider=self.name,
            sgp_id=str(c.get("id", "")),
            nome=str(c.get("nome", "")),
            cpf_cnpj=clean,
            whatsapp=str(c.get("celular") or c.get("telefone") or ""),
            contratos=contratos,
            endereco=_build_endereco(c.get("endereco")),
            titulos=titulos,
        )

    async def listar_faturas(self, sgp_id: str, *, apenas_abertas: bool = True) -> list[Fatura]:
        # SGP nao tem endpoint dedicado pra listar faturas por id de cliente
        # — o /api/ura/clientes/ ja retorna `titulos`. Para `listar_faturas`
        # usamos o cache do cliente. Esta funcao e chamada pela tool
        # enviar_boleto que ja tem o ClienteSgp em maos via cache; nao
        # deveria ser invocada diretamente.
        raise NotImplementedError("use ClienteSgp.titulos via sgp_cache")
