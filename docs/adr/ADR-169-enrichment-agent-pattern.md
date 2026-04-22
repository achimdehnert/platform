---
status: Proposed
date: 2026-04-22
amended: 2026-04-22
decision-makers: Achim Dehnert
implementation_status: partial
implementation_evidence:
  - "iil-enrichment v0.1.0 package skeleton: github.com/achimdehnert/iil-enrichment (18/18 tests)"
consulted: []
informed: []
<!-- Drift-Detector-Felder
staleness_months: 6
drift_check_paths:
  - iil-enrichment/enrichment/provider.py
  - iil-enrichment/enrichment/registry.py
  - risk-hub/src/global_sds/services/upload_pipeline.py
supersedes_check: null
-->
---

# ADR-169: Adopt iil-enrichment as generic pattern for bridging managed records with external knowledge sources

## Context and Problem Statement

Across the IIL Platform, document-centric modules store structured records with
version management, compliance workflows, and audit trails. However, these
**Managed Records** contain only a fraction of the available knowledge.
External authoritative sources hold significantly richer data that is not
systematically captured.

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

## Decision Drivers

- **Data completeness gap:** SDS parser extracts ~15%, GESTIS provides ~90% — users see incomplete records
- **DRY violation:** Each hub builds its own ad-hoc enrichment logic (or none at all)
- **Regulatory pressure:** SDS data must be complete per EU-REACH Art. 31; incomplete data = compliance risk
- **Existing infrastructure:** risk-hub already has `SubstanceLookupService` (GESTIS + PubChem) and EAV schema (`SdsRevisionProperty`)
- **Testability:** Enrichment logic must be mockable and provider-independent for CI
- **Audit trail:** Enrichment sources and raw text must be traceable for regulatory review

## Considered Options

1. **Hub-specific enrichment services** — each hub implements its own enrichment in `services.py`
2. **Shared Django app** — `iil-enrichment` as a Django app installed via `INSTALLED_APPS`
3. **Generic PyPI package with Provider Protocol** — `iil-enrichment` as pure Python core + optional Django mixin
4. **Do nothing** — keep manual lookup via `/substances/lookup/` separate from SDS library

## Decision Outcome

**Chosen option: 3 — Generic PyPI package with Provider Protocol**, because:

- Pure Python core has **zero Django dependency** — usable in CLI tools, Celery workers, and non-Django contexts
- Provider Protocol enables **compile-time-checkable** contracts (`runtime_checkable`)
- Optional Django mixin keeps **framework coupling opt-in** (`pip install iil-enrichment[django]`)
- Registry pattern enables **runtime provider discovery** without import-time side effects
- Aligns with existing `iil-*` package conventions (`iil-aifw`, `iil-promptfw`, `iil-reflex`)

### Core Abstractions

```python
# enrichment/provider.py
class EnrichmentProvider(Protocol):
    """External knowledge source — the contract every provider implements."""
    name: str
    supported_domains: list[str]
    def can_enrich(self, domain: str, natural_key: str) -> bool: ...
    def enrich(self, domain: str, natural_key: str) -> EnrichmentResult: ...

# enrichment/types.py
@dataclass(frozen=True)
class PropertyValue:
    value: str | float | bool
    unit: str = ""
    section: str = ""           # e.g. SDS section "9.1"
    value_type: str = "text"    # numeric, text, boolean, range, enum
    note: str = ""

@dataclass(frozen=True)
class EnrichmentResult:
    source: str
    confidence: float           # 0.0–1.0
    properties: dict[str, PropertyValue]
    raw_sections: dict[str, str]  # original text per section (audit)
    natural_key: str = ""
```

### Registry (domain-based dispatch)

```python
# enrichment/registry.py
class EnrichmentRegistry:
    def register(self, domain: str, provider: EnrichmentProvider) -> None: ...
    def enrich(self, domain: str, natural_key: str) -> list[EnrichmentResult]: ...
    def enrich_merged(self, domain: str, natural_key: str) -> EnrichmentResult:
        """Run all providers, merge results (first provider wins on conflict)."""
```

### Django Mixin (optional)

