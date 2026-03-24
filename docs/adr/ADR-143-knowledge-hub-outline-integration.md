---
status: "accepted"
date: 2026-03-13
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-142-unified-identity-authentik-platform-idp.md", "ADR-132-ai-context-defense-in-depth.md", "ADR-114-discord-ide-like-communication-gateway.md", "ADR-116-dynamic-model-router.md", "ADR-045-secrets-management.md", "ADR-120-unified-deployment-pipeline.md", "ADR-130-content-store-shared-persistence.md"]
implementation_status: partial
implementation_evidence:
  - "Phase 1 Infrastructure deployed 2026-03-13: Docker Compose, DNS, Nginx"
  - "Phase 3 OIDC completed 2026-03-14: authentik SSO login working"
  - "URL: https://knowledge.iil.pet (HTTP 200, OIDC Login via id.iil.pet)"
  - "Containers: iil_knowledge_outline, iil_knowledge_outline_db, iil_knowledge_outline_redis — all healthy"
  - "Port: 3100 (intern 3000, extern 3100 wegen Port-Konflikt), DNS: CNAME knowledge.iil.pet → Cloudflare Tunnel"
  - "Backup: /etc/cron.daily/outline-backup"
  - "Nginx: WebSocket /realtime, default.crt (Tunnel TLS)"
  - "Fix: DATABASE_URL mit ?sslmode=disable für interne PG"
  - "OIDC Fix: Signing Key + Scope Mappings + extra_hosts + NODE_TLS_REJECT_UNAUTHORIZED (see docs/guides/oidc-authentik-integration.md)"
  - "Phase Cascade Action (2026-03-24): /_action Page, /_upload Helper, /_cascade.js FAB auto-injected via Nginx sub_filter"
  - "CSP Override: Outline nonce-based CSP replaced with 'self'+'unsafe-inline' in Nginx (nonce blocks sub_filter-injected scripts)"
  - "Collections: ADRs-Mirror, ADR-Drafts, Inbox, Cascade-Aufträge, Hub-Doku, Konzepte, Lessons, Runbooks — all sorted title/asc"
  - "ADR Sync Dedup: 148 duplicate documents cleaned (5-6x import runs)"
  - "Pending: Phase 4-11 (research-hub Integration, outline_mcp, Webhook-Automation)"
---

# ADR-143: Knowledge-Hub — Outline Wiki + research-hub Integration

---

## 1. Kontext & Problemstellung

### 1.1 Drei Wissenskategorien ohne zentralen Ort

| Kategorie | Aktueller Ort | Problem |
|-----------|--------------|---------|
| **ADRs (final)** | Git-Repo Markdown | ✅ Gut — aber kein Editor, kein Kommentar-Workflow |
| **Konzepte (in Arbeit)** | Lokal / im Kopf / Chat-Verläufe | ❌ Kein zentraler Ort, kein Suchindex |
| **Recherchen & Unterlagen** | Verschiedene Dateien, URLs, PDFs | ❌ Nicht durchsuchbar, kein ADR-Bezug |

### 1.2 AI Context Amnesia (ADR-132)

Cascade/Windsurf hat **kein Kontextgedächtnis** für Zwischenartefakte (ADR-132, AI Context Defense-in-Depth). Konzepte, die letzte Woche besprochen wurden, sind in der nächsten Session nicht mehr verfügbar. pgvector Memory (ADR-114) speichert nur kurze Snippets — keine ganzen Dokumente.

### 1.3 Fehlende Fähigkeit

Ein zentrales, durchsuchbares Wissens-Wiki, das:
1. Im Browser editierbar ist (Markdown, Echtzeit)
2. Per API programmatisch zugänglich ist
3. In Windsurf/Cascade als MCP-Tool nutzbar ist
4. Automatisch AI-Enrichment bekommt (Summary, Keywords)
5. ADR-Verknüpfungen pflegen kann

---

## 2. Entscheidung

**Outline Wiki** als selbst-gehostetes Knowledge-Frontend, **research-hub** als Metadaten-Backend und AI-Enrichment-Layer, **outline_mcp** als MCP-Server für Windsurf/Cascade.

