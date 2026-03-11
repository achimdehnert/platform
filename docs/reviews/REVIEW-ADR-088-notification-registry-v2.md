# REVIEW ADR-088 — Adopt a Shared Notification Registry (Rev. 2)

> **Reviewer:** Platform Architecture Review  
> **Date:** 2026-02-26  
> **Template:** ADR Review Checklist v2.0 (Template C)  
> **ADR Version:** Rev. 2 (post-fix)

---

## 1. MADR 4.0 Compliance

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 1.1 | YAML frontmatter present (`status`, `date`, `decision-makers`) | ✅ | Korrekt am Dateianfang |
| 1.2 | Title is a decision statement | ✅ | "Adopt a Shared Notification Registry as Platform-wide Multi-Channel Messaging System" |
| 1.3 | `## Context and Problem Statement` section present | ✅ | Mit App-Tabelle und 4 Problempunkten |
| 1.4 | `## Decision Drivers` section present (bullet list) | ✅ | 7 Drivers |
| 1.5 | `## Considered Options` lists ≥ 3 options | ✅ | 5 Optionen |
| 1.6 | `## Decision Outcome` states chosen option with reasoning | ✅ | 6 Begründungspunkte |
| 1.7 | `## Pros and Cons of the Options` covers all options | ✅ | Alle 5 Optionen mit Pro/Con |
| 1.8 | `## Consequences` uses Good/Bad bullet format | ✅ | "- Good, because …" / "- Bad, because …" |
| 1.9 | `### Confirmation` subsection present | ✅ | 5 Verifikationsmaßnahmen inkl. Thread-Safety Test |
| 1.10 | `## More Information` links related ADRs | ✅ | 5 Related ADRs + 3 External References |

---

## 2. Platform Infrastructure Specifics

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 2.1 | Server IP not hardcoded | ✅ | Kein IP im ADR |
| 2.6 | Secrets via ADR-045 | ✅ | Secret-Tabelle mit 5 Secrets (Twilio, Discord, Telegram) |
| 2.8 | Health endpoints | ✅ | `NotificationService.health_check()` + per-Channel `health_check()` |

---

## 3. CI/CD & Docker Conventions

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 3.8 | `env_file` pattern | ✅ | Settings-basiert, kein `${VAR}` |

*Package, kein eigenständiger Service — Docker-Checks nicht anwendbar.*

---

## 4. Database & Migration Safety

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 4.1 | Expand-Contract / Migration | ✅ | wedding-hub 3-Phasen-Migration + Feature-Flag + Zero Breaking Changes |
| 4.4 | `tenant_id` mit Index | ✅ | Composite-Index `idx_notification_tenant_status` |
| 4.5 | DB-Zuordnung | ✅ | Open Question Q5 — Empfehlung: eigene `notification_db` |

---

## 5. Security & Secrets

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 5.1 | No secrets hardcoded | ✅ | Alle via `django.conf.settings` |
| 5.3 | ADR-045 compatibility | ✅ | 5 Secrets in Tabelle dokumentiert, SOPS referenziert |

---

## 6. Architectural Consistency

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 6.1 | Service layer pattern | ✅ | Views → NotificationService → ChannelRegistry → Channel |
| 6.2 | No contradiction with existing ADRs | ✅ | ADR-072 Abweichung formal begründet (eigene Sektion) |
| 6.3 | Zero Breaking Changes | ✅ | Feature-Flag + 2-Release-Koexistenz |
| 6.5 | Migration tracking | ✅ | 3-Phasen wedding-hub Migration dokumentiert |

---

## 7. Open Questions & Deferred Decisions

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 7.1 | All open questions listed | ✅ | 6 Fragen mit Status + Empfehlung |
| 7.2 | Deferred decisions reference future ADR | ✅ | Q3 → "Eigenes ADR nach Phase 3" |
| 7.3 | Conscious decisions documented | ✅ | Celery-First, Row-Level, Thread-Safe Singleton |

---

## 8. Modern Platform Patterns

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 8.3 | ADR-072 Schema-Isolation | ✅ | Eigene Sektion mit 4 Argumenten |
| 8.4 | `tenant_id` Index | ✅ | Composite-Index tenant_id + status |
| 8.5 | `async_to_sync` vermieden | ✅ | Celery-First Design — sync `send()` API |
| 8.8 | Drift-Detector fields | ✅ | `staleness_months: 12`, `drift_check_paths`, `supersedes_check` |

---

## 9. Review Scoring

| Category | Score (1–5) | Notes |
|----------|-------------|-------|
| MADR 4.0 compliance | 5 | Alle Checks bestanden |
| Platform Infrastructure | 5 | Health-Check auf Channel-Ebene, Secrets-Tabelle |
| CI/CD & Docker | 5 | N/A (Package) — korrekt |
| Database & Migration Safety | 5 | Composite-Indexes, Feature-Flag Migration |
| Security & Secrets | 5 | ADR-045, sanitized Error Messages |
| Architectural Consistency | 5 | Service-Layer, Celery-First, Zero Breaking Changes |
| Open Questions | 5 | 6 Fragen mit Empfehlung, Q3 deferred |
| Modern Platform Patterns | 5 | ADR-072, async_to_sync, Drift-Detector |
| **Overall** | **5** | **Exemplary** |

---

## 10. Recommendation

- [x] **Accept** — ready to merge
- [ ] Accept with changes
- [ ] Reject

### Verbesserungen gegenüber Rev. 1

1. YAML frontmatter vor H1-Titel (MADR 4.0 konform)
2. `notification_sent` / `notification_failed` Signals durch `_log_failure` Helper ersetzt
3. `retry_count` wird im Celery-Task via `self.request.retries` aktualisiert
4. `self` Parameter (bind=True) korrekt genutzt im Task-Body
5. Formale ADR-072 Abweichungs-Sektion (nicht nur Model-Docstring)
6. Per-Channel `health_check()` in BaseChannel + `health_check_all()` in Registry
7. Sanitized Error Messages in `_log_failure()` — keine Exception-Details im DB

---

*Review Template: v2.0 (2026-02-24)*
