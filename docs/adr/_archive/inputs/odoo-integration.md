# Odoo Integration \u2014 Input-Dokument f\u00fcr ADR-029

> **Typ:** Input / Entscheidungsgrundlage
> **Datum:** 2026-02-12
> **Ziel-ADR:** ADR-029 \u2014 Dual-Framework-Governance (Django + Odoo)
> **Quelle:** Architektur-Session 2026-02-12, ChatGPT-Analyse, Server-Setup

---

## 1. Strategische Entscheidungen

### 1.1 Koexistenz-Modell

| Entscheidung | Wert |
| --- | --- |
| **Django** | Bleibt dauerhaft f\u00fcr bestehende 7+ Apps |
| **Odoo** | Neue Apps f\u00fcr separate Business Cases |
| **Team** | Ein Entwicklungsteam betreut beide Frameworks |
| **Zeithorizont** | Dauerhaft parallel, kein Exit aus Django |

### 1.2 Begr\u00fcndung

- Django und Odoo adressieren **verschiedene Business Cases**
- Kein Migrations-Szenario \u2014 beide Plattformen sind gleichberechtigt
- Ein Team erfordert **konsistente Governance** \u00fcber Framework-Grenzen hinweg
- Django-Investment bleibt gerechtfertigt (7 aktive Produktions-Apps)

---

## 2. Odoo als Applikationsplattform

### 2.1 St\u00e4rken

- **RAD-Plattform:** Datenmodell + UI + Rechte + Workflow eng integriert
- **ORM:** Python-Klassen mit automatischer Persistenz, Recordset-basiert
- **UI:** Metadaten-getriebene Views (Form/List/Kanban/Pivot/Graph), OWL f\u00fcr Custom-Frontend
- **Security:** Deklaratives Rollen-/Rechte-System (Gruppen, Access Rights, Record Rules)
- **Modulsystem:** Saubere Paketierung, Abh\u00e4ngigkeitsverwaltung, kundenspezifisches Customizing
- **Integration:** External API (XML-RPC, JSON-RPC) f\u00fcr Satelliten-Services

### 2.2 Risiken

- **Upgrade-Kosten:** Major-Versionen alle ~2 Jahre, 3 Jahre Support, Migrationsaufwand
- **Framework-Lock-in:** Je mehr Kern-\u00dcberschreibungen, desto teurer Upgrades
- **Frontend-Doku:** Nicht immer aktuell \u2014 OWL-Referenzen bevorzugen
- **Security-Fehlkonfiguration:** Deklarativ = leicht falsch konfiguriert ohne Reviews
- **Lizenzierung:** Community (LGPL) vs. Enterprise kl\u00e4ren, IP-Abgrenzung fr\u00fch definieren

### 2.3 Eignungsbewertung

| Eignung | Kriterien |
| --- | --- |
| **Sehr gut** | Datenmodellgetriebene Business-Apps, ERP-nahe Dom\u00e4nen, Standard-Backoffice-UI |
| **Mittel** | Hochgradig individuelle UI/UX, Nicht-ERP Realtime/Streaming |
| **Riskant** | Massive Kern-\u00dcberschreibungen, kein Upgrade-Plan, keine Tests |

### 2.4 Best Practices

- **Standard first:** Standardmodule als Backbone, Custom nur f\u00fcr Differenzierung
- **Modularisierung nach Dom\u00e4nen:** Pro Dom\u00e4ne ein Modul, klare Abh\u00e4ngigkeiten
- **Upgrade-F\u00e4higkeit als NFR:** Erweiterung/Vererbung statt Monkey-Patches
- **Testpyramide:** Unit Tests + Tours f\u00fcr kritische E2E-Prozesse
- **Dev/Staging/Prod:** Git-Branching + staging builds strikt leben

### 2.5 Framework-Entscheidungsmatrix

