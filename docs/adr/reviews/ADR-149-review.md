# 🔍 ADR Review: ADR-149 — Adopt d.velop Cloud DMS as Platform Document Archive Service (dms-hub)

**Reviewer**: Cascade (IT-Architekt, Platform-Standards)
**Datum**: 2026-03-26
**Checklist-Version**: v2.0 (2026-02-24)

---

## 1. MADR 4.0 Compliance

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 1.1 | YAML frontmatter present | ✅ | `status`, `date`, `decision-makers`, `implementation_status`, `staleness_months`, `drift_check_paths` — alles vorhanden |
| 1.2 | Title is a decision statement | ✅ | "Adopt d.velop Cloud DMS as Platform Document Archive Service" — klare Entscheidungs-Aussage |
| 1.3 | Context and Problem Statement | ✅ | Section 1 mit Ist-Zustand, Auslösendes Ereignis, Technische Rahmenbedingungen — vorbildlich |
| 1.4 | Decision Drivers | ✅ | 6 Drivers mit Gesetzesreferenzen (DSGVO, ArbSchG, GoBD) |
| 1.5 | Considered Options ≥ 3 | ✅ | 4 Optionen (A–D) |
| 1.6 | Decision Outcome | ✅ | Option A gewählt mit 5 Begründungspunkten + Abweisungstabelle |
| 1.7 | Pros and Cons | ✅ | Alle 4 Optionen bewertet |
| 1.8 | Consequences Good/Bad | ✅ | Section 10 mit Positiv/Negativ/Risiken-Matrix |
| 1.9 | Confirmation subsection | ✅ | Section 9 mit 9 konkreten Akzeptanzkriterien |
| 1.10 | More Information | ✅ | Section 11 mit externen Quellen, Input-Dokumenten, verwandten ADRs |

---

## 2. Platform Infrastructure Specifics

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 2.1 | Server IP korrekt | ⚠️ | IP `88.198.191.108` korrekt in Phase 3 referenziert — aber **hardcoded im ADR** (Section 8, Phase 3). Besser: nur `Prod-Server` referenzieren, IP in separater Infra-Tabelle |
| 2.2 | SSH access: root | n/a | Kein SSH-Zugriff im ADR definiert |
| 2.3 | StrictHostKeyChecking=no absent | ✅ | Nicht vorhanden |
| 2.4 | Registry ghcr.io/achimdehnert/ | ✅ | Korrekt in docker-compose (Zeile 499) |
| 2.5 | GITHUB_TOKEN scope | n/a | CI/CD-Pipeline nicht detailliert — akzeptabel für Proposed-Status |
| 2.6 | Secrets via DEPLOY_* | ✅ | ADR-045 referenziert, `decouple.config()` konsistent |
| 2.7 | Deploy path /opt/<repo> | ⚠️ | Nicht explizit genannt. Konvention wäre `/opt/dms-hub` — **ergänzen** |
| 2.8 | Health endpoints /livez/ + /healthz/ | ✅ | In Section 5.2 und docker-compose Healthcheck |
| 2.9 | Port registered in ADR-021 | ❌ | **Port 8107 ist NICHT in ADR-021 §2.9 Tabelle registriert.** Die Tabelle geht bis 8090. Port 8092 (billing-hub) und 8103 (recruiting-hub) fehlen ebenfalls. ADR-021 Port-Registry muss aktualisiert werden. |
| 2.10 | Nginx as reverse proxy | ✅ | Nginx in Phase 3 referenziert |

---

