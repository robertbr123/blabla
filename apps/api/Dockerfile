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
COPY --chown=app:app alembic /app/alembic
COPY --chown=app:app alembic.ini /app/alembic.ini
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Layer 2.5: instala qrcode DEPOIS do `uv sync --frozen` porque o sync com
# --frozen remove qualquer pacote que nao esteja no uv.lock. qrcode esta no
# pyproject.toml mas ainda nao foi adicionado ao lockfile (precisa rodar
# `uv lock` localmente). Ate la, instalamos aqui no final.
# VIRTUAL_ENV faz `uv pip install` cair direto na venv ja criada pelo sync.
# A venv do uv NAO tem pip instalado (uv usa seu proprio resolver) entao
# precisamos usar `uv pip install`, nao `pip` diretamente.
RUN --mount=type=cache,target=/root/.cache/uv \
    VIRTUAL_ENV=/app/.venv uv pip install "qrcode[pil]>=7.4.0" \
    && /app/.venv/bin/python -c "from qrcode import QRCode; print('qrcode import ok')"

COPY --chown=app:app entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Pastas de midia (volumes nomeados em prod). Pre-criadas com dono `app` para
# que volumes NOVOS nascam gravaveis pelo usuario nao-root — senao o Docker cria
# o mountpoint como root:root e a escrita falha (Errno 13 Permission denied).
RUN mkdir -p /tmp/ondeline_conversa_media /tmp/ondeline_os_fotos /tmp/ondeline_cliente_fotos \
    && chown -R app:app /tmp/ondeline_conversa_media /tmp/ondeline_os_fotos /tmp/ondeline_cliente_fotos

USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/livez || exit 1

CMD ["/app/entrypoint.sh"]