### Warum Outline?

| Kriterium | Outline | BookStack | Wiki.js | Notion (SaaS) |
|-----------|---------|-----------|---------|---------------|
| **Lizenz** | BSL 1.1 (frei für <10 User) | MIT | AGPL | SaaS ($$$) |
| **Markdown nativ** | ✅ | ❌ (WYSIWYG) | ✅ | ⚠️ (proprietär) |
| **REST API** | ✅ (Bearer Token) | ✅ | ✅ | ✅ |
| **Webhooks** | ✅ (HMAC-SHA256) | ❌ | ❌ | ❌ |
| **OIDC-Support** | ✅ (nativ) | ✅ | ✅ | ❌ |
| **Echtzeit-Kollaboration** | ✅ | ❌ | ❌ | ✅ |
| **Python-Client (PyPI)** | ✅ `outline-wiki-api` | ❌ | ❌ | ✅ |
| **Docker Compose** | ✅ | ✅ | ✅ | ❌ |
| **Stack** | Node.js + PostgreSQL + Redis | PHP + MySQL | Node.js + DB | Cloud |

**Outline gewinnt** durch: native Markdown, HMAC-Webhooks, OIDC-Support (ADR-142), Python-Client auf PyPI, und Echtzeit-Kollaboration.

---

## 3. Architektur

### 3.1 Komponenten-Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE-HUB ARCHITEKTUR                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐      Webhook       ┌──────────────────┐   │
│  │  Outline Wiki    │ ─────────────────▶ │  research-hub    │   │
│  │  (knowledge.     │                    │  (Django)        │   │
│  │   iil.pet)       │                    │                  │   │
│  │                  │  REST API (Bearer) │  • KnowledgeDoc  │   │
│  │  • Markdown-Ed.  │ ◀────────────────▶ │  • ADR-Sync      │   │
│  │  • Collections   │                    │  • AI-Enrichment │   │
│  │  • Full-Text     │                    │  • Celery Tasks  │   │
│  │  • Echtzeit-     │                    │                  │   │
│  │    Kollaboration │                    │                  │   │
│  │  • OIDC (ADR-142)│                    │                  │   │
│  └──────────────────┘                    └────────┬─────────┘   │
│                                                    │             │
│                                           ┌────────▼─────────┐  │
│                                           │  outline_mcp     │  │
│                                           │  (FastMCP Server)│  │
│                                           │                  │  │
│                                           │  search_knowledge│  │
│                                           │  get_document    │  │
│                                           │  create_concept  │  │
│                                           │  list_recent     │  │
│                                           └──────────────────┘  │
│                                                    │             │
│                                           Windsurf/Cascade       │
│                                           (AI Context Feed)      │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Collections-Struktur

```
📁 ADRs (Platform)
    └── ADR-001 bis ADR-14x (gespiegelt aus Git)
📁 Konzepte (in Arbeit)
    └── Konzept: bieterpilot Phase 2
    └── Konzept: ship-workflow.sh
📁 Hub-Dokumentation
    └── coach-hub / risk-hub / travel-beat ...
📁 Recherchen & Unterlagen
    └── Technologie-Evaluationen
    └── Referenz-Links
📁 Meeting-Notes & Entscheidungen
```

### 3.3 Datenmodell: KnowledgeDocument (research-hub)

Platform-Standards: `BigAutoField PK`, `public_id`, `tenant_id`, `deleted_at`, `UniqueConstraint`.
Alle `verbose_name` und `help_text` mit `_()` (i18n ab Tag 1).

Outline ist die **Single Source of Truth** für Inhalte. Django hält Metadaten, ADR-Links und AI-Enrichments.

