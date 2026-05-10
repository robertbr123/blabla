"""HermesProvider — POST /v1/chat/completions OpenAI-compatible."""
from __future__ import annotations

from typing import Any

import pytest
import respx
from httpx import Response
from ondeline_api.adapters.llm.base import (
    ChatMessage,
    ChatRequest,
    Role,
    ToolSpec,
)
from ondeline_api.adapters.llm.hermes import HermesProvider

pytestmark = pytest.mark.asyncio

BASE = "http://hermes.test/v1"


def _ok(content: str | None = "Olá!", tool_calls: list[dict[str, Any]] | None = None, finish: str = "stop"):
    msg: dict[str, Any] = {"role": "assistant"}
    if content is not None:
        msg["content"] = content
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return {
        "id": "cmpl-1",
        "model": "Hermes-3",
        "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 30, "total_tokens": 40},
    }


async def test_basic_chat() -> None:
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/chat/completions").respond(200, json=_ok("Bem vindo!"))
        p = HermesProvider(base_url=BASE, model="Hermes-3", api_key="k", timeout=5)
        out = await p.chat(
            ChatRequest(model="Hermes-3", messages=[ChatMessage(role=Role.USER, content="oi")])
        )
        assert out.content == "Bem vindo!"
        assert out.tokens_used == 40
        assert out.finish_reason == "stop"
        await p.aclose()


async def test_tool_calls_parsed() -> None:
    tc = [
        {
            "id": "call_abc",
            "type": "function",
            "function": {
                "name": "buscar_cliente_sgp",
                "arguments": '{"cpf_cnpj": "11122233344"}',
            },
        }
    ]
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/chat/completions").respond(
            200, json=_ok(content=None, tool_calls=tc, finish="tool_calls")
        )
        p = HermesProvider(base_url=BASE, model="Hermes-3", api_key="k", timeout=5)
        out = await p.chat(
            ChatRequest(
                model="Hermes-3",
                messages=[ChatMessage(role=Role.USER, content="meu cpf eh 11122233344")],
                tools=[
                    ToolSpec(
                        name="buscar_cliente_sgp",
                        description="x",
                        parameters={"type": "object"},
                    )
                ],
            )
        )
        assert out.content is None
        assert len(out.tool_calls) == 1
        assert out.tool_calls[0].name == "buscar_cliente_sgp"
        assert out.tool_calls[0].arguments == {"cpf_cnpj": "11122233344"}
        await p.aclose()


async def test_5xx_raises() -> None:
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/chat/completions").respond(503, json={"error": "down"})
        p = HermesProvider(base_url=BASE, model="Hermes-3", api_key="k", timeout=2, retries=0)
        with pytest.raises(RuntimeError):
            await p.chat(
                ChatRequest(model="Hermes-3", messages=[ChatMessage(role=Role.USER, content="x")])
            )
        await p.aclose()


async def test_messages_serialized_with_tool_calls_and_tool_role() -> None:
    """Mensagens role=assistant com tool_calls e role=tool com tool_call_id devem
    ser enviadas no formato OpenAI."""
    captured: dict[str, bytes] = {}

    def _cap(request):
        captured["body"] = request.read()
        return Response(200, json=_ok("ok"))

    async with respx.mock() as router:
        router.post(f"{BASE}/chat/completions").mock(side_effect=_cap)
        p = HermesProvider(base_url=BASE, model="Hermes-3", api_key="k", timeout=2)
        from ondeline_api.adapters.llm.base import ToolCall

        await p.chat(
            ChatRequest(
                model="Hermes-3",
                messages=[
                    ChatMessage(role=Role.SYSTEM, content="sys"),
                    ChatMessage(role=Role.USER, content="oi"),
                    ChatMessage(
                        role=Role.ASSISTANT,
                        content=None,
                        tool_calls=[
                            ToolCall(
                                id="call_1",
                                name="t",
                                arguments={"a": 1},
                            )
                        ],
                    ),
                    ChatMessage(
                        role=Role.TOOL,
                        content='{"ok": true}',
                        tool_call_id="call_1",
                        name="t",
                    ),
                ],
            )
        )
        await p.aclose()
    body = captured["body"].decode()
    assert '"role":"system"' in body or '"role": "system"' in body
    assert '"tool_call_id":"call_1"' in body or '"tool_call_id": "call_1"' in body