| Kriterium | Django w\u00e4hlen | Odoo w\u00e4hlen |
| --- | --- | --- |
| **UI-Typ** | Custom (Tailwind + HTMX) | Standard Backoffice |
| **ERP-Funktionen** | Nicht sinnvoll | Invoicing, CRM, Inventory nativ |
| **Multi-Tenancy** | Subdomain-basiert (platform-core) | res.company / Multi-DB |
| **API-First** | DRF + REST | JSON-RPC / REST (OCA) |
| **Rapid Prototyping** | Django-Templates | Odoo Views + Studio |
| **Business Logic** | Service Layer Pattern | Odoo Model Methods |
| **Reporting** | Custom (Charts.js, PDF) | QWeb Reports, Pivot nativ |
| **Workflow** | Celery + Custom | Automated Actions nativ |

---

## 3. Infrastruktur-Entscheidungen

### 3.1 Separate Server

| Aspekt | Django-Server | Odoo-Server |
| --- | --- | --- |
| **IP** | 88.198.191.108 | 46.225.127.211 |
| **Typ** | CX (8 GB, 4 vCPU) | CPX32 (8 GB, 4 vCPU) |
| **Location** | nbg1, N\u00fcrnberg | nbg1-dc3, N\u00fcrnberg |
| **Container** | 32 (7 Django-Apps + Infra) | 2 (Odoo + PostgreSQL) |
| **RAM-Nutzung** | ~50% (3.9 GB) | ~11% (870 MB) |

### 3.2 Begr\u00fcndung f\u00fcr Trennung

1. **Blast Radius:** Zwei Business Cases = zwei Ausfalldom\u00e4nen
2. **Ressourcen:** Django-Server bei 50% RAM
3. **PostgreSQL-Konflikte:** Odoo hat spezifische PG-Anforderungen (unaccent, Locale)
4. **Unabh\u00e4ngige Skalierung:** Jeder Server nach Bedarf dimensionierbar
5. **Experiment-Exit:** Server l\u00f6schen ohne Cleanup auf Prod

### 3.3 Netzwerk

- Beide Server im selben Hetzner-Datacenter (nbg1)
- Private Networking via Hetzner vSwitch m\u00f6glich (kostenlos, low-latency)
- Inter-Server-Kommunikation via REST/JSON-RPC \u00fcber Private Network

---

## 4. Framework-Abgrenzung

### 4.1 Django-\u00d6kosystem (bestehend)

| App | Funktion | Status |
| --- | --- | --- |
| bfagent | Book Factory Agent | Produktion |
| risk-hub (Schutztat) | Occupational Safety SaaS | Produktion |
| travel-beat (DriftTales) | Travel Story Platform | Produktion |
| weltenhub (Weltenforger) | Story Universe Platform | Produktion |
| pptx-hub | Presentation Studio | Produktion |
| trading-hub | Trading Platform | Produktion |
| wedding-hub | Wedding Planning | Produktion |

### 4.2 Odoo-\u00d6kosystem (geplant)

- Erster Use Case: **Management-Interface f\u00fcr produktionsnahe Daten**
- Architektur: Odoo als Reporting/Management UI + Security + Workflow
- Datenquelle: Read-Replica / ETL in Odoo-Reporting-Models (nicht direkt Prod-DB)

### 4.3 Was Odoo nativ mitbringt

| Concern | Django (Custom) | Odoo (Built-in) |
| --- | --- | --- |
| Multi-Tenancy | SubdomainTenantMiddleware | res.company + Multi-Company Rules |
| RBAC | CorePermission + CoreRolePermission | res.groups + ir.rule + ir.model.access |
| User Management | CoreUser mit SSO | res.users + auth_signup + OAuth |
| Audit Trail | AuditEvent + emit_audit_event() | mail.tracking.value + Chatter |
| Event System | OutboxMessage | bus.bus + base_automation |
| Request Context | contextvars + RequestContext | self.env (Environment) |
| DB Migrations | Django Migrations (explizit) | Odoo ORM Auto-Migration |
| Admin UI | Django Admin | Odoo Backend Views |

**Konsequenz:** `platform-core` hat kein \u00c4quivalent in Odoo \u2014 Odoo bringt alles nativ.

---

## 5. Shared Governance

### 5.1 Was geteilt werden SOLL

