FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download model to bake into image (avoids download at runtime)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-large')"

FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy cached model from builder
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface

COPY app.py .

# Non-root user
RUN useradd -r -u 1000 app && chown -R app:app /app
USER app

EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/livez/')" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "1"]
