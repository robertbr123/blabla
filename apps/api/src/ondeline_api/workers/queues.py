"""Canonical Celery queue names.

Single source of truth for the list of queues. Imported by:
  - workers/celery_app.py (builds task_queues from QUEUES)
  - observability/celery_queue.py (queue-depth helper)
  - tests/test_compose_queues_sync.py (drift-catch test)

If you add or rename a queue, update:
  1. QUEUES below
  2. infra/docker-compose.dev.yml — worker `command: ["celery", ..., "-Q", "<csv>", ...]`
  3. infra/docker-compose.prod.yml — same
  4. workers/celery_app.py task_routes — route the new task to the new queue

The drift-catch test asserts the compose files' `-Q` CSV matches QUEUES.
"""
from __future__ import annotations

QUEUES: tuple[str, ...] = ("default", "llm", "sgp", "notifications")
DEFAULT_QUEUE: str = "default"
