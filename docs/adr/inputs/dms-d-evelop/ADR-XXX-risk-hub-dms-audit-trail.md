---
status: "proposed"
date: 2026-03-25
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related:
  - ADR-038  # DSB-Modul — Externer Datenschutzbeauftragter
  - ADR-050  # Platform Decomposition — Hub Landscape
  - ADR-045  # Secrets Management (SOPS + read_secret)
  - ADR-057  # Platform Test Strategy
  - ADR-072  # Multi-Tenancy Schema Isolation
  - ADR-075  # Deployment Execution Strategy
  - ADR-078  # Docker HEALTHCHECK Convention
staleness_months: 12
drift_check_paths:
  - src/dms_archive/
  - src/dsb/services/
  - src/risk/services/
---

# AD XXX: Adopt d.velop DMS REST API as Revisionssicheres Archiv-Backend für risk-hub Compliance-Dokumente

## Metadaten

| Attribut          | Wert                                                                                     |
|-------------------|------------------------------------------------------------------------------------------|
| **Status**        | Proposed                                                                                 |
| **Scope**         | service                                                                                  |
| **Erstellt**      | 2026-03-25                                                                               |
| **Autor**         | Achim Dehnert                                                                            |
| **Reviewer**      | –                                                                                        |
| **Supersedes**    | –                                                                                        |
| **Superseded by** | –                                                                                        |
| **Relates to**    | ADR-038 (DSB-Modul), ADR-050 (Hub Landscape), ADR-045 (Secrets), ADR-057 (Tests),       |
|                   | ADR-072 (Multi-Tenancy), ADR-075 (Deployment), ADR-078 (Healthcheck)                    |

## Repo-Zugehörigkeit

| Repo        | Rolle    | Betroffene Pfade / Komponenten                                            |
|-------------|----------|---------------------------------------------------------------------------|
| `risk-hub`  | Primär   | `src/dms_archive/` (neu), `src/dsb/services/*.py`, `src/risk/services/`   |
| `platform`  | Referenz | `docs/adr/`, `.windsurf/workflows/`                                       |
| `mcp-hub`   | Sekundär | zukünftiger `dvelop_mcp.py` FastMCP-Server (ADR-147, geplant)             |

---

## Decision Drivers

- **Gesetzliche Aufbewahrungspflicht**: DSGVO Art. 5(2) (Rechenschaftspflicht), ArbSchG §3,
  GoBD §147 AO verlangen revisionssichere, unveränderliche Dokumentenablage — die risk-hub
  Datenbank allein ist hierfür ungeeignet (UPDATE/DELETE möglich, keine Signaturkette).
- **Behördenkunde Landratsamt**: Der erste Produktiv-Mandant betreibt d.velop DMS bereits
  on-premises und erwartet alle Compliance-Dokumente darin — kein zweites DMS-System.
- **Audit-Trail-Lücke**: risk-hub erzeugt hochwertige Compliance-Dokumente
  (Datenpannen-Meldungen, Gefährdungsbeurteilungen, DSB-Jahresberichte), die nach
  Erzeugung nicht systematisch außerhalb der eigenen Datenbank gesichert werden.
- **d.velop REST API verfügbar**: IIL hat d.velop Cloud gebucht
  (`https://iil.d-velop.cloud/`); die API ist vollständig dokumentiert und
  produktionsreif (JSON-HAL, OAuth2/Bearer, Webhook-Unterstützung).
- **Entkopplung von Paperless-ngx**: Paperless-ngx (ADR-144) ist für
  IIL-interne Dokumente ausgelegt, bietet keinen Freigabe-Workflow, keine
  digitale Signatur und keine GOBD-Konformität — es ist kein Ersatz für
  behördliches DMS.
- **Platform-Konsistenz**: Neue Funktionalität als eigene Django-App
  `dms_archive` in risk-hub, Service-Layer-Pattern (ADR-050), keine Logik
  in Views, SeparateDatabaseAndState-Migrationen.

---

## 1. Context and Problem Statement

### 1.1 Ist-Zustand

risk-hub (`schutztat.de`) verwaltet mandantenfähige Compliance-Daten für:

