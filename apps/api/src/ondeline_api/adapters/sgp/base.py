"""Interface SGP (Sistema de Gestao de Provedor).

Os dois provedores reais (Ondeline e LinkNetAM) compartilham endpoint
`POST /api/ura/clientes/` com body form `{token, app, cpfcnpj}`. O retorno
e uma lista de clientes; cada cliente tem uma lista de `contratos`. Cada
contrato tem `servicos[0].plano.descricao`, `endereco`, `status`, e o
cliente tem `titulos[]` com faturas (link PDF, codigoPix, valor, vencimento).

Isolamos isso atras de uma interface simples para que tools e cache nao
precisem conhecer o shape cru.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum

# Re-export explícito para mypy --no-implicit-reexport.
# `SgpProvider` (classe abstrata abaixo) é importável diretamente; o enum
# precisa do alias `SgpProviderEnum` listado em `__all__`.
__all__ = [
    "ClienteSgp",
    "EnderecoSgp",
    "SgpProvider",
    "SgpProviderEnum",
]


@dataclass(frozen=True, slots=True)
class EnderecoSgp:
    logradouro: str = ""
    numero: str = ""
    bairro: str = ""
    cidade: str = ""
    uf: str = ""
    cep: str = ""
    complemento: str = ""


@dataclass(frozen=True, slots=True)
class Fatura:
    id: str
    valor: float
    vencimento: str  # YYYY-MM-DD
    status: str  # "aberto" | "pago" | ...
    link_pdf: str | None = None
    codigo_pix: str | None = None
    dias_atraso: int = 0
    # Id do contrato ao qual o titulo pertence. Quando SGP nao expoe a
    # associacao, fica None e o backend trata como "fatura global do CPF".
    contrato_id: str | None = None


@dataclass(frozen=True, slots=True)
class Contrato:
    id: str
    plano: str
    status: str
    motivo_status: str = ""
    cidade: str = ""
    pppoe_login: str = ""
    pppoe_senha: str = ""
    endereco: EnderecoSgp = field(default_factory=EnderecoSgp)


@dataclass(frozen=True, slots=True)
class ClienteSgp:
    provider: SgpProviderEnum
    sgp_id: str
    nome: str
    cpf_cnpj: str  # apenas digitos
    whatsapp: str = ""
    contratos: list[Contrato] = field(default_factory=list)
    endereco: EnderecoSgp = field(default_factory=EnderecoSgp)
    titulos: list[Fatura] = field(default_factory=list)
    # Data de nascimento — None quando o SGP nao expoe ou cliente nao
    # cadastrou. Formato 'YYYY-MM-DD' (normalizado).
    data_nascimento: str | None = None


class SgpProvider(ABC):
    """Implementacao concreta para Ondeline / LinkNetAM. Apenas leitura."""

    name: SgpProviderEnum

    @abstractmethod
    async def buscar_por_cpf(self, cpf: str) -> ClienteSgp | None: ...

    @abstractmethod
    async def listar_faturas(self, sgp_id: str, *, apenas_abertas: bool = True) -> list[Fatura]: ...

    @abstractmethod
    async def aclose(self) -> None: ...
