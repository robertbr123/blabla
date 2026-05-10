"""HermesProvider — fala HTTP direto com gateway OpenAI-compatible.

Nao usamos o SDK `openai` para manter controle fino sobre timeout/retry/JSON
parsing. O endpoint esperado e `<base>/chat/completions`, no formato
OpenAI v1 (com `tools`/`tool_calls`).
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import structlog

from ondeline_api.adapters.llm.base import (
    ChatRequest,
    ChatResponse,
    LLMProvider,
    Role,
    ToolCall,
)

log = structlog.get_logger(__name__)


class HermesProvider(LLMProvider):
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout: float = 30.0,
        retries: int = 1,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._retries = retries
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def chat(self, req: ChatRequest) -> ChatResponse:
        body = self._serialize(req)
        url = f"{self._base}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        for attempt in range(self._retries + 1):
            try:
                resp = await self._client.post(url, json=body, headers=headers)
                if 200 <= resp.status_code < 300:
                    return self._parse(resp.json())
                if resp.status_code >= 500 and attempt < self._retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise RuntimeError(
                    f"Hermes HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except httpx.HTTPError as e:
                if attempt < self._retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise RuntimeError(f"Hermes network error: {e}") from e
        raise RuntimeError("Hermes: exhausted retries")  # defensivo

    # ── serialization ─────────────────────────────────────────

    def _serialize(self, req: ChatRequest) -> dict[str, Any]:
        msgs: list[dict[str, Any]] = []
        for m in req.messages:
            d: dict[str, Any] = {"role": m.role.value}
            if m.content is not None:
                d["content"] = m.content
            if m.role is Role.TOOL:
                d["tool_call_id"] = m.tool_call_id or ""
                if m.name:
                    d["name"] = m.name
            if m.role is Role.ASSISTANT and m.tool_calls:
                d["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    for tc in m.tool_calls
                ]
            msgs.append(d)

        body: dict[str, Any] = {
            "model": req.model or self._model,
            "messages": msgs,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        if req.tools:
            body["tools"] = [t.to_openai_schema() for t in req.tools]
            body["tool_choice"] = "auto"
        return body

    def _parse(self, payload: dict[str, Any]) -> ChatResponse:
        choice = (payload.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        finish = choice.get("finish_reason") or "stop"
        usage = payload.get("usage") or {}
        tool_calls_raw = msg.get("tool_calls") or []
        tool_calls: list[ToolCall] = []
        for tc in tool_calls_raw:
            fn = tc.get("function") or {}
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                log.warning("hermes.bad_tool_args", raw=fn.get("arguments"))
                args = {}
            tool_calls.append(
                ToolCall(id=tc.get("id", ""), name=fn.get("name", ""), arguments=args)
            )
        return ChatResponse(
            content=msg.get("content"),
            tool_calls=tool_calls,
            tokens_used=int(usage.get("total_tokens", 0)),
            finish_reason=str(finish),
        )
