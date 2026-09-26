---
id: ADR-305
title: "rag-mcp als einzige API und Collection-Namenskonvention {repo}:{domain}"
status: accepted
decision_date: 2026-05-07
amended: 2026-09-16
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [Repo-Owner risk-hub, meiki-hub, bfagent, coach-hub, weltenhub]
supersedes: []
amends: []
related: [ADR-188, ADR-172, ADR-075, ADR-303, ADR-304, ADR-306]
repo: platform
implementation_status: partial
last_reviewed: 2026-09-16
staleness_months: 6
drift_check_paths:
  - mcp-hub/rag_mcp/
---

# ADR-305: rag-mcp als einzige API und Collection-Namenskonvention `{repo}:{domain}`

> **Herkunft:** Herausgelöst aus ADR-188 (Unified Vector Store) am 2026-09-16 —
> Owner-Entscheid „smallest-viable cut“ zu [#169](https://github.com/achimdehnert/platform/issues/169):
> sieben Entscheidungen in einem ADR, 426 Zeilen, drei Entscheidungsverben im Titel.
> Der Beschluss stammt vom 2026-05-07 (ADR-188 v1.0/v1.1) und ist **unverändert**;
> neu ist nur der Schnitt. ADR-188 bleibt das Hub-Dokument mit Kontext, Treibern,
> Alternativen, Phasen und Konsequenzen — dort steht das *Warum*, hier das *Was*.

## Entscheidung

### E3: Eine API — rag-mcp als Single Access Point

```
Consumer-Repos                   rag-mcp (ADR-172)              pgvector (ADR-171)
┌─────────────┐                ┌──────────────────┐           ┌──────────────┐
│ meiki-hub   │──rag_ingest───▶│                  │──INSERT──▶│ rag_chunks   │
│ risk-hub    │──rag_search───▶│  Tools (MCP)     │──SELECT──▶│ rag_documents│
│ bfagent     │──rag_supersede▶│  Services        │──UPDATE──▶│ rag_collects │
│ weltenhub   │──rag_history──▶│  Celery Worker   │           │              │
│ platform    │──rag_list─────▶│  Embedder Svc    │           │ mcp_hub_db   │
└─────────────┘                └──────────────────┘           └──────────────┘
```

**Kein Consumer greift direkt auf die DB zu.** Auch Django-Repos nutzen rag-mcp Tools.

> **ADR-075 Abgrenzung:** `rag_ingest` und `rag_supersede` sind **Daten-Operationen** (vergleichbar mit DB-INSERT), keine Deployment-/Infrastruktur-Operationen. ADR-075 Write-Op-Restriktion betrifft nur infrastrukturelle Aktionen (migrate, deploy, backup). Daten-CRUD via MCP ist explizit erlaubt.

### E4: Collection-Namenskonvention (platform-weit)

| Repo | Collection | Dokumenttyp | Chunking-Strategie |
|------|-----------|-------------|-------------------|
| `meiki-hub` | `meiki:gesetze` | Bayerische Gesetze | `paragraph` (§/Art.) |
| `meiki-hub` | `meiki:avos` | Ausführungsverordnungen | `paragraph` |
| `meiki-hub` | `meiki:fallakten` | Gescannte Fallakten-Docs | `sliding` |
| `risk-hub` | `risk:sds` | Sicherheitsdatenblätter | `sliding` |
| `risk-hub` | `risk:exdoc` | Ex-Schutz-Dokumente | `semantic` (Markdown) |
| `risk-hub` | `risk:gbu` | Gefährdungsbeurteilungen | `semantic` |
| `risk-hub` | `risk:bibliothek` | Allgemeine Dokumente (Normen etc.) | `sliding` |
| `bfagent` | `bfagent:stories` | Kapitel, Szenen | `sliding` |
| `weltenhub` | `welten:lore` | Weltenbau-Dokumente | `sliding` |
| `coach-hub` | `coach:materials` | Coaching-Materialien | `sliding` |
| `platform` | `platform:adrs` | Architecture Decision Records | `semantic` |
| `platform` | `platform:docs` | Workflows, Runbooks | `semantic` |

**Naming:** `{repo_prefix}:{domain}` — eindeutig, sortierbar, filterbar.

## Konsequenzen

- Consumer kennen genau eine API; Schema-Wechsel (ADR-303) bleiben hinter rag-mcp verborgen.
- Neue Collections tragen den Präfix des Repos; die Tabelle oben ist der Ausgangsbestand, keine geschlossene Liste — Ergänzungen sind Register-Pflege, keine ADR-Änderung.
- SPOF `mcp_hub_db`: Backup + Graceful Degradation (FTS-only) laut ADR-188 §4.

## Referenzen

ADR-188 (Hub) · ADR-172 (rag-mcp Server) · ADR-075 (Abgrenzung Daten-Operation vs. Infrastruktur)
