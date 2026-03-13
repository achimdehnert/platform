---
status: "accepted"
date: 2026-03-13
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-142-unified-identity-authentik-platform-idp.md", "ADR-143-knowledge-hub-outline-integration.md", "ADR-130-content-store-shared-persistence.md", "ADR-116-dynamic-model-router.md", "ADR-045-secrets-management.md"]
implementation_status: implemented
implementation_evidence:
  - "Phase 1-3 deployed 2026-03-13: Docker Compose, DNS, Nginx"
  - "URL: https://docs.iil.pet (HTTP 200)"
  - "Containers: iil_dochub_web, iil_dochub_db, iil_dochub_redis, iil_dochub_tika, iil_dochub_gotenberg"
  - "Port: 8102, DNS: CNAME docs.iil.pet → Cloudflare Tunnel"
  - "OIDC: authentik SSO (ADR-142), client_id=doc-hub, allauth openid_connect"
  - "MCP: paperless_mcp (5 Tools, 13 Tests) in mcp-hub, Windsurf registered"
  - "Sync: apps.documents.DocumentMetadata in research-hub, Celery task + management command"
  - "Nginx: 200M upload, 120s timeout"
  - "Review fixes: B1/B2/B3/K1/K2/K3/K4/H2/H3/M3 all applied"
---

# ADR-144: doc-hub — Paperless-ngx als Dokumentenmanagement-System

---

## 1. Kontext & Problemstellung

### 1.1 Fehlende Dokumentenverwaltung

Die Platform hat derzeit **keinen zentralen Ort für Dokumente**: Rechnungen, Verträge, Belege, Korrespondenz, Lizenzen, Zertifikate. Diese landen in E-Mail-Postfächern, lokalen Ordnern oder werden gar nicht archiviert.

| Dokumenttyp | Aktueller Ort | Problem |
|-------------|--------------|---------|
| **Rechnungen** | E-Mail / Downloads | ❌ Nicht durchsuchbar, kein OCR |
| **Verträge** | Lokal / Cloud-Drive | ❌ Keine Versionierung, keine Tags |
| **Belege** | Papier / Scans | ❌ Nicht digitalisiert oder nur als Bild |
| **Lizenzen/Zertifikate** | Verstreut | ❌ Kein Ablauf-Tracking |
| **Korrespondenz** | E-Mail | ❌ Nicht mit Geschäftsobjekten verknüpft |

### 1.2 Abgrenzung zu knowledge-hub (ADR-143)

| | **doc-hub (dieses ADR)** | **knowledge-hub (ADR-143)** |
|---|---|---|
| **Zweck** | Dokumentenmanagement (Dateien) | Wissensmanagement (Wiki) |
| **Input** | PDF, Bild, E-Mail → OCR → Volltext | Markdown im Browser-Editor |
| **Typische Frage** | "Wo ist die Hetzner-Rechnung Q1?" | "Was war das Konzept für Phase 2?" |
| **Beziehung** | **Komplementär** — keine Überschneidung |

### 1.3 Warum jetzt?

- Steuerjahr-Ende: Belege müssen strukturiert archiviert werden
- Wachsende Anzahl Verträge (Hetzner, Cloudflare, Domains, Lizenzen)
- AI-Enrichment: OCR + LLM-Summary automatisch bei Upload
- Platform-Vollständigkeit: DMS ist Standard-Baustein jeder Business-Plattform

---

## 2. Entscheidung

**Paperless-ngx** als self-hosted DMS, deployed als `doc-hub` auf dem Platform-Server.

### Warum Paperless-ngx?

| Kriterium | Paperless-ngx | Docspell | Mayan EDMS | Eigenbau (Django) |
|-----------|--------------|----------|------------|-------------------|
| **Lizenz** | GPLv3 | AGPL-3.0 | Apache 2.0 | — |
| **Stack** | **Python/Django** ✅ | Scala/JVM | Python/Django | Python/Django |
| **OCR** | ✅ Tesseract + Tika | ✅ | ✅ | Selbst bauen |
| **Auto-Klassifikation** | ✅ ML-basiert | ✅ | ❌ | Selbst bauen |
| **REST API** | ✅ DRF | ✅ | ✅ | Selbst bauen |
| **E-Mail Import** | ✅ IMAP | ✅ | ❌ | Selbst bauen |
| **Consume Folder** | ✅ | ✅ | ❌ | Selbst bauen |
| **Docker Compose** | ✅ | ✅ | ✅ | — |
| **Community** | ~20k GitHub Stars | ~2k | ~5k | — |
| **OIDC** | ✅ (v2.x, allauth) | ✅ | ❌ | — |
| **Multi-Tenant** | ❌ | ❌ | ❌ | ✅ |

