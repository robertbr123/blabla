"""Pydantic schemas para /cliente-app/auth/*."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


def _cpf_digits(v: str) -> str:
    return "".join(c for c in v if c.isdigit())


def _normalize_cpf(v: str) -> str:
    digits = _cpf_digits(v)
    if len(digits) != 11:
        raise ValueError("cpf invalido")
    return digits


class RegisterStartIn(BaseModel):
    cpf: str

    @field_validator("cpf")
    @classmethod
    def _check_cpf(cls, v: str) -> str:
        return _normalize_cpf(v)


class RegisterStartOut(BaseModel):
    masked_phone: str  # ex: "(92) ****-1234"


class RegisterVerifyIn(BaseModel):
    cpf: str
    code: str = Field(min_length=6, max_length=6)

    @field_validator("cpf")
    @classmethod
    def _check_cpf(cls, v: str) -> str:
        return _normalize_cpf(v)


class RegisterVerifyOut(BaseModel):
    setup_token: str  # JWT curto (10min) que autoriza POST /register/password


class RegisterPasswordIn(BaseModel):
    setup_token: str
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    cpf: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("cpf")
    @classmethod
    def _check_cpf(cls, v: str) -> str:
        return _normalize_cpf(v)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class ForgotIn(BaseModel):
    cpf: str

    @field_validator("cpf")
    @classmethod
    def _check_cpf(cls, v: str) -> str:
        return _normalize_cpf(v)


# ════════ Fase 3: Me, Plano, Avisos ════════


from datetime import datetime as _Dt  # noqa: E402


class MeOut(BaseModel):
    id: str
    nome: str
    cpf_last4: str
    telefone: str
    email: str | None = None
    biometric_enabled: bool
    plano_nome: str | None = None
    status_conexao: str | None = None


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
    severidade: str
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


# ════════ Fase 4: Faturas ════════


class FaturaOut(BaseModel):
    id: str
    valor: float
    vencimento: str
    status: str
    dias_atraso: int = 0
    tem_pdf: bool
    tem_pix: bool


class FaturasOut(BaseModel):
    items: list[FaturaOut]


class PixOut(BaseModel):
    codigo: str


class BoletoUrlOut(BaseModel):
    url: str


# ════════ Fase 5: OS pelo cliente ════════


class OsCreateIn(BaseModel):
    tipo: str  # sem_internet | mudanca_endereco | troca_plano
    descricao: str = Field(min_length=0, max_length=2000)
    payload: dict = Field(default_factory=dict)

    @field_validator("tipo")
    @classmethod
    def _check_tipo(cls, v: str) -> str:
        if v not in {"sem_internet", "mudanca_endereco", "troca_plano"}:
            raise ValueError("tipo invalido")
        return v


class OsOut(BaseModel):
    id: str
    tipo: str
    descricao: str
    status: str
    created_at: str
    updated_at: str


class OsListOut(BaseModel):
    items: list[OsOut]


# ════════ Fase 6: Chat in-app ════════


class ChatMessageOut(BaseModel):
    id: str
    role: str  # "user" | "bot"
    content: str
    created_at: str


class ChatMessagesOut(BaseModel):
    items: list[ChatMessageOut]
    next_cursor: str | None = None  # iso datetime da msg mais antiga retornada


class ChatSendIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class ChatSendOut(BaseModel):
    user_message: ChatMessageOut
    bot_message: ChatMessageOut
