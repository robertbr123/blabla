#!/usr/bin/env python3
"""Verifica no SGP (dado fresco) os titulos de um cliente por CPF.

Serve pra diagnosticar a confirmacao de pagamento: mostra status +
dataPagamento de cada titulo, exatamente como o planner ve. Se aparecer
status='pago' com data_pagamento de hoje, o schedule_pagamentos vai agendar
o "obrigado" no proximo ciclo.

A imagem do GHCR NAO inclui scripts/, entao copie pro container antes:

    cd ~/blabla
    docker cp scripts/verificar_pagamento_sgp.py blabla-api:/tmp/
    docker exec -it blabla-api python /tmp/verificar_pagamento_sgp.py 02019889250
"""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "/app/src")

from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider  # noqa: E402
from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider  # noqa: E402
from ondeline_api.adapters.sgp.router import SgpRouter  # noqa: E402
from ondeline_api.config import get_settings  # noqa: E402
from ondeline_api.services.sgp_cache import SgpCacheService  # noqa: E402
from ondeline_api.services.sgp_config import load_sgp_config  # noqa: E402
from ondeline_api.workers.runtime import get_redis, task_session  # noqa: E402


async def main(cpf: str) -> int:
    cpf_digits = "".join(c for c in cpf if c.isdigit())
    s = get_settings()
    redis = await get_redis()
    router: SgpRouter | None = None
    try:
        async with task_session() as session:
            sgp_ond = await load_sgp_config(session, "ondeline")
            sgp_lnk = await load_sgp_config(session, "linknetam")
            router = SgpRouter(
                primary=SgpOndelineProvider(**sgp_ond),
                secondary=SgpLinkNetAMProvider(**sgp_lnk),
            )
            cache = SgpCacheService(
                redis=redis,
                session=session,
                router=router,
                ttl_cliente=s.sgp_cache_ttl_cliente,
                ttl_negativo=s.sgp_cache_ttl_negativo,
            )
            # Forca leitura fresca (ignora cache) pra ver o estado ATUAL no SGP.
            await cache.invalidate(cpf_digits)
            cli = await cache.get_cliente(cpf_digits)
    finally:
        if router is not None:
            await router.aclose()

    if cli is None:
        print(f"✗ CPF {cpf_digits}: nao encontrado no SGP")
        return 1

    print(f"Cliente: {cli.nome} (sgp_id={cli.sgp_id})")
    print(f"{len(cli.titulos)} titulo(s):")
    print("-" * 72)
    for t in cli.titulos:
        print(
            f"  id={t.id}  status={t.status!r}  venc={t.vencimento}  "
            f"valor={t.valor}  data_pagamento={t.data_pagamento!r}"
        )
    print("-" * 72)
    pagos_hoje = [t for t in cli.titulos if t.status == "pago" and t.data_pagamento]
    print(f"Pagos com data_pagamento: {len(pagos_hoje)}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uso: python verificar_pagamento_sgp.py <CPF>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(asyncio.run(main(sys.argv[1])))
