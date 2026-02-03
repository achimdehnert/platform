# CAD-Hub Platform Dockerfile
# Multi-stage build for Django + FastAPI

FROM python:3.12-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY sql/ ./sql/

ENV PYTHONPATH=/app/src

# FastAPI Service
FROM base as fastapi
EXPOSE 8000
CMD ["uvicorn", "cad_services.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# Django Service
FROM base as django
EXPOSE 8001
WORKDIR /app/src/cad_services/django
RUN python -c "import django; django.setup()" 2>/dev/null || true
CMD ["gunicorn", "--bind", "0.0.0.0:8001", "cad_services.django.wsgi:application"]
