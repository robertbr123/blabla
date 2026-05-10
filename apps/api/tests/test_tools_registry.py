"""Registry de tools — registro, schema OpenAI, invoke, lookup, dedup."""
from __future__ import annotations

import pytest
from ondeline_api.tools import registry as reg

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _clean():
    """Salva e restaura o registry global; evita poluir outros testes
    que dependem das tools reais ja registradas via import."""
    saved = dict(reg._REGISTRY)
    reg.reset_for_tests()
    yield
    reg.reset_for_tests()
    reg._REGISTRY.update(saved)


async def test_register_and_invoke() -> None:
    @reg.tool(name="echo", description="echoes", parameters={"type": "object"})
    async def _echo(ctx, **kw):
        return {"ok": True, "got": kw}

    out = await reg.invoke("echo", ctx=None, arguments={"x": 1})  # type: ignore[arg-type]
    assert out == {"ok": True, "got": {"x": 1}}


async def test_specs_to_openai_schema_has_function_wrapper() -> None:
    @reg.tool(
        name="t",
        description="d",
        parameters={"type": "object", "properties": {"a": {"type": "string"}}},
    )
    async def _t(ctx, **kw):
        return {}

    [spec] = reg.specs()
    s = spec.to_openai_schema()
    assert s["type"] == "function"
    assert s["function"]["name"] == "t"


async def test_unknown_tool_returns_error() -> None:
    out = await reg.invoke("nope", ctx=None, arguments={})  # type: ignore[arg-type]
    assert "error" in out


async def test_bad_arguments_returns_error() -> None:
    @reg.tool(name="strict", description="", parameters={"type": "object"})
    async def _strict(ctx, *, must_have: str):
        return {"ok": must_have}

    out = await reg.invoke("strict", ctx=None, arguments={})  # type: ignore[arg-type]
    assert "error" in out


async def test_double_register_raises() -> None:
    @reg.tool(name="dup", description="", parameters={"type": "object"})
    async def _a(ctx, **kw):
        return {}

    with pytest.raises(ValueError):

        @reg.tool(name="dup", description="", parameters={"type": "object"})
        async def _b(ctx, **kw):
            return {}