- **DSB-Modul** (ADR-038): Verarbeitungsverzeichnis (VVT), Datenschutz-Audits,
  Datenpannen-Meldungen (72h-Frist Art. 33 DSGVO), Jahresberichte
- **risk-Modul**: Gefährdungsbeurteilungen (ArbSchG), Vorfallsberichte, Maßnahmenpläne

Diese Dokumente werden als Django-Model-Instanzen in PostgreSQL gespeichert und
können als PDF exportiert werden. Nach dem Export existiert keine revisionssichere
Kopie außerhalb der Anwendungsdatenbank. Folgende Risiken bestehen:

| Risiko | Eintrittswahrscheinlichkeit | Auswirkung |
|--------|----------------------------|------------|
| Datenbankfehler / -korruption | Niedrig | Kritisch — Dokument unwiederbringlich verloren |
| Versehentliches DELETE durch Admin | Mittel | Kritisch — Compliance-Nachweis fehlt |
| Manueller Manipulationsvorwurf | Niedrig | Hoch — kein kryptografischer Integritätsbeweis |
| Behördliche Prüfung ohne DMS-Nachweis | Mittel | Hoch — Bußgeld bis 4 % Jahresumsatz (Art. 83 DSGVO) |

### 1.2 Auslösendes Ereignis

Ein Landratsamt (Behördenkunde) beauftragt IIL mit dem Betrieb der risk-hub
Compliance-Plattform. Das Landratsamt betreibt bereits d.velop d.3ecm als
zertifiziertes DMS (GOBD-konform, BSI TR-03125-zertifiziert für Langzeitarchivierung).
Der Kunde erwartet, dass alle über risk-hub erzeugten Compliance-Dokumente
**automatisch** im d.velop DMS erscheinen — ohne manuellen Export-Schritt.

### 1.3 Technische Rahmenbedingungen

```
risk-hub (Django 6, Celery 5, PostgreSQL 16)
    │
    │  Celery-Task (Queue: "dms")
    ▼
d.velop Cloud REST API
    https://iil.d-velop.cloud/
    Auth: Bearer Token (d.ecs Identity Provider)
    Format: JSON-HAL (Hypertext Application Language)
    CSRF: Origin-Header Pflicht bei POST/PUT/DELETE/PATCH
    │
    ▼
d.3ecm Repository (on-premises beim Landratsamt)
    Kategorien: DSGVO_AUDIT, DSGVO_PANNE, DSGVO_VVT, GB_BERICHT, ...
```

Die d.velop API ist vollständig REST-basiert. Upload erfolgt zweistufig:
1. `POST /dms/r/{repo_id}/b` — Datei-Blob hochladen → `blob_id`
2. `POST /dms/r/{repo_id}/o` — DMS-Objekt mit Metadaten + `blob_id` anlegen

---

## 2. Considered Options

### Option A — Neue Django-App `dms_archive` in risk-hub (empfohlen)

Eine eigenständige, entkoppelte App innerhalb von risk-hub, die ausschließlich
für DMS-Archivierungen zuständig ist. Kommuniziert mit d.velop via `httpx`-Client
in einem dedizierten Celery-Task auf Queue `"dms"`.

**Architektur-Skizze:**

```
risk-hub/src/
├── dms_archive/
│   ├── models.py      ← DmsArchiveRecord (Audit-Trail, nie löschen)
│   ├── services.py    ← DmsArchiveService, RiskHubPdfExporter
│   ├── tasks.py       ← archive_document_to_dms (Celery, bind, max_retries=3)
│   ├── api.py         ← Django Ninja: /status/, /retry/, /failed/
│   └── migrations/    ← SeparateDatabaseAndState + Partial-Index
│
├── dsb/services/audit_service.py   ← +3 Zeilen am Ende von finalize_audit()
├── dsb/services/breach_service.py  ← +3 Zeilen nach submit_to_authority()
├── dsb/services/report_service.py  ← +3 Zeilen nach generate_jahresbericht()
└── risk/services/assessment_service.py ← +3 Zeilen nach finalize_assessment()
```

**Datenfluss:**

