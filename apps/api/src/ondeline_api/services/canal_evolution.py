"""Re-export shim — logica real foi pra ``services.canal_whatsapp``.

Mantido pra nao quebrar imports legados (workers/outbound, workers/asr_jobs,
workers/llm_turn). Codigo novo deve importar de ``services.canal_whatsapp``
e preferir ``adapter_for_conversa`` (provider-aware) ao par
``resolver_instance`` + ``evolution_for_instance``.
"""
from ondeline_api.services.canal_whatsapp import (
    adapter_for_canal,
    adapter_for_conversa,
    evolution_for_instance,
    resolver_instance,
)

__all__ = [
    "adapter_for_canal",
    "adapter_for_conversa",
    "evolution_for_instance",
    "resolver_instance",
]
