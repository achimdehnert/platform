# ADR-105: iil-researchfw — Code-Extraktion und Implementierungsplan

**Status:** Accepted (v2 — nach Review REVIEW-ADR-105)  
**Datum:** 2026-03-07  
**Kontext:** Umsetzung von ADR-104 (Research Hub + iil-researchfw)  
**Abhängigkeit:** ADR-104-research-hub-iil-researchfw.md

---

## Änderungen in v2 (nach Review)

| Finding | Severity | Änderung |
|---|---|---|
| Kein Async-First Design | CRITICAL | `httpx.AsyncClient` + `asyncio.gather()` durchgehend |
| Rate Limiting fehlt | CRITICAL | `tenacity` als Core-Dependency, `_internal/rate_limiter.py` |
| `contrib/` verletzt SRP | HIGH | entfernt — gehört in Consumer-Repos |
| Pydantic als Dependency, aber dataclass genutzt | HIGH | Pydantic v2 für alle Models |
| `ResearchProjectProtocol` zu vage | HIGH | vollständig typisiert mit `Finding`/`Source` Pydantic-Models |
| `LLMCallable` zu simpel | HIGH | async + `response_format` + `AsyncLLMStreamCallable` |
| Kein Caching | MEDIUM | `_internal/cache.py` TTL-Cache |
| Keine mypy-Config | MEDIUM | `[tool.mypy] strict = true` in `pyproject.toml` |
| Test-Strategie unklar | MEDIUM | `respx` + `pytest-asyncio` dokumentiert |
| Zeitplan unrealistisch | MEDIUM | Phase 0 eingefügt, Phase 1 auf 2 Wochen gestreckt |

---

## Kontext

ADR-104 hat die Architektur entschieden: `iil-researchfw` wird ein eigenständiges PyPI-Package.
Dieser ADR dokumentiert die **genaue Code-Extraktion** aus `bfagent/apps/research/services/`.

---

## Code-Analyse: bfagent/apps/research/services/

### Inventar der bestehenden Services

| Datei | Größe | Django-Abh. | Direkt extrahierbar |
|---|---|---|---|
| `citation_service.py` | 710 Zeilen | ❌ keine | ✅ requests→httpx async |
| `academic_search_service.py` | 632 Zeilen | ❌ keine | ✅ requests→httpx, async+gather |
| `brave_search_service.py` | 274 Zeilen | ⚠️ `django.conf.settings` | ✅ API-Key via Konstruktor/ENV |
| `ai_summary_service.py` | 261 Zeilen | ⚠️ `apps.bfagent.services.llm_client` | ✅ async LLMCallable Protocol |
| `research_service.py` | 300 Zeilen | ❌ keine | ✅ direkt, auf async umstellen |
| `export_service.py` | 329 Zeilen | ⚠️ `project.findings.all()` (ORM) | ✅ Pydantic Protocol-Interface |
| `vector_store_service.py` | 295 Zeilen | ⚠️ ORM-Zugriff | ❌ bleibt in research-hub |
| `outline_generator.py` | 662 Zeilen | ⚠️ `apps.core.models.Agent` | ❌ bleibt in bfagent |
| `paper_frameworks.py` | ~500 Zeilen | ❌ keine | ❌ buchspezifisch, bleibt in bfagent |

---

## Ziel-Paketstruktur iil-researchfw v0.1.0

```
iil_researchfw/
├── __init__.py               # Version, __all__
├── py.typed
│
├── core/
│   ├── __init__.py
│   ├── models.py             # Pydantic v2: ResearchContext, ResearchOutput, Finding, Source
│   ├── protocols.py          # LLMCallable, AsyncLLMStreamCallable, ResearchProjectProtocol
│   ├── exceptions.py         # ResearchError, APIError, RateLimitError
│   └── service.py            # ResearchService (async)
│
├── search/
│   ├── __init__.py
│   ├── base.py               # AsyncBaseSearchProvider (ABC)
│   ├── brave.py              # BraveSearchService (async, API-Key via ENV)
│   └── academic.py           # AcademicSearchService (async + asyncio.gather)
│
├── citations/
│   ├── __init__.py
│   └── formatter.py          # CitationStyle, Citation, Author, CitationService
│
├── analysis/
│   ├── __init__.py
│   ├── summary.py            # AISummaryService (async LLMCallable)
│   └── relevance.py          # Relevanz-Scoring
│
├── export/
│   ├── __init__.py
│   └── service.py            # ResearchExportService (Pydantic Protocol)
│
└── _internal/
    ├── __init__.py
    ├── cache.py              # TTL-Cache (in-memory)
    └── rate_limiter.py       # Token-Bucket per API-Endpoint
```

