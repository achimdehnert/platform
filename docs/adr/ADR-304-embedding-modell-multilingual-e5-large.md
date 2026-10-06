---
id: ADR-304
title: "Embedding-Modell: multilingual-e5-large als Primärmodell"
status: accepted
decision_date: 2026-05-07
amended: 2026-09-16
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [Repo-Owner risk-hub, meiki-hub, bfagent, coach-hub, weltenhub]
supersedes: []
amends: []
related: [ADR-188, ADR-303, ADR-305, ADR-306, ADR-171]
repo: platform
implementation_status: implemented
last_reviewed: 2026-09-16
staleness_months: 6
drift_check_paths:
  - mcp-hub/rag_mcp/embedder.py
---

# ADR-304: Embedding-Modell — `multilingual-e5-large` als Primärmodell

> **Herkunft:** Herausgelöst aus ADR-188 (Unified Vector Store) am 2026-09-16 —
> Owner-Entscheid „smallest-viable cut“ zu [#169](https://github.com/achimdehnert/platform/issues/169):
> sieben Entscheidungen in einem ADR, 426 Zeilen, drei Entscheidungsverben im Titel.
> Der Beschluss stammt vom 2026-05-07 (ADR-188 v1.0/v1.1) und ist **unverändert**;
> neu ist nur der Schnitt. ADR-188 bleibt das Hub-Dokument mit Kontext, Treibern,
> Alternativen, Phasen und Konsequenzen — dort steht das *Warum*, hier das *Was*.

## Entscheidung

### E2: Ein Embedding-Modell — multilingual-e5-large (Primär)

| Kriterium | multilingual-e5-large | text-embedding-3-small |
|-----------|----------------------|----------------------|
| **Kosten** | ✅ Open Source, lokal | ❌ $0.02/1M Tokens |
| **Offline** | ✅ | ❌ |
| **Deutsch** | ✅ Exzellent | ✅ Gut |
| **Dimensionen** | 1024 | 1536 |
| **Vendor Lock-in** | ✅ Keiner | ❌ OpenAI-Abhängigkeit |
| **Latenz** | ⚠️ ~50ms/Chunk (CPU) | ✅ ~10ms/Chunk (API) |
| **DSGVO** | ✅ Daten bleiben lokal | ⚠️ Daten an OpenAI |
| **RAM** | ⚠️ ~3 GB (Model + Runtime) | ✅ Kein lokaler RAM |

**Entscheidung:** `multilingual-e5-large` (1024 Dimensionen) als **Primärmodell**. OpenAI als **optionaler Fallback** nur für Collections ohne DSGVO-Restriktion (siehe E7).

> **Wichtig:** E5-Modelle erfordern Prefix `"query: "` bei Search-Queries und `"passage: "` bei Ingest-Texten für optimale Retrieval-Qualität. Ohne Prefix: ~15% Recall-Verlust. Die rag-mcp API setzt diese Prefixes automatisch.

#### E2-Nachtrag 2026-08-31: der Latenz-Vorbehalt ist eingelöst

Die Tabelle oben führt die Latenz als den einen Nachteil des lokalen Modells
(`⚠️ ~50ms/Chunk (CPU)`), und der Spike auf Hetzner-CPU bestätigte das mit
**114 ms p50** — Budget knapp gerissen, damals als „für UX akzeptabel" abgehakt.

Am 2026-08-31 lief **derselbe Spike, unverändert, mit derselben `benchmark.py`**
auf dem GX10 (NVIDIA GB10, aarch64, `torch 2.13.0+cu130`, Modell auf `cuda:0`):

| Messwert | Hetzner CPX (CPU) | GX10 (GB10) | Budget |
|---|---|---|---|
| Latenz p50 | 114 ms | **9,0 ms** | ≤ 100 ms |
| Durchsatz (batch=50) | 57 chunks/s | **681,6 chunks/s** | — |
| RAM | 2.019 MB | **1.239 MB** | ≤ 3.000 MB |
| Recall@1 (deutsche Rechtstexte) | 5/5 | **5/5** | ≥ 80 % |

**Was das an der Entscheidung ändert: nichts — es räumt ihren einzigen Einwand ab.**
Die Latenz-Zeile der Tabelle vergleicht 50 ms lokal gegen ~10 ms API; auf dem GX10
ist das lokale Modell mit 9,0 ms **schneller als der API-Wert** und die Daten bleiben
im Haus.

**Warum es ein Nachtrag und keine neue Entscheidung ist:** Modell und Dimensionen
bleiben gleich (`multilingual-e5-large`, 1024). `rag_mcp/embedder.py` spricht den
Dienst über `RAG_MCP_EMBEDDER_URL` an — ein Ortswechsel ist eine Umgebungsvariable,
keine Neuberechnung des Vektorbestands.

**Offen und ausdrücklich nicht mitentschieden:** ob der Dienst dorthin *umzieht*.
Der GX10 ist Owner-Hardware außerhalb des Bürgerdaten-Perimeters
(`platform:KONZ-platform-053` §4) — für Collections mit Sozial- oder Bürgerdaten
kommt er nicht in Frage, gleich wie schnell er ist. Gemessen wurde ein Einzeldienst
ohne Nebenlast.

## Konsequenzen

- Kein laufender API-Verbrauch für Embeddings, Daten bleiben im Haus, Cross-Repo-Suche perspektivisch möglich (ein Modell für alle).
- Embedder-Dienst als eigener Container (~3 GB RAM auf CPU; 1,2 GB auf GX10); Batch-Ingest über Celery, nicht request-kritisch.
- Ob Collections mit Bürger- oder Sozialdaten den Dienst je auf Owner-Hardware nutzen dürfen, entscheidet der Datenperimeter (KONZ-platform-053 §4), nicht die Latenz.

## Referenzen

ADR-188 (Hub, Implementierungs-Evidenz des Spikes im Frontmatter) · ADR-306 (wann ein Cloud-Fallback erlaubt ist)