| Concern | Mechanismus | Framework-agnostisch? |
| --- | --- | --- |
| **ADRs** | `platform/docs/adr/` | Ja |
| **Naming Conventions** | Governance-Dokument | Ja |
| **CI/CD Basis-Patterns** | Reusable Workflows | Teilweise |
| **API-Contracts** | Pydantic / JSON-Schema | Ja |
| **Infrastructure** | Docker, Nginx, PostgreSQL, TLS | Ja |
| **Monitoring** | Health Endpoints, Log-Patterns | Ja |
| **Backup-Strategie** | pg_dump-basiert | Ja |
| **Firewall-Patterns** | Hetzner Firewall (22, 80, 443, ICMP) | Ja |

### 5.2 Gemeinsame Release-Standards

| Regel | Staging | Production |
| --- | --- | --- |
| **Image Tag** | SHA (immutable) | semver vX.Y.Z |
| **Trigger** | CI success auf main | Push tag v* |
| **Approval** | Automatisch | Required Reviewers |
| **Rollback** | Tag zur\u00fccksetzen | deploy-remote.sh --rollback-to |

### 5.3 Gemeinsame Architekturprinzipien

- Standard first, custom only for differentiation
- Upgrade-/Migrationsf\u00e4higkeit ist ein NFR
- Tests sind Teil des Release-Artefakts
- Reporting-Workloads niemals direkt auf Prod-Systeme
- Build once, deploy many (immutable Container Images)

---

## 6. Nicht-teilbare Concerns

### 6.1 Framework-spezifisch \u2014 KEIN Sharing

| Aspekt | Warum nicht teilbar |
| --- | --- |
| **ORM Models** | Django ORM und Odoo ORM fundamental inkompatibel |
| **Middleware / Controller** | Verschiedene Request Lifecycles |
| **Template-System** | Django Templates / Jinja2 vs. QWeb |
| **Auth/Session** | Django Auth vs. Odoo Auth |
| **Migrations** | Explizit (Django) vs. Auto (Odoo) |

### 6.2 Anti-Patterns (vermeiden)

| Anti-Pattern | Warum schlecht |
| --- | --- |
| Shared ORM Base-Class | Zwei verschiedene ORMs |
| Shared Middleware | Werkzeug (Odoo) vs. Django Middleware |
| Shared Context-Management | self.env vs. contextvars |
| Abstraktes Permission-System | ir.rule vs. Django RBAC zu verschieden |

---

## 7. Deploy-Framework Mapping

### 7.1 deploy-remote.sh Review-Findings

Das bestehende Deploy-Script ist solide (Expand-only Gate, Healthcheck + Rollback,
Audit Trail, Exit Codes). Odoo-Anpassungen:

| Aspekt | Django (aktuell) | Odoo (Anpassung) |
| --- | --- | --- |
| **Migration** | python manage.py migrate | compose --profile migration run --rm app-migrate |
| **Health Port** | 8000 | 8069 |
| **Health Endpoint** | /healthz/ | /web/login (oder custom /healthz) |
| **collectstatic** | python manage.py collectstatic | Entf\u00e4llt (Odoo Assets nativ) |
| **Backup** | pg_dumpall | pg_dump -Fc + Filestore-Snapshot |
| **Worker** | Celery Worker Service | Odoo Workers (integriert) |

### 7.2 Compose-Design f\u00fcr Odoo

- **app-web:** Odoo Runtime (proxy_mode, Workers)
- **app-migrate:** Profil migration, --stop-after-init, -u modules
- **postgres:** PG 16 mit Healthcheck
- **nginx:** Reverse Proxy mit WebSocket-Support

Vollst\u00e4ndige Templates: siehe `deployment/templates/odoo/`

### 7.3 CI f\u00fcr Odoo

- Neuer Reusable Workflow: `_ci-odoo.yml`
- Lint: ruff auf Custom Addons
- Test: Odoo mit --test-enable --stop-after-init
- Build/Push: Identisch zum Django-Standard (GHCR, semver + SHA Tags)

---

## 8. Auswirkungen auf bestehende ADRs