**tenant_id-Strategie:** Outline ist ein internes Tool. `tenant_id = PLATFORM_INTERNAL_TENANT_ID` (Konstante `1`). Wird in `settings.py` als `PLATFORM_INTERNAL_TENANT_ID = 1` definiert.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | BigAutoField (PK) | Auto-generiert |
| `public_id` | UUIDField (unique, indexed) | Externe Referenz |
| `tenant_id` | BigIntegerField (indexed) | Immer `PLATFORM_INTERNAL_TENANT_ID` (1) |
| `outline_document_id` | CharField(36, unique, indexed) | Outline UUID |
| `outline_collection_id` | CharField(36, indexed) | Collection-Referenz |
| `title` | CharField(500) | Dokumenttitel |
| `outline_url` | URLField | Link zum Outline-Dokument |
| `status` | CharField(20, indexed) | `draft` / `active` / `archived` (TextChoices) |
| `doc_type` | CharField(30, indexed) | `adr` / `concept` / `hub_doc` / `research` / `meeting_note` (TextChoices) |
| `related_adr_numbers` | ArrayField(IntegerField) | z.B. `[141, 116, 82]` — DB-001 konform (kein JSONField für strukturierte Daten) |
| `related_hubs` | ArrayField(CharField) | z.B. `["coach-hub", "risk-hub"]` — DB-001 konform |
| `ai_summary` | TextField | Automatische Zusammenfassung |
| `ai_keywords` | JSONField (list) | Extrahierte Keywords (variabel strukturiert — JSONField erlaubt per DB-001 Exception) |
| `ai_enriched_at` | DateTimeField (nullable) | Letztes Enrichment |
| `outline_updated_at` | DateTimeField (nullable) | Letzte Outline-Änderung |
| `last_synced_at` | DateTimeField (nullable) | Letzte Synchronisierung |
| `deleted_at` | DateTimeField (nullable) | Soft-Delete |
| `created_at` / `updated_at` | DateTimeField | Timestamps |

**Constraint:** `UniqueConstraint(fields=["outline_document_id"], condition=Q(deleted_at__isnull=True), name="uq_knowledge_doc_outline_id_active")`

### 3.4 Sync-Flow (Outline → Django)

```
Outline: Dokument erstellt/geändert
  → Webhook POST an research-hub (HMAC-SHA256 signiert)
  → Webhook-Handler verifiziert Signatur
  → Celery-Task: sync_outline_document_task.delay(doc_id)
  → Service: KnowledgeDocumentService.sync_from_outline()
    → Outline API: documents.info(id=doc_id)
    → KnowledgeDocument.objects.update_or_create()
  → Wenn AI-Enrichment nötig:
    → Celery-Task: enrich_knowledge_document_task.delay(public_id)
    → llm_mcp → Summary + Keywords generieren (ADR-116 Kosten-Tracking)
```

### 3.5 outline_mcp — FastMCP Server

Vier Tools für Windsurf/Cascade:

| Tool | Beschreibung |
|------|-------------|
| `search_knowledge(query, limit)` | Volltext-Suche über alle Dokumente |
| `get_document_content(document_id)` | Vollständigen Markdown-Inhalt abrufen |
| `create_concept(title, content, collection_name)` | Neues Konzept in Outline erstellen |
| `list_recent_concepts(limit)` | Zuletzt aktualisierte Dokumente |

**Registrierung** in Windsurf als MCP-Server (`outline-knowledge`), analog zu `platform-context`.

### 3.6 Docker Deployment