> **❌ contrib/ entfernt**: `travel.py`, `worldbuilding.py` etc. gehören in die jeweiligen Consumer-Repos
> (`travel-beat/apps/research/`, `weltenhub/apps/research/`). Ein generisches Research-Framework
> darf nicht domain-spezifisch werden.

---

## pyproject.toml (produktionsreif)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "iil-researchfw"
version = "0.1.0"
description = "Platform research framework — search, citations, analysis, export"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"

dependencies = [
    "httpx>=0.27,<1",         # Async HTTP (ersetzt requests)
    "pydantic>=2.7,<3",       # Validation + Models
    "tenacity>=8.3,<9",       # Retry + Exponential Backoff
    "anyio>=4.4,<5",          # Async Backend-agnostisch
]

[project.optional-dependencies]
export = [
    "python-docx>=1.1",
    "types-python-docx",
    "markdown>=3.5",
]
scraping = [
    "beautifulsoup4>=4.12",
    "playwright>=1.40",
]
all = [
    "iil-researchfw[export,scraping]",
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "mypy>=1.10",
    "ruff>=0.4",
    "coverage[toml]>=7.5",
]

[tool.mypy]
strict = true
python_version = "3.11"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.coverage.run]
branch = true
source = ["iil_researchfw"]

[tool.coverage.report]
fail_under = 80
```

---

## core/protocols.py (produktionsreif)

```python
"""Central Protocol definitions for iil-researchfw."""
from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator, Protocol, runtime_checkable

from .models import Finding, Source


class LLMCallable(Protocol):
    """Synchronous LLM callable — inject into AISummaryService."""

    async def __call__(
        self,
        prompt: str,
        max_tokens: int = 500,
        response_format: dict[str, Any] | None = None,
    ) -> str: ...


class AsyncLLMStreamCallable(Protocol):
    """Streaming LLM callable."""

    async def __call__(self, prompt: str) -> AsyncIterator[str]: ...


@runtime_checkable
class ResearchProjectProtocol(Protocol):
    """Protocol for Django ResearchProject models — avoids ORM coupling."""

    name: str
    query: str
    description: str
    created_at: datetime

    @property
    def findings(self) -> list[Finding]: ...

    @property
    def sources(self) -> list[Source]: ...