```
[Service Layer] finalize_audit()
       │
       ▼
DmsArchiveService.schedule_archival(ArchiveRequest)
       │  transaction.on_commit()
       ▼
Celery Task: archive_document_to_dms
       │
       ├── RiskHubPdfExporter.export(source_type, source_id)
       │         └── dsb/services/report_service.export_audit_pdf()
       │
       ├── DvelopDmsClient.upload_document(repo_id, ...)
       │         ├── POST /dms/r/{id}/b  ← blob upload
       │         └── POST /dms/r/{id}/o  ← DMS object + metadata
       │
       └── DmsArchiveRecord.mark_success(dms_doc_id, repo_id, category)
```

### Option B — Separater `dms-hub` Microservice

d.velop-Archivierung als eigenständiger Django-Hub (analog zu research-hub,
cad-hub). risk-hub ruft `dms-hub` via interner REST-API auf.

### Option C — Direkte Archivierung in der View-Schicht

DMS-Upload beim PDF-Download-Request des Benutzers synchron ausführen
(`views.py` ruft `DvelopDmsClient` direkt auf).

### Option D — Datei-basierte Integration (d.velop File Importer)

PDF-Dateien in ein freigegebenes Verzeichnis schreiben; d.velop File Importer
holt diese regelmäßig ab (Pull-Prinzip, kein Push).

---

## 3. Decision Outcome

**Gewählt: Option A** — Neue Django-App `dms_archive` in risk-hub.

### 3.1 Begründung

Option A wird gewählt, weil:

1. **Keine neue Infrastruktur** — risk-hub hat bereits Celery, Redis, PostgreSQL
   und den gesamten Platform-Context-Stack. Option B (separater Microservice)
   würde diesen kompletten Stack ein zweites Mal aufbauen für eine Funktion,
   die keine eigene Datenhaltung jenseits des Tracking-Records benötigt.

2. **Service-Layer-Pattern bleibt rein** — durch `transaction.on_commit()` wird
   der Celery-Task erst nach dem erfolgreichen DB-Commit dispatcht. Die bestehenden
   `services.py`-Dateien bekommen nur 3 Zeilen am Ende — keine Logik in Views,
   keine zirkulären Importe.

3. **Option C (synchron in View)** ist ein Anti-Pattern: Ein externer HTTP-Call
   im Request-Response-Zyklus blockiert den Gunicorn-Worker für bis zu 30 Sekunden.
   Bei d.velop-Ausfällen wäre der PDF-Download für den Benutzer unbenutzbar.

4. **Option D (File Importer)** scheidet aus, da d.velop on-premises beim
   Landratsamt steht. Datei-basierter Transfer über WireGuard-Tunnel wäre
   möglich, erzeugt aber zusätzliche Infrastruktur-Abhängigkeiten ohne Mehrwert
   gegenüber dem direkten REST-Push.

5. **Idempotenz-Garantie** — `DmsArchiveService.schedule_archival()` prüft
   vor dem Task-Dispatch ob bereits ein `SUCCESS`-Eintrag für `source_id`
   existiert. Doppelaufrufe (z.B. durch Retry-Logik in vorgelagerten Services)
   sind sicher.

### 3.2 Abgewiesene Alternativen — Kurzfassung

| Option | Hauptablehnungsgrund |
|--------|----------------------|
| B — separater dms-hub | Überengineering: kompletter Hub-Stack für 1 Funktion; keine eigene DB nötig |
| C — synchron in View | Blockiert Gunicorn-Worker; d.velop-Ausfälle brechen PDF-Download |
| D — File Importer | Zusätzlicher WireGuard-Dateitransfer; keine Metadaten-Kontrolle; kein Status-Tracking |

---

## 4. Pros and Cons of the Options

### Option A — `dms_archive` App in risk-hub ✅

**Pro:**

- Keine neue Deployment-Infrastruktur: bestehende Celery-Worker übernehmen Queue `"dms"`
- Vollständige Entkopplung über Celery: d.velop-Ausfälle beeinflussen risk-hub-Betrieb nicht
- `DmsArchiveRecord` als unveränderlicher Audit-Trail: jeder Archivierungsversuch
  protokolliert (inkl. Fehler, Retry-Zähler, Celery-Task-ID)
- Idempotenz: mehrfacher Aufruf für dasselbe Objekt ist sicher
- `transaction.on_commit()`: kein Task vor dem DB-Commit → keine Race Conditions
- Partial-Unique-Index in PostgreSQL: exakt ein `SUCCESS`-Eintrag pro `source_id`
  auf DB-Ebene erzwungen (nicht nur in Python)