```yaml
# docker-compose.outline.yml — auf hetzner-prod
name: outline-stack

networks:
  outline_net:
    name: iil_outline_net
    driver: bridge

services:
  outline:
    image: outlinewiki/outline:1.6.0
    container_name: iil_knowledge_outline
    networks: [outline_net]
    ports:
      - "127.0.0.1:3100:3000"
    environment:
      DATABASE_URL: "postgres://${OUTLINE_DB_USER}:${OUTLINE_DB_PASS}@iil_knowledge_outline_db:5432/outline?sslmode=disable"
      REDIS_URL: "redis://:${OUTLINE_REDIS_PASSWORD}@iil_knowledge_outline_redis:6379"
      SECRET_KEY: "${OUTLINE_SECRET_KEY}"
      UTILS_SECRET: "${OUTLINE_UTILS_SECRET}"
      URL: "https://knowledge.iil.pet"
      PORT: "3000"
      FORCE_HTTPS: "false"
      FILE_STORAGE: local
      FILE_STORAGE_LOCAL_ROOT_DIR: /var/lib/outline/data
      FILE_STORAGE_UPLOAD_MAX_SIZE: "26214400"
      # OIDC via authentik (ADR-142) — app-slug: outline
      OIDC_CLIENT_ID: "${OUTLINE_OIDC_CLIENT_ID}"
      OIDC_CLIENT_SECRET: "${OUTLINE_OIDC_CLIENT_SECRET}"
      OIDC_AUTH_URI: "https://id.iil.pet/application/o/authorize/"
      OIDC_TOKEN_URI: "https://id.iil.pet/application/o/token/"
      OIDC_USERINFO_URI: "https://id.iil.pet/application/o/userinfo/"
      OIDC_DISPLAY_NAME: "IIL Platform Login"
      OIDC_SCOPES: "openid profile email"
      OIDC_USERNAME_CLAIM: "preferred_username"
      NODE_TLS_REJECT_UNAUTHORIZED: "0"  # self-signed cert behind Cloudflare Tunnel
    extra_hosts:
      - "id.iil.pet:host-gateway"  # resolve to Docker host for server-to-server OIDC calls
    env_file: [.env.outline]
    volumes:
      - outline_data:/var/lib/outline/data
    depends_on:
      outline_db:
        condition: service_healthy
      outline_redis:
        condition: service_healthy
    mem_limit: 512m
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "node -e \"require('http').get('http://localhost:3000/_health', r => process.exit(r.statusCode === 200 ? 0 : 1))\""]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  outline_db:
    image: postgres:16
    container_name: iil_knowledge_outline_db
    networks: [outline_net]
    environment:
      POSTGRES_USER: "${OUTLINE_DB_USER}"
      POSTGRES_PASSWORD: "${OUTLINE_DB_PASS}"
      POSTGRES_DB: outline
    volumes:
      - outline_db_data:/var/lib/postgresql/data
    mem_limit: 256m
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${OUTLINE_DB_USER} -d outline"]
      interval: 30s
      timeout: 5s
      retries: 3

  outline_redis:
    image: redis:7-alpine
    container_name: iil_knowledge_outline_redis
    networks: [outline_net]
    command: redis-server --requirepass "${OUTLINE_REDIS_PASSWORD}"
    mem_limit: 64m
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${OUTLINE_REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  outline_data:
  outline_db_data:
```

### 3.7 Ressourcen-Bedarf

| Container | RAM | Disk |
|-----------|-----|------|
| Outline (Node.js) | 512 MB | ~200 MB (Image + Data) |
| outline_db (PostgreSQL 16) | 256 MB | ~200 MB (initial) |
| outline_redis | 64 MB | ~50 MB |
| **Gesamt** | **~832 MB** | **~450 MB** |

Zusammen mit authentik (ADR-142): ~2.15 + 0.83 = **~3 GB zusätzlich**. Server: 10 + 3 = ~13 GB von 22 GB — machbar.

### 3.8 Auth-Integration (ADR-142)

Outline nutzt authentik als OIDC-Provider (Phase 1, Step 1.4 in ADR-142):

- Interne User (platform-admin, developer) loggen sich via `id.iil.pet` ein
- Outline erstellt User automatisch beim ersten OIDC-Login
- Gruppen-Mapping: authentik-Gruppen → Outline-Rollen (Admin, Member, Viewer)

### 3.9 Nginx-Konfiguration

```nginx
# /etc/nginx/conf.d/outline.conf
server {
    listen 80;
    server_name knowledge.iil.pet;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name knowledge.iil.pet;

    ssl_certificate     /etc/letsencrypt/live/knowledge.iil.pet/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/knowledge.iil.pet/privkey.pem;

    client_max_body_size 25m;

    # WebSocket fuer Echtzeit-Kollaboration (Outline Y.js)
    location /realtime {
        proxy_pass          http://127.0.0.1:3000;
        proxy_http_version  1.1;
        proxy_set_header    Upgrade    $http_upgrade;
        proxy_set_header    Connection "upgrade";
        proxy_set_header    Host              $host;
        proxy_set_header    X-Real-IP         $remote_addr;
        proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass          http://127.0.0.1:3000;
        proxy_http_version  1.1;
        proxy_set_header    Host              $host;
        proxy_set_header    X-Real-IP         $remote_addr;
        proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto $scheme;
    }
}
```

