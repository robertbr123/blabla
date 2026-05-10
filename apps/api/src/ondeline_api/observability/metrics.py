"""Prometheus counters/histograms compartilhados por router e workers.

Nada e expose ainda neste M3 (endpoint /metrics fica para M8). Aqui apenas
declaramos os instrumentos para que o codigo de producao ja use desde ja
e os testes possam validar incremento.
"""
from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter


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
