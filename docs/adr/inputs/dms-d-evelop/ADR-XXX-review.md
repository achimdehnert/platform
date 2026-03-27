# 🔍 ADR Review: ADR-XXX — Adopt d.velop DMS REST API as Revisionssicheres Archiv-Backend

**Reviewer**: Cascade (IT-Architekt, Platform-Standards)
**Datum**: 2026-03-26
**Geprüfte Dateien**:
- `ADR-XXX-risk-hub-dms-audit-trail.md` (649 Zeilen)
- `risk-hub-dms/src/dms_archive/` (7 Dateien: models, services, tasks, api, integration, tests, migration)

---

## 1. MADR 4.0 Compliance

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 1.1 | YAML frontmatter present | ⚠️ | Vorhanden, aber `implementation_status` fehlt (ADR-138 Pflicht). Außerdem: **Nummer ist XXX** — muss echte Nummer bekommen |
| 1.2 | Title is a decision statement | ✅ | "Adopt d.velop DMS REST API as Revisionssicheres Archiv-Backend" — klar formuliert |
| 1.3 | Context and Problem Statement | ✅ | Sehr gut: Ist-Zustand, Auslösendes Ereignis, Technische Rahmenbedingungen — vorbildlich |
| 1.4 | Decision Drivers | ✅ | 6 klare Drivers mit Gesetzesreferenzen (DSGVO, ArbSchG, GoBD) |
| 1.5 | Considered Options ≥ 3 | ✅ | 4 Optionen (A–D) — gut |
| 1.6 | Decision Outcome | ✅ | Option A gewählt mit 5 Begründungspunkten |
| 1.7 | Pros and Cons | ✅ | Alle 4 Optionen ausführlich bewertet |
| 1.8 | Consequences | ✅ | Positiv/Negativ/Risiken — exzellent strukturiert |
| 1.9 | Confirmation subsection | ✅ | Section 9 mit 8 konkreten Akzeptanzkriterien |
| 1.10 | More Information | ✅ | Externe Quellen + verwandte ADRs + zukünftige ADRs |

---

## 2. Platform Infrastructure Specifics

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 2.1 | Server IP nicht hardcoded | ✅ | Keine IP im ADR |
| 2.4 | Registry ghcr.io/achimdehnert/ | ✅ | Korrekt in docker-compose Snippet |
| 2.7 | Deploy path `/opt/<repo>` | n/a | Deployment als App in risk-hub, kein eigener Deploy-Pfad |
| 2.8 | Health endpoints /livez/ + /healthz/ | ⚠️ | Für den DMS-Worker: nur `celery inspect ping` definiert, keine HTTP-Health-Endpoints für die `dms_archive`-App selbst |
| 2.9 | Port allocation | n/a | Kein eigener Port (eingebettet in risk-hub) |

---

## 3. CI/CD & Docker Conventions

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 3.4 | HEALTHCHECK nicht im Dockerfile | ✅ | Healthcheck nur in docker-compose |
| 3.7 | Compose hardening | ⚠️ | `risk-dms-worker` hat keinen `deploy.resources.limits.memory` und kein `logging` |
| 3.8 | env_file statt ${VAR} | ✅ | `${IMAGE_TAG:-develop}` ist eine akzeptable Compose-Interpolation (nicht App-Config) |
| 3.10 | Worker Healthcheck | ❌ | **`celery inspect ping`** ist FALSCH — Platform-Standard ist `pidof python3.12` (ADR-021 §3.10). `celery inspect ping` schlägt bei Broker-Ausfall fehl → Restart-Loop |

---

## 4. Database & Migration Safety

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 4.1 | Expand-Contract | ✅ | Neue Tabelle, kein ALTER/DROP |
| 4.2 | makemigrations --check | n/a | Migration ist manuell (SeparateDatabaseAndState) |
| 4.3 | Backwards-compatible | ✅ | Neue Tabelle, kein Impact auf bestehende |
| 4.4 | tenant_id mit Index | ✅ | `tenant_id = models.UUIDField(db_index=True)` |
| 4.X | **BigAutoField PK** | ❌ | **`id = models.UUIDField(primary_key=True)`** — BLOCK. Platform-Standard (ADR-022, DB-001): `DEFAULT_AUTO_FIELD = BigAutoField`. UUID als PK ist **verboten**. |
| 4.X | **SeparateDatabaseAndState** | ⚠️ | Korrekt angewendet, aber die Raw-SQL-Migration enthält `DEFAULT gen_random_uuid()` — mit BigAutoField PK wäre das hinfällig |
| 4.X | Partial Unique Index | ✅ | `uq_dmsarchive_one_success` — exzellent, DB-Level-Garantie |