**Paperless-ngx gewinnt** durch: identischen Tech-Stack (Django/DRF), größte Community, ML-Auto-Klassifikation, E-Mail-Import, und OIDC-Support.

---

## 3. Architektur

### 3.1 Komponenten-Übersicht

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DOC-HUB ARCHITEKTUR                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌───────────────────┐                    ┌──────────────────────┐  │
│  │  Paperless-ngx    │   REST API (DRF)   │  research-hub        │  │
│  │  (docs.iil.pet)   │ ◀────────────────▶ │  (Django)            │  │
│  │                   │                    │                      │  │
│  │  • OCR (Tesseract)│                    │  • DocumentMetadata  │  │
│  │  • Auto-Tagging   │                    │  • AI-Enrichment     │  │
│  │  • ML-Klassifik.  │                    │  • Celery Tasks      │  │
│  │  • Volltext-Suche │                    │  • pgvector Search   │  │
│  │  • E-Mail Import  │                    │                      │  │
│  │  • Consume Folder │                    │                      │  │
│  │  • OIDC (ADR-142) │                    └──────────┬───────────┘  │
│  └───────────────────┘                               │              │
│         │                                   ┌────────▼───────────┐  │
│         │ Consume                            │  paperless_mcp     │  │
│         ▼                                    │  (FastMCP Server)  │  │
│  ┌───────────────┐                          │                    │  │
│  │ Scanner/E-Mail│                          │  search_documents  │  │
│  │ Upload/Folder │                          │  get_document      │  │
│  └───────────────┘                          │  upload_document   │  │
│                                              │  list_tags         │  │
│                                              └────────────────────┘  │
│                                                       │              │
│                                              Windsurf/Cascade        │
│                                              (AI Document Access)    │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Docker Deployment