- 3-faches exponentielles Retry (60s → 120s → 240s): transiente Netzwerkfehler
  werden automatisch behandelt
- `acks_late=True` + `reject_on_worker_lost=True`: kein Task-Verlust bei
  Worker-Absturz
- Alle 4 Integrationspunkte sind chirurgische Ergänzungen (≤ 5 Zeilen) in
  bestehende `services.py`-Dateien
- Django Ninja API (`/api/v1/dms-archive/`) für Monitoring und manuelle
  Retry-Triggerung

**Con:**

- `dms_archive` App hat Wissens-Abhängigkeiten zu allen Domain-Services
  (`dsb`, `risk`) für den PDF-Export — Kopplung über den `RiskHubPdfExporter`-
  Dispatcher. Bei Umbenennung von Service-Methoden muss `RiskHubPdfExporter`
  aktualisiert werden.
- Celery-Queue `"dms"` benötigt mindestens 1 dedizierten Worker-Prozess.
  Bei hohem Archivierungsvolumen (> 100 Dokumente/Tag) könnte Queue-Backpressure
  entstehen — dann `concurrency=4` auf dms-Worker erhöhen.
- d.velop Cloud-Abhängigkeit: wenn `iil.d-velop.cloud` dauerhaft nicht erreichbar
  ist, akkumulieren `FAILED`-Einträge. Maximal 3 automatische Retries, danach
  manuelle Intervention nötig.

### Option B — Separater `dms-hub` ✅/❌

**Pro:**

- Vollständige Isolation: dms-hub kann unabhängig deployed, skaliert und versioniert werden
- Eigene Datenbank ermöglicht zukünftige DMS-Funktionen (Suche, UI, Webhook-Receiver)
- Mandanten-übergreifende DMS-Konfiguration (mehrere Kunden mit jeweils eigenem Repository)

**Con:**

- Neues Repo, neuer Docker-Stack (Web + Worker + DB + Redis = 4 Container)
- Interne REST-Kommunikation risk-hub → dms-hub mit X-Hub-Signature-Auth
  und Timeout/Retry-Handling (ADR-050 §3.3) — erheblicher Boilerplate
- Ein Ausfall von dms-hub blockiert risk-hub-Archivierungen
- Für die aktuelle Anforderung (3–4 Archivierungstypen, 1 Mandant) klares Overengineering

### Option C — Synchron in View ❌

**Pro:**

- Einfachste Implementierung: 5 Zeilen in `download_pdf()` View

**Con:**

- **Kritisch**: HTTP-Request an externe API blockiert Gunicorn-Worker für bis zu 30s
- Bei d.velop-Timeout schlägt der PDF-Download für den Benutzer fehlt
- Kein Retry-Mechanismus
- Kein Audit-Trail
- Verletzt Service-Layer-Pattern (Logik in View) — direkt abzulehnen per ADR-050

### Option D — File Importer ❌

**Pro:**

- Keine direkte API-Abhängigkeit zur Laufzeit: Datei schreiben ist lokal

**Con:**

- Keine Bestätigung ob d.velop das Dokument tatsächlich importiert hat
- Kein Metadaten-Mapping zur Laufzeit: Kategorien und Eigenschaften können
  nicht dynamisch pro Mandant konfiguriert werden
- Polling-Latenz (File Importer prüft typisch alle 5 Minuten)
- WireGuard-Tunnel-Abhängigkeit für on-premises d.velop Installation
- Kein strukturierter Fehler-Feedback-Kanal

---

## 5. Implementation Plan

### Phase 1 — App-Skeleton + Celery-Task (Woche 1)

```
Dateien neu:
  src/dms_archive/__init__.py
  src/dms_archive/apps.py
  src/dms_archive/models.py            ← DmsArchiveRecord
  src/dms_archive/services.py          ← DmsArchiveService, RiskHubPdfExporter
  src/dms_archive/tasks.py             ← archive_document_to_dms
  src/dms_archive/migrations/0001_initial.py  ← SeparateDatabaseAndState
  src/dms_archive/tests/__init__.py
  src/dms_archive/tests/test_dms_archive.py   ← 8 Basis-Tests

Konfiguration:
  config/settings/base.py:
    INSTALLED_APPS += ["dms_archive"]
    CELERY_TASK_ROUTES["dms_archive.tasks.*"] = {"queue": "dms"}

  config/settings/production.py:
    DVELOP_BASE_URL = "https://iil.d-velop.cloud"
    # Kein direkter Key — read_secret("DVELOP_API_KEY") in tasks.py

Migration ausführen:
  python manage.py migrate dms_archive
```