---

## 5. Security & Secrets

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 5.1 | Keine hardcoded Secrets | ✅ | API-Key via `read_secret()` — korrekt |
| 5.2 | .env.prod nie committed | ✅ | Nicht relevant (kein neues Repo) |
| 5.3 | SOPS/ADR-045 | ⚠️ | ADR referenziert `read_secret("DVELOP_API_KEY")`, aber `platform_context.secrets.read_secret` existiert nicht. Korrekt wäre `decouple.config("DVELOP_API_KEY")` (ADR-045) |
| 5.X | CSRF-Analyse | ✅ | `Origin`-Header-Pflicht dokumentiert |
| 5.X | Minimale API-Berechtigungen | ✅ | `dms:read` + `dms:write`, kein admin/delete |
| 5.X | Key-Rotation | ✅ | Mindestens jährlich dokumentiert |

---

## 6. Architectural Consistency

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 6.1 | Service Layer Pattern | ✅ | `services.py` → `tasks.py`, Views nur dünne Ninja-Endpoints |
| 6.2 | Keine ADR-Widersprüche | ❌ | **Widerspruch mit User-Vision**: Das ADR empfiehlt Option A (eingebettet in risk-hub) und lehnt Option B (separater dms-hub) explizit ab. Der User will aber einen **DMS-Hub als Platform-Service**. Das ADR muss grundlegend umgeschrieben werden. |
| 6.3 | Zero Breaking Changes | ✅ | Additive Änderung (neue App + 3-Zeilen-Patches) |
| 6.4 | Guardian compatibility | ✅ | `drift_check_paths` im Frontmatter |
| 6.5 | Migration tracking | ✅ | Section 11 mit detaillierter Tracking-Tabelle |
| 6.X | `transaction.on_commit()` | ✅ | Korrekt: Task erst nach DB-Commit |
| 6.X | Celery Best Practices | ✅ | `acks_late`, `reject_on_worker_lost`, exponentieller Backoff |
| 6.X | Idempotenz | ✅ | Partial-Unique-Index + Python-Check — doppelt abgesichert |

---

## 7. Open Questions & Deferred Decisions

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 7.1 | Open Questions gelistet | ⚠️ | Kategorie-Mapping (Phase 5) ist als "zukünftig" markiert, aber nicht als offene Frage formuliert |
| 7.2 | Deferred Decisions | ✅ | ADR-147 (MCP), ADR-148 (bieterpilot), ADR-149 (Inbound-Scan) explizit genannt |
| 7.3 | Bewusste Entscheidungen | ❌ | **Fehlend**: Keine Aussage zu Multi-Provider-Strategie. Was passiert wenn ein Mandant kein d.velop hat sondern z.B. DocuWare, ELO, SharePoint? Das ADR ist hart auf d.velop fixiert. |

---

## 8. Modern Platform Patterns

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 8.1 | infra-deploy (ADR-075) | ✅ | Worker-Deployment via GitHub Actions |
| 8.3 | Multi-Tenancy | ⚠️ | `tenant_id` korrekt, aber `_get_tenant_dms_config()` hat Fallback auf globale Settings — das bricht Mandantentrennung bei >1 Mandant |
| 8.7 | catalog-info.yaml | n/a | Kein neues Repo |
| 8.8 | Drift-Detector | ✅ | `staleness_months: 12`, `drift_check_paths` vorhanden |

---

## 9. Code-Review: 7 Source-Dateien

### models.py

```
[BLOCK]    models.py:47 · UUIDField(primary_key=True) · ADR-022/DB-001
           Fix: Entfernen. BigAutoField wird automatisch durch DEFAULT_AUTO_FIELD gesetzt.
           Falls UUID benötigt: `uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)`
```

