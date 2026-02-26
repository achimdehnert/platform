# Review: ADR-087 — Hybrid Search Architecture

> **Reviewer:** Platform Review (Template C — Intensive)  
> **Datum:** 2026-02-26  
> **ADR:** [ADR-087-hybrid-search-architecture.md](../ADR-087-hybrid-search-architecture.md)  
> **Status des ADR:** `Proposed`  

---

## 1. MADR 4.0 Compliance

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 1.1 | YAML frontmatter present (`status`, `date`, `decision-makers`) | ⚠️ | Blockquote-Format statt YAML frontmatter; `decision-makers` fehlt — nur `Autor` vorhanden |
| 1.2 | Title is a decision statement (not a topic) | ⚠️ | Titel beschreibt Architektur, nicht Entscheidung. Besser: "Adopt pgvector + FTS Hybrid Search as Platform-wide Semantic Search Engine" |
| 1.3 | `## Context and Problem Statement` section present | ✅ | Vorhanden als `## Kontext` — Problem klar dargestellt mit App-Tabelle und konkreten Lücken |
| 1.4 | `## Decision Drivers` section present (bullet list) | ❌ | **Fehlt komplett.** Drivers sind implizit im Kontext, aber nicht als eigene Sektion mit Bullet-Liste |
| 1.5 | `## Considered Options` section lists ≥ 3 options | ✅ | 5 Alternativen in Tabelle (Elasticsearch, SQLite+vec, nur Vector, nur FTS, ChromaDB/Pinecone) |
| 1.6 | `## Decision Outcome` states chosen option with explicit reasoning | ⚠️ | Entscheidung klar in `## Entscheidung`, aber kein explizites "Chosen Option: X, because Y" Statement |
| 1.7 | `## Pros and Cons of the Options` covers all considered options | ❌ | **Nur die verworfenen Alternativen haben Contra.** Keine Pro/Contra-Analyse pro Option — nur 1-Zeiler in Tabelle |
| 1.8 | `## Consequences` uses Good/Bad bullet format | ⚠️ | Vorhanden als Positiv/Negativ/Risiken — aber nicht im MADR Good/Bad Format mit Bullet-Prefixen |
| 1.9 | `### Confirmation` subsection explains how compliance is verified | ❌ | **Fehlt komplett.** Keine Angabe, wie verifiziert wird, ob das System korrekt implementiert ist |
| 1.10 | `## More Information` links related ADRs | ⚠️ | `## Referenzen` vorhanden, aber keine Verlinkung zu verwandten ADRs (ADR-062 Content Store, ADR-035 Tenancy) |

---

## 2. Platform Infrastructure Specifics

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 2.1 | Server IP `88.198.191.108` referenced correctly | N/A | Kein Server-Bezug im ADR |
| 2.2 | SSH access rationale | N/A | |
| 2.3 | `StrictHostKeyChecking=no` absent | N/A | |
| 2.4 | Registry `ghcr.io/achimdehnert/` used | N/A | Kein Docker-Image |
| 2.5 | `GITHUB_TOKEN` scope declared | N/A | |
| 2.6 | Secrets via `DEPLOY_*` | ⚠️ | OpenAI API Key wird benötigt (`EMBEDDING_PROVIDER=openai`) — aber Secret-Management nicht spezifiziert. Sollte auf ADR-045 verweisen |
| 2.7 | Deploy path follows `/opt/<repo>` | N/A | |
| 2.8 | Health endpoints | ❌ | **Fehlt.** Kein Health-Endpoint für den Search-Service definiert (z.B. `/api/search/healthz/` oder pgvector-Verfügbarkeitsprüfung) |
| 2.9 | Port allocation registered | N/A | Kein eigener Port |
| 2.10 | Nginx retained | N/A | |

---

