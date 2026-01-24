FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PYTHONPATH=/app/packages

WORKDIR /app

# System deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    make \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
COPY docs/requirements.txt /app/docs/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install Sphinx and all documentation dependencies
RUN pip install --no-cache-dir -r /app/docs/requirements.txt

COPY . /app

# Install local packages (so Django can import bfagent_mcp, etc.)
RUN pip install --no-cache-dir -e /app/packages/bfagent_mcp

# Build Sphinx documentation (ARG invalidates cache)
ARG CACHEBUST=1
RUN cd /app/docs && make html

RUN chmod +x /app/docker/entrypoint.web.sh

EXPOSE 8000
