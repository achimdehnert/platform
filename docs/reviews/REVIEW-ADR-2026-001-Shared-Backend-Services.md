# Architecture Review: ADR-2026-001 — Shared Backend Services

| | |
|---|---|
| **Reviewer** | Cascade (IT-Architekt-Perspektive) |
| **Datum** | 2026-02-12 |
| **Reviewed ADR** | ADR-2026-001 Shared Backend Services Library |
| **Verdict** | ⚠️ **REVISION REQUIRED** — gutes Problemstatement, aber erhebliche Architektur- und Konsistenzprobleme |

---

## Bewertungsskala

| Symbol | Bedeutung |
|--------|-----------|
| 🔴 | **Blocker** — muss vor Annahme gelöst werden |
| 🟡 | **Signifikant** — sollte adressiert werden |
| 🟢 | **Minor** — Empfehlung, kein Blocker |

---

## 1. ADR-Nummerierung und Formatierung

### 🟡 F-01: ADR-Nummerierung inkonsistent

Das ADR verwendet `ADR-2026-001` (Jahresprefix), während alle Platform-ADRs sequentiell nummeriert sind: `ADR-009`, `ADR-012`, `ADR-013`, `ADR-014`, `ADR-016`, `ADR-022`. Auch die App-ADRs folgen dem Schema `ADR-024`, `ADR-025`, `ADR-026`.

**Empfehlung:** Nächste freie Nummer verwenden (vermutlich `ADR-027` oder Platform-spezifisch weiterführen). Einheitliche Nummerierung ist Pflicht für Traceability.

### 🟢 F-02: Fehlende Pflichtfelder

Platform-ADRs haben üblicherweise: Status, Supersedes/Superseded-by, Related ADRs, Review-Datum. Hier fehlen:
- **Related ADRs**: ADR-009 (Platform Architecture), ADR-012 (MCP Quality Standards)
- **Supersedes**: keines (ist ok)
- **Review-Date**: fehlt

---

## 2. Scope und Ökosystem-Konsistenz

### 🔴 S-01: Bestehende Projekte ignoriert

> *"Betrifft: wedding-hub, iil.pet, zukünftige Django-Projekte"*

Die Plattform hat **6 produktive Django-Projekte**: bfagent, risk-hub (Schutztat), travel-beat (DriftTales), weltenhub (Weltenforger), trading-hub, pptx-hub. Das ADR ignoriert alle existierenden Projekte und fokussiert nur auf wedding-hub + hypothetische zukünftige Apps.

Wenn die Library einen echten Mehrwert hat, muss sie **rückwärtskompatibel für die bestehenden 6 Projekte** sein — nicht nur für ein neues. Andernfalls löst sie das Duplikationsproblem nicht.

**Empfehlung:** Scope auf alle Django-Projekte der Plattform erweitern. Migration-Strategie pro bestehendem Projekt skizzieren.

### 🔴 S-02: Bestehende Package-Strategie ignoriert

`platform/packages/` enthält bereits 8 Packages:
```
bfagent-core/  bfagent-llm/  cad-services/  creative-services/
inception-mcp/  sphinx-export/  task_scorer/  adr-review/
```

Das ADR erwähnt dieses bestehende Ökosystem mit keinem Wort. Zentrale Fragen:
- Wie verhält sich `iil-django-commons` zu diesen Packages?
- Gehört es in `platform/packages/` oder in ein eigenes Repo?
- Gibt es Dependency-Konflikte?

**Empfehlung:** Explizit klären, ob `iil-django-commons` als `platform/packages/django-commons/` lebt (Monorepo, konsistent mit Bestand) oder als eigenständiges Repo (wie vorgeschlagen, aber mit Begründung warum anders).

### 🟡 S-03: Onboarding-Workflow nicht referenziert

Die Plattform hat einen etablierten Onboarding-Workflow (`.windsurf/workflows/onboard-repo.md`) mit Compliance-Matrix, Naming Conventions und Reusable CI/CD Workflows. Das ADR erwähnt Cookiecutter als Ergänzung, integriert aber nicht den bestehenden Onboarding-Prozess.

**Empfehlung:** Cookiecutter-Ergänzung durch Integration in den bestehenden `onboard-repo`-Workflow ersetzen.

---

## 3. Architekturprinzipien-Verletzungen

### 🔴 A-01: Database-First-Prinzip nicht adressiert