### 3.10 Sicherheit & Backup

| Aspekt | Maßnahme |
|--------|----------|
| **Redis-Auth** | `requirepass` auf outline_redis — kein unauth. Zugriff |
| **Netzwerk-Isolation** | Eigenes Docker-Netzwerk `iil_outline_net` |
| **Backup** | Täglicher `pg_dump` Cron auf `outline_db` → `/opt/backups/outline/`. Rotation: 7 Tage. |
| **Secrets** | Alle Credentials via `read_secret()` (ADR-045) |
| **Version-Pinning** | `outlinewiki/outline:1.6.0` — Update nur gezielt nach Test |

### 3.11 outline_mcp — async/sync Hinweis (K3)

Die `outline-wiki-api` Python-Bibliothek ist **synchron** (blockierende HTTP-Requests). Da FastMCP Tools `async def` sind, müssen alle Outline-API-Calls via `asyncio.to_thread()` in den Thread-Pool ausgelagert werden. **Niemals `asyncio.run()` im ASGI-Kontext** (Platform-Standard).

### 3.12 Dependencies

```txt
# research-hub requirements.txt Ergänzung
outline-wiki-api==0.3.2    # Version gepinnt (Community-Wrapper)
```

---

## 4. Workflows (konkreter Mehrwert)

### 4.1 Neues Konzept schreiben

```
Vorher:  Notiz im Kopf → lokal irgendwo → Cascade kennt es nicht → Wiederholen
Nachher: Outline (knowledge.iil.pet) → Markdown schreiben → Webhook → research-hub sync
         → Cascade: search_knowledge("bieterpilot phase 2") → findet Konzept sofort
```

### 4.2 ADR-Draft → finales ADR

```
Outline: ADR-Draft in "Konzepte (in Arbeit)"
  → Wenn fertig: Cascade erstellt ADR-Datei in platform/docs/adr/ (via edit)
  → PR für Review → nach Merge: Outline-Doc in "ADRs (final)" verschieben
```

### 4.3 Recherche festhalten

```
Recherche fertig → Outline: neues Doc in "Recherchen"
  → Celery: AI-Enrichment (Summary + Keywords via llm_mcp)
  → Nächste Woche: Cascade findet es via search_knowledge()
```

### 4.4 Cascade-Integration

```
User: "Gibt es ein Konzept zur ship-workflow.sh?"
Cascade → search_knowledge("ship-workflow staging production promote")
  → Findet Konzept aus letzter Woche
  → Implementiert direkt darauf aufbauend
```

---

## 5. Implementierungsplan

| Phase | Inhalt | Abhängigkeit | Aufwand |
|-------|--------|-------------|---------|
| **1** | Outline Docker Compose deployen, Nginx-Config, SSL | — | 2h |
| **2** | DNS: `knowledge.iil.pet` (Cloudflare A-Record) | Phase 1 | 0.5h |
| **3** | OIDC-Integration mit authentik (ADR-142 Phase 1) | ADR-142 Step 1.4 | 1h |
| **4** | Collections-Struktur anlegen, initiale Docs importieren | Phase 1 | 1h |
| **5** | `KnowledgeDocument` Model + Migration in research-hub | — | 1.5h |
| **6** | Webhook-Handler + HMAC-Signatur-Verifikation | Phase 5 | 1.5h |
| **7** | `KnowledgeDocumentService` + `outline-wiki-api` Client | Phase 5 | 2h |
| **8** | Celery-Tasks: sync + AI-Enrichment via llm_mcp | Phase 7 | 2h |
| **9** | `outline_mcp` FastMCP Server | Phase 7 | 2h |
| **10** | Windsurf-Konfiguration: outline_mcp als MCP-Server registrieren | Phase 9 | 0.5h |
| **11** | Tests: pytest-Suite für Webhook, Service, MCP-Tools | Phase 8+9 | 2h |

