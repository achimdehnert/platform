# REVIEW ADR-087 — Adopt pgvector + FTS Hybrid Search (Rev. 2)

> **Reviewer:** Platform Architecture Review  
> **Date:** 2026-02-26  
> **Template:** ADR Review Checklist v2.0 (Template C)  
> **ADR Version:** Rev. 2 (post-fix)

---

## 1. MADR 4.0 Compliance

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 1.1 | YAML frontmatter present (`status`, `date`, `decision-makers`) | ✅ | Korrekt am Dateianfang |
| 1.2 | Title is a decision statement | ✅ | "Adopt pgvector + FTS Hybrid Search as Platform-wide Semantic Search Engine" |
| 1.3 | `## Context and Problem Statement` section present | ✅ | Mit App-Tabelle und Problembeschreibung |
| 1.4 | `## Decision Drivers` section present (bullet list) | ✅ | 6 Drivers |
| 1.5 | `## Considered Options` lists ≥ 3 options | ✅ | 6 Optionen |
| 1.6 | `## Decision Outcome` states chosen option with reasoning | ✅ | 5 Begründungspunkte |
| 1.7 | `## Pros and Cons of the Options` covers all options | ✅ | Alle 6 Optionen mit Pro/Con |
| 1.8 | `## Consequences` uses Good/Bad bullet format | ✅ | "- Good, because …" / "- Bad, because …" |
| 1.9 | `### Confirmation` subsection present | ✅ | 4 Verifikationsmaßnahmen |
| 1.10 | `## More Information` links related ADRs | ✅ | 5 Related ADRs + 5 External References |

---

## 2. Platform Infrastructure Specifics

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 2.1 | Server IP not hardcoded | ✅ | Kein IP im ADR |
| 2.6 | Secrets via ADR-045 | ✅ | `OPENAI_API_KEY` via SOPS referenziert |
| 2.8 | Health endpoints | ✅ | `SearchService.health_check()` für `/healthz/` |

---

## 3. CI/CD & Docker Conventions

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 3.8 | `env_file` pattern | ✅ | Settings-basiert, kein `${VAR}` Interpolation |

*Package, kein eigenständiger Service — Docker-Checks nicht anwendbar.*

---

## 4. Database & Migration Safety

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 4.1 | Expand-Contract pattern | ✅ | Eigene §Schema-Evolution Sektion (3-Phasen) |
| 4.4 | `tenant_id` mit Index | ✅ | `idx_chunks_tenant` B-Tree Index |
| 4.5 | DB-Zuordnung | ✅ | Content Store DB (ADR-062) |

---

## 5. Security & Secrets

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 5.1 | No secrets hardcoded | ✅ | `_get_api_key()` lädt aus Settings |
| 5.3 | ADR-045 compatibility | ✅ | Explizit referenziert |

---

## 6. Architectural Consistency

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 6.1 | Service layer pattern | ✅ | `SearchService` als Service-Klasse |
| 6.2 | No contradiction with existing ADRs | ✅ | ADR-072 Abweichung begründet |
| 6.3 | Zero Breaking Changes | ✅ | Neues Package, kein Breaking Change |
| 6.5 | Migration tracking | ✅ | `embedding_model` Column für Tracking |

---

## 7. Open Questions & Deferred Decisions

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 7.1 | All open questions listed with pros/cons | ✅ | 6 Fragen mit Empfehlung |
| 7.2 | Deferred decisions reference future ADR | ✅ | Q6 → "Nach Phase 3 evaluieren" |
| 7.3 | Conscious decisions documented | ✅ | ADR-072 Abweichung, HNSW vs IVFFlat |

---

## 8. Modern Platform Patterns

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 8.3 | ADR-072 Schema-Isolation | ✅ | Row-Level mit formaler Begründung (4 Argumente) |
| 8.4 | `tenant_id` Index | ✅ | `idx_chunks_tenant` |
| 8.5 | `async_to_sync` pattern | ✅ | Sync httpx Client — kein async_to_sync nötig |
| 8.6 | Content Store DSN as Secret | ✅ | ADR-062 + Graceful Degradation |
| 8.8 | Drift-Detector fields | ✅ | `staleness_months: 12`, `drift_check_paths`, `supersedes_check` |

---

## 9. Review Scoring

| Category | Score (1–5) | Notes |
|----------|-------------|-------|
| MADR 4.0 compliance | 5 | Alle Checks bestanden |
| Platform Infrastructure | 5 | Health-Check, kein hardcoded IP |
| CI/CD & Docker | 5 | N/A (Package) — korrekt |
| Database & Migration Safety | 5 | Expand-Contract, tenant_id Index, DB-Zuordnung |
| Security & Secrets | 5 | ADR-045, keine hardcoded Secrets |
| Architectural Consistency | 5 | Service-Layer, ADR-072 Abweichung begründet |
| Open Questions | 5 | 6 Fragen mit Status + Empfehlung |
| Modern Platform Patterns | 5 | Alle relevanten Patterns abgedeckt |
| **Overall** | **5** | **Exemplary** |

---

## 10. Recommendation

- [x] **Accept** — ready to merge
- [ ] Accept with changes
- [ ] Reject

### Verbesserungen gegenüber Rev. 1

1. YAML frontmatter vor H1-Titel (MADR 4.0 konform)
2. `embed_texts` jetzt sync (httpx statt async) — konsistent mit SearchService
3. `_vector_search` + `_text_search` vollständig typisiert und implementiert
4. Schema-Evolution §Expand-Contract explizit dokumentiert
5. Consequences im kanonischen "- Good/Bad, because" Format

---

*Review Template: v2.0 (2026-02-24)*
