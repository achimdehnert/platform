# IIL Platform — Django App Dockerfile (Golden Path)
# Kopiere in Repo-Root und ersetze REPO_NAME
# Referenz: ADR-056 (Docker + Health), ADR-022 (Secrets via env_file)

FROM python:3.12-slim AS base

LABEL org.opencontainers.image.source="https://github.com/achimdehnert/REPO_NAME"
LABEL org.opencontainers.image.description="REPO_NAME Django Application"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup --system app && adduser --system --group app

# ── Dependencies ──────────────────────────────────────────────────────────────
FROM base AS deps

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# ── Production Image ──────────────────────────────────────────────────────────
FROM base AS production

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY --chown=app:app . .

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/livez/')" || exit 1

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