## 3. CI/CD & Docker Conventions

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 3.1 | Dockerfile at `docker/app/Dockerfile` | N/A | Shared Package, kein eigener Container |
| 3.2 | `docker-compose.prod.yml` at root | N/A | |
| 3.3 | Non-root user in Dockerfile | N/A | |
| 3.4 | HEALTHCHECK nicht im Dockerfile | N/A | |
| 3.5 | Multi-stage build | N/A | |
| 3.6 | Image tags | N/A | |
| 3.7 | Compose hardening | N/A | |
| 3.8 | `env_file: .env.prod` used | N/A | |
| 3.9 | Three-stage pipeline | N/A | |
| 3.10 | Worker/Beat Healthcheck | ⚠️ | Embedding-Indexing via Celery Task erwähnt — aber kein Celery-Worker-Healthcheck definiert |

---

## 4. Database & Migration Safety

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 4.1 | Expand-Contract pattern | ⚠️ | SQL-Schema direkt definiert — aber keine Migrationsstrategie für Schema-Änderungen (z.B. Dimensions-Wechsel bei Modell-Upgrade) |
| 4.2 | `makemigrations --check` passes | N/A | Raw SQL, kein Django-Model |
| 4.3 | Migration backwards-compatible | ⚠️ | Kein Fallback definiert, wenn pgvector-Extension fehlt oder Embedding-Service unavailable |
| 4.4 | `tenant_id = UUIDField(db_index=True)` | ✅ | `tenant_id UUID NOT NULL` mit Index vorhanden |
| 4.5 | Shared DB risk assessed | ❌ | **Nicht adressiert.** Welche Datenbank? Eigene DB `platform_search` oder in jeder App-DB? Wenn shared: ADR-062 Content Store Kompatibilität prüfen |

---

## 5. Security & Secrets

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 5.1 | No secrets hardcoded | ✅ | Keine Secrets in Code-Beispielen |
| 5.2 | `.env.prod` never committed | N/A | |
| 5.3 | SOPS/ADR-045 compatibility | ❌ | **OpenAI API Key** (`OPENAI_API_KEY`) wird benötigt — kein Hinweis auf Secret-Management via ADR-045 |
| 5.4 | `DEPLOY_*` secrets org-level | N/A | |

---

## 6. Architectural Consistency

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 6.1 | Service layer pattern | ⚠️ | Code-Skizzen zeigen standalone Functions statt Service-Klasse. Platform-Standard: `SearchService` als Service-Layer |
| 6.2 | No contradiction with existing ADRs | ⚠️ | **ADR-062 (Content Store)** definiert bereits `content_store` Schema in PostgreSQL für AI-Inhalte. `search_chunks` Tabelle könnte/sollte dort integriert werden |
| 6.3 | Zero Breaking Changes | ✅ | Neues System, keine bestehende Funktionalität betroffen |
| 6.4 | ADR-054 Architecture Guardian | N/A | |
| 6.5 | Migration tracking table | ❌ | **Fehlt.** Bei Embedding-Modell-Wechsel braucht man Re-Indexing-Tracking (welche Chunks schon re-embedded sind) |

---

## 7. Open Questions & Deferred Decisions

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 7.1 | All open questions explicitly listed | ❌ | **Keine `## Open Questions` Sektion.** Offene Fragen: (a) Eigene DB oder App-DB? (b) Chunk-Größe? (c) Overlap-Strategie? (d) Re-Indexing bei Modell-Wechsel? |
| 7.2 | Deferred decisions reference future ADR | ❌ | MMR und Temporal Decay als "Optional" markiert — aber kein Kriterium wann sie aktiviert werden |
| 7.3 | Conscious decisions documented with rationale | ⚠️ | IVFFlat vs. HNSW Index-Wahl nicht diskutiert (HNSW ist für <1M rows oft besser) |

---

