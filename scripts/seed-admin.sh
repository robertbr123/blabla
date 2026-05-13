#!/usr/bin/env bash
# Seed an initial ADMIN user idempotently. Reads ADMIN_EMAIL/ADMIN_PASSWORD/ADMIN_NAME
# from the project root .env (which the user populates before running).
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
    echo "ERROR: .env not found at repo root" >&2
    exit 1
fi

# Run inside the api container so DATABASE_URL resolves on the docker network.
docker compose -f infra/docker-compose.dev.yml exec -T \
    -e ADMIN_EMAIL -e ADMIN_PASSWORD -e ADMIN_NAME \
    api python -m ondeline_api.scripts.seed_admin