```yaml
# docker-compose.doc-hub.yml — KORRIGIERT (Review-Fixes B2, B3, K1, K2, H2, H3, M3)
name: doc-hub-stack                    # B3 Fix: COMPOSE_PROJECT_NAME

networks:
  dochub_internal:
    name: iil_dochub_internal
    driver: bridge                     # B2 Fix: NUR internes Netzwerk, kein bf_platform_prod

services:
  paperless-web:
    image: ghcr.io/paperless-ngx/paperless-ngx:2.14
    container_name: iil_dochub_web
    networks: [dochub_internal]
    ports:
      - "127.0.0.1:8102:8000"
    environment:
      PAPERLESS_DBHOST: iil_dochub_db
      PAPERLESS_DBNAME: paperless
      PAPERLESS_DBUSER: "${DOCHUB_DB_USER}"
      PAPERLESS_DBPASS: "${DOCHUB_DB_PASS}"
      PAPERLESS_REDIS: "redis://:${DOCHUB_REDIS_PASSWORD}@iil_dochub_redis:6379"  # K1 Fix
      PAPERLESS_SECRET_KEY: "${DOCHUB_SECRET_KEY}"
      PAPERLESS_URL: https://docs.iil.pet
      PAPERLESS_ALLOWED_HOSTS: "docs.iil.pet,localhost"
      PAPERLESS_CSRF_TRUSTED_ORIGINS: "https://docs.iil.pet"
      PAPERLESS_OCR_LANGUAGE: deu+eng
      # M3 Fix: PAPERLESS_OCR_LANGUAGES entfernt (wirkungslos bei vorgefertigtem Image)
      PAPERLESS_TIME_ZONE: Europe/Berlin
      PAPERLESS_FILENAME_FORMAT: "{created.year}/{correspondent}/{title}"  # H3 Fix: Dot-Notation
      PAPERLESS_CONSUMER_RECURSIVE: "true"
      PAPERLESS_CONSUMER_SUBDIRS_AS_TAGS: "true"
      PAPERLESS_TIKA_ENABLED: "1"
      PAPERLESS_TIKA_GOTENBERG_ENDPOINT: http://iil_dochub_gotenberg:3000
      PAPERLESS_TIKA_ENDPOINT: http://iil_dochub_tika:9998
      PAPERLESS_ADMIN_USER: "${DOCHUB_ADMIN_USER}"
      PAPERLESS_ADMIN_PASSWORD: "${DOCHUB_ADMIN_PASS}"
    env_file: [.env]
    volumes:
      - dochub_data:/usr/src/paperless/data
      - dochub_media:/usr/src/paperless/media
      - dochub_consume:/usr/src/paperless/consume
      - dochub_export:/usr/src/paperless/export
    depends_on:
      dochub_db:
        condition: service_healthy     # K2 Fix
      dochub_redis:
        condition: service_healthy     # K2 Fix
      dochub_tika:
        condition: service_started     # Tika: kein curl im Image
      dochub_gotenberg:
        condition: service_healthy     # K2 Fix
    mem_limit: 1024m
    restart: unless-stopped
    healthcheck:                       # H2 Fix: /api/ statt / (302-Problem)
      test: ["CMD-SHELL", "curl -fs http://localhost:8000/api/ | grep -q documents || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 90s

  dochub_db:
    image: postgres:16-alpine
    container_name: iil_dochub_db
    networks: [dochub_internal]
    environment:
      POSTGRES_USER: "${DOCHUB_DB_USER}"
      POSTGRES_PASSWORD: "${DOCHUB_DB_PASS}"
      POSTGRES_DB: paperless
    volumes:
      - dochub_db_data:/var/lib/postgresql/data
    mem_limit: 256m
    restart: unless-stopped
    healthcheck:                       # K2 Fix
      test: ["CMD-SHELL", "pg_isready -U ${DOCHUB_DB_USER} -d paperless"]
      interval: 10s
      timeout: 5s
      retries: 5

  dochub_redis:
    image: redis:7-alpine
    container_name: iil_dochub_redis
    networks: [dochub_internal]
    command: ["redis-server", "--requirepass", "${DOCHUB_REDIS_PASSWORD}"]  # K1 Fix
    mem_limit: 64m
    restart: unless-stopped
    healthcheck:                       # K1+K2 Fix
      test: ["CMD", "redis-cli", "-a", "${DOCHUB_REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  dochub_tika:
    image: apache/tika:3.2.3.0
    container_name: iil_dochub_tika
    networks: [dochub_internal]
    mem_limit: 512m
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "java -cp /tika-server-standard.jar org.apache.tika.server.core.TikaServerCli --help > /dev/null 2>&1 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  dochub_gotenberg:
    image: docker.io/gotenberg/gotenberg:8.14
    container_name: iil_dochub_gotenberg
    networks: [dochub_internal]
    command:
      - "gotenberg"
      - "--chromium-disable-javascript=true"
      - "--chromium-allow-list=file:///tmp/.*"
      - "--api-timeout=30s"
    mem_limit: 512m
    restart: unless-stopped
    healthcheck:                       # K2 Fix
      test: ["CMD-SHELL", "curl -fs http://localhost:3000/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  dochub_data:
  dochub_media:
  dochub_db_data:
  dochub_consume:
  dochub_export:
```

### 3.3 Ressourcen-Bedarf

| Container | RAM | Disk |
|-----------|-----|------|
| paperless-web (Django + Celery) | 1024 MB | ~500 MB (Image) |
| dochub_db (PostgreSQL 16) | 256 MB | ~200 MB |
| dochub_redis | 64 MB | ~50 MB |
| dochub_tika (Apache Tika) | 512 MB | ~500 MB (JVM) |
| dochub_gotenberg | 512 MB | ~200 MB |
| **Gesamt** | **~2.4 GB** | **~1.3 GB** |

Server-Budget (hetzner-prod): 22 GB RAM, aktuell ~9 GB belegt, ~12 GB available → 2.4 GB doc-hub = **machbar** (~9.6 GB Reserve nach Deploy).

### 3.4 Port-Zuweisung

| Hub | Port |
|-----|------|
| coach-hub | 8007 |
| billing-hub | 8009 |
| research-hub | 8011 |
| dev-hub | 8085 |
| ausschreibungs-hub | 8095 |
| **doc-hub (paperless)** | **8102** |

### 3.5 Nginx-Config (Cloudflare Tunnel)

