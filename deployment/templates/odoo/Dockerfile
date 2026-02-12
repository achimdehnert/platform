# syntax=docker/dockerfile:1
# =============================================================================
# Odoo Dockerfile Baseline — GHCR Image: Odoo + Custom Addons
# =============================================================================
# Addons liegen im Repo unter addons/
# Optional: Python deps unter requirements.txt
# =============================================================================
ARG ODOO_BASE=odoo:18.0
FROM ${ODOO_BASE}

ARG GIT_SHA=unknown
LABEL org.opencontainers.image.revision=$GIT_SHA

USER root

# -- System dependencies (baseline) ------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# -- Python deps for custom modules (optional) -------------------------------
COPY requirements.txt /tmp/requirements.txt
RUN if [ -s /tmp/requirements.txt ]; then \
        pip install --no-cache-dir -r /tmp/requirements.txt; \
    fi

# -- Copy custom addons -------------------------------------------------------
COPY addons/ /mnt/extra-addons/

USER odoo