ADR-009 definiert **Database-First** als Kernprinzip:
> *"Die Datenbank ist die Single Source of Truth. Schema-Änderungen zuerst. FK statt String. Validierung in DB."*

Das ADR enthält **kein einziges Datenbankschema**. Alle 8 Module sind reine Middleware/Config-Layer. Dabei haben mehrere Module datenbanknahe Aspekte:
- **Rate Limiting**: Wo werden Zähler persistiert? Nur Redis? Was bei Redis-Ausfall?
- **Health Checks**: Brauchen DB-Checks `SELECT 1` — aber keine eigenen Tabellen?
- **Email**: Transactional Emails sollten in einer `email_log`-Tabelle auditierbar sein (Database-First)
- **Monitoring**: Sollen Metriken auch in der DB landen (Audit)?

**Empfehlung:** Für jedes Modul klären: Hat es DB-Aspekte? Wenn ja, Schema definieren. Wenn nein, explizit begründen warum nicht.

### 🔴 A-02: Multi-Tenancy komplett ausgeblendet

Die globalen Entwicklungsregeln sind eindeutig:
> *"Jedes User-Data-Model MUSS `tenant_id` haben. Alle Queries MÜSSEN nach `tenant_id` filtern."*

Das ADR erwähnt `tenant_id` kein einziges Mal. Dabei ist Tenant-Isolation für mehrere Module kritisch:

| Modul | Tenant-Relevanz |
|-------|-----------------|
| **Cache** | Cache-Keys MÜSSEN `tenant_id` enthalten, sonst Data-Leak |
| **Rate Limiting** | Per-Tenant Limits? Per-User-within-Tenant? |
| **Logging** | Correlation-ID MUSS `tenant_id` enthalten |
| **Email** | Absender/Quota per Tenant |
| **Monitoring** | Metriken per Tenant isoliert? |

**Empfehlung:** Jedes Modul muss explizit definieren, wie es mit `tenant_id` umgeht. `CorrelationIDMiddleware` muss `request.tenant_id` in den Log-Context injizieren.

### 🟡 A-03: Separation of Concerns — Monolith-Library vs. Micro-Packages

Das ADR bündelt **8 völlig unabhängige Concerns** in ein Package:
- Logging hat nichts mit Email zu tun
- Monitoring hat nichts mit Rate Limiting zu tun
- Security Headers hat nichts mit Celery Tasks zu tun

Die `[extras]`-Syntax (`pip install iil-django-commons[cache,ratelimit]`) ist ein Workaround, kein echtes Separation of Concerns. Alle Module teilen sich:
- Versionsnummer (Major-Bump in `security` zwingt auch `logging`-Consumer zum Upgrade)
- Release-Zyklus
- CI Pipeline
- Changelog

**Empfehlung:** Evaluieren, ob ein Set kleiner, unabhängiger Packages (`iil-django-logging`, `iil-django-health`, etc.) nicht besser zum Prinzip der Isolation passt. Alternativ: den Monolith-Ansatz explizit begründen (z.B. "Module interagieren untereinander, daher gemeinsam versioniert").

### 🟡 A-04: Service-Layer-Pattern nicht beachtet

Die globalen Regeln definieren: `views.py → services.py → models.py`. Das ADR platziert Business-Logik direkt in Middleware-Klassen und Dekoratoren. Beispiel:

```python
# ADR schlägt vor:
@rate_limit(requests=10, window=60, key="user")
def api_endpoint(request): ...

# Platform-Pattern wäre:
# views.py → delegiert an services/ratelimit.py
```

Für einfache Middleware ist das akzeptabel, aber `EmailService` und `BaseTask` sollten dem Service-Layer-Pattern folgen.

---

## 4. Naming Conventions

### 🟡 N-01: Package-Name `iil-django-commons`

Probleme:
1. **`iil` als Prefix**: `iil.pet` ist eine Hosting-Domain, kein Produktname. Wenn sich die Domain ändert, ist der Package-Name veraltet.
2. **`commons`**: Generisch, vermittelt keinen Inhalt. Gängiger in der Java-Welt, unüblich in Python.
3. **Import-Path `iil_commons`**: Verstößt gegen die Naming Convention `{app}_{entity}`. Was ist die "App"? Was die "Entity"?