## 3. CI/CD & Docker Conventions

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 3.1 | Dockerfile at docker/app/Dockerfile | ✅ | In Section 5.2 Verzeichnisbaum |
| 3.2 | docker-compose.prod.yml at root | ✅ | Im Verzeichnisbaum |
| 3.3 | Non-root user in Dockerfile | ⚠️ | "Multi-stage, python:3.12-slim, non-root" erwähnt, aber **kein konkretes Beispiel** (USER app, uid 1000). Andere ADRs zeigen das explizit. |
| 3.4 | HEALTHCHECK nicht im Dockerfile | ✅ | Healthchecks nur in docker-compose — korrekt (Coach-hub Incident beachtet) |
| 3.5 | Multi-stage build | ✅ | In Section 5.2 erwähnt |
| 3.6 | Image tags latest + sha7 | ⚠️ | `${IMAGE_TAG:-latest}` im Compose, aber CI/CD-Pipeline nicht beschrieben — für Proposed OK |
| 3.7 | Compose hardening | ❌ | **Mehrere Lücken**: (1) `shm_size: 128m` fehlt bei dms-hub-db (ADR-021 §2.11), (2) `depends_on: condition: service_healthy` fehlt komplett — Web und Worker starten ohne DB/Redis-Readiness, (3) Kein `COMPOSE_PROJECT_NAME` definiert |
| 3.8 | env_file statt ${VAR} | ⚠️ | `env_file: .env.prod` korrekt, aber `${IMAGE_TAG:-latest}` und `$${REDIS_PASSWORD}` sind Compose-Interpolation — akzeptabel. **Aber**: Redis `$${REDIS_PASSWORD}` in healthcheck braucht separate `.env` für Compose-Interpolation (wie recruiting-hub Pattern: `.env` für Compose, `.env.prod` für App) |
| 3.9 | Three-stage pipeline | n/a | CI/CD noch nicht definiert — für Proposed akzeptabel |
| 3.10 | Worker Healthcheck pidof | ✅ | `pidof python3.12` — korrekt (nicht `celery inspect ping`) |

---

## 4. Database & Migration Safety

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 4.1 | Expand-Contract | ✅ | Alles neue Tabellen, kein ALTER/DROP |
| 4.2 | makemigrations --check | n/a | Noch kein Code |
| 4.3 | Backwards-compatible | ✅ | Neues Repo, kein Impact auf bestehende |
| 4.4 | tenant_id mit Index | ✅ | `UUIDField(db_index=True)` auf DmsArchiveRecord und DmsConnection |
| 4.5 | Shared DB risk | ✅ | Eigene DB (dms_hub_db), kein shared-DB-Risiko |
| 4.X | BigAutoField PK | ✅ | Kein UUID-PK — implizites BigAutoField via DEFAULT_AUTO_FIELD ✅ (B1 aus ADR-XXX-Review behoben) |
| 4.X | Migrate-Service | ❌ | **Kein `migrate`-Service in docker-compose.prod.yml.** Platform-Konvention: separater `migrate`-Service der vor `web` läuft (`depends_on: db: condition: service_healthy`, `restart: "no"`). Ohne diesen laufen Migrationen nicht automatisch beim Deploy. |

---

## 5. Security & Secrets

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 5.1 | Keine hardcoded Secrets | ✅ | API-Key nur via `decouple.config()` referenziert |
| 5.2 | .env.prod nie committed | ✅ | Implizit, kein .gitignore gezeigt aber Standard |
| 5.3 | SOPS/ADR-045 | ✅ | ADR-045 explizit in `related` und in Section 6.1 |
| 5.4 | DEPLOY_* org-level | n/a | CI/CD noch nicht definiert |
| 5.X | Hub-zu-Hub Auth | ⚠️ | Section 6.2 sagt `X-Hub-Token`, aber Consumer-Code (Section 5.5) nutzt `Authorization: Bearer {DMS_HUB_TOKEN}`. **Inkonsistenz** — welches Auth-Schema gilt? Außerdem: Wie validiert dms-hub den Token? Kein Auth-Middleware-Snippet gezeigt. |
| 5.X | API-Key per Tenant | ✅ | `api_key_env_var` in DmsConnection — cleveres Pattern: verschiedene Env-Vars pro Mandant möglich |
| 5.X | PII in Logs | ⚠️ | Nicht explizit adressiert: Was wird in `error_message` geloggt? Enthält es PII aus dem PDF-Inhalt? Empfehlung: nur technische Fehlermeldung, keine Dokumentinhalte. |

---

## 6. Architectural Consistency

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 6.1 | Service Layer Pattern | ✅ | `services.py` → `tasks.py` → `dvelop_client`; API-Endpoints sind dünne Schicht |
| 6.2 | Keine ADR-Widersprüche | ⚠️ | ADR-XXX (Input-Dokument) empfiehlt Option A (embedded). ADR-149 wählt das Gegenteil. Kein formaler Widerspruch (ADR-XXX war nie accepted), aber **Section 3.2 sollte expliziter auf die Argumente des Input-Dokuments eingehen** und begründen warum sie nicht mehr gelten. |
| 6.3 | Zero Breaking Changes | ✅ | Additive Änderung; Consumer-Hubs bekommen neuen Client, kein bestehender Code bricht |
| 6.4 | Guardian compatibility | ✅ | `drift_check_paths` vorhanden |
| 6.5 | Migration tracking | ✅ | Section 12 mit detaillierter Tracking-Tabelle |
| 6.X | Celery Best Practices | ✅ | `acks_late`, `reject_on_worker_lost`, exponentieller Backoff — korrekt |
| 6.X | Idempotenz | ✅ | Partial-Unique-Index `uq_dmsarchive_one_success_per_source` — exzellent |