**Akzeptanzkriterien Phase 1:**
- `DmsArchiveRecord` mit `PENDING`-Status wird angelegt
- Celery-Task landet auf Queue `"dms"`
- Bei simuliertem d.velop-Fehler wird 3× wiederholt, dann `FAILED`
- `DmsArchiveRecord.mark_success()` setzt alle Felder korrekt
- Alle 8 Tests grün

### Phase 2 — d.velop Client-Integration + httpx (Woche 1)

```
Dateien neu:
  src/dms_archive/client/__init__.py
  src/dms_archive/client/dvelop_client.py   ← httpx-Client, JSON-HAL, Retry

Abhängigkeiten (requirements.txt):
  httpx>=0.27
  tenacity>=9.0
```

**d.velop-Client-Anforderungen:**

```python
# Pflicht-Header für alle Requests:
Authorization: Bearer {read_secret("DVELOP_API_KEY")}
Accept: application/hal+json

# Zusätzlich für POST/PUT/DELETE/PATCH (CSRF):
Origin: https://iil.d-velop.cloud
Content-Type: application/hal+json
```

**Upload-Sequenz (dokumentiert in d.velop API v2.15):**

```
1. POST /dms/r/{repo_id}/b
   Body: raw PDF bytes
   Headers: Content-Disposition: attachment; filename="{name}"
   Response: 201 Created, Location: /dms/r/{id}/b/{blob_id}

2. POST /dms/r/{repo_id}/o
   Body: {
     "sourceCategory": "DSGVO_AUDIT",
     "sourceProperties": [{"key": "Mandant", "value": "Landratsamt Neu-Ulm"}],
     "contentLocationUri": "/dms/r/{repo_id}/b/{blob_id}"
   }
   Response: 201 Created, Location: /dms/r/{id}/o/{doc_id}
```

**Akzeptanzkriterien Phase 2:**
- `dvelop_verify.py` läuft erfolgreich gegen `https://iil.d-velop.cloud`
- `DvelopDmsClient.list_repositories()` gibt ≥ 1 Repository zurück
- `DvelopDmsClient.upload_document()` gibt valide `doc_id` zurück
- Alle HTTP-Calls mit `pytest-httpx` gemockt (kein echtes Netz in Tests)

### Phase 3 — Integration in bestehende Services (Woche 2)

Chirurgische Erweiterungen in bestehenden `services.py`-Dateien:

```python
# Muster für alle 4 Integrationspunkte (am Ende der jeweiligen Methode,
# nach emit_audit_event(), innerhalb des bestehenden transaction.atomic()-Blocks):

from src.dms_archive.services import DmsArchiveService, ArchiveRequest
from src.dms_archive.models import DmsArchiveRecord

DmsArchiveService.schedule_archival(ArchiveRequest(
    tenant_id     = <objekt>.tenant_id,
    source_type   = DmsArchiveRecord.DocumentType.<TYPE>,
    source_id     = <objekt>.id,
    source_label  = f"<Lesbare Bezeichnung>",
    performed_by  = performed_by,
    dms_category  = "<D-VELOP-KATEGORIE-ID>",
    dms_properties = { ... },
))
```

**Betroffene Methoden:**

| Datei | Methode | source_type | dms_category |
|-------|---------|-------------|--------------|
| `dsb/services/audit_service.py` | `finalize_audit()` | `PRIVACY_AUDIT` | `DSGVO_AUDIT` |
| `dsb/services/breach_service.py` | `submit_breach_to_authority()` | `DATA_BREACH` | `DSGVO_PANNE` |
| `dsb/services/report_service.py` | `generate_jahresbericht()` | `JAHRESBERICHT` | `DSGVO_JAHRESBERICHT` |
| `risk/services/assessment_service.py` | `finalize_assessment()` | `RISK_ASSESSMENT` | `GB_BERICHT` |

