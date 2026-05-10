"""LLMProvider interface — types e FakeLLMProvider scriptable."""
from __future__ import annotations

import pytest
from ondeline_api.adapters.llm.base import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Role,
    ToolCall,
    ToolSpec,
)
from ondeline_api.adapters.llm.fakes import FakeLLMProvider

pytestmark = pytest.mark.asyncio


def test_chat_message_roles() -> None:
    m = ChatMessage(role=Role.USER, content="oi")
    assert m.role is Role.USER


def test_tool_spec_to_openai_schema() -> None:
    spec = ToolSpec(
        name="my_tool",
        description="faz coisa",
        parameters={
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        },
    )
    s = spec.to_openai_schema()
    assert s == {
        "type": "function",
        "function": {
            "name": "my_tool",
            "description": "faz coisa",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            },
        },
    }


async def test_fake_provider_returns_scripted_response() -> None:
    fake = FakeLLMProvider(
        responses=[
            ChatResponse(
                content="Olá! Pode me passar seu CPF?",
                tool_calls=[],
                tokens_used=42,
                finish_reason="stop",
            )
        ]
    )
    out = await fake.chat(
        ChatRequest(
            model="x",
            messages=[ChatMessage(role=Role.USER, content="oi")],
            tools=[],
        )
    )
    assert out.content == "Olá! Pode me passar seu CPF?"
    assert out.tokens_used == 42


async def test_fake_provider_returns_tool_calls() -> None:
    fake = FakeLLMProvider(
        responses=[
            ChatResponse(
                content=None,
                tool_calls=[
                    ToolCall(id="c1", name="buscar_cliente_sgp", arguments={"cpf_cnpj": "123"})
                ],
                tokens_used=20,
                finish_reason="tool_calls",
            )
        ]
    )
    out = await fake.chat(
        ChatRequest(model="x", messages=[], tools=[])
    )
    assert out.tool_calls and out.tool_calls[0].name == "buscar_cliente_sgp"


async def test_fake_provider_exhausts() -> None:
    fake = FakeLLMProvider(responses=[])
    with pytest.raises(RuntimeError):
        await fake.chat(ChatRequest(model="x", messages=[], tools=[]))