---

## 7. Open Questions & Deferred Decisions

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 7.1 | Open Questions gelistet | ❌ | **Keine explizite "Open Questions" Section.** Folgende Fragen sind implizit offen aber nicht formalisiert: (1) Wie werden PDFs temporär gespeichert bis der Celery-Task sie verarbeitet? (2) Wie groß dürfen PDFs sein? (File-Upload-Limit?) (3) Wie werden Consumer-Hub-Tokens generiert und rotiert? |
| 7.2 | Deferred Decisions | ⚠️ | Provider-Abstraktion (DocuWare/ELO/SharePoint) wird erwähnt aber nicht als explizite Deferred Decision mit zukünftiger ADR-Referenz |
| 7.3 | Bewusste Entscheidungen | ⚠️ | Die Entscheidung gegen Option C (shared Package) ist gut begründet. Aber: **Warum nicht Celery auf Consumer-Seite?** Der Consumer macht einen synchronen `httpx.post()` in `transaction.on_commit()` — bei dms-hub-Ausfall blockiert der Thread bis zum Timeout (30s). Begründung fehlt warum kein async-Dispatch auf Consumer-Seite. |

---

## 8. Modern Platform Patterns

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 8.1 | infra-deploy (ADR-075) | ⚠️ | "Deployment via GitHub Actions" in Related-ADRs, aber CI/CD-Pipeline nicht beschrieben. Für Phase 3 nötig — mindestens Skeleton `ci.yml` referenzieren. |
| 8.3 | Multi-Tenancy (ADR-072) | ⚠️ | `tenant_id` Index ✅, aber **kein Schema-Isolation erwähnt**. ADR-072 fordert PostgreSQL-Schema per Tenant für neue Apps. Ist das hier relevant? dms-hub hat geringe Datenmenge — Row-Level via `tenant_id` ist vermutlich ausreichend, aber die **bewusste Entscheidung gegen Schema-Isolation sollte dokumentiert** werden. |
| 8.7 | catalog-info.yaml | ✅ | In Confirmation-Kriterium 9 gefordert |
| 8.8 | Drift-Detector | ✅ | `staleness_months: 12`, `drift_check_paths` in Frontmatter |

---

## 9. ADR-138 Implementation Tracking

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 9.1 | `implementation_status` in Frontmatter | ✅ | `implementation_status: none` — korrekt für Proposed |
| 9.2 | `implementation_evidence` | n/a | Nicht nötig bei `none` |
| 9.3 | INDEX.md sync | ✅ | `⬜` in INDEX.md = `none` — korrekt |

---

## 10. Code-Snippet-Review

### 5.3 Models

```
[SUGGEST]  DmsConnection.api_key_env_var · Clever, aber Risiko: Wenn jemand "DJANGO_SECRET_KEY"
           als Wert setzt, wird der falsche Secret geladen. Validierung/Whitelist dokumentieren.
```

```
[SUGGEST]  DmsArchiveRecord · Kein Feld für die PDF-Datei selbst.
           Task referenziert `record.file_bytes` und `record.properties` (Zeile 483, 485)
           — diese Felder existieren nicht im Model. Wohin wird die Datei gespeichert?
           Optionen: (a) FileField + MEDIA_ROOT, (b) Temp-Verzeichnis, (c) S3/MinIO.
           Muss im ADR geklärt werden.
```

### 5.5 Consumer-Integration

```
[SUGGEST]  DmsHubClient.archive() · Synchroner httpx.post() in transaction.on_commit().
           Bei dms-hub Timeout (30s) blockiert ein Gunicorn-Worker-Thread.
           Besser: (a) Consumer dispatcht eigenen Celery-Task der dms-hub aufruft, oder
           (b) fire-and-forget httpx mit sehr kurzem Timeout (5s) + dms-hub queued intern.
           Aktuell ist (b) impliziert, aber nicht dokumentiert.
```

