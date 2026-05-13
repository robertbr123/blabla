"""Drift-catch: assert docker-compose `-Q` strings match workers.queues.QUEUES.

The Celery worker is launched via the `command:` array in docker-compose. Its
`-Q` flag must list exactly the queues the application registers, otherwise
tasks routed to an unsubscribed queue silently sit in Redis forever.

This test parses the YAML and compares the comma-separated queue list in the
worker `command` to the canonical QUEUES tuple. If you add a queue, both compose
files and QUEUES must change together — this test catches the drift.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from ondeline_api.workers.queues import QUEUES

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILES = [
    REPO_ROOT / "infra" / "docker-compose.dev.yml",
    REPO_ROOT / "infra" / "docker-compose.prod.yml",
]


def _worker_q_flag(compose_path: Path) -> tuple[str, ...]:
    data = yaml.safe_load(compose_path.read_text())
    cmd = data["services"]["worker"]["command"]
    # cmd is a list like [..., "-Q", "default,llm,sgp,notifications", ...]
    try:
        idx = cmd.index("-Q")
    except ValueError as e:
        raise AssertionError(f"{compose_path}: worker command has no -Q flag") from e
    csv = cmd[idx + 1]
    return tuple(q.strip() for q in csv.split(",") if q.strip())


@pytest.mark.parametrize("compose_path", COMPOSE_FILES, ids=lambda p: p.name)
def test_compose_worker_queues_match_QUEUES(compose_path: Path) -> None:
    if not compose_path.exists():
        pytest.skip(f"{compose_path} not present")
    compose_qs = _worker_q_flag(compose_path)
    assert compose_qs == QUEUES, (
        f"{compose_path.name} worker -Q flag {compose_qs!r} drifted from "
        f"workers.queues.QUEUES {QUEUES!r}. Update both together."
    )
