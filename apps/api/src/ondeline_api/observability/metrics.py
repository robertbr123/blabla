"""Prometheus counters/histograms compartilhados por router e workers.

Em M8 expomos via GET /metrics (ver api/metrics.py). Aqui declaramos os
instrumentos custom (ondeline_*) e tambem registramos os collectors padrao
(process_*, python_*, platform_*) no mesmo REGISTRY para que a exposicao
unica em /metrics contenha tudo.
"""
from __future__ import annotations

from prometheus_client import (
    CollectorRegistry,
    Counter,
    PlatformCollector,
    ProcessCollector,
)

REGISTRY = CollectorRegistry(auto_describe=True)


def _counter(name: str, doc: str) -> Counter:
    return Counter(name, doc, registry=REGISTRY)


webhook_received_total = _counter("ondeline_webhook_received_total", "Webhooks recebidos")
webhook_invalid_signature_total = _counter(
    "ondeline_webhook_invalid_signature_total", "Webhooks com HMAC invalido"
)
webhook_rate_limited_total = _counter(
    "ondeline_webhook_rate_limited_total", "Webhooks bloqueados por rate limit"
)
msgs_processed_total = _counter("ondeline_msgs_processed_total", "Mensagens processadas")
msgs_dedup_total = _counter("ondeline_msgs_dedup_total", "Mensagens duplicadas ignoradas")
evolution_send_total = _counter("ondeline_evolution_send_total", "Envios via Evolution OK")
evolution_send_failure_total = _counter(
    "ondeline_evolution_send_failure_total", "Envios via Evolution falharam"
)

# Default collectors (process_cpu_seconds_total, python_info, etc.).
# Registrados uma unica vez no import do modulo (Python cacheia o import).
ProcessCollector(registry=REGISTRY)
PlatformCollector(registry=REGISTRY)
