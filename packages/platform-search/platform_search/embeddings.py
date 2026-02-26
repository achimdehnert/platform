"""Embedding service for platform-search (ADR-087).

Provides synchronous text embedding via OpenAI API.
Safe for Django views and Celery tasks.
"""

import logging
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class EmbeddingConfig(BaseModel):
    """Configuration for embedding provider."""

    model_config = ConfigDict(frozen=True)

    provider: str = Field(default="openai", description="openai | local")
    model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name",
    )
    dimensions: int = Field(default=1536, description="Vector dimensions")
    batch_size: int = Field(default=100, description="Chunks per API call")


def embed_texts(
    texts: list[str],
    config: EmbeddingConfig | None = None,
) -> list[list[float]]:
    """Embed texts via configured provider (sync).

    Args:
        texts: List of text strings to embed.
        config: Optional embedding configuration.

    Returns:
        List of embedding vectors.
    """
    if config is None:
        config = EmbeddingConfig()

    if not texts:
        return []

    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), config.batch_size):
        batch = texts[i : i + config.batch_size]
        batch_embeddings = _embed_batch(batch, config)
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


def _embed_batch(
    texts: list[str],
    config: EmbeddingConfig,
) -> list[list[float]]:
    """Embed a single batch of texts via OpenAI API."""
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {_get_api_key()}"},
            json={"input": texts, "model": config.model},
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
    return [item["embedding"] for item in data["data"]]


def _get_api_key() -> str:
    """Load OPENAI_API_KEY from Django settings (ADR-045)."""
    from django.conf import settings

    key: str = getattr(settings, "OPENAI_API_KEY", "")
    if not key:
        raise ValueError("OPENAI_API_KEY not configured in Django settings")
    return key