**Gesamt: ~16h über 2-3 Sessions**

**Hinweis:** Phase 3 (OIDC) kann übersprungen werden, wenn authentik (ADR-142) noch nicht deployed ist. Outline kann initial mit API-Token-Auth betrieben werden. OIDC wird nachgerüstet.

---

## 6. Offene Fragen

| Frage | Empfehlung | Status |
|-------|-----------|--------|
| ADR-Git-Sync automatisieren? | Phase 2+ — initial manuell (Copy-Paste von Git nach Outline). Automatisierung via GitHub Webhook → Outline API ist möglich. | Offen |
| Full-Sync als Fallback? | Täglicher Celery-Beat-Task: alle Outline-Docs re-syncen (Schutz gegen verpasste Webhooks). | Entschieden |
| Outline-Version pinnen? | Ja — `outlinewiki/outline:1.6.0` statt `:latest`. Update nur gezielt. | Entschieden |
| Wer darf Dokumente erstellen? | Alle authentik-User mit Gruppe `developer` oder `platform-admin`. | Entschieden |
| Kommt `outline-wiki-api` nach research-hub requirements? | Ja — `pip install outline-wiki-api` in research-hub + mcp-hub. | Entschieden |

---

## 7. Abgrenzung

- **Outline = Editor + Store für Inhalte** — Django speichert nur Metadaten, keine Inhalte duplizieren
- **Kein Ersatz für ADR-Git-Workflow** — finale ADRs bleiben in Git. Outline für Drafts + Konzepte.
- **Kein eigenes CMS** — Outline ist ein Wiki, kein Content-Management-System
- **Kein Kunden-Zugang in Phase 1** — nur internes Team. Kunden-Zugang erst wenn ADR-142 Phase 2 abgeschlossen.
- **Lizenz: BSL 1.1** — kostenlos für Solo/kleines Team, kein kommerzieller Weiterverkauf als gehosteter Service

---

## 8. Kosten

| Komponente | Lizenz | Kosten |
|------------|--------|--------|
| Outline (self-hosted) | BSL 1.1 | **0 €** |
| outline-wiki-api (Python) | MIT | **0 €** |
| Hetzner CPX52 (bereits vorhanden) | — | **0 €** extra |
| AI-Enrichment (llm_mcp) | — | ~$0.01/Dokument |

**Gesamtkosten: ~0 € + marginale LLM-Kosten.**

---

## 9. Konsequenzen

### Positiv

- **Zentraler Ort für alle Wissensartefakte** — Konzepte, Recherchen, Meeting-Notes
- **Cascade bekommt Zugriff** via outline_mcp — löst AI Context Amnesia (ADR-132)
- **Markdown-nativer Editor** — identisches Format wie ADRs
- **AI-Enrichment automatisch** — Summary + Keywords ohne manuellen Aufwand
- **OIDC-Integration** mit authentik (ADR-142) — kein zusätzliches Login

### Negativ / Risiken

- **Zusätzliche Infrastruktur**: ~832 MB RAM, 3 neue Container
- **Outline ist Node.js** — Fremdkörper im Python-Stack (aber nur als Service, keine Codebasis)
- **BSL 1.1 Lizenz** — kein kommerzieller Weiterverkauf möglich
- **Webhook-Abhängigkeit** — bei Ausfall: täglicher Full-Sync als Fallback
- **Doppelte Datenhaltung** — Outline hat Inhalt, Django hat Metadaten. Muss konsistent bleiben.

---

## 10. Referenzen

- Outline: https://www.getoutline.com / https://github.com/outline/outline
- authentik Integration: ADR-142
- Konzept-Input: `docs/adr/inputs/dms/konzept-outline-research-hub.md`
- outline-wiki-api (PyPI): https://pypi.org/project/outline-wiki-api/
