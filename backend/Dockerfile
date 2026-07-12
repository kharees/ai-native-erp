# AI-Native ERP — Backend (FastAPI) production image
#
# Not verified with a live `docker build` — no Docker daemon available in
# the sandbox this was written in (see docs/production-hardening.md). Built
# from the actual requirements.txt / runtime this repo already targets
# (Python 3.12, per the dev environment this project has run under all
# along), not guessed generically.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for asyncpg / psycopg-style builds and bcrypt's native
# extension — kept minimal, removed from the final layer's apt cache.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Runs as a non-root user — the image has no reason to run as root.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# --workers 4 matches the documented production command in main.py's own
# module docstring. Alembic migrations are NOT run here — apply them as a
# separate step/job before starting new containers (running them from the
# app's own entrypoint on every container start races multiple replicas
# against each other during a rolling deploy).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
