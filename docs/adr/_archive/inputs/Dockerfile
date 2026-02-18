# ===========================================================================
# Platform Standard Dockerfile (ADR-022)
# ===========================================================================
# Multi-stage build: builder → production
# Base: python:3.12-slim (Debian bookworm)
# User: app (UID 1000, non-root)
# Healthcheck: python urllib on /livez/ (no curl)
# ===========================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install dependencies, compile wheels
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependencies (removed in production stage)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies as wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Production — minimal image, non-root user
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS production

# Build arg for image labels (pass via --build-arg APP_NAME=<app>)
ARG APP_NAME=app

# Labels for GHCR and traceability
LABEL org.opencontainers.image.source="https://github.com/achimdehnert/${APP_NAME}"
LABEL org.opencontainers.image.description="Platform app (ADR-022 compliant)"

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime-only dependencies (no build tools)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (UID 1000)
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid 1000 --create-home app

# Install pre-built wheels from builder stage
COPY --from=builder /build/wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/*.whl && \
    rm -rf /tmp/wheels

# Copy application code
WORKDIR /app
COPY --chown=app:app . .

# Collect static files at build time (no runtime dependency)
# Uses dummy values for settings that require env vars
RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    SECRET_KEY=build-dummy-key-not-for-production \
    DATABASE_URL=sqlite:///tmp/build.db \
    ALLOWED_HOSTS=* \
    python manage.py collectstatic --noinput 2>/dev/null || true

# Copy and set entrypoint permissions
COPY docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER app

# Expose application port (gunicorn binds to 8000)
EXPOSE 8000

# Healthcheck: python urllib, no curl (smaller attack surface)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/livez/')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]
