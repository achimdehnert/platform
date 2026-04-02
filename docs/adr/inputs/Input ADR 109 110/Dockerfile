# hub_template/Dockerfile
#
# Fixes ADR-110:
#   H-7: compilemessages mit --locale=de --locale=en (nicht alle System-Locales)
#   B-2: RUN-Schritte mit set -euo pipefail (Shell-Fehler propagieren)
#
# Multi-stage build: builder (deps + messages) → production (minimal image)

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ---------------------------------------------------------------------------
# Builder stage: install all deps + compile messages
# ---------------------------------------------------------------------------
FROM base AS builder

# System deps for psycopg2, Pillow etc.
RUN set -euo pipefail && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gettext \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN set -euo pipefail && \
    pip install --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
# Production stage
# ---------------------------------------------------------------------------
FROM base AS production

# gettext required for compilemessages at runtime
RUN set -euo pipefail && \
    apt-get update && \
    apt-get install -y --no-install-recommends gettext libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

COPY . .

# Static files
RUN set -euo pipefail && \
    python manage.py collectstatic --noinput

# Fix H-7: Compile ONLY defined locales (not all system locales)
# Fix B-2: set -euo pipefail (fail build if .po file has syntax error)
RUN set -euo pipefail && \
    python manage.py compilemessages --locale=de --locale=en

# Non-root user (security best practice)
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