**Akzeptanzkriterien Phase 3:**
- `finalize_audit()` → `DmsArchiveRecord(status=PENDING)` in DB
- Celery-Task dispatcht mit korrekten `kwargs`
- Kein bestehender Test bricht

### Phase 4 — Django Ninja API + Docker-Konfiguration (Woche 2)

```python
# config/urls.py (Ergänzung):
from src.dms_archive.api import router as dms_archive_router
api.add_router("/dms-archive/", dms_archive_router)
```

**Neue API-Endpunkte:**

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| `GET` | `/api/v1/dms-archive/status/{source_id}` | Archivierungs-Status eines Objekts |
| `POST` | `/api/v1/dms-archive/retry/{source_id}` | Fehlgeschlagene Archivierung wiederholen |
| `GET` | `/api/v1/dms-archive/failed/` | Alle fehlgeschlagenen Einträge des Mandanten |

**Docker Compose (Ergänzung `docker-compose.prod.yml`):**

```yaml
# Bestehenden risk-worker ODER neuen dms-worker konfigurieren.
# Empfehlung: eigener Worker für Queue-Isolation.

risk-dms-worker:
  <<: *common
  image: ghcr.io/achimdehnert/risk-hub:${IMAGE_TAG:-develop}
  container_name: risk-hub-dms-worker
  command: celery -A config worker -Q dms -c 2 -l info --without-gossip
  depends_on:
    risk-db:
      condition: service_healthy
    risk-redis:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "celery", "-A", "config", "inspect", "ping", "-d",
           "celery@risk-dms-worker"]
    interval: 60s
    timeout: 15s
    retries: 3
    start_period: 30s
```

### Phase 5 — Kategorie-Mapping Konfiguration (Woche 3)

Für den Landratsamt-Produktivbetrieb müssen die d.velop-Kategorien-IDs
(`DSGVO_AUDIT`, `GB_BERICHT` etc.) gegen die tatsächlichen Kategorie-IDs
im d.3ecm-Repository des Kunden abgeglichen werden.

```bash
# Abfrage der verfügbaren Kategorien im Repository:
GET /dms/r/{repo_id}/objectdefinitions
Accept: application/hal+json
Authorization: Bearer {key}
```

Die Mapping-Tabelle wird in `DVELOP_CATEGORY_MAP` in `tasks.py` gepflegt
(oder zukünftig als DB-Konfiguration via `DmsCategoryMapping`-Model aus
dem separaten `dms-hub`-Skeleton).

---

## 6. Sicherheitsanalyse

### 6.1 API-Key-Management

Der d.velop API-Key (`DVELOP_API_KEY`) wird ausschließlich via
`read_secret()` aus dem SOPS-verschlüsselten Secret-Store geladen
(ADR-045). **Niemals** als Klartext in `settings.py`, `docker-compose.yml`
oder Umgebungsvariablen ohne Verschlüsselung.

Der Key hat im d.velop-System minimale Berechtigungen:
- `dms:read` (für Repository-Listing)
- `dms:write` (für Blob-Upload + DMS-Objekt-Anlage)
- **Kein** `admin`, **kein** `delete`, **kein** `user-management`

Key-Rotation: mindestens jährlich, nach jedem Mitarbeiter-Offboarding.

### 6.2 CSRF-Schutz

d.velop erfordert den `Origin`-Header bei allen schreibenden Requests.
Der Client setzt `Origin: https://iil.d-velop.cloud` auf allen
`POST`/`PUT`/`DELETE`/`PATCH`-Requests. Fehlt der Header → HTTP 403.

### 6.3 Datenschutz der übertragenen Inhalte

Alle übertragenen PDFs enthalten personenbezogene Daten (DSGVO Art. 4).
Übertragung ausschließlich über HTTPS (TLS 1.2+). `iil.d-velop.cloud`
ist ein DSGVO-konformer europäischer Dienst (d.velop AG, Münster, Deutschland).

Die `DmsOperationLog.payload_summary`-Felder enthalten **keine** PII —
nur Metadaten (Dokumenttyp, Dateiname, Kategorie, Anzahl Befunde).

### 6.4 Mandantentrennung

