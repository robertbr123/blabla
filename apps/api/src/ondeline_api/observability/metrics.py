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


def _counter_labeled(name: str, doc: str, labels: list[str]) -> Counter:
    return Counter(name, doc, labels, registry=REGISTRY)


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

# F2 — Régua de cobrança
cobranca_lembrete_enviado_total = _counter_labeled(
    "ondeline_cobranca_lembrete_enviado_total",
    "Lembretes de cobranca enviados por gatilho",
    ["gatilho"],
)
cobranca_lembrete_skipped_total = _counter_labeled(
    "ondeline_cobranca_lembrete_skipped_total",
    "Lembretes pulados (opt-out, rate-limit, ja enviado, falha)",
    ["motivo"],
)
cobranca_optout_total = _counter(
    "ondeline_cobranca_optout_total", "Clientes que optaram por nao receber lembretes"
)

# F3 — Pix QR Code
pix_qr_source_total = _counter_labeled(
    "ondeline_pix_qr_source_total",
    "Origem do BR Code usado pra gerar QR: 'sgp' | 'gerado' | 'indisponivel'",
    ["fonte"],
)

# Default collectors (process_cpu_seconds_total, python_info, etc.).
# Registrados uma unica vez no import do modulo (Python cacheia o import).
ProcessCollector(registry=REGISTRY)
PlatformCollector(registry=REGISTRY)