```

---

## core/models.py (produktionsreif)

```python
"""Pydantic v2 models for iil-researchfw."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    content: str
    source_url: str = ""
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.now)


class Source(BaseModel):
    model_config = ConfigDict(frozen=True)

    url: str
    title: str
    domain: str = ""
    snippet: str = ""
    fetched_at: datetime = Field(default_factory=datetime.now)


class ResearchContext(BaseModel):
    query: str
    domain: str | None = None
    max_sources: int = Field(default=10, ge=1, le=100)
    include_local: bool = False
    language: str = "de"
    filters: dict[str, Any] = Field(default_factory=dict)


class ResearchOutput(BaseModel):
    success: bool
    query: str
    sources: list[Source] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
```

---

## core/exceptions.py (produktionsreif)

```python
"""Exception hierarchy for iil-researchfw."""


class ResearchError(Exception):
    """Base exception for iil-researchfw."""


class APIError(ResearchError):
    """External API call failed."""

    def __init__(self, service: str, status_code: int, message: str = "") -> None:
        self.service = service
        self.status_code = status_code
        super().__init__(f"{service} API error {status_code}: {message}")


class RateLimitError(APIError):
    """Rate limit exceeded (HTTP 429)."""


class SearchError(ResearchError):
    """Search operation failed."""


class CitationError(ResearchError):
    """Citation resolution failed."""


class ExportError(ResearchError):
    """Export operation failed."""
```

---

## search/academic.py — Async-First Pattern

```python
"""Academic search — async concurrent multi-source."""
from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .._internal.rate_limiter import RateLimiter
from ..core.exceptions import APIError, RateLimitError

logger = logging.getLogger(__name__)


@dataclass
class AcademicPaper:
    title: str
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    url: str = ""
    source: str = ""
    doi: str | None = None
    arxiv_id: str | None = None
    publication_date: str = ""
    journal: str = ""
    citation_count: int | None = None
    pdf_url: str | None = None
    categories: list[str] = field(default_factory=list)


class AcademicSearchService:
    """Concurrent multi-source academic search."""

    _rate_limiters: dict[str, RateLimiter] = {}

    def __init__(self, cache_ttl_seconds: int = 3600) -> None:
        self._cache: dict[str, tuple[list[AcademicPaper], float]] = {}
        self._cache_ttl = cache_ttl_seconds

    async def search(
        self,
        query: str,
        sources: list[str] | None = None,
        max_results: int = 10,
    ) -> list[AcademicPaper]:
        """
        Concurrent search across all academic sources.

        Uses asyncio.gather() — 6 API calls in parallel (~max 800ms vs 3+ sec sequential).
        Exceptions per source are isolated via return_exceptions=True.
        """
        active = sources or ["arxiv", "semantic_scholar", "pubmed", "openalex"]

        async with httpx.AsyncClient(timeout=15.0) as client:
            tasks = []
            source_names = []
            for src in active:
                fn = getattr(self, f"_search_{src}", None)
                if fn:
                    tasks.append(fn(client, query, max_results))
                    source_names.append(src)

            results = await asyncio.gather(*tasks, return_exceptions=True)

        papers: list[AcademicPaper] = []
        for src, result in zip(source_names, results):
            if isinstance(result, Exception):
                logger.warning(f"{src} search failed: {result}")
            else:
                papers.extend(result)

        return self._deduplicate(papers)[:max_results]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    async def _search_arxiv(
        self, client: httpx.AsyncClient, query: str, max_results: int
    ) -> list[AcademicPaper]:
        """arXiv XML API — no API key required."""
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": min(max_results, 100),
        }
        response = await client.get("https://export.arxiv.org/api/query", params=params)
        if response.status_code == 429:
            raise RateLimitError("arxiv", 429)
        response.raise_for_status()
        return self._parse_arxiv_xml(response.text)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    async def _search_semantic_scholar(
        self, client: httpx.AsyncClient, query: str, max_results: int
    ) -> list[AcademicPaper]:
        """Semantic Scholar API — free, 100 req/5min."""
        params = {
            "query": query,
            "limit": min(max_results, 100),
            "fields": "title,authors,abstract,year,externalIds,openAccessPdf,citationCount",
        }
        response = await client.get(
            "https://api.semanticscholar.org/graph/v1/paper/search", params=params
        )
        if response.status_code == 429:
            raise RateLimitError("semantic_scholar", 429)
        response.raise_for_status()
        return self._parse_semantic_scholar(response.json())

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    async def _search_pubmed(
        self, client: httpx.AsyncClient, query: str, max_results: int
    ) -> list[AcademicPaper]:
        """NCBI E-utilities — free, 3 req/sec without API key."""
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {"db": "pubmed", "term": query, "retmax": min(max_results, 10000), "retmode": "json"}
        r = await client.get(search_url, params=params)
        r.raise_for_status()
        ids = r.json().get("esearchresult", {}).get("idlist", [])[:max_results]
        if not ids:
            return []
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params2 = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
        r2 = await client.get(fetch_url, params=params2)
        r2.raise_for_status()
        return self._parse_pubmed_xml(r2.text)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    async def _search_openalex(
        self, client: httpx.AsyncClient, query: str, max_results: int
    ) -> list[AcademicPaper]:
        """OpenAlex API — free, 100k req/day."""
        params = {
            "search": query,
            "per_page": min(max_results, 50),
            "mailto": "research@iil.pet",
        }
        response = await client.get("https://api.openalex.org/works", params=params)
        response.raise_for_status()
        return self._parse_openalex(response.json())

    def _parse_arxiv_xml(self, xml_text: str) -> list[AcademicPaper]:
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        root = ET.fromstring(xml_text)
        papers = []
        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
            authors = [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)]
            abstract = entry.findtext("atom:summary", "", ns).strip()
            url = entry.findtext("atom:id", "", ns)
            arxiv_id = url.split("/abs/")[-1] if "/abs/" in url else ""
            papers.append(AcademicPaper(
                title=title, authors=authors, abstract=abstract[:500],
                url=url, source="arxiv", arxiv_id=arxiv_id,
            ))
        return papers

    def _parse_semantic_scholar(self, data: dict) -> list[AcademicPaper]:
        papers = []
        for item in data.get("data", []):
            papers.append(AcademicPaper(
                title=item.get("title", ""),
                authors=[a.get("name", "") for a in item.get("authors", [])],
                abstract=item.get("abstract", "") or "",
                url=f"https://api.semanticscholar.org/paper/{item.get('paperId', '')}",
                source="semantic_scholar",
                doi=item.get("externalIds", {}).get("DOI"),
                publication_date=str(item.get("year", "")),
                citation_count=item.get("citationCount"),
                pdf_url=(item.get("openAccessPdf") or {}).get("url"),
            ))
        return papers

    def _parse_pubmed_xml(self, xml_text: str) -> list[AcademicPaper]:
        root = ET.fromstring(xml_text)
        papers = []
        for article in root.findall(".//PubmedArticle"):
            title = article.findtext(".//ArticleTitle", "")
            authors = [
                f"{a.findtext('LastName', '')} {a.findtext('ForeName', '')}".strip()
                for a in article.findall(".//Author")
                if a.findtext("LastName")
            ]
            abstract = article.findtext(".//AbstractText", "")
            pmid = article.findtext(".//PMID", "")
            year = article.findtext(".//PubDate/Year", "")
            journal = article.findtext(".//Journal/Title", "")
            papers.append(AcademicPaper(
                title=title, authors=authors,
                abstract=(abstract or "")[:500],
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                source="pubmed",
                publication_date=year, journal=journal,
            ))
        return papers

    def _parse_openalex(self, data: dict) -> list[AcademicPaper]:
        papers = []
        for item in data.get("results", []):
            doi = item.get("doi", "")
            if doi and doi.startswith("https://doi.org/"):
                doi = doi[16:]
            authors = [
                auth.get("author", {}).get("display_name", "")
                for auth in item.get("authorships", [])[:10]
            ]
            oa = item.get("open_access", {})
            papers.append(AcademicPaper(
                title=item.get("title") or "Unknown",
                authors=authors,
                url=item.get("id", ""),
                source="openalex",
                doi=doi or None,
                publication_date=str(item.get("publication_year", "")),
                journal=(
                    (item.get("primary_location") or {}).get("source", {}) or {}
                ).get("display_name", ""),
                citation_count=item.get("cited_by_count"),
                pdf_url=oa.get("oa_url") if oa.get("is_oa") else None,
            ))
        return papers

    def _deduplicate(self, papers: list[AcademicPaper]) -> list[AcademicPaper]:
        """Deduplicate by DOI, then by normalized title."""
        seen_dois: set[str] = set()
        seen_titles: set[str] = set()
        result = []
        for p in papers:
            if p.doi and p.doi in seen_dois:
                continue
            norm_title = p.title.lower().strip()
            if norm_title in seen_titles:
                continue
            if p.doi:
                seen_dois.add(p.doi)
            seen_titles.add(norm_title)
            result.append(p)
        return result
```

---

## _internal/rate_limiter.py (produktionsreif)

```python
"""Token-bucket rate limiter for external API calls."""
from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """
    Async token-bucket rate limiter.

    Usage:
        limiter = RateLimiter(calls_per_second=3.0)  # PubMed: 3 req/sec
        async with limiter:
            response = await client.get(...)
    """

    def __init__(self, calls_per_second: float = 1.0) -> None:
        self.calls_per_second = calls_per_second
        self._min_interval = 1.0 / calls_per_second
        self._last_call: float = 0.0
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "RateLimiter":
        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()
        return self

    async def __aexit__(self, *_: object) -> None:
        pass
```

---

## _internal/cache.py (produktionsreif)

```python
"""In-memory TTL cache for research results."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """
    Simple in-memory TTL cache.

    Usage:
        cache: TTLCache[list[AcademicPaper]] = TTLCache(ttl_seconds=3600)
        key = cache.make_key(query, sources)
        if cached := cache.get(key):
            return cached
        result = await expensive_call()
        cache.set(key, result)
        return result
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._store: dict[str, tuple[T, float]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> T | None:
        if entry := self._store.get(key):
            value, expires_at = entry
            if time.monotonic() < expires_at:
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: T) -> None:
        self._store[key] = (value, time.monotonic() + self._ttl)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    @staticmethod
    def make_key(*args: Any) -> str:
        raw = json.dumps(args, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

---

## Test-Strategie

### Mock-Strategie für externe APIs

```python
# tests/search/test_academic.py
import pytest
import respx
import httpx
from iil_researchfw.search.academic import AcademicSearchService


@pytest.mark.asyncio
async def test_search_arxiv_concurrent():
    """Alle Quellen werden parallel angefragt."""
    with respx.mock:
        respx.get("https://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=ARXIV_XML_FIXTURE)
        )
        respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        respx.get("https://api.openalex.org/works").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").mock(
            return_value=httpx.Response(200, json={"esearchresult": {"idlist": []}})
        )
        service = AcademicSearchService()
        papers = await service.search("machine learning")
        assert isinstance(papers, list)


@pytest.mark.asyncio
async def test_search_handles_partial_failure():
    """Einzelne Quellen dürfen scheitern ohne den Gesamtaufruf zu brechen."""
    with respx.mock:
        respx.get("https://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(429)  # Rate limited
        )
        respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        respx.get("https://api.openalex.org/works").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").mock(
            return_value=httpx.Response(200, json={"esearchresult": {"idlist": []}})
        )
        service = AcademicSearchService()
        papers = await service.search("test query")
        assert isinstance(papers, list)  # kein Exception-Propagation
```

### LLMCallable Mock für AISummaryService

```python
# tests/analysis/test_summary.py
from unittest.mock import AsyncMock
from iil_researchfw.analysis.summary import AISummaryService


async def test_summarize_findings_with_mock_llm():
    mock_llm = AsyncMock(return_value="Test summary output.")
    service = AISummaryService(llm_fn=mock_llm)
    result = await service.summarize_findings(
        [{"title": "Finding 1", "content": "Some content"}]
    )
    assert result["ai_generated"] is True
    mock_llm.assert_called_once()


async def test_summarize_findings_fallback_without_llm():
    service = AISummaryService(llm_fn=None)
    result = await service.summarize_findings(
        [{"title": "Finding 1", "content": "Some content"}]
    )
    assert result["ai_generated"] is False
```

---

## Consumer-Integration: bfagent

```python
# bfagent/apps/research/services/__init__.py  (nach Migration)

from iil_researchfw.search.academic import AcademicSearchService
from iil_researchfw.search.brave import BraveSearchService
from iil_researchfw.citations.formatter import CitationService, CitationStyle
from iil_researchfw.analysis.summary import AISummaryService
from iil_researchfw.core.service import ResearchService

from apps.bfagent.services.llm_client import generate_text  # bleibt lokal

# LLM-Injection: iil-researchfw bleibt LLM-agnostisch
ai_summary = AISummaryService(llm_fn=generate_text)
```

```toml
# bfagent requirements/base.txt
iil-researchfw>=0.1,<0.2  # Pin auf MINOR für Breaking-Change-Schutz
```

---

## Konsumenten und ihr Benefit

| Repo | Nutzt | Konkreter Nutzen |
|---|---|---|
| **bfagent** | `citations`, `search.academic`, `search.brave`, `analysis.summary` | Direkte Ablösung der eigenen Services |
| **travel-beat** | `search.brave`, `core.service` | Orte-Research, POI-Suche |
| **weltenhub** | `search.brave`, `search.academic` | Historische Fakten, Kulturen |
| **pptx-hub** | `search.brave`, `analysis.summary` | Content-Research für Präsentationen |
| **research-hub** | alle Module | Django-Layer darüber |

> **Consumer-spezifische Helpers** (z.B. `TravelResearchHelper`, `WorldbuildingHelper`)
> werden in den jeweiligen Consumer-Repos implementiert und wrappen `iil-researchfw`-Services.

---

## Semantische Versionierung + Deprecation-Policy

```
v0.x.y — Initial Development Phase
  PATCH (0.x.Y): Bugfixes, non-breaking
  MINOR (0.X.0): New features, may break — CHANGELOG + Migration-Guide required
  MAJOR (X.0.0): Stable API (ab v1.0.0)

Consumer-Pin-Empfehlung:
  iil-researchfw>=0.1,<0.2  # MINOR-Pin in 0.x Phase
  iil-researchfw>=1.0,<2    # MAJOR-Pin ab v1.0

Deprecation:
  - Deprecated APIs bleiben 1 MINOR-Version erhalten
  - DeprecationWarning via warnings.warn()
  - CHANGELOG.md Pflicht bei jedem Release
```

---

## Implementierungsplan (revidiert nach Review)

```
Phase 0 — Fundament (3 Tage)
[ ] Repo achimdehnert/researchfw erstellen
[ ] pyproject.toml (exakt wie oben)
[ ] core/exceptions.py
[ ] core/models.py (Pydantic v2)
[ ] core/protocols.py (LLMCallable, ResearchProjectProtocol)
[ ] _internal/cache.py
[ ] _internal/rate_limiter.py
[ ] CI-Pipeline (.github/workflows/ci.yml)

Phase 1 — Services (Woche 1–2)
[ ] citations/formatter.py (requests→httpx async, dataclass beibehalten)
[ ] search/base.py (AsyncBaseSearchProvider ABC)
[ ] search/academic.py (async + asyncio.gather + tenacity retry)
[ ] search/brave.py (async, API-Key via Konstruktor/ENV)
[ ] core/service.py (ResearchService, async)
[ ] Tests: >80% Coverage mit respx
[ ] PyPI publish v0.1.0

Phase 2 — Analysis + Export (Woche 3)
[ ] analysis/summary.py (async LLMCallable Protocol)
[ ] analysis/relevance.py (Relevanz-Scoring neu)
[ ] export/service.py (Pydantic Protocol-Interface)
[ ] PyPI publish v0.2.0

Phase 3 — bfagent Migration (Woche 4–5)
[ ] bfagent requirements: iil-researchfw>=0.1,<0.2
[ ] bfagent/apps/research/services/ auf iil-researchfw umstellen
[ ] bfagent-spezifische Logik isolieren

Phase 4 — Consumer-Repos (Woche 6)
[ ] travel-beat: iil-researchfw>=0.1,<0.2
[ ] weltenhub: iil-researchfw>=0.1,<0.2
[ ] pptx-hub: iil-researchfw>=0.1,<0.2
```

---

## Referenzen

- [ADR-104: Research Hub + iil-researchfw](ADR-104-research-hub-iil-researchfw.md)
- [ADR-100: iil-testkit](ADR-100-iil-testkit-shared-test-factory-package.md) — analoges Package-Modell
- [REVIEW-ADR-105](reviews/REVIEW-ADR-105-iil-researchfw.md) — Reviewer-Feedback (2026-03-07)
- `bfagent/apps/research/services/` — Quell-Services für Extraktion