```nginx
# /etc/nginx/sites-available/docs.iil.pet.conf

# HTTP → HTTPS Redirect (für direkte Zugriffe)
server {
    listen 80;
    listen [::]:80;
    server_name docs.iil.pet;
    return 301 https://$host$request_uri;
}

# Rate-Limiting auf API (Schutz gegen Scraping)
limit_req_zone $binary_remote_addr zone=paperless_api:10m rate=30r/m;

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name docs.iil.pet;

    ssl_certificate     /etc/letsencrypt/live/iil.pet/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/iil.pet/privkey.pem;

    client_max_body_size 200M;       # Paperless akzeptiert grosse Scans
    client_body_timeout  120s;

    # Rate-Limiting auf REST API
    location /api/ {
        limit_req zone=paperless_api burst=50 nodelay;
        limit_req_status 429;
        proxy_pass          http://127.0.0.1:8102;
        proxy_http_version  1.1;
        proxy_set_header    Host              $host;
        proxy_set_header    X-Real-IP         $remote_addr;
        proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto https;
        proxy_read_timeout  120s;
    }

    location / {
        proxy_pass          http://127.0.0.1:8102;
        proxy_http_version  1.1;
        proxy_set_header    Host              $host;
        proxy_set_header    X-Real-IP         $remote_addr;
        proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto https;
        proxy_read_timeout  120s;
    }
}
```

**Hinweise:**
- `listen 443 ssl http2` + `listen [::]:443 ssl http2` — IPv4 + IPv6, da cloudflared über IPv6 (`::1`) verbindet. IPv4-only Binding verursacht 502.
- `client_max_body_size 200M` für große Scan-Uploads.
- Rate-Limiting auf `/api/` aktiviert (30 req/min + Burst 50).

### 3.6 Auth-Integration (ADR-142)

**Phase 1 (sofort):** Paperless-ngx mit lokalem Admin-Account.
**Phase 2 (nach ADR-142 Deploy):** OIDC via authentik:

```bash
# .env.doc-hub — OIDC-Ergänzung (Phase 2, nach ADR-142 Deploy)
# Werte via read_secret() / deploy-Skript injizieren — NICHT plain in Git!

PAPERLESS_SOCIALACCOUNT_PROVIDERS={"openid_connect":{"APPS":[{"provider_id":"authentik","name":"IIL Platform Login","client_id":"${DOCHUB_OIDC_CLIENT_ID}","secret":"${DOCHUB_OIDC_SECRET}","settings":{"server_url":"https://id.iil.pet/application/o/doc-hub/.well-known/openid-configuration"}}],"OAUTH_PKCE_ENABLED":true}}
```

**Hinweis:** Der JSON-String wird als einzelne Env-Var übergeben. `client_id` und `secret` werden beim Deploy via `envsubst` aus dem Secret-Store (ADR-045) eingesetzt. Kein Plaintext-Secret in Git.

### 3.7 Multi-Tenancy Roadmap

| Phase | Tenant-Modell | Zielgruppe |
|-------|--------------|-----------|
| **Phase 1** | Single-Instance, intern | iil.gmbh Team |
| **Phase 2** | User-Permissions (Owner/View/Edit) | Interne Abteilungen |
| **Phase 3** | Evaluierung: Fork + `tenant_id` vs. Instance-per-Tenant | Externe Kunden |

**Phase 1+2 ausreichend für internen Betrieb.** Phase 3 nur wenn externer SaaS-Bedarf entsteht.

### 3.8 Sicherheit & Backup

| Aspekt | Maßnahme |
|--------|----------|
| **Netzwerk-Isolation** | Eigenes Docker-Netzwerk `iil_dochub_internal` — kein Zugriff auf Platform-Container |
| **Redis-Auth** | `requirepass` auf dochub_redis |
| **Secrets** | Alle Credentials via `.env.doc-hub`, Injection via `envsubst` beim Deploy (ADR-045) |
| **Backup (DB)** | Täglicher `pg_dump` Cron → `/opt/backups/doc-hub/`. Rotation: 30 Tage. |
| **Backup (Docs)** | `paperless-ngx document_exporter` → Export-Volume → `/opt/backups/doc-hub/export/` |
| **Version-Pinning** | `paperless-ngx:2.14`, `postgres:16-alpine`, `tika:3.2.3.0`, `gotenberg:8.14` |
| **Admin-Passwort** | `PAPERLESS_ADMIN_USER`/`PAPERLESS_ADMIN_PASSWORD` nur bei Erststart. Nach Setup aus `.env` entfernen. |

### 3.9 DocumentMetadata Model (research-hub)

