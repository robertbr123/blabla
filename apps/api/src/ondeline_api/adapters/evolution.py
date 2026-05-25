"""Re-export shim — implementacao real foi pra ``adapters.whatsapp.evolution``.

Mantido pra nao quebrar imports legados (workers, services, tools, api/v1).
Novo codigo deve importar de ``ondeline_api.adapters.whatsapp``.
"""
from ondeline_api.adapters.whatsapp.evolution import EvolutionAdapter, EvolutionError

__all__ = ["EvolutionAdapter", "EvolutionError"]
