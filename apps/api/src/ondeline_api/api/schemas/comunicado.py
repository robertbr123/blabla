# apps/api/src/ondeline_api/api/schemas/comunicado.py
"""Schemas da API de comunicados/disparo em massa."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class SegmentoFiltros(BaseModel):
    cidade: str | None = None
    status: str | None = None
    plano: str | None = None


class PreviewOut(BaseModel):
    total: int
    amostra: list[dict[str, Any]]


class TemplateVar(BaseModel):
    indice: int
    label: str
    tipo: str


class TemplateButton(BaseModel):
    index: int
    tipo: str
    texto: str
    url_dinamica: bool


class BroadcastTemplateOut(BaseModel):
    id: UUID
    name: str
    language: str
    category: str
    variaveis: list[TemplateVar]
    botoes: list[TemplateButton] = []
    header_tipo: str


class CampanhaCreate(BaseModel):
    titulo: str
    canal_id: UUID
    template_name: str
    template_language: str = "pt_BR"
    body_params: list[str] = []
    header_media_url: str | None = None
    segmentacao: SegmentoFiltros = SegmentoFiltros()
    origem: str = "segmento"
    button_param: str | None = None


class CampanhaListItem(BaseModel):
    id: UUID
    titulo: str
    template_name: str
    status: str
    total_destinatarios: int
    enviadas: int
    falhas: int
    created_at: datetime


class CampanhaDetail(CampanhaListItem):
    canal_id: UUID
    template_language: str
    body_params: list[str]
    header_media_url: str | None
    segmentacao: SegmentoFiltros
    started_at: datetime | None
    finished_at: datetime | None
    # contagem viva por status dos destinatários
    status_counts: dict[str, int]


class TestSendIn(BaseModel):
    whatsapp: str


class SegmentoValores(BaseModel):
    cidades: list[str]
    status: list[str]
    planos: list[str]


class TemplateUpsert(BaseModel):
    name: str
    language: str = "pt_BR"
    category: str = "MARKETING"
    variaveis: list[TemplateVar] = []
    botoes: list[TemplateButton] = []
    header_tipo: str = "none"
    ativo: bool = True


class SyncResult(BaseModel):
    sincronizados: int
    canais: int


class ImportResult(BaseModel):
    importados: int
    invalidos: int
    amostra_invalidos: list[str]
