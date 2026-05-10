# Ondeline v2

[![CI](https://github.com/robertbr123/blabla/actions/workflows/ci.yml/badge.svg)](https://github.com/robertbr123/blabla/actions/workflows/ci.yml)

Reescrita paralela do bot de WhatsApp + dashboard da Ondeline Telecom.

**Status:** em desenvolvimento (M1 — Fundação).

## Stack

- Backend: FastAPI + Celery (Python 3.11)
- Banco: PostgreSQL 16 (Docker)
- Cache/fila: Redis 7
- Frontend: Next.js 15 (em milestones futuros)

## Comandos rápidos

| Comando | O quê |
|---|---|
| `make dev` | Sobe stack de dev (postgres + redis + api) |
| `make down` | Derruba stack |
| `make test` | Roda pytest |
| `make lint` | Roda ruff + mypy |
| `make logs` | Tail dos logs dos containers |

## Documentação

- Spec de design: [docs/superpowers/specs/2026-05-09-ondeline-v2-fase1-fase2-design.md](docs/superpowers/specs/2026-05-09-ondeline-v2-fase1-fase2-design.md)
- Plano M1: [docs/superpowers/plans/2026-05-09-m1-fundacao.md](docs/superpowers/plans/2026-05-09-m1-fundacao.md)

## Setup local

```bash
cp .env.example .env
# editar .env com seus secrets
make dev
curl http://localhost:8000/healthz
```