## 8. Modern Platform Patterns

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 8.1 | infra-deploy (ADR-075): Write-Ops via GH Actions | N/A | |
| 8.2 | MCP Deprecation-Warning | N/A | |
| 8.3 | Multi-Tenancy (ADR-072): Schema-Isolation | ❌ | **Kritisch:** ADR-072 fordert Schema-Isolation. `search_chunks` Tabelle verwendet Row-Level (`WHERE tenant_id = ...`) statt Schema-Isolation. Muss entweder begründet abweichen oder Schema-kompatibel werden |
| 8.4 | `tenant_id` Index auf Cross-Tenant-Tabellen | ✅ | `idx_chunks_tenant` vorhanden |
| 8.5 | Content Store: `async_to_sync` | N/A | |
| 8.6 | Content Store DSN als Secret | ⚠️ | ADR-062 definiert `CONTENT_STORE_DSN` — `search_chunks` sollte sich an diesem Pattern orientieren |
| 8.7 | Catalog `catalog-info.yaml` | N/A | Package, kein Repo |
| 8.8 | Drift-Detector Felder | ❌ | `<!-- Drift-Detector-Felder -->` Kommentar fehlt |
| 8.9 | Runner Labels | N/A | |
| 8.10 | Temporal Workflows | N/A | |

---

## 9. Review Scoring

| Category | Score (1–5) | Notes |
|----------|-------------|-------|
| MADR 4.0 compliance | **2** | Fehlende Decision Drivers, Confirmation, Pro/Cons pro Option |
| Platform Infrastructure Specifics | **3** | API-Key-Management und Health-Endpoint fehlen |
| CI/CD & Docker Conventions | **4** | Nicht direkt betroffen (Package) |
| Database & Migration Safety | **3** | DB-Zuordnung unklar, Migrations-Strategie fehlt |
| Security & Secrets | **3** | OpenAI API Key Management nicht adressiert |
| Architectural Consistency | **3** | ADR-062 Overlap, Service-Layer-Pattern nicht eingehalten |
| Open Questions | **2** | Keine Open-Questions-Sektion trotz vieler offener Punkte |
| Modern Platform Patterns | **2** | ADR-072 Schema-Isolation Konflikt, Drift-Detector fehlt |
| **Overall** | **2.75** | |

---

## 10. Recommendation

- [ ] **Accept** — ready to merge
- [x] **Accept with changes** — minor fixes required (list below)
- [ ] **Reject** — fundamental issues (list below)

### Required changes

1. **[CRITICAL] ADR-072 Kompatibilität klären**: Row-Level `tenant_id` vs. Schema-Isolation. Entweder:
   - (a) Begründete Ausnahme dokumentieren ("Cross-Tenant-Suche nicht benötigt → Row-Level reicht")
   - (b) Schema-aware Design: `SET search_path TO <tenant_schema>` vor Queries

2. **[CRITICAL] DB-Zuordnung definieren**: Eigene DB `platform_search` oder in jeder App-DB oder im `content_store` (ADR-062)? Empfehlung: Integration in Content Store.

3. **[HIGH] Decision Drivers ergänzen**: Eigene Sektion mit Bullet-Liste:
   - Semantische Suche über heterogene Textmengen
   - Kein zusätzlicher Infra-Service
   - Multi-Tenant-Isolation
   - Wiederverwendbarkeit als Shared Package

4. **[HIGH] Open Questions Sektion**: Chunk-Größe, Overlap-Strategie, Re-Indexing-Prozess, IVFFlat vs. HNSW.

5. **[HIGH] Confirmation Sektion**: "Compliance wird verifiziert durch: (a) pytest-Suite mit mindestens 3 Known-Good-Queries pro App, (b) pgvector Health-Check im `/healthz/` Endpoint."

6. **[MEDIUM] Secret-Management**: Verweis auf ADR-045 für `OPENAI_API_KEY`-Handling.

7. **[MEDIUM] ADR-062 Querverweise**: Explizite Beziehung zum Content Store dokumentieren.

8. **[LOW] Drift-Detector Felder**: `<!-- staleness_months: 12, drift_check_paths: platform/packages/platform-search/** -->` einfügen.

9. **[LOW] Graceful Degradation**: Was passiert wenn pgvector nicht installiert ist oder Embedding-API nicht erreichbar? Fallback auf reine FTS?

---

*Review-Template: v2.0 (2026-02-24) — Intensive Review*