### 5.6 Celery Task

```
[BLOCK]    Task-Code Zeile 483: `record.file_bytes` — Feld existiert nicht im Model.
           Zeile 485: `record.properties` — Feld existiert nicht im Model.
           Zeile 491: `record.save(update_fields=[...])` — Literal-Ellipsis, nicht valides Python.
           Der Task-Code ist als Sketch OK, aber sollte als "Pseudocode" markiert sein
           oder die fehlenden Felder müssen im Model ergänzt werden.
```

### 5.7 Docker Compose

```
[BLOCK]    docker-compose: Kein `depends_on` mit `condition: service_healthy` auf Web/Worker.
           Fix:
           dms-hub-web:
             depends_on:
               dms-hub-db: { condition: service_healthy }
               dms-hub-redis: { condition: service_healthy }
           dms-hub-worker:
             depends_on:
               dms-hub-db: { condition: service_healthy }
               dms-hub-redis: { condition: service_healthy }
```

```
[BLOCK]    docker-compose: Kein `migrate`-Service. Platform-Konvention:
           dms-hub-migrate:
             <<: *common
             container_name: dms_hub_migrate
             command: python manage.py migrate --noinput
             depends_on:
               dms-hub-db: { condition: service_healthy }
             restart: "no"
```

```
[SUGGEST]  docker-compose: dms-hub-db fehlt `shm_size: 128m` (ADR-021 §2.11).
```

```
[SUGGEST]  docker-compose: `COMPOSE_PROJECT_NAME` nicht definiert.
           Konvention: `COMPOSE_PROJECT_NAME=dms-hub` in `.env`.
```

---

## 11. Zusätzliche Findings

### Z1: ADR-Nummernkonflikt

Es existiert bereits `docs/adr/inputs/dms/ADR-149-inbound-scan-dms.md` — ein Input-Dokument das ebenfalls die Nummer 149 trägt. Obwohl Input-Dokumente keine formalen ADRs sind, sollte das Input-Dokument umbenannt werden (z.B. `ADR-150-inbound-scan-dms.md`) um Verwirrung zu vermeiden.

### Z2: Blob-Storage ungeklärt

Das ADR definiert kein Storage-Konzept für die empfangenen PDFs:
- Consumer sendet PDF als `multipart/form-data`
- API-Endpoint empfängt die Datei
- Celery-Task muss die Datei lesen

**Wo wird die Datei zwischen API-Empfang und Task-Verarbeitung gespeichert?** Optionen:
- (a) `FileField` auf `DmsArchiveRecord` + `MEDIA_ROOT`
- (b) Temporäres Dateisystem (verloren bei Container-Restart)
- (c) Redis/DB als Blob (schlecht bei großen PDFs)
- (d) S3-kompatibles Object Storage

Empfehlung: (a) `FileField` + Docker Volume. Einfach, persistent, kein zusätzlicher Service.

### Z3: Consumer-Resilience bei dms-hub-Ausfall

Wenn dms-hub nicht erreichbar ist, schlägt `DmsHubClient.archive()` fehl — **innerhalb** von `transaction.on_commit()`. Das bedeutet:
- Die DB-Transaktion ist bereits committed
- Der dms-hub-Call schlägt mit Timeout fehl
- Es gibt keinen automatischen Retry auf Consumer-Seite
- Das Dokument wird nie archiviert

**Empfehlung**: Consumer sollte einen eigenen Celery-Task dispatchen statt synchronem HTTP-Call in `on_commit()`.

---

## 📊 Scoring

| Category | Score | Notes |
|----------|-------|-------|
| MADR 4.0 Compliance | **5/5** | Vorbildlich: alle Sections, Änderungshistorie, Confirmation |
| Platform Infrastructure | **3/5** | Port nicht registriert, Deploy-Path fehlt, IP hardcoded |
| CI/CD & Docker | **2/5** | 3 BLOCKs: depends_on, migrate-Service, fehlende Felder im Code |
| Database & Migration | **4/5** | BigAutoField ✅, Partial-Index ✅, migrate-Service fehlt |
| Security & Secrets | **4/5** | Auth-Inkonsistenz (X-Hub-Token vs. Bearer), PII in Logs ungeklärt |
| Architectural Consistency | **4/5** | Sehr gut; Consumer-Resilience-Lücke |
| Open Questions | **2/5** | Keine explizite Section; Blob-Storage, Auth, PDF-Limits ungeklärt |
| Modern Platform Patterns | **4/5** | Schema-Isolation-Entscheidung fehlt |
| ADR-138 Tracking | **5/5** | Korrekt |
| **Overall** | **3.7/5** | Gutes ADR mit 3 technischen BLOCKs und mehreren offenen Fragen |