Platform-Standards: `BigAutoField PK`, `public_id`, `tenant_id`, `deleted_at`, `UniqueConstraint`, `_()` i18n.

**tenant_id-Strategie:** doc-hub ist ein internes Tool. `tenant_id = PLATFORM_INTERNAL_TENANT_ID` (Konstante `1`), analog zu ADR-143/Knowledge-Hub.

Paperless-ngx = **Single Source of Truth** für Dateien + OCR-Text. Django = Metadaten, AI-Enrichments, Platform-Verknüpfungen.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | BigAutoField (PK) | Auto-generiert |
| `public_id` | UUIDField (unique, indexed) | Externe Referenz |
| `tenant_id` | BigIntegerField (indexed) | Immer `PLATFORM_INTERNAL_TENANT_ID` (1) |
| `paperless_document_id` | IntegerField (indexed) | Paperless-ngx Document ID |
| `title` | CharField(500) | Dokumenttitel |
| `correspondent` | CharField(255, blank) | Korrespondent-Name |
| `paperless_url` | URLField (blank) | Link zum Paperless-Dokument |
| `status` | CharField(20, indexed) | `pending` / `indexed` / `enriched` / `error` (TextChoices) |
| `doc_type` | CharField(30, indexed) | `invoice` / `contract` / `receipt` / `license` / `correspondence` / `other` (TextChoices) |
| `document_date` | DateField (nullable, indexed) | Datum des Dokuments (aus Paperless) |
| `tags` | JSONField (list) | Paperless-Tags (unstrukturiert — JSONField per DB-001 Exception erlaubt) |
| `ai_summary` | TextField | Automatische Zusammenfassung |
| `ai_keywords` | JSONField (list) | Extrahierte Keywords (variabel — JSONField erlaubt) |
| `ai_enriched_at` | DateTimeField (nullable) | Letztes AI-Enrichment |
| `paperless_updated_at` | DateTimeField (nullable) | Letzte Paperless-Änderung |
| `last_synced_at` | DateTimeField (nullable) | Letzte Synchronisierung |
| `deleted_at` | DateTimeField (nullable) | Soft-Delete |
| `created_at` / `updated_at` | DateTimeField | Timestamps |

**Constraint:** `UniqueConstraint(fields=["paperless_document_id"], condition=Q(deleted_at__isnull=True), name="uq_document_metadata_paperless_id_active")`

---

## 4. paperless_mcp — MCP-Server für Cascade

| Tool | Beschreibung |
|------|-------------|
| `search_documents(query, tags, date_from, date_to)` | Volltext-Suche über alle Dokumente |
| `get_document(doc_id)` | Metadaten + OCR-Text eines Dokuments |
| `list_correspondents()` | Alle Korrespondenten auflisten |
| `list_tags()` | Alle Tags auflisten |
| `upload_document_from_url(source_url, title, correspondent, tags)` | Dokument von URL hochladen |

**Sicherheitshinweise (Review-Fixes B1 + K4):**

- **B1 Fix:** Kein `file_path`-Parameter — nur URL-basierter Upload. Verhindert Path-Traversal auf Server-Dateisystem (`.env`, Private Keys).
- **K4 Fix:** Alle REST-API-Calls via `asyncio.to_thread()` — blockierende `httpx`-Calls sind im `async def` FastMCP-Kontext verboten.
- Auth via `PAPERLESS_API_TOKEN` (aus Secret-Store, ADR-045).

Registrierung in Windsurf als MCP-Server (`paperless-docs`), analog zu `platform-context` und `outline-knowledge`.

---

## 5. Workflows

### 5.1 Rechnung archivieren

```
Rechnung per E-Mail empfangen
  → IMAP-Consumer holt PDF
  → OCR → Volltext extrahiert
  → ML-Klassifikation: Tag "Rechnung", Korrespondent "Hetzner"
  → Dateiname: 2026/Hetzner/Rechnung_Q1_2026.pdf
  → Cascade: search_documents("Hetzner Rechnung 2026") → findet sofort
```

### 5.2 Vertrag ablegen

```
Upload via Web-UI (docs.iil.pet)
  → Tags: "Vertrag", "Cloudflare"
  → Custom Fields: Ablaufdatum, Kündigungsfrist
  → Celery-Task: Erinnerung 30 Tage vor Ablauf
```

### 5.3 Cascade-Integration

```
User: "Was kostet der Hetzner-Server monatlich?"
Cascade → search_documents("Hetzner Rechnung monatlich")
  → Findet letzte Rechnung mit OCR-Text
  → Extrahiert Betrag
```