```
[SUGGEST]  models.py:9 · Kommentar "UUID PK" als Platform-Standard bezeichnet
           Das ist KEIN Platform-Standard — es ist das Gegenteil. Kommentar korrigieren.
```

```
[NITS]     models.py:98-113 · mark_success() und mark_failed() mutieren self + save()
           Besser: Classmethod oder Service-Methode statt Mutation auf Model-Instanz.
           Akzeptabel für PoC, sollte bei Refactoring in Service wandern.
```

### services.py

```
[BLOCK]    services.py:160 · from dms_hub.client.dvelop_client import DvelopDmsClient
           Referenziert ein Package das nicht existiert. Code ist nicht lauffähig.
```

```
[BLOCK]    services.py:165 · from platform_context.secrets import read_secret
           Modul existiert nicht. Korrekt: from decouple import config (ADR-045)
```

```
[SUGGEST]  services.py:188-242 · _export_privacy_audit() etc.
           Alle Exporter importieren risk-hub-spezifische Models (src.dsb.models.audit).
           Bei einem DMS-Hub-Ansatz: Consumer liefert PDF-Bytes, DMS-Hub archiviert nur.
           → RiskHubPdfExporter gehört in risk-hub, nicht in dms_archive.
```

### tasks.py

```
[SUGGEST]  tasks.py:24-34 · DVELOP_CATEGORY_MAP hardcoded
           Nicht mandantenfähig. Sollte DB-Model oder Settings-basiert sein.
```

```
[NITS]     tasks.py:121 · except Exception as exc — zu breit
           Besser: httpx.HTTPStatusError, httpx.ConnectTimeout separat fangen
           für differenziertes Retry-Verhalten (403 = kein Retry, 429 = Retry mit Backoff).
           Im ADR-Text korrekt beschrieben, im Code nicht umgesetzt.
```

### api.py

```
[SUGGEST]  api.py:25-26 · Import von Schema und datetime nicht am Dateianfang
           Imports gehören an den Anfang der Datei (PEP 8).
```

```
[SUGGEST]  api.py:94 · Model.objects.filter() direkt in View
           Verletzt Service-Layer-Pattern (ADR-041). Sollte DmsArchiveService.list_failed() sein.
```

### migration/0001_initial.py

```
[BLOCK]    migration:23 · UUID primary key in SQL
           Muss auf BigAutoField/BIGSERIAL umgestellt werden.
```

### tests/test_dms_archive.py

```
[SUGGEST]  tests:44 · patch("src.dms_archive.tasks....")
           Mock-Pfad mit src.-Prefix — funktioniert nur wenn src/ im PYTHONPATH.
           Risk-hub verwendet `apps.`-Prefix für Django-Apps. Prüfen ob Pfad korrekt ist.
```

```
[NITS]     tests · 8 Tests — solide Basis, aber es fehlen:
           - Test für DvelopDmsClient (HTTP-Mock mit pytest-httpx)
           - Test für 403/429/401 Error-Handling
           - Test für transaction.on_commit() Timing
```

---

## 📊 Scoring

| Category | Score | Notes |
|----------|-------|-------|
| MADR 4.0 Compliance | **4/5** | Sehr gut, nur `implementation_status` + Nummer fehlen |
| Platform Infrastructure | **4/5** | Worker-Healthcheck falsch |
| CI/CD & Docker | **3/5** | `celery inspect ping` statt `pidof`; fehlende Compose-Hardening |
| Database & Migration | **2/5** | UUID-PK = BLOCK; ansonsten exzellent (Partial-Index) |
| Security & Secrets | **4/5** | `read_secret()` existiert nicht; sonst vorbildlich |
| Architectural Consistency | **2/5** | ADR empfiehlt Option A, User will Option B; `DvelopDmsClient` fehlt |
| Open Questions | **3/5** | Multi-Provider nicht adressiert |
| Modern Platform Patterns | **4/5** | Drift-Detector ✅, Multi-Tenancy ⚠️ |
| **Overall** | **3.25/5** | Gute Basis, aber fundamentaler Scope-Mismatch + 4 BLOCKs |

---

## ✅ Stärken