Jeder Mandant hat genau eine `DmsRepository`-Konfiguration (FK auf
`tenant_id`). Der Celery-Task liest `tenant_id` aus dem `DmsArchiveRecord`
und ruft `_get_tenant_dms_config(tenant_id)` auf — es ist strukturell
ausgeschlossen, dass Mandant A in das Repository von Mandant B archiviert.

---

## 7. Fehlerszenarien und Mitigationen

| Szenario | Erkennung | Mitigation |
|----------|-----------|------------|
| d.velop-API nicht erreichbar (Timeout) | Task wirft `httpx.ConnectTimeout` | Automatischer Retry 3× (60/120/240s); danach `FAILED`-Status |
| d.velop antwortet mit HTTP 429 (Rate Limit) | `httpx.HTTPStatusError` mit `status_code=429` | Retry mit exponentiell erhöhtem Backoff; `Retry-After`-Header auswerten |
| d.velop antwortet mit HTTP 403 (fehlender Origin) | `httpx.HTTPStatusError` mit `status_code=403` | Kein Retry (Konfigurationsfehler) — sofort `FAILED`, Alert |
| PDF-Export schlägt fehl (Service-Bug) | `Exception` in `RiskHubPdfExporter.export()` | Task schlägt fehl, `DmsArchiveRecord.mark_failed()`, Retry |
| Doppeltes `schedule_archival()` | `DmsArchiveRecord.objects.filter(status=SUCCESS)` | Idempotenz-Check gibt existierenden Record zurück, kein Task |
| Worker-Absturz während Upload | `acks_late=True` + `reject_on_worker_lost=True` | Task landet zurück in Queue, Neustart bei nächstem Worker |
| API-Key abgelaufen | HTTP 401 vom d.velop-Server | Kein Retry (Auth-Fehler), sofort `FAILED`, Alert an Admin |
| Celery-Queue `"dms"` läuft voll | Grafana-Alert auf Queue-Tiefe > 50 | Celery Worker `concurrency` erhöhen; d.velop-Verfügbarkeit prüfen |

---

## 8. Konsequenzen

### 8.1 Positiv

- Revisionssichere Archivierung aller Compliance-Dokumente in einem
  DMS das vom Kunden bereits betrieben und auditiert wird
- Keine manuelle Export-Tätigkeit für den Benutzer: Archivierung
  erfolgt transparent nach Dokument-Finalisierung
- Vollständiger Audit-Trail in `DmsArchiveRecord`: wann, von wem,
  welches Dokument, mit welchem Ergebnis archiviert
- Idempotente Implementierung: mehrfacher Aufruf ist sicher
- Kein Einfluss auf risk-hub Response-Zeiten (asynchroner Celery-Task)
- Basis für zukünftige DMS-Integrationen (bieterpilot → Vergabedokumente,
  pptx-hub → Präsentationsarchiv)

### 8.2 Negativ

- Neue externe Abhängigkeit: d.velop Cloud-Verfügbarkeit beeinflusst
  Archivierungsvollständigkeit (nicht risk-hub-Betrieb selbst)
- Celery-Worker für Queue `"dms"` erhöht Container-Anzahl um 1
- `RiskHubPdfExporter` ist gekoppelt an alle Domain-Service-Methoden:
  Methodenumbenennungen in `dsb/services/` erfordern Update in `dms_archive`
- Kategorie-Mapping muss pro d.velop-Instanz (Mandant) konfiguriert werden

### 8.3 Risiken

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|------------|
| d.velop ändert API (Breaking Change) | Niedrig | Hoch | `httpx`-Client isoliert in `dms_archive/client/`; ADR-Drift-Detector prüft alle 12 Monate |
| API-Key-Leak via Chat/Log | Mittel | Kritisch | `read_secret()` Pflicht (ADR-045); kein Logging des Keys; Rotation nach Incident |
| Kategorie-IDs ändern sich in d.velop | Mittel | Mittel | `DVELOP_CATEGORY_MAP` zentral in `tasks.py`; DB-Konfiguration in Phase 5 |
| Hohe Dokumentvolumen (> 500/Tag) | Niedrig | Mittel | Celery-Worker `concurrency` erhöhen; d.velop-Rate-Limits prüfen |

---

## 9. Confirmation

