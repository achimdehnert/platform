#!/bin/bash
# ===========================================================================
# entrypoint.sh — Platform Standard Entrypoint (ADR-022)
# ===========================================================================
# Modes: web | worker | beat
#
# Environment variables:
#   DJANGO_SETTINGS_MODULE  (required)
#   GUNICORN_WORKERS        (optional, default: 2)
#   GUNICORN_TIMEOUT        (optional, default: 120)
#   CELERY_LOG_LEVEL        (optional, default: info)
#   CELERY_CONCURRENCY      (optional, default: 2)
#
# Exit codes:
#   0  — clean shutdown
#   1  — invalid arguments or missing env
#   2  — migration failure (only if ENTRYPOINT_MIGRATE=true)
# ===========================================================================
set -euo pipefail

# --- Validate required environment ----------------------------------------
: "${DJANGO_SETTINGS_MODULE:?ERROR: DJANGO_SETTINGS_MODULE must be set}"

# --- Optional: run migrations (default: false, use separate migrate job) ---
if [ "${ENTRYPOINT_MIGRATE:-false}" = "true" ]; then
    echo "[entrypoint] Running migrations..."
    python manage.py migrate --noinput --skip-checks || exit 2
fi

# --- Select service mode ---------------------------------------------------
MODE="${1:?ERROR: Usage: entrypoint.sh [web|worker|beat]}"

case "${MODE}" in
    web)
        echo "[entrypoint] Starting gunicorn (workers=${GUNICORN_WORKERS:-2}, timeout=${GUNICORN_TIMEOUT:-120})"
        # collectstatic is done at Docker build time (see Dockerfile)
        exec gunicorn config.wsgi:application \
            --bind 0.0.0.0:8000 \
            --workers "${GUNICORN_WORKERS:-2}" \
            --timeout "${GUNICORN_TIMEOUT:-120}" \
            --access-logfile - \
            --error-logfile -
        ;;

    worker)
        echo "[entrypoint] Starting celery worker (concurrency=${CELERY_CONCURRENCY:-2})"
        exec celery -A config worker \
            -l "${CELERY_LOG_LEVEL:-info}" \
            --concurrency="${CELERY_CONCURRENCY:-2}"
        ;;

    beat)
        echo "[entrypoint] Starting celery beat"
        exec celery -A config beat \
            -l "${CELERY_LOG_LEVEL:-info}" \
            --schedule=/tmp/celerybeat-schedule
        ;;

    *)
        echo "ERROR: Unknown mode '${MODE}'. Usage: entrypoint.sh [web|worker|beat]" >&2
        exit 1
        ;;
esac
