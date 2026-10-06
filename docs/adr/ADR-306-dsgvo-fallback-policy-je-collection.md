---
id: ADR-306
title: "DSGVO-Fallback-Policy je Collection: Cloud-Embedding nur mit allow_cloud"
status: accepted
decision_date: 2026-05-07
amended: 2026-09-16
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [Repo-Owner risk-hub, meiki-hub, bfagent, coach-hub, weltenhub]
supersedes: []
amends: []
related: [ADR-188, ADR-304, ADR-305, ADR-303]
repo: platform
implementation_status: partial
last_reviewed: 2026-09-16
staleness_months: 6
drift_check_paths:
  - mcp-hub/rag_mcp/embedder.py
---

# ADR-306: DSGVO-Fallback-Policy je Collection — Cloud-Embedding nur mit `allow_cloud`

> **Herkunft:** Herausgelöst aus ADR-188 (Unified Vector Store) am 2026-09-16 —
> Owner-Entscheid „smallest-viable cut“ zu [#169](https://github.com/achimdehnert/platform/issues/169):
> sieben Entscheidungen in einem ADR, 426 Zeilen, drei Entscheidungsverben im Titel.
> Der Beschluss stammt vom 2026-05-07 (ADR-188 v1.0/v1.1) und ist **unverändert**;
> neu ist nur der Schnitt. ADR-188 bleibt das Hub-Dokument mit Kontext, Treibern,
> Alternativen, Phasen und Konsequenzen — dort steht das *Warum*, hier das *Was*.

## Entscheidung

### E7: DSGVO-Fallback-Policy (collection-spezifisch)

Der OpenAI-Fallback darf **NICHT automatisch** für alle Collections greifen. Policy pro Collection:

```python
EMBEDDING_POLICY = {
    # DSGVO-kritisch: NUR lokales Embedding. Bei Embedder-Ausfall → Fehler, kein Fallback.
    "meiki:fallakten": {"allow_cloud": False},
    "meiki:gesetze":   {"allow_cloud": False},   # Amtliche Werke = unkritisch, aber lokal bevorzugt
    "risk:sds":        {"allow_cloud": False},    # Betriebsgeheimnisse
    "risk:gbu":        {"allow_cloud": False},

    # Unkritisch: Cloud-Fallback erlaubt wenn lokaler Embedder unavailable.
    "bfagent:stories": {"allow_cloud": True},
    "welten:lore":     {"allow_cloud": True},
    "platform:adrs":   {"allow_cloud": True},
    "coach:materials":  {"allow_cloud": True},
}
```

**Verhalten bei Embedder-Ausfall:**
- `allow_cloud: False` → `EmbeddingUnavailableError` → Ingest schlägt fehl, Search degradiert auf FTS-only
- `allow_cloud: True` → Transparenter Fallback auf OpenAI API

## Konsequenzen

- Für DSGVO-kritische Collections gibt es **keinen** stillen Ausweg auf eine Cloud-API: Embedder-Ausfall heißt Ingest-Fehler, Suche degradiert auf Volltext.
- Die Policy ist Code (`EMBEDDING_POLICY`), Änderungen laufen über Review; wer eine Collection auf `allow_cloud: True` stellt, entscheidet über den Datenperimeter dieser Collection.
- Neue Collections ohne Eintrag: die sichere Vorgabe ist `allow_cloud: False`.

## Referenzen

ADR-188 (Hub, Treiber D-2 DSGVO) · ADR-304 (Primärmodell) · ADR-305 (Collection-Namen)