---

## ✅ Stärken

1. **Exzellente MADR-Struktur** — Alle Sections, 4 Optionen, klare Begründung
2. **2-Schicht-Architektur** — Package + Hub Trennung ist architektonisch elegant
3. **Provider-Abstraktion** — `DmsConnection.provider` ermöglicht zukünftige DMS-Systeme
4. **Idempotenz** — Partial-Unique-Index auf DB-Ebene (aus ADR-XXX übernommen)
5. **Sicherheitsanalyse** — API-Key-Management, CSRF, Mandantentrennung gut dokumentiert
6. **Fehlerszenarien-Matrix** — 8 Szenarien mit Erkennung + Mitigation
7. **BigAutoField** — ADR-022/DB-001 korrekt beachtet (B1 aus ADR-XXX behoben)
8. **Worker Healthcheck** — `pidof python3.12` statt `celery inspect ping` (ADR-078)
9. **Celery Best Practices** — `acks_late`, `reject_on_worker_lost`, `transaction.on_commit()`

## ❌ Kritische Punkte (BLOCK)

1. **B1: `depends_on: condition: service_healthy` fehlt** — Web und Worker starten ohne DB/Redis-Readiness. Fix: `depends_on` mit conditions auf alle Services.

2. **B2: Kein `migrate`-Service in docker-compose** — Migrationen laufen nicht automatisch beim Deploy. Platform-Konvention: separater `migrate`-Service mit `restart: "no"`.

3. **B3: Blob-Storage ungeklärt** — Task referenziert `record.file_bytes` und `record.properties`, Felder fehlen im Model. Wie werden PDFs zwischen API-Empfang und Celery-Task gespeichert? Muss vor Implementierung geklärt sein.

## ⚠️ Verbesserungsvorschläge

1. **S1**: Port 8107 in ADR-021 §2.9 Port-Registry eintragen
2. **S2**: Deploy-Path `/opt/dms-hub` explizit dokumentieren
3. **S3**: Auth-Schema konsistent machen (X-Hub-Token vs. Bearer) und Validierung beschreiben
4. **S4**: `shm_size: 128m` auf dms-hub-db, `COMPOSE_PROJECT_NAME` definieren
5. **S5**: Eigenen Celery-Task auf Consumer-Seite statt synchronem httpx in `on_commit()`
6. **S6**: Explizite "Open Questions" Section mit: Blob-Storage, PDF-Size-Limit, Token-Rotation
7. **S7**: Schema-Isolation-Entscheidung dokumentieren (Row-Level reicht bei geringem Volume)
8. **S8**: Pseudocode im Task-Snippet als solchen markieren oder fehlende Felder ergänzen
9. **S9**: ADR-Nummernkonflikt mit `inputs/dms/ADR-149-inbound-scan-dms.md` auflösen
10. **S10**: PII-in-Logs Policy für `error_message` Feld dokumentieren

---

## 🎯 Empfehlung

### ⚠️ ACCEPT WITH CHANGES

Das ADR ist **architektonisch überzeugend** — die 2-Schicht-Entscheidung (Package + Hub) ist fundiert begründet, die MADR-Struktur ist vorbildlich, und die wesentlichen Platform-Standards (BigAutoField, Secrets, Healthcheck) sind korrekt angewendet.

Die **3 BLOCKs sind alle im docker-compose/Model-Bereich** und lassen sich ohne strukturelle Änderungen am ADR beheben. Die 10 Verbesserungsvorschläge sind größtenteils Ergänzungen, keine Umbauten.

**Empfohlene Reihenfolge:**
1. B1–B3 fixen (docker-compose + Model-Felder)
2. S1 (Port-Registry) + S6 (Open Questions) ergänzen
3. Restliche S-Findings nach Belieben
4. Status → `Accepted`

---

*Review gegen: ADR Review Checklist v2.0 (2026-02-24), Platform-Standards ADR-021/022/045/050/072/075/078/138*
