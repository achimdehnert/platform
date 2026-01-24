"""
Core Search Service - Data Models

Pydantic models for search configuration, requests, and responses.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SearchBackend(str, Enum):
    """Available search backends"""

    FAISS = "faiss"
    POSTGRES_VECTOR = "postgres_vector"
    ELASTICSEARCH = "elasticsearch"
    HYBRID = "hybrid"


class EmbeddingModel(str, Enum):
    """Available embedding models"""

    # Fast & Lightweight (384 dim)
    MINILM_L6 = "all-MiniLM-L6-v2"

    # Better Quality (768 dim)
    MPNET_BASE = "all-mpnet-base-v2"

    # Multilingual (768 dim)
    MULTILINGUAL_E5 = "intfloat/multilingual-e5-large"

    # German-optimized (768 dim)
    GERMAN_BERT = "deutsche-telekom/gbert-large-paraphrase-cosine"

    # Domain-specific
    BIOMEDICAL = "pritamdeka/S-PubMedBert-MS-MARCO"
    CODE = "microsoft/codebert-base"


class SearchConfig(BaseModel):
    """Search engine configuration"""

    backend: SearchBackend = SearchBackend.FAISS
    model: str = EmbeddingModel.MINILM_L6.value
    device: str = "cpu"
    dimension: Optional[int] = None
    cache_dir: Optional[str] = None
    similarity_metric: str = "cosine"
    min_score: float = 0.35
    relative_threshold: float = 0.90

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "backend": "faiss",
                "model": "all-MiniLM-L6-v2",
                "device": "cpu",
                "cache_dir": "~/.bfagent/search",
            }
        }
    )


class SearchResult(BaseModel):
    """Single search result"""

    id: str
    score: float
    title: str = ""
    description: str = ""
    content: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "dwg_parser",
                "score": 0.89,
                "title": "DWG/DXF Parser",
                "description": "Parse AutoCAD files",
                "metadata": {"category": "input", "version": "1.0.0"},
            }
        }
    )


class SearchRequest(BaseModel):
    """Search request"""

    query: str
    top_k: int = 10
    filters: Optional[Dict[str, Any]] = None
    min_score: float = 0.0
    namespace: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response"""

    query: str
    results: List[SearchResult]
    total: int
    backend: SearchBackend
    search_time_ms: float
    namespace: Optional[str] = None


class IndexItem(BaseModel):
    """Item to be indexed"""

    id: str
    text: str
    title: str = ""
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    """Text chunk for document indexing"""

    idx: int
    text: str
    start_char: int
    end_char: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchAnalytics(BaseModel):
    """Search analytics event"""

    query: str
    results_count: int
    top_score: float
    search_time_ms: float
    backend: str
    namespace: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: Optional[int] = None


__all__ = [
    "SearchBackend",
    "EmbeddingModel",
    "SearchConfig",
    "SearchResult",
    "SearchRequest",
    "SearchResponse",
    "IndexItem",
    "Chunk",
    "SearchAnalytics",
]
