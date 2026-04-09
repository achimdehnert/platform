# ADR-160: LLM-Powered Research Pipeline — Von Keyword-Suche zu intelligenter Literaturrecherche

- **Status:** proposed
- **Date:** 2026-04-09
- **Deciders:** Achim Dehnert, Cascade
- **Scope:** iil-researchfw (Package), Consumers: writing-hub, research-hub

## Context and Problem Statement

Wenn ein Nutzer bei Claude.ai eine Literaturrecherche anfordert ("Recherchiere zum Thema Klimawandel und Landwirtschaft"), erhält er hochwertige, relevante Ergebnisse. Unsere aktuelle `researchfw`-Pipeline liefert deutlich schlechtere Ergebnisse — trotz Zugriff auf dieselben akademischen Quellen (Semantic Scholar, arXiv, PubMed, OpenAlex).

### Ist-Zustand (researchfw v0.4.1)

```
User-Query → 1:1 an 4 APIs → Keyword-Dedup → Keyword-Relevanz → LLM-Summary
```

| Schritt | Methode | Problem |
|---------|---------|---------|
| Query | Roher User-Text | Keine Synonyme, keine Fachbegriffe, keine Schlüsselforscher |
| Suche | 1× Single-Shot | Keine Lückenanalyse, kein Nachsuchen |
| Relevanz | Token-Overlap | Falsche Positiv-/Negativrate hoch |
| Synthese | LLM-Summary | Keine Themen-Extraktion, keine Widersprüche |

### Soll-Zustand (Claude.ai-Qualität)

```
User-Query → LLM-Query-Expansion → Multi-Round Search → LLM-Relevanz → Synthese
```

## Decision Drivers

1. **Ergebnisqualität**: Nutzer sollen relevante Schlüsselwerke finden, nicht nur Keyword-Treffer
2. **Token-Kosten**: Jeder LLM-Call kostet Geld — Balance zwischen Qualität und Kosten
3. **Latenz**: Literaturrecherche darf 30-60s dauern, aber nicht 5 Minuten
4. **Framework-Agnostik**: researchfw bleibt LLM-agnostisch (Protocol-basiert, kein OpenAI-Lock-in)
5. **Abwärtskompatibilität**: Bestehende Consumer (writing-hub) müssen ohne Änderung funktionieren

## Considered Options

### Option A: LLM-Query-Expansion Only (Minimal)

Nur die Query-Generierung wird LLM-gesteuert. Rest bleibt wie bisher.

```python
class SmartSearchService:
    async def search(self, topic: str, llm_fn: LLMCallable) -> list[AcademicPaper]:
        queries = await self._expand_query(topic, llm_fn)  # 1 LLM-Call
        papers = await self._search_all(queries)            # N×4 API-Calls
        return self._deduplicate(papers)
```

- **Pro:** +1 LLM-Call, ~500 Token, ~0.001$ pro Suche
- **Pro:** Größter einzelner Hebel (bessere Queries → bessere Ergebnisse)
- **Con:** Keine intelligente Filterung, kein iteratives Nachsuchen

### Option B: Query-Expansion + LLM-Relevanz-Scoring (Empfohlen)

Query-Expansion + LLM bewertet jedes Paper auf Relevanz.

```python
class SmartSearchService:
    async def search(self, topic: str, llm_fn: LLMCallable) -> list[AcademicPaper]:
        queries = await self._expand_query(topic, llm_fn)       # 1 LLM-Call
        papers = await self._search_all(queries)                 # N×4 API-Calls
        papers = self._deduplicate(papers)
        scored = await self._score_relevance(papers, topic, llm_fn)  # 1-2 LLM-Calls (batch)
        return [p for p in scored if p.relevance_score >= 7]
```

- **Pro:** Eliminiert False Positives, nur wirklich relevante Papers bleiben
- **Pro:** 2-3 LLM-Calls, ~2000 Token, ~0.005$ pro Suche
- **Con:** Kein iteratives Nachsuchen

### Option C: Full Pipeline — Query-Expansion + LLM-Relevanz + Iterative Search

Volle Claude.ai-Qualität: Multi-Round mit Gap-Analyse.

```python
class SmartSearchService:
    async def search(self, topic: str, llm_fn: LLMCallable, rounds: int = 2) -> list[AcademicPaper]:
        queries = await self._expand_query(topic, llm_fn)            # 1 LLM-Call
        papers = await self._search_all(queries)                      # N×4 API-Calls
        papers = self._deduplicate(papers)
        scored = await self._score_relevance(papers, topic, llm_fn)   # 1-2 LLM-Calls
        top_papers = [p for p in scored if p.relevance_score >= 7]

        for _ in range(rounds - 1):
            gaps = await self._analyze_gaps(top_papers, topic, llm_fn)  # 1 LLM-Call
            if not gaps:
                break
            new_queries = await self._expand_query(gaps, llm_fn)        # 1 LLM-Call
            new_papers = await self._search_all(new_queries)
            new_scored = await self._score_relevance(new_papers, topic, llm_fn)
            top_papers = self._merge(top_papers, new_scored)

        return top_papers
```

- **Pro:** Beste Ergebnisqualität, findet Lücken und Schlüsselwerke
- **Pro:** Findet Aspekte die dem Nutzer nicht einfallen
- **Con:** 5-7 LLM-Calls, ~5000 Token, ~0.015$ pro Suche
- **Con:** 30-60s Latenz (akzeptabel für Literaturrecherche)
- **Con:** Höhere Komplexität, mehr Fehlerquellen

### Option D: Citation Graph Expansion (Ergänzung)

Zusätzlich zu B oder C: Nutze Semantic Scholar Citation Graph.

