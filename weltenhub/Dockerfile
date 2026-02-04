# =============================================================================
# Weltenhub Dockerfile
# =============================================================================
# Multi-stage build for production Django application
# Base: Python 3.12 slim
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:3.12-slim as builder

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Production
# -----------------------------------------------------------------------------
FROM python:3.12-slim as production

# Labels
LABEL maintainer="Achim Dehnert <achim@dehnert.dev>"
LABEL description="Weltenhub - Central Story Universe Platform"
LABEL version="1.0.0"

# Environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.production

# Create non-root user for security
RUN groupadd --gid 1000 weltenhub \
    && useradd --uid 1000 --gid weltenhub --shell /bin/bash --create-home weltenhub

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy application code
COPY --chown=weltenhub:weltenhub . .

# Create directories for static and media files
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R weltenhub:weltenhub /app/staticfiles /app/media

# Switch to non-root user
USER weltenhub

# Collect static files (with dummy env vars for build)
RUN SECRET_KEY=build-dummy-key \
    DB_NAME=dummy DB_USER=dummy DB_PASSWORD=dummy DB_HOST=localhost \
    REDIS_URL=redis://localhost:6379/0 \
    CELERY_BROKER_URL=redis://localhost:6379/0 \
    CELERY_RESULT_BACKEND=redis://localhost:6379/0 \
    python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--worker-class", "gthread", "--worker-tmp-dir", "/dev/shm", "config.wsgi:application"]