---

## 6. Implementierungsplan

| Phase | Inhalt | Abhängigkeit | Aufwand |
|-------|--------|-------------|---------|
| **1** | Docker Compose erstellen + deployen | — | 2h |
| **2** | DNS: `docs.iil.pet` (Cloudflare Tunnel) | Phase 1 | 0.5h |
| **3** | Nginx-Config + SSL | Phase 2 | 0.5h |
| **4** | Admin-Account + initiale Tags/Korrespondenten | Phase 1 | 1h |
| **5** | E-Mail Import konfigurieren (IMAP) | Phase 4 | 1h |
| **6** | OIDC-Integration (ADR-142 Phase 2) | ADR-142 | 1h |
| **7** | `paperless_mcp` FastMCP Server | Phase 1 | 3h |
| **8** | research-hub Integration (DocumentMetadata Model) | Phase 7 | 3h |
| **9** | Tests: pytest-Suite | Phase 7+8 | 2h |

**Gesamt: ~14h über 2-3 Sessions**

---

## 7. Offene Fragen

| Frage | Empfehlung | Status |
|-------|-----------|--------|
| Domain: `docs.iil.pet` oder `dms.iil.pet`? | `docs.iil.pet` — kürzer, verständlicher. Bereits deployed + DNS aktiv. | Entschieden |
| Paperless Version pinnen? | Ja — `2.14` statt `:latest`. Tika: `2.9.2`. Gotenberg: `8.14`. | Entschieden |
| Backup-Strategie? | Täglicher `pg_dump` + `document_exporter` → `/opt/backups/doc-hub/`. Rotation: 30 Tage. (Section 3.8) | Entschieden |
| Consume-Folder per SFTP? | Phase 2+ — SSH-Key-basiert, für Scanner-Integration. Erstmal Upload via Web-UI. | Offen |
| Wie viel RAM auf Server noch frei? | ~22 GB gesamt, ~9 GB used, ~12 GB available, 2.4 GB doc-hub → ~9.6 GB Reserve | Geprüft |
| Tika-Version? | `apache/tika:3.2.3.0` — gepinnt statt `:latest` | Entschieden |

---

## 8. Kosten

| Komponente | Lizenz | Kosten |
|------------|--------|--------|
| Paperless-ngx (self-hosted) | GPLv3 | **0 €** |
| Tika + Gotenberg | Apache 2.0 | **0 €** |
| Hetzner (bereits vorhanden) | — | **0 €** extra |
| AI-Enrichment (llm_mcp) | — | ~$0.01/Dokument |

**Gesamtkosten: 0 € + marginale LLM-Kosten.**

---

## 9. Konsequenzen

### Positiv

- **Zentraler Ort für alle Geschäftsdokumente** — Rechnungen, Verträge, Belege
- **OCR + Volltext-Suche** — jedes Dokument sofort findbar
- **Auto-Klassifikation** — ML lernt aus Tags, minimiert manuellen Aufwand
- **E-Mail-Import** — Rechnungen automatisch aus Mailbox archiviert
- **Django/Python Stack** — kein Fremdkörper, identische Technologie
- **Cascade bekommt Zugriff** via paperless_mcp — Dokumente als AI-Kontext
- **Komplementär zu knowledge-hub** (ADR-143) — Dateien vs. Wiki

### Negativ / Risiken

- **Zusätzliche Infrastruktur**: ~2.4 GB RAM, 5 Container
- **Kein Multi-Tenant**: Phase 1 nur intern nutzbar
- **Tika + Gotenberg** sind Java/Go-Services — zusätzliche Angriffsfläche
- **GPLv3 Lizenz** — bei Fork: Änderungen müssen veröffentlicht werden
- **OCR-Qualität** abhängig von Scan-Qualität

---

## 10. Referenzen

- Paperless-ngx: https://docs.paperless-ngx.com / https://github.com/paperless-ngx/paperless-ngx
- Apache Tika: https://tika.apache.org (Image: `apache/tika:2.9.2`)
- Gotenberg: https://gotenberg.dev (Image: `gotenberg/gotenberg:8.14`)
- authentik Integration: ADR-142
- Knowledge-Hub (Outline): ADR-143
- Content-Store: ADR-130
- Deployment: `/opt/doc-hub/docker-compose.yml` auf hetzner-prod
