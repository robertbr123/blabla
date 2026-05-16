"""Tool registry — decorator + lookup + JSON Schema export OpenAI-compatible.

Cada tool se auto-registra ao ser importada. O `llm_loop` inicia importando
o pacote `tools` (que importa cada tool), entao chama `registry.specs()` pra
montar a request ao LLM, e `registry.invoke(name, ctx, args)` quando o LLM
chama tools.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import structlog

from ondeline_api.adapters.llm.base import ToolSpec
from ondeline_api.tools.context import ToolContext

log = structlog.get_logger(__name__)

ToolFn = Callable[..., Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class _Entry:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: ToolFn

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(name=self.name, description=self.description, parameters=self.parameters)


_REGISTRY: dict[str, _Entry] = {}


def tool(*, name: str, description: str, parameters: dict[str, Any]) -> Callable[[ToolFn], ToolFn]:
    def deco(fn: ToolFn) -> ToolFn:
        if name in _REGISTRY:
            raise ValueError(f"tool '{name}' already registered")
        _REGISTRY[name] = _Entry(name=name, description=description, parameters=parameters, fn=fn)
        return fn

    return deco


def specs() -> list[ToolSpec]:
    return [e.spec for e in _REGISTRY.values()]


def names() -> list[str]:
    return list(_REGISTRY.keys())


async def invoke(name: str, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
    entry = _REGISTRY.get(name)
    if entry is None:
        log.warning("tool.unknown", name=name)
        return {"error": f"unknown tool: {name}"}
    try:
        return await entry.fn(ctx, **arguments)
    except TypeError as e:
        log.warning("tool.bad_arguments", name=name, error=str(e), args=arguments)
        return {"error": f"bad arguments for {name}: {e}"}
    except Exception as e:
        log.exception("tool.failed", name=name, error=str(e), exc_type=type(e).__name__)
        return {"error": f"tool {name} failed: {type(e).__name__}: {e}"}


def reset_for_tests() -> None:
    _REGISTRY.clear()


def force_register(entry: _Entry) -> None:
    """Test helper: bypassa o decorator (uso em tests/test_tools_registry)."""
    _REGISTRY[entry.name] = entry
