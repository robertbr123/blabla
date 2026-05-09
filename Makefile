.PHONY: dev down test lint logs install

dev:
	docker compose -f infra/docker-compose.dev.yml --env-file .env up -d --build

down:
	docker compose -f infra/docker-compose.dev.yml down

logs:
	docker compose -f infra/docker-compose.dev.yml logs -f

install:
	cd apps/api && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"

test:
	cd apps/api && . .venv/bin/activate && pytest -v

lint:
	cd apps/api && . .venv/bin/activate && ruff check src tests && mypy src

format:
	cd apps/api && . .venv/bin/activate && ruff format src tests