```python
async def _expand_via_citations(self, top_papers: list[AcademicPaper]) -> list[AcademicPaper]:
    """Find seminal works by following citation graph."""
    for paper in top_papers[:5]:
        references = await self._get_references(paper.doi or paper.url)
        citing = await self._get_citing_papers(paper.doi or paper.url)
    # → Findet die "Klassiker" die alle Top-Papers zitieren
```

- **Pro:** Findet Schlüsselwerke die Keyword-Suche nicht findet
- **Con:** Zusätzliche API-Calls, erhöht Latenz um 5-10s
- **Con:** Nur für Semantic Scholar verfügbar

## Decision

**Option B (Query-Expansion + LLM-Relevanz-Scoring)** als Basis, mit **Option D (Citation Graph)** als optionalem Add-on.

### Begründung

1. **80/20-Regel**: Query-Expansion + Relevanz-Scoring liefern ~80% der Qualitätsverbesserung bei ~20% der Komplexität von Option C
2. **Kosten**: ~0.005$ pro Suche ist akzeptabel (writing-hub: ~5-10 Recherchen pro Essay = 0.05$)
3. **Iterative Search (Option C)** kann in v2 nachgerüstet werden — die API ist abwärtskompatibel
4. **Citation Graph (Option D)** als `expand_citations=True` Parameter — opt-in, kein Default

### Architektur

```
┌─────────────────────────────────────────────────────┐
│                  SmartSearchService                  │
│                                                     │
│  topic ──→ [LLM Query Expansion] ──→ 3-5 Queries   │
│                     │                               │
│                     ▼                               │
│            [AcademicSearchService]                   │
│            arXiv │ S2 │ PubMed │ OpenAlex           │
│                     │                               │
│                     ▼                               │
│            [Fuzzy Dedup + Merge]                     │
│                     │                               │
│                     ▼                               │
│          [LLM Relevance Scoring]                    │
│          Batch: 10-20 Papers → Score 0-10           │
│                     │                               │
│                     ▼                               │
│          [Filter: score ≥ 7] ──→ Top Papers         │
│                     │                               │
│                     ▼ (optional)                    │
│          [Citation Graph Expansion]                  │
│                     │                               │
│                     ▼                               │
│          [Final Ranking + Output]                    │
└─────────────────────────────────────────────────────┘
```

### API-Design

```python
# Abwärtskompatibel: bestehende AcademicSearchService bleibt unverändert
# SmartSearchService ist ein neuer High-Level-Service

class SmartSearchService:
    def __init__(
        self,
        llm_fn: LLMCallable,
        academic_service: AcademicSearchService | None = None,
        expand_citations: bool = False,
        relevance_threshold: float = 7.0,
        max_queries: int = 5,
    ) -> None: ...

    async def search(self, topic: str, max_results: int = 20) -> SmartSearchResult: ...

@dataclass
class SmartSearchResult:
    papers: list[ScoredPaper]
    queries_used: list[str]
    total_found: int
    total_after_filter: int
    search_duration_seconds: float

@dataclass
class ScoredPaper(AcademicPaper):
    relevance_score: float = 0.0
    relevance_reason: str = ""
```

### LLM-Prompts (Kern-Design)

**Query-Expansion Prompt:**
```
Given the research topic: "{topic}"

Generate 3-5 academic search queries that would find the most relevant papers.
Include:
- Synonyms and alternative phrasings
- Key technical terms in the field
- Names of prominent researchers (if known)
- Both broad and specific queries

Return as JSON: {"queries": ["query1", "query2", ...]}
```

**Relevance-Scoring Prompt:**
```
Research topic: "{topic}"

Rate each paper's relevance (0-10) and explain briefly:
{papers_json}

Return as JSON: [{"index": 0, "score": 8, "reason": "Directly addresses..."}, ...]
```

## Consequences

### Positive
- **Deutlich bessere Ergebnisqualität** — vergleichbar mit Claude.ai-Recherche
- **Abwärtskompatibel** — `AcademicSearchService` bleibt unverändert
- **LLM-agnostisch** — nutzt bestehendes `LLMCallable` Protocol
- **Kosten kontrollierbar** — ~0.005$ pro Suche, konfigurierbar

### Negative
- **LLM-Abhängigkeit** — ohne LLM-Funktion fällt SmartSearch auf Keyword-Search zurück
- **Prompt-Engineering** — Qualität hängt von Prompt-Design ab (iterativ verbessern)
- **Zusätzliche Latenz** — ~5-10s durch LLM-Calls (akzeptabel für Research-Kontext)

### Neutral
- **Token-Kosten** — ~2000 Token pro Suche bei Option B, ~5000 bei späterer Option C
- **Testbarkeit** — LLM-Calls können in Tests gemockt werden (LLMCallable Protocol)

## Implementation Plan

| Phase | Was | Aufwand |
|-------|-----|---------|
| Phase 1 | `SmartSearchService` mit Query-Expansion | 30 min |
| Phase 2 | LLM-Relevanz-Scoring (Batch) | 30 min |
| Phase 3 | Integration in writing-hub `citation_service.py` | 15 min |
| Phase 4 | Tests + Docs | 15 min |
| Phase 5 (optional) | Citation Graph Expansion | 30 min |
| Phase 6 (v2) | Iterative Search mit Gap-Analyse | 45 min |

## Related

- researchfw v0.4.1 — aktuelle Version mit Fuzzy Dedup + LRU Cache
- writing-hub `apps/projects/services/citation_service.py` — Haupt-Consumer
- `LLMCallable` Protocol in `iil_researchfw/core/protocols.py`
