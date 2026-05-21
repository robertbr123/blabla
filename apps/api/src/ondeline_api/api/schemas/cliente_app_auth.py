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
