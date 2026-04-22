# ADR-169: Enrichment Agent Pattern — Managed Record + External Knowledge

| Metadata    | Value                                           |
|-------------|-------------------------------------------------|
| Status      | Proposed                                        |
| Date        | 2026-04-22                                      |
| Driver      | SDS content gap (risk-hub #9), generalisierbar  |
| Scope       | Platform-wide (iil-enrichment package)          |
| Related     | ADR-012 (SDS Library), ADR-041 (Service Layer)  |

## Context and Problem Statement

Across the IIL Platform, document-centric modules store structured records with
version management, compliance workflows, and audit trails. However, these
**Managed Records** contain only a fraction of the available knowledge.

**Concrete example — risk-hub SDS:**

| Aspect         | `/sds/` (SDS Library)            | `/substances/lookup/` (Research DB) |
|----------------|----------------------------------|-------------------------------------|
| Source          | PDF upload → Regex parser        | GESTIS + PubChem + ECHA APIs        |
| Coverage        | ~15% of SDS content              | ~90% of substance knowledge         |
| Stores          | H/P codes, 4 phys. values       | AGW, first aid, storage, transport, regulations, density, boiling point, … |
| Versioning      | ✅ SHA-256, supersession, diffs  | ❌ Transient (not persisted)        |

The same pattern recurs in other hubs:

| Hub               | Managed Record        | Missing External Knowledge              |
|-------------------|-----------------------|-----------------------------------------|
| risk-hub (GBU)    | HazardAssessment      | TRGS 400/500 measure catalogs           |
| ausschreibungs-hub| Tender document       | TED/DTVP context, reference prices      |
| cad-hub           | CAD drawing           | Material databases, DIN standards       |
| trading-hub       | Trade/Position        | Market data APIs, fundamentals          |
| travel-beat       | Trip                  | Weather, safety advisories              |

## Decision

Introduce a generic **Enrichment Agent Pattern** as `iil-enrichment` PyPI
package with a Provider Registry, Django Mixin, and hybrid storage architecture.

### Core Abstractions

```python
# iil-enrichment/enrichment/provider.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


class EnrichmentProvider(Protocol):
    """External knowledge source."""
    name: str
    supported_domains: list[str]

    def can_enrich(self, domain: str, natural_key: str) -> bool: ...
    def enrich(self, domain: str, natural_key: str) -> EnrichmentResult: ...


@dataclass(frozen=True)
class PropertyValue:
    """Single enrichment property."""
    value: str | float | bool
    unit: str = ""
    section: str = ""          # e.g. SDS section "9.1"
    value_type: str = "text"   # numeric, text, boolean, range


@dataclass(frozen=True)
class EnrichmentResult:
    """Result from one provider."""
    source: str
    confidence: float
    properties: dict[str, PropertyValue] = field(default_factory=dict)
    raw_sections: dict[str, str] = field(default_factory=dict)
    enriched_at: datetime = field(default_factory=datetime.now)
```

### Registry

```python
# iil-enrichment/enrichment/registry.py
class EnrichmentRegistry:
    """Central registry of providers per domain."""

    def register(self, domain: str, provider: EnrichmentProvider) -> None: ...

    def enrich(
        self, domain: str, natural_key: str
    ) -> list[EnrichmentResult]:
        """Run all registered providers for domain, return merged results."""
        ...
```

### Django Mixin

```python
# iil-enrichment/enrichment/django/mixins.py
class EnrichableModelMixin(models.Model):
    """Add to any model that can be enriched from external sources."""
    enrichment_data = models.JSONField(default=dict, blank=True)
    enrichment_sources = models.JSONField(default=list, blank=True)
    last_enriched_at = models.DateTimeField(null=True, blank=True)
    enrichment_confidence = models.FloatField(null=True, blank=True)

    class Meta:
        abstract = True

    def get_natural_key_for_enrichment(self) -> str:
        raise NotImplementedError

    def get_enrichment_domain(self) -> str:
        raise NotImplementedError
```

### Hybrid Storage Architecture

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Structured Store (PostgreSQL)          │
│  ─────────────────────────────────────────       │
│  EAV (SdsRevisionProperty) or JSONB              │
│  → Display, filter, export, compliance           │
│  → WHERE flash_point_c > 21                      │
├─────────────────────────────────────────────────┤
│  Layer 2: Raw Text Store (PostgreSQL Text)       │
│  ─────────────────────────────────────────       │
│  raw_text / enrichment_data.raw_sections (JSONB) │
│  → Audit trail, fulltext search, LLM input       │
├─────────────────────────────────────────────────┤
│  Layer 3: Vector Store (pgvector) — Phase 2+     │
│  ─────────────────────────────────────────       │
│  EnrichmentEmbedding (generic via ContentType)   │
│  → Semantic search, identity resolution, RAG     │
│  → "Is 'Ethanol azeotrop' = 'Ethylalkohol'?"    │
└─────────────────────────────────────────────────┘
```

**Phase 1** uses only Layer 1+2 (PostgreSQL). **Phase 2+** adds pgvector for
semantic matching and RAG-based extraction.

### SDS as Pilot Implementation

risk-hub already has the required infrastructure:

- `SdsPropertyDefinition` + `SdsRevisionProperty` → EAV store (Layer 1)
- `SdsRevisionProperty.raw_text` → audit trail (Layer 2)
- `SdsEnrichmentService` → skeleton in upload pipeline
- `SubstanceLookupService` → working GESTIS + PubChem client

Bridge: Extract GESTIS/PubChem logic into `iil-enrichment` providers,
call from `SdsUploadPipeline._create_revision()`, persist into existing
`SdsRevisionProperty` records.

## Rollout

| Phase | Scope                                           | Timeline   |
|-------|-------------------------------------------------|------------|
| 0     | ADR + package skeleton (`iil-enrichment`)       | Now        |
| 1     | GESTIS + PubChem providers, SDS pilot (risk-hub)| Sprint 1   |
| 2     | pgvector identity resolution, trading-hub       | Sprint 2-3 |
| 3     | LLM provider (PDF→structured via `aifw`)        | Sprint 3+  |

## Consequences

### Positive

- **DRY:** Shared enrichment logic across all hubs
- **Extensible:** New providers (APIs, LLM) plug in without model changes
- **Audit:** Raw text preserved for compliance verification
- **Testable:** Providers are pure functions, mockable in tests

### Negative

- **New package** to maintain (`iil-enrichment`)
- **External API dependency** (rate limits, availability)
- **pgvector** adds operational complexity in Phase 2+

### Risks

- GESTIS API key may be revoked (mitigation: caching + fallback to PubChem)
- Enrichment data may conflict with parser data (mitigation: confidence scoring,
  parser data wins on conflict)
- pgvector DB availability (known issue on orchestrator, port 15435)

## Compliance

- Enrichment sources logged per record (audit trail)
- Raw text preserved for regulatory review
- Confidence scores enable human review of low-confidence enrichments
- No external API calls for read-only display (data persisted at upload time)