```python
# enrichment/django/mixins.py
class EnrichableModelMixin(models.Model):
    enrichment_data = models.JSONField(default=dict, blank=True)
    enrichment_sources = models.JSONField(default=list, blank=True)
    last_enriched_at = models.DateTimeField(null=True, blank=True)
    enrichment_confidence = models.FloatField(null=True, blank=True)

    class Meta:
        abstract = True

    def get_natural_key_for_enrichment(self) -> str: ...  # e.g. CAS number
    def get_enrichment_domain(self) -> str: ...            # e.g. "substance"
    def run_enrichment(self, registry=None, save=True) -> EnrichmentResult: ...
```

### Hybrid Storage Architecture

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Structured Store (PostgreSQL)          │
│  EAV (SdsRevisionProperty) or JSONB mixin       │
│  → Display, filter, export, compliance           │
│  → WHERE flash_point_c > 21                      │
├─────────────────────────────────────────────────┤
│  Layer 2: Raw Text Store (PostgreSQL Text/JSONB) │
│  raw_sections in enrichment_data                 │
│  → Audit trail, fulltext search, LLM input       │
├─────────────────────────────────────────────────┤
│  Layer 3: Vector Store (pgvector) — Phase 2+     │
│  EnrichmentEmbedding (generic via ContentType)   │
│  → Semantic search, identity resolution, RAG     │
└─────────────────────────────────────────────────┘
```

Phase 1 uses Layer 1+2 only. Phase 2+ adds pgvector (see ADR-TBD).

## Pros and Cons of the Options

### Option 1: Hub-specific enrichment services

- Good: No new package to maintain
- Good: Full control per hub, no abstraction overhead
- Bad: **DRY violation** — GESTIS/PubChem client code duplicated across hubs
- Bad: No shared testing, no consistent audit trail
- Bad: New hubs start from scratch

### Option 2: Shared Django app

- Good: Familiar Django pattern (`INSTALLED_APPS`)
- Good: Can include models, views, admin
- Bad: **Hard Django coupling** — unusable in CLI tools, Celery workers, non-Django contexts
- Bad: Migration conflicts when installed in multiple hubs with different Django versions
- Bad: Violates `iil-*` package convention (packages are framework-agnostic at core)

### Option 3: Generic PyPI package with Provider Protocol ✅

- Good: **Zero Django dependency** in core — pure Python Protocol + dataclasses
- Good: Optional Django mixin via extras (`[django]`)
- Good: Provider pattern enables **pluggable sources** without schema changes
- Good: Registry enables **runtime configuration** — different providers per environment
- Good: Frozen dataclasses ensure **immutability** — safe for concurrent enrichment
- Good: Aligns with `iil-aifw`, `iil-promptfw`, `iil-reflex` conventions
- Bad: New package to maintain
- Bad: Slight indirection vs. direct service calls

### Option 4: Do nothing

- Good: No development effort
- Bad: SDS records remain at ~15% completeness
- Bad: Users must manually cross-reference `/sds/` with `/substances/lookup/`
- Bad: Compliance gap persists (REACH Art. 31)

## SDS as Pilot Implementation

risk-hub already has the required infrastructure:

- `SdsPropertyDefinition` + `SdsRevisionProperty` → EAV store (Layer 1)
- `SdsRevisionProperty.raw_text` → audit trail (Layer 2)
- `SdsEnrichmentService` → skeleton in upload pipeline
- `SubstanceLookupService` → working GESTIS + PubChem client

**Bridge:** Extract GESTIS/PubChem logic into `iil-enrichment` providers,
call from `SdsUploadPipeline._create_revision()`, persist into existing
`SdsRevisionProperty` records.

### Migration Strategy

The `EnrichableModelMixin` adds 4 fields to existing models. All fields are
safe for Expand-Contract migration (backwards-compatible):

| Field | Type | Default | Nullable | Migration Risk |
|-------|------|---------|----------|----------------|
| `enrichment_data` | `JSONField` | `{}` | No | None (empty dict) |
| `enrichment_sources` | `JSONField` | `[]` | No | None (empty list) |
| `last_enriched_at` | `DateTimeField` | — | Yes | None (nullable) |
| `enrichment_confidence` | `FloatField` | — | Yes | None (nullable) |

Existing records remain untouched. Enrichment runs on-demand (upload) or batch.

## Rollout

| Phase | Scope | Repo | Status |
|-------|-------|------|--------|
| 0 | ADR + package skeleton (`iil-enrichment`) | platform, iil-enrichment | ✅ Done |
| 1 | GESTIS + PubChem providers, SDS pilot | risk-hub | ⬜ Pending |
| 2 | pgvector identity resolution, trading-hub | iil-enrichment, trading-hub | ⬜ Pending |
| 3 | LLM provider (PDF→structured via `aifw`) | iil-enrichment | ⬜ Pending |

## Consequences

### Good

- **DRY:** Shared enrichment logic across all hubs via single package
- **Extensible:** New providers (APIs, LLM) plug in without model changes
- **Audit:** Raw text preserved per record for compliance verification
- **Testable:** Providers are pure functions with Protocol contract, fully mockable
- **Backwards-compatible:** Mixin fields all nullable/defaulted, no data loss

### Bad

- **New package** to maintain (`iil-enrichment`) — CI, versioning, PyPI publish
- **External API dependency** — GESTIS/PubChem rate limits, availability, format changes
- **pgvector complexity** in Phase 2+ — embedding generation, index tuning, operational overhead

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| GESTIS API key revoked | Low | High | Cache results, fallback to PubChem |
| Enrichment conflicts with parser data | Medium | Medium | Confidence scoring; parser data wins on conflict |
| pgvector DB unavailable | Medium | Low | Phase 2+ only; graceful degradation to Layer 1+2 |
| Provider returns stale data | Low | Medium | `last_enriched_at` + configurable TTL for re-enrichment |
| API rate limiting | Medium | Low | Per-provider rate limiter, request caching |

### Confirmation

Compliance with this ADR is verified by:

1. **Package tests:** `iil-enrichment` CI runs `pytest` — all providers must satisfy `EnrichmentProvider` Protocol
2. **Architecture Guardian:** Rule "No direct external API calls in views/services — use EnrichmentRegistry"
3. **Enrichment audit:** Every enriched record has non-empty `enrichment_sources` and `last_enriched_at`
4. **Integration test:** SDS upload + enrichment produces ≥10 additional properties vs. parser-only

## Open Questions

1. **EAV vs. JSONB per hub:** Should hubs use the existing EAV pattern (`SdsRevisionProperty`) or the JSONB mixin? Recommendation: JSONB mixin for new hubs, EAV bridge for risk-hub (existing infrastructure).
2. **Caching strategy:** Should enrichment results be cached at provider level (TTL-based) or at registry level? Deferred to Phase 1 implementation.
3. **Rate limiting:** Per-provider rate limiter needed for GESTIS (undocumented limits). Deferred to Phase 1.
4. **Re-enrichment trigger:** When should existing records be re-enriched? Options: manual, on SDS re-upload, scheduled batch. Deferred to Phase 1.
5. **pgvector embedding model:** `text-embedding-3-small` (1536d) vs. `nomic-embed-text` (768d). Deferred to Phase 2 (see ADR-TBD for pgvector enrichment).

## Compliance

- Enrichment sources logged per record (audit trail)
- Raw text preserved for regulatory review (REACH Art. 31)
- Confidence scores enable human review of low-confidence enrichments
- No external API calls for read-only display (data persisted at upload time)
- API keys configurable via `decouple.config()` (ADR-045), never hardcoded

## More Information

- **Related ADRs:** [ADR-012](ADR-012-sds-library.md) (SDS Library), [ADR-041](ADR-041-service-layer.md) (Service Layer), [ADR-045](ADR-045-secrets-management.md) (Secrets)
- **Package:** [github.com/achimdehnert/iil-enrichment](https://github.com/achimdehnert/iil-enrichment)
- **Pilot:** risk-hub `global_sds` module — `SdsUploadPipeline` + `SubstanceLookupService`
- **New repo requires:** `catalog-info.yaml` (ADR-077) — to be added in Phase 1
