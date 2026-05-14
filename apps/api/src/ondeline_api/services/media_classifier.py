"""Classificacao deterministica de midia recebida.

Usa MIME type + keywords no caption para categorizar antes de escalar.
Sem LLM — puro match de regras.
"""
from __future__ import annotations

import unicodedata
from enum import StrEnum

from ondeline_api.webhook.parser import InboundKind


class MediaCategory(StrEnum):
    COMPROVANTE = "comprovante"
    FOTO_EQUIPAMENTO = "foto_equipamento"
    DOCUMENTO = "documento"
    AUDIO = "audio"
    OUTRO = "outro"


_KW_COMPROVANTE = {"comprovante", "pix", "pagamento", "paguei", "boleto", "transferencia", "recibo"}
_KW_EQUIPAMENTO = {"roteador", "cabo", "sinal", "equipamento", "poste", "instalacao", "antena", "onu", "foto"}
_KW_DOCUMENTO = {"rg", "cnh", "documento", "identidade", "cpf", "cadastro"}


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def classify_media(kind: InboundKind, caption: str | None) -> MediaCategory:
    """Classifica o tipo de midia com base no InboundKind e caption."""
    if kind is InboundKind.AUDIO:
        return MediaCategory.AUDIO

    if kind not in (InboundKind.IMAGE, InboundKind.DOCUMENT):
        return MediaCategory.OUTRO

    if not caption:
        return MediaCategory.OUTRO

    words = set(_normalize(caption).split())
    if words & _KW_COMPROVANTE:
        return MediaCategory.COMPROVANTE
    if words & _KW_EQUIPAMENTO:
        return MediaCategory.FOTO_EQUIPAMENTO
    if words & _KW_DOCUMENTO:
        return MediaCategory.DOCUMENTO
    return MediaCategory.OUTRO


# Mensagem de ACK por categoria
CATEGORY_ACK: dict[MediaCategory, str] = {
    MediaCategory.COMPROVANTE: (
        "Recebi seu comprovante, obrigado! Estou encaminhando para análise. "
        "Em breve um atendente retornará. 🙏"
    ),
    MediaCategory.FOTO_EQUIPAMENTO: (
        "Recebi a foto! Vou abrir um chamado técnico para verificar. "
        "Em breve entraremos em contato. 🔧"
    ),
    MediaCategory.DOCUMENTO: (
        "Documento recebido! Encaminhando para o setor de cadastro. "
        "Em breve um atendente retornará. 📄"
    ),
    MediaCategory.AUDIO: (
        "Não consigo ouvir áudios por aqui. 😅 "
        "Por favor, escreva sua mensagem em texto que te atendo melhor!"
    ),
    MediaCategory.OUTRO: (
        "Recebi seu arquivo! Encaminhando para um atendente. "
        "Em breve retornaremos. 📎"
    ),
}

# Tags que serão salvas na conversa por categoria
CATEGORY_TAG: dict[MediaCategory, str | None] = {
    MediaCategory.COMPROVANTE: "comprovante",
    MediaCategory.FOTO_EQUIPAMENTO: "tecnico",
    MediaCategory.DOCUMENTO: "documento",
    MediaCategory.AUDIO: None,
    MediaCategory.OUTRO: None,
}

# Categorias que devem escalar para humano (exceto AUDIO)
CATEGORIES_ESCALATE = {
    MediaCategory.COMPROVANTE,
    MediaCategory.FOTO_EQUIPAMENTO,
    MediaCategory.DOCUMENTO,
    MediaCategory.OUTRO,
}
