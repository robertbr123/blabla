"""EvolutionAdapter — wrapper httpx para sendText/sendMedia."""
from __future__ import annotations

import httpx
import pytest
import respx

from ondeline_api.adapters.evolution import (
    EvolutionAdapter,
    EvolutionError,
)


pytestmark = pytest.mark.asyncio

BASE = "http://evo.test"
INSTANCE = "hermes-wa"
KEY = "evo-key"


async def test_send_text_posts_correctly() -> None:
    async with respx.mock(assert_all_called=True) as router:
        route = router.post(f"{BASE}/message/sendText/{INSTANCE}").respond(
            200, json={"key": {"id": "WAEVT_OUT_1"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INSTANCE, api_key=KEY)
        result = await adapter.send_text("5511@s", "Olá")
        assert result["key"]["id"] == "WAEVT_OUT_1"
        sent = route.calls.last.request
        assert sent.headers["apikey"] == KEY
        body = sent.read()
        assert b'"number":"5511@s"' in body or b'"number": "5511@s"' in body
        assert b"Ol" in body  # texto presente
        await adapter.aclose()


async def test_send_media_passes_link() -> None:
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendMedia/{INSTANCE}").respond(200, json={"ok": True})
        adapter = EvolutionAdapter(base_url=BASE, instance=INSTANCE, api_key=KEY)
        await adapter.send_media(
            "5511@s",
            url="https://x/y.pdf",
            mediatype="document",
            mimetype="application/pdf",
            file_name="fatura.pdf",
            caption="📄",
        )
        await adapter.aclose()


async def test_non_2xx_raises() -> None:
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INSTANCE}").respond(503, json={"err": "down"})
        adapter = EvolutionAdapter(base_url=BASE, instance=INSTANCE, api_key=KEY)
        with pytest.raises(EvolutionError):
            await adapter.send_text("5511@s", "x")
        await adapter.aclose()


async def test_network_error_raises() -> None:
    async with respx.mock() as router:
        router.post(f"{BASE}/message/sendText/{INSTANCE}").mock(
            side_effect=httpx.ConnectError("nope")
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INSTANCE, api_key=KEY, retries=0)
        with pytest.raises(EvolutionError):
            await adapter.send_text("5511@s", "x")
        await adapter.aclose()


async def test_retries_then_success() -> None:
    async with respx.mock(assert_all_called=True) as router:
        route = router.post(f"{BASE}/message/sendText/{INSTANCE}")
        route.side_effect = [
            httpx.Response(503, json={"err": "down"}),
            httpx.Response(200, json={"ok": True}),
        ]
        adapter = EvolutionAdapter(base_url=BASE, instance=INSTANCE, api_key=KEY, retries=1)
        await adapter.send_text("5511@s", "ok depois de retry")
        await adapter.aclose()
        assert route.call_count == 2
