"""LLMProvider interface — shape OpenAI-compatible.

Tudo que o sistema sabe sobre LLM passa por aqui. Trocar Hermes por outra
coisa = swap de implementacao, sem tocar tools/services.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Role
    content: str | None
    name: str | None = None  # role=tool: nome da tool que respondeu
    tool_call_id: str | None = None  # role=tool: liga a chamada original
    tool_calls: list[ToolCall] | None = None  # role=assistant: tools chamadas


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass(frozen=True, slots=True)
class ChatRequest:
    model: str
    messages: list[ChatMessage]
    tools: list[ToolSpec] = field(default_factory=list)
    temperature: float = 0.4
    max_tokens: int = 800


@dataclass(frozen=True, slots=True)
class ChatResponse:
    content: str | None
    tool_calls: list[ToolCall]
    tokens_used: int
    finish_reason: str  # "stop" | "tool_calls" | "length"


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, req: ChatRequest) -> ChatResponse: ...

    @abstractmethod
    async def aclose(self) -> None: ...
