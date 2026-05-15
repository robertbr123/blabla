.PHONY: dev dev-build down test lint logs worker-logs install format

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

install:
	cd apps/api && [ -d .venv ] || python3 -m venv .venv
	cd apps/api && . .venv/bin/activate && pip install -e ".[dev]"

test:
	cd apps/api && . .venv/bin/activate && pytest -v

lint:
	cd apps/api && . .venv/bin/activate && ruff check src tests && mypy src

format:
	cd apps/api && . .venv/bin/activate && ruff format src tests