Diese ADR gilt als implementiert, wenn:

1. `pytest src/dms_archive/tests/ -v` — alle Tests grün (≥ 8 Tests)
2. `DmsArchiveRecord` in PostgreSQL angelegt, Partial-Index `uq_dmsarchive_one_success` aktiv
3. Celery-Worker auf Queue `"dms"` läuft (`celery -A config inspect ping`)
4. `finalize_audit()` → `DmsArchiveRecord(status=SUCCESS)` in d.velop nachweisbar
4. Django Ninja API `/api/v1/dms-archive/status/{id}` liefert korrekten Status
5. `dvelop_verify.py` läuft erfolgreich gegen `https://iil.d-velop.cloud`
6. `docker-compose.prod.yml` enthält `risk-dms-worker` mit Healthcheck (ADR-078)
7. `DVELOP_API_KEY` ausschließlich via `read_secret()` geladen — kein Klartext in Config
8. `catalog-info.yaml` in risk-hub aktualisiert: `dms_archive` als neue App dokumentiert

---

## 10. More Information

### Externe Quellen

| Quelle | URL | Abgerufen |
|--------|-----|-----------|
| d.velop DMS API Dokumentation (v2.15) | https://help.d-velop.de/docs/api/documentations/de/dms-developer/2.15.0 | 2026-03-25 |
| d.velop Developer Portal | https://portal.d-velop.de/documentation/dmsap/en | 2026-03-25 |
| d.velop Inbound Scan API | https://help.d-velop.de/dev/documentation | 2026-03-25 |
| DSGVO Art. 5(2) — Rechenschaftspflicht | EUR-Lex | — |
| GoBD §147 AO — Aufbewahrungsfristen | BMF-Schreiben 2019 | — |
| httpx Dokumentation | https://www.python-httpx.org/ | — |
| tenacity Dokumentation | https://tenacity.readthedocs.io/ | — |

### Verwandte ADRs

| ADR | Titel | Relevanz |
|-----|-------|----------|
| ADR-038 | DSB-Modul | Definiert `PrivacyAudit`, `Breach`, `ProcessingActivity` — Quell-Objekte dieser Integration |
| ADR-045 | Secrets Management | `read_secret("DVELOP_API_KEY")` — Pflichtmuster |
| ADR-050 | Hub Landscape | Service-Layer-Pflicht; `dms_archive` als neue App in risk-hub |
| ADR-057 | Test Strategy | `pytest-httpx` für HTTP-Mocking ohne echtes Netz |
| ADR-072 | Multi-Tenancy | `tenant_id` auf `DmsArchiveRecord`; Mandantentrennung im Task |
| ADR-075 | Deployment | GitHub Actions für Worker-Deployment; kein Write-MCP |
| ADR-078 | Healthcheck | `risk-dms-worker` Healthcheck via `celery inspect ping` |

### Zukünftige ADRs (angekündigt)

- **ADR-147**: `dvelop_mcp.py` — FastMCP-Server für agentic DMS-Zugriff via Windsurf/Cascade
- **ADR-148**: bieterpilot → DMS-Archivierung von Vergabedokumenten
- **ADR-149**: d.velop Inbound-Scan Integration (Fujitsu iX1600 → WireGuard → d.velop)

---

## 11. Migration Tracking

| Schritt | Status | Datum | Notiz |
|---------|--------|-------|-------|
| ADR-XXX erstellt | ✅ Done | 2026-03-25 | Initiale Version |
| ADR-XXX Review | ⏳ Pending | – | – |
| Phase 1: App-Skeleton + Tests | ⏳ Pending | – | – |
| Phase 2: d.velop Client-Integration | ⏳ Pending | – | – |
| Phase 3: Service-Hooks (4 Methoden) | ⏳ Pending | – | – |
| Phase 4: API + Docker | ⏳ Pending | – | – |
| Phase 5: Kategorie-Mapping Landratsamt | ⏳ Pending | – | – |
| Erster Produktiv-Archivierungstest | ⏳ Pending | – | Datenschutz-Audit → d.velop |
| ADR-XXX Status → Accepted | ⏳ Pending | – | Nach Produktiv-Test |

---

*Erstellt: 2026-03-25 · Autor: Achim Dehnert · Review: ausstehend*
