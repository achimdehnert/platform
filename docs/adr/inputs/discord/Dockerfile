FROM python:3.12-slim

LABEL maintainer="iil.gmbh" \
      description="llm_mcp — Layer 2 LLM Gateway für Discord/Cascade"

RUN set -euo pipefail && \
    apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

COPY llm_mcp/ ./llm_mcp/

RUN addgroup --system llm && adduser --system --ingroup llm llm
USER llm

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "llm_mcp.main:app", "--host", "0.0.0.0", "--port", "8001", \
     "--workers", "2", "--log-config", "/dev/null"]
