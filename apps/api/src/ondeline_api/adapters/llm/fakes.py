"""Fake LLM scriptable para testes de loop e tools."""
from __future__ import annotations

from collections.abc import Sequence

from ondeline_api.adapters.llm.base import ChatRequest, ChatResponse, LLMProvider


class FakeLLMProvider(LLMProvider):
    """Devolve `responses[i]` no i-esimo `chat()`. Falha se exaurir."""

    def __init__(self, responses: Sequence[ChatResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[ChatRequest] = []

    async def chat(self, req: ChatRequest) -> ChatResponse:
        self.calls.append(req)
        if not self._responses:
            raise RuntimeError("FakeLLMProvider exhausted")
        return self._responses.pop(0)

    async def aclose(self) -> None:
        return None
