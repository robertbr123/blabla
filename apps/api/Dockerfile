# syntax=docker/dockerfile:1.7

FROM python:3.11-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --system app && useradd --system --gid app --create-home app
WORKDIR /app

# Copy project metadata + source for editable install
COPY --chown=app:app pyproject.toml /app/
COPY --chown=app:app src /app/src

RUN pip install --upgrade pip && \
    pip install .

# Drop build-essential after install to keep image small
RUN apt-get purge -y --auto-remove build-essential

USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/livez || exit 1

CMD ["uvicorn", "ondeline_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
