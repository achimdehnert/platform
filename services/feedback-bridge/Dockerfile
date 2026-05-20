FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml .
COPY src/ ./src/

RUN pip install --no-cache-dir -e . && \
    useradd -m -u 1001 bridge

USER bridge
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/v1/health').raise_for_status()"

CMD ["uvicorn", "feedback_bridge.main:app", "--host", "0.0.0.0", "--port", "8000"]