**Alternativen:**
- `platform-django` / `platform_django` — konsistent mit dem `platform`-Repo
- `iilpet-core` / `iilpet_core` — wenn Domain als Brand gewollt
- Oder einfach als `platform/packages/django-infrastructure/` im Monorepo

### 🟡 N-02: Settings-Namespace `IIL_COMMONS`

Ein einziges flaches Dictionary für 8 Module ist schlechte Praxis:

```python
# ADR schlägt vor:
IIL_COMMONS = {
    "LOG_FORMAT": "json",
    "CACHE_DEFAULT_TTL": 300,
    "RATE_LIMIT_DEFAULT": "100/h",
    "EMAIL_PROVIDER": "resend",
}
```

Probleme:
- Django-Konvention ist separate Settings per Concern: `CACHES`, `LOGGING`, `REST_FRAMEWORK`
- Kein Namespace-Scoping — `LOG_FORMAT` könnte mit anderem Package kollidieren
- Autovervollständigung und Dokumentation leiden

**Empfehlung:** Pro Modul eigener Namespace:
```python
IIL_LOGGING = {"FORMAT": "json", "LEVEL": "INFO"}
IIL_CACHE = {"DEFAULT_TTL": 300}
IIL_RATELIMIT = {"DEFAULT": "100/h"}
```

Oder besser: Django AppConfig mit `default_settings` Pattern.

---

## 5. Technische Redundanzen

### 🟡 T-01: Overlap mit Django Built-ins und etablierten Packages

| Modul | Bestehendes Äquivalent | Delta |
|-------|----------------------|-------|
| `security` | Django `SecurityMiddleware` + `django-csp` | Minimal — nur Wrapper |
| `ratelimit` | DRF `throttling` + `django-ratelimit` | Minimal — nur Config |
| `health` | `django-health-check` (2.5k ★, aktiv maintained) | Wrapper |
| `monitoring` | `django-prometheus` (1.5k ★) | Wrapper |
| `logging` | Django `LOGGING` dictconfig + `structlog` | Config-Helper |
| `cache` | Django `CACHES` + `django-redis` | Decorator-Layer |

Von den 8 Modulen sind **6 dünne Wrapper** um existierende, gut gewartete Packages. Die eigentliche Wertschöpfung ist:
1. Vorkonfiguration (opinionated defaults)
2. Konsistente Integration

Das ist kein "Package" — das ist ein **Settings-Template** oder **Django AppConfig mit Defaults**. Der Overhead eines eigenen PyPI-Packages mit Semver, Changelog, CI-Pipeline und Extras-Matrix ist dafür unverhältnismäßig.

### 🟡 T-02: Email-Modul ist premature

Drei Email-Provider (SMTP, Resend, Postmark) für eine Plattform, die aktuell **keinen transaktionalen Email-Versand** hat. YAGNI. Das Modul sollte erst dann entstehen, wenn ein konkreter Consumer existiert.

### 🟢 T-03: Prometheus ohne Grafana-Stack

Das ADR schlägt Prometheus-Metriken vor, aber der Server hat keinen Prometheus/Grafana-Stack. In den offenen Fragen steht: *"Hetzner Docker Compose (Prometheus + Grafana als Sidecars)"*. Das ist ein eigenes Infrastruktur-Projekt, kein Library-Modul.

---

## 6. Rollout und Migration

### 🟡 R-01: Unrealistischer Timeline

8 Wochen für 8 Module + Integration in 2 Projekte + CI Pipeline + Cookiecutter + Docs? Bei einem Ein-Personen-Entwickler mit 7 aktiven Repos ist das ambitioniert. Risiko: Die Library wird auf v0.1.0 stehen bleiben und verwaisen.

**Empfehlung:** Scope drastisch reduzieren. Phase 1: **nur** Logging + Health (die beiden Module mit dem klarsten ROI). Alles andere erst bei konkretem Bedarf.

### 🟡 R-02: Migrationsstrategie fehlt für Bestandsprojekte

Das ADR beschreibt Migration nur für wedding-hub (Sektion 6). Die 6 bestehenden Projekte werden ignoriert. Ohne Migrationspfad für z.B. risk-hub oder travel-beat ist der ROI fraglich — dann bleibt die Duplikation bestehen.

---

## 7. Was gut ist

Trotz der Kritikpunkte hat das ADR valide Aspekte:

- ✅ **Problemerkennung korrekt**: Code-Duplikation über Projekte ist ein reales Problem
- ✅ **Optionenbewertung solide**: Die 4 Optionen mit Vergleichsmatrix sind nachvollziehbar
- ✅ **Structured Logging mit Correlation-ID**: Echter Mehrwert, der in keinem Projekt existiert
- ✅ **Health-Check-Standardisierung**: Aktuell hat jedes Projekt einen anderen Endpoint (`/livez/`, `/health/`, `/healthz/`)
- ✅ **Risiko-Awareness**: Over-Engineering und YAGNI werden benannt (aber nicht konsequent angewandt)
- ✅ **pyproject.toml + PEP 621**: Korrekte Package-Tooling-Wahl

---

## 8. Empfehlung: Gegenvorschlag

Statt einer monolithischen Library empfehle ich einen **Drei-Stufen-Ansatz**:

### Stufe 1: `platform/packages/django-defaults/` (Woche 1-2)
Ein **leichtgewichtiges Django AppConfig** im bestehenden `platform/packages/` Monorepo:
- Opinionated `LOGGING` dictconfig mit structlog + Correlation-ID
- Standardisierter Health-Check unter `/health/` (vereinheitlicht `/livez/`, `/healthz/`, `/health/`)
- `tenant_id`-aware Log-Context-Middleware
- Installiert als Git-Dependency: `pip install git+...@v0.1.0#subdirectory=packages/django-defaults`

### Stufe 2: Onboarding-Workflow erweitern (Woche 3)
Den bestehenden `onboard-repo.md` Workflow um die Library-Integration ergänzen:
- `django-defaults` als Pflicht-Dependency
- Standard-Middleware-Stack dokumentiert
- Health-Endpoint-Convention vereinheitlicht

### Stufe 3: Module nach Bedarf auslagern (fortlaufend)
Wenn ein zweites Projekt ein Modul braucht, wird es extrahiert:
- Caching-Patterns → `platform/packages/django-cache/`
- Rate Limiting → `platform/packages/django-ratelimit/`
- Jeweils eigene Version, eigener Changelog

### Vorteile gegenüber ADR-Vorschlag:
| Aspekt | ADR-2026-001 | Gegenvorschlag |
|--------|--------------|----------------|
| Initaler Aufwand | 8 Module, 8 Wochen | 2 Module, 2 Wochen |
| YAGNI-Risiko | Hoch (6 Module ohne Consumer) | Niedrig (nur bei Bedarf) |
| Monorepo-Konsistenz | Neues Repo | `platform/packages/` |
| Tenant-Awareness | Fehlt | Von Anfang an |
| Versionierung | Ein Semver für alles | Pro Modul unabhängig |
| Breaking-Change-Blast-Radius | 8 Module betroffen | 1 Modul betroffen |

---

## 9. Zusammenfassung der Findings

| ID | Severity | Bereich | Finding |
|----|----------|---------|---------|
| F-01 | 🟡 | Format | ADR-Nummerierung inkonsistent |
| F-02 | 🟢 | Format | Fehlende Pflichtfelder |
| S-01 | 🔴 | Scope | Bestehende 6 Projekte ignoriert |
| S-02 | 🔴 | Scope | Bestehende Package-Strategie ignoriert |
| S-03 | 🟡 | Scope | Onboarding-Workflow nicht referenziert |
| A-01 | 🔴 | Architektur | Database-First nicht adressiert |
| A-02 | 🔴 | Architektur | Multi-Tenancy komplett ausgeblendet |
| A-03 | 🟡 | Architektur | Monolith-Library statt Micro-Packages |
| A-04 | 🟡 | Architektur | Service-Layer-Pattern nicht beachtet |
| N-01 | 🟡 | Naming | Package-Name `iil-django-commons` problematisch |
| N-02 | 🟡 | Naming | Flat Settings-Dict statt per-Modul Namespace |
| T-01 | 🟡 | Technik | 6/8 Module sind dünne Wrapper |
| T-02 | 🟡 | Technik | Email-Modul premature |
| T-03 | 🟢 | Technik | Prometheus ohne Stack |
| R-01 | 🟡 | Rollout | Unrealistischer Timeline |
| R-02 | 🟡 | Rollout | Migrationsstrategie für Bestand fehlt |

**Blocker (🔴): 4** | **Signifikant (🟡): 10** | **Minor (🟢): 2**
