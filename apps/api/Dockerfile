# syntax=docker/dockerfile:1.7

FROM python:3.11-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libglib2.0-0 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf2.0-0 \
        shared-mime-info \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# uv: gerenciador de pacotes Python muito mais rápido que pip
COPY --from=ghcr.io/astral-sh/uv:0.11.12 /uv /usr/local/bin/uv

RUN groupadd --system app && useradd --system --gid app --create-home app
WORKDIR /app

# Layer 1: instala só as dependências (cacheada enquanto pyproject.toml/uv.lock não mudam)
COPY --chown=app:app pyproject.toml uv.lock /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Layer 2: copia o código e instala o pacote (rápido — só o pacote, deps já estão no cache)
COPY --chown=app:app src /app/src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/livez || exit 1

CMD ["uvicorn", "ondeline_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
