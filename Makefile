.PHONY: dev down test lint logs worker-logs install format

dev:
	docker compose -f infra/docker-compose.dev.yml --env-file .env up -d --build

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