1. **Exzellente Compliance-Analyse** — DSGVO Art. 5(2), ArbSchG §3, GoBD §147 korrekt referenziert
2. **Sicherheitsanalyse** — API-Key-Management, CSRF, Mandantentrennung, PII-Analyse — vorbildlich
3. **Fehlerszenarien-Matrix** — 8 konkrete Szenarien mit Erkennung + Mitigation
4. **Idempotenz-Design** — Partial-Unique-Index auf DB-Ebene + Python-Check — doppelt abgesichert
5. **Celery-Patterns** — `acks_late`, `reject_on_worker_lost`, `transaction.on_commit()` — korrekt
6. **Integrations-Snippets** — Chirurgische 3-Zeilen-Patches, minimal-invasiv
7. **Risikobewertung** mit Wahrscheinlichkeit × Impact — professionell

## ❌ Kritische Punkte (BLOCK — muss vor Accept gefixt werden)

1. **B1: `UUIDField(primary_key=True)`** — Verletzt ADR-022/DB-001. Platform-Standard ist BigAutoField.
   *Fix*: PK-Feld entfernen, `uuid = UUIDField(default=uuid.uuid4, unique=True)` als separates Feld.

2. **B2: `DvelopDmsClient` existiert nicht** — Code referenziert `from dms_hub.client.dvelop_client` — das Modul fehlt komplett. Der Code ist nicht lauffähig.
   *Fix*: Client implementieren oder als Phase-0-Deliverable definieren.

3. **B3: `read_secret()` Import-Pfad falsch** — `platform_context.secrets` existiert nicht.
   *Fix*: `from decouple import config` verwenden (ADR-045).

4. **B4: Scope-Mismatch** — ADR empfiehlt Option A (eingebettet in risk-hub) und lehnt Option B (separater Hub) ab. Der User-Wunsch ist aber ein **DMS-Hub als Platform-Service für N Consumer**. Das ADR muss entweder:
   - (a) Für den neuen Scope (dms-hub) komplett umgeschrieben werden, oder
   - (b) Als "risk-hub-spezifisches" ADR beibehalten und ein **neues ADR** für den dms-hub geschrieben werden.

## ⚠️ Verbesserungsvorschläge

1. **S1**: Worker-Healthcheck `celery inspect ping` → `pidof python3.12` (Platform-Standard, ADR-021 §3.10)
2. **S2**: `DVELOP_CATEGORY_MAP` hardcoded → DB-Model `DmsCategoryMapping` für Mandantenfähigkeit
3. **S3**: `RiskHubPdfExporter` in `dms_archive` → gehört in risk-hub Consumer-Code (Entkopplung)
4. **S4**: `api.py:94` ORM-Query in View → in `DmsArchiveService.list_failed()` verschieben
5. **S5**: `except Exception` im Task → differenziertes Error-Handling (403 ≠ 429 ≠ Timeout)
6. **S6**: Compose `risk-dms-worker` → `deploy.resources.limits.memory` + `logging` hinzufügen
7. **S7**: Multi-Provider-Strategie dokumentieren (DocuWare, ELO, SharePoint als zukünftige Optionen)
8. **S8**: ADR-Nummer vergeben + `implementation_status: none` im Frontmatter

---

## 🎯 Empfehlung

### ⚠️ CHANGES REQUESTED

Das ADR ist **fachlich exzellent** (Compliance-Analyse, Sicherheit, Fehlerbehandlung) aber hat **4 technische BLOCKs** und einen **fundamentalen Scope-Mismatch** mit dem User-Ziel (DMS-Hub statt embedded App).

### Empfohlenes Vorgehen

1. **Neues ADR** schreiben für den **dms-hub als Platform-Service** (2-Schicht: Package + Hub)
2. Das bestehende ADR-XXX als **Input-Dokument** referenzieren — die fachliche Analyse ist erstklassig und kann 1:1 übernommen werden
3. Die **4 BLOCKs** im Code fixen bevor der Code in irgendein Repo übernommen wird
4. Die Source-Dateien als **Startpunkt** für die dms-hub Implementierung nutzen — ~60% ist wiederverwendbar

---

*Review durchgeführt gegen: ADR Review Checklist v2.0 (2026-02-24), Platform-Standards ADR-022/041/045/050/075/078/138*
