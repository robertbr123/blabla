.PHONY: dev dev-build down logs worker-logs prod prod-build prod-down prod-logs prod-worker-logs test lint install format

# ── Desenvolvimento ──────────────────────────────────────────────────────────

# Sobe os serviços usando imagens cacheadas (não reconstrói)
dev:
	docker compose -f infra/docker-compose.dev.yml --env-file .env up -d

# Força rebuild das imagens antes de subir (use após mudar Dockerfile ou deps)
dev-build:
	docker compose -f infra/docker-compose.dev.yml --env-file .env up -d --build --force-recreate

down:
	docker compose -f infra/docker-compose.dev.yml down

logs:
	docker compose -f infra/docker-compose.dev.yml logs -f

worker-logs:
	docker compose -f infra/docker-compose.dev.yml logs -f worker

# ── Produção ─────────────────────────────────────────────────────────────────

# Sobe produção usando imagens cacheadas
prod:
	docker compose -f infra/docker-compose.prod.yml --env-file .env up -d

# Força rebuild em produção (use após deploy de nova versão)
prod-build:
	docker compose -f infra/docker-compose.prod.yml --env-file .env up -d --build --force-recreate

prod-down:
	docker compose -f infra/docker-compose.prod.yml down

prod-logs:
	docker compose -f infra/docker-compose.prod.yml logs -f

prod-worker-logs:
	docker compose -f infra/docker-compose.prod.yml logs -f worker

install:
	cd apps/api && [ -d .venv ] || python3 -m venv .venv
	cd apps/api && . .venv/bin/activate && pip install -e ".[dev]"

test:
	cd apps/api && . .venv/bin/activate && pytest -v

lint:
	cd apps/api && . .venv/bin/activate && ruff check src tests && mypy src

format:
	cd apps/api && . .venv/bin/activate && ruff format src tests