### 8.1 ADR-027 (Shared Backend Services)

| Package | Odoo-relevant? | Empfehlung |
| --- | --- | --- |
| django-logging | Nein, Django-only | Aufwand/Nutzen pr\u00fcfen |
| django-health | Nein, Django-only | Aufwand/Nutzen pr\u00fcfen |
| platform-core | Nein, Django-only | Bleibt als Django-Foundation |

Team-Kapazit\u00e4t flie\u00dft jetzt auch in Odoo. Priorisierung anpassen.

### 8.2 ADR-028 (Platform Context)

- Rename best\u00e4tigt: bfagent-core -> platform-core
- Scope: Nur Django-Foundation, kein Anspruch auf Odoo-Kompatibilit\u00e4t
- Review-Findings (4 Blocker) m\u00fcssen gel\u00f6st werden

### 8.3 ADR-022 (Platform Consistency)

Compliance-Checkliste um Odoo-Sektion erg\u00e4nzen:

- `__manifest__.py` mit korrekten Abh\u00e4ngigkeiten
- `ir.model.access.csv` f\u00fcr alle Models
- `security.xml` f\u00fcr Record Rules
- Docker-Setup folgt Compose-Pattern
- Nginx Reverse Proxy mit WebSocket-Support
- CI mit ruff / pylint-odoo Linting

---

## 9. Offene Fragen

| Nr | Frage | Priorit\u00e4t |
| --- | --- | --- |
| Q1 | Welche konkreten Business Cases werden in Odoo umgesetzt? | Hoch |
| Q2 | Brauchen Django-Apps und Odoo-Apps API-Kommunikation? | Hoch |
| Q3 | Odoo Community vs. Enterprise Edition? | Hoch |
| Q4 | Shared Authentication (SSO) zwischen Django und Odoo? | Mittel |
| Q5 | Domain-Strategie? (odoo.example.com vs. app.example.com) | Mittel |
| Q6 | Hetzner Private Network f\u00fcr Inter-Server-Kommunikation? | Niedrig |
| Q7 | Backup-Rotation und Monitoring f\u00fcr zweiten Server? | Mittel |

---

## 10. Server-Setup Referenz

### 10.1 Odoo-Server (eingerichtet 2026-02-12)

| Komponente | Version / Detail |
| --- | --- |
| **Server** | odoo-prod, 46.225.127.211, CPX32 |
| **OS** | Ubuntu 24.04.3 LTS |
| **Docker** | 29.2.1 + Compose v5.0.2 |
| **Odoo** | 18.0 (Official Docker Image) |
| **PostgreSQL** | 16-alpine |
| **Nginx** | 1.24.0 (Reverse Proxy) |
| **Certbot** | Installiert, bereit f\u00fcr SSL |
| **Firewall** | fw-odoo-prod (TCP 22/80/443, ICMP) |

### 10.2 Pfade auf dem Server

```text
/opt/odoo/
\u251c\u2500\u2500 .env                    # Credentials (chmod 600)
\u251c\u2500\u2500 docker-compose.yml      # Stack-Definition
\u251c\u2500\u2500 odoo.conf               # 4 Workers, proxy_mode
\u251c\u2500\u2500 addons/                 # Custom Odoo-Module
\u251c\u2500\u2500 data/                   # Daten-Verzeichnis
\u2514\u2500\u2500 backups/                # Backup-Verzeichnis
```

### 10.3 Ressourcen nach Setup

- **RAM:** 870 / 7.745 MB (11,2%)
- **Disk:** 5,3 / 150 GB (4%)
- **Load:** 0,37 auf 4 Cores

---

## Zugeh\u00f6rige Dateien

- `docs/guides/FRAMEWORK-GUIDE.md` \u2014 Wann Odoo, wann Django, wann Hybrid
- `deployment/templates/odoo/docker-compose.prod.yml` \u2014 Odoo Compose Template
- `deployment/templates/odoo/Dockerfile` \u2014 Odoo Image Baseline
- `deployment/scripts/backup-odoo.sh` \u2014 DB + Filestore Backup
