"""Embedder Service — multilingual-e5-large on CPU (ADR-188 Spike).

FastAPI service wrapping sentence-transformers for embedding generation.
Validates latency, RAM, and recall quality on Hetzner CPX31.
"""

import logging
import os
import time
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MODEL_NAME = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-large")
BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "32"))

model = None
model_load_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, model_load_time
    logger.info("Loading model: %s", MODEL_NAME)
    t0 = time.perf_counter()
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    model_load_time = time.perf_counter() - t0
    logger.info("Model loaded in %.1fs, dim=%d", model_load_time, model.get_sentence_embedding_dimension())
    yield
    logger.info("Shutting down embedder service")


app = FastAPI(title="Embedder Service", version="0.1.0", lifespan=lifespan)


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=100)
    prefix: str = Field(default="passage: ", description="E5 prefix: 'query: ' for search, 'passage: ' for ingest")


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    model: str
    dimensions: int
    elapsed_ms: float
    count: int


@app.post("/embed", response_model=EmbedResponse)
async def embed(req: EmbedRequest):
    if model is None:
        raise HTTPException(503, "Model not loaded yet")

    prefixed = [f"{req.prefix}{t}" for t in req.texts]

    t0 = time.perf_counter()
    vectors = model.encode(prefixed, batch_size=BATCH_SIZE, normalize_embeddings=True, show_progress_bar=False)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    return EmbedResponse(
        embeddings=vectors.tolist(),
        model=MODEL_NAME,
        dimensions=vectors.shape[1],
        elapsed_ms=round(elapsed_ms, 2),
        count=len(req.texts),
    )


@app.get("/livez/")
async def livez():
    return "ok\n"


@app.get("/healthz/")
async def healthz():
    if model is None:
        raise HTTPException(503, "Model not loaded")
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "dimensions": model.get_sentence_embedding_dimension(),
        "model_load_time_s": round(model_load_time, 1),
    }


@app.get("/info")
async def info():
    import psutil
    import torch

    process = psutil.Process()
    mem_mb = process.memory_info().rss / 1024 / 1024
    return {
        "model": MODEL_NAME,
        "dimensions": model.get_sentence_embedding_dimension() if model else None,
        "ram_mb": round(mem_mb, 1),
        "cpu_count": os.cpu_count(),
        "torch_threads": torch.get_num_threads(),
        "batch_size": BATCH_SIZE,
    }
