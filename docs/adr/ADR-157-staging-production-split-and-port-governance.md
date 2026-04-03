---
parent: Decisions
nav_order: 157
title: "ADR-157: Adopt same-port staging on Dev Desktop with automated port governance and onboarding"
status: accepted
amended: 2026-04-02
date: 2026-04-02
deciders: Achim Dehnert
consulted: Cascade AI
informed: []
amends: ["ADR-063-staging-environment-strategy.md"]
related: ["ADR-021-unified-deployment-pattern.md", "ADR-075-deployment-execution-strategy.md", "ADR-106-port-audit.md", "ADR-156-reliable-deployment-pipeline.md"]
implementation_status: none
---

# Adopt same-port staging on Dev Desktop with automated port governance and onboarding

<!-- Drift-Detector-Felder
staleness_months: 6
drift_check_paths:
  - infra/ports.yaml
  - .windsurf/workflows/onboard-repo.md
  - .windsurf/workflows/ship.md
supersedes_check: ADR-063
-->

---

## 1. Context and Problem Statement

### 1.0 Beziehung zu ADR-063

ADR-063 ("Staging Environment Strategy", Accepted 2026-02-22) wählte **Option 3:
Branch-basiertes Staging auf dem damaligen dev-server (46.225.113.1) mit Port-Offset +100**.

Diese Entscheidung ist **überholt**, weil:
- Der alte dev-server (46.225.113.1) nicht mehr existiert
- Port-Offset +100 zu Konflikten führt (risk-hub staging 8099 = tax-hub prod 8099)
- Ein dedizierter Dev Desktop (88.99.38.75) seit 2026-04-01 existiert
- Branch-basiertes Staging sich als unpraktisch erwiesen hat (staging-Branch-Pflege)

**ADR-157 amends ADR-063** und ersetzt die Staging-Strategie vollständig.

### 1.1 Ist-Zustand

Die Plattform betreibt **22 Hubs** auf einem einzelnen Production-Server (88.198.191.108).
Staging existiert faktisch nicht — nur 4 von 22 Hubs haben Staging-Ports,
und die DNS-Records zeigen auf mindestens 3 verschiedene, teils unbekannte IPs.

**Beobachtete Probleme:**

1. **DNS-Wildwuchs**: Staging-DNS zeigt auf alte/unbekannte IPs (46.225.127.211, 46.225.113.1),
   nicht auf den Dev Desktop (88.99.38.75)
2. **Port-Konflikt**: `risk-hub staging: 8099` = `tax-hub prod: 8099` (gleicher Port!)
3. **18 von 22 Hubs** haben `staging: null` in `ports.yaml`
4. **Multi-Domain-Chaos**: Repos mit mehreren Domains (z.B. travel-beat: 3 TLDs) haben
   keine konsistente Staging-Zuordnung
5. **Kein automatisches Onboarding**: Port-Vergabe, DNS-Setup, Nginx-Config sind manuelle Schritte
   die leicht vergessen oder inkonsistent ausgeführt werden

### 1.2 Infrastruktur

| Server | IP | Rolle | Zweck |
|--------|------|-------|-------|
| **Production** | 88.198.191.108 | Hetzner Dedicated | Alle Hubs live |
| **Dev Desktop** | 88.99.38.75 | Hetzner CPX62 | Entwicklung + **Staging** |

### 1.3 Multi-Domain-Repos (18 Cloudflare Zones)

| Hub | Prod-Domain (Primary) | Weitere Domains | CF Zones |
|-----|----------------------|-----------------|----------|
| travel-beat | drifttales.com | drifttales.de, drifttales.app | 3 |
| risk-hub | schutztat.de | schutztat.com, kiohnerisiko.de | 3 |
| pptx-hub | prezimo.de | prezimo.com | 2 |
| weltenhub | weltenforger.com | weltenforger.de | 2 |
| writing-hub | writing.iil.pet | wishreads.app, wishreads.com | 2 |
| bfagent | iil.pet | iil.ai | 2 |
| 137-hub | 137herz.de | 137herz.ai | 2 |
| trading-hub | trading-hub.iil.pet | ai-trades.de | 1+1 |
| cad-hub | nl2cad.de | — | 1 |
| ausschreibungs-hub | bieterpilot.de | — | 1 |
| Alle anderen | *.iil.pet | — | iil.pet |

**Erkenntnis:** 7 Repos haben **mehrere Domains** über verschiedene TLDs. Das Staging-
und DNS-Management muss diese Multi-Domain-Situation als First-Class-Konzept behandeln.

---

## 2. Decision Drivers

- **D-01**: Staging und Production MÜSSEN physisch getrennte Server sein
- **D-02**: Port-Vergabe MUSS automatisch und konfliktfrei sein
- **D-03**: Multi-Domain-Repos MÜSSEN konsistentes Staging-DNS bekommen
- **D-04**: Onboarding neuer Hubs MUSS automatisiert sein (Port, DNS, Nginx, Compose)
- **D-05**: `ports.yaml` bleibt Single Source of Truth (ADR-106)
- **D-06**: Staging-Domains folgen einer einheitlichen Konvention

---

## 3. Considered Options

### Option A: Gleiche Ports, verschiedene Server

Staging bekommt **identische Ports** wie Production, aber auf dem Dev Desktop (88.99.38.75).

- **Pro**: Kein Port-Mapping nötig, Compose-Files sind identisch
- **Pro**: Einfache Migration Staging → Production
- **Contra**: Kann verwirren wenn man nicht weiß welcher Server gemeint ist

### Option B: Getrennte Port-Ranges (Prod 8000-8099, Staging 8100-8199)

Staging bekommt eigene Port-Range auf dem gleichen Server.

- **Pro**: Prod und Staging auf einem Server
- **Contra**: Port-Konflikte wenn beide Ranges voll werden
- **Contra**: Server-Last verdoppelt sich

### Option C: Staging auf Dev Desktop mit Port-Offset (+100)

Port 8090 (Prod) → 8190 (Staging) auf 88.99.38.75.

- **Pro**: Eindeutige Zuordnung
- **Contra**: Compose-Files müssen angepasst werden
- **Contra**: Unnötige Komplexität

---

## 4. Decision

**Option A: Gleiche Ports, verschiedene Server.**

```
Production (88.198.191.108)          Staging (88.99.38.75)
┌──────────────────────────┐        ┌──────────────────────────┐
│  risk-hub        :8090   │        │  risk-hub        :8090   │
│  travel-beat     :8089   │        │  travel-beat     :8089   │
│  billing-hub     :8092   │        │  billing-hub     :8092   │
│  ...                     │        │  ...                     │
│                          │        │                          │
│  schutztat.de            │        │  staging.schutztat.de    │
│  drifttales.com          │        │  staging.drifttales.com  │
│  billing.iil.pet         │        │  staging.billing.iil.pet │
└──────────────────────────┘        └──────────────────────────┘
```

### 4.1 Staging-Domain-Konvention

| Prod-Domain-Typ | Staging-Pattern | Beispiel |
|-----------------|-----------------|----------|
| `*.iil.pet` | `staging.<app>.iil.pet` | `staging.billing.iil.pet` |
| Custom Domain (primary) | `staging.<domain>` | `staging.schutztat.de` |
| Custom Domain (alias) | Kein Staging-DNS | `schutztat.com` → nur Redirect |

**Regel für Multi-Domain-Repos:**
- Nur die **Primary Domain** bekommt ein Staging-DNS
- Alias-Domains (andere TLDs) bekommen **kein** Staging — sie leiten in Prod nur auf die Primary weiter
- In `ports.yaml` wird `domain_staging` nur für die Primary gesetzt

### 4.2 Port-Governance

```yaml
# ports.yaml — erweiterte Struktur
services:
  risk-hub:
    prod_port: 8090           # Port auf Production-Server
    staging_port: 8090         # GLEICHER Port auf Staging-Server
    server_prod: 88.198.191.108
    server_staging: 88.99.38.75
    domain_prod: schutztat.de
    domain_staging: staging.schutztat.de
    domain_aliases:            # NEU: weitere Domains die auf prod zeigen
      - schutztat.com
      - kiohnerisiko.de
    repo: achimdehnert/risk-hub
    next_free_port: false      # Automatisch berechnet
```

### 4.3 Automatische Port-Vergabe beim Onboarding

1. `port_audit.py` liest `ports.yaml` und berechnet den nächsten freien Port
2. Onboarding-Workflow ruft `port_audit.py --next-free` auf
3. Port wird in `ports.yaml` eingetragen BEVOR der erste Deploy passiert
4. Port-Audit wird im CI als Pre-Deploy-Check ausgeführt

### 4.4 DNS-Aufräumung (Migration)

**Phase 1: Sofort — DNS-Leichen entfernen**

| DNS Record | Aktion | Grund |
|-----------|--------|-------|
| `staging.ai-tr...` → 88.198.191.108 | Umbiegen auf 88.99.38.75 | Zeigt auf Prod! |
| `staging.coa...` → 46.225.113.1 | Umbiegen auf 88.99.38.75 | Unbekannte IP |
| `staging.risk...` → 46.225.113.1 | Umbiegen auf 88.99.38.75 | Unbekannte IP |
| `grafana-sta...` → 46.225.127.211 | Prüfen oder löschen | Unbekannte IP |
| `stagingv18/v19` → 46.225.127.211 | Löschen | Veraltet |

**Phase 2: Staging-DNS für alle Hubs anlegen**

Für jeden Hub mit `staging: null` in ports.yaml ein `staging.<domain>` → 88.99.38.75 anlegen.

### 4.5 Erweiterte Onboarding-Checkliste

Beim Onboarding eines neuen Hubs MÜSSEN folgende Schritte automatisch passieren:

| # | Schritt | Tool/Automation |
|---|---------|-----------------|
| 1 | **Port reservieren** | `port_audit.py --next-free` → ports.yaml |
| 2 | **ports.yaml eintragen** | Automatisch via Onboarding-Script |
| 3 | **DNS Prod anlegen** | `cf_dns_upsert(domain, "@", "A", "88.198.191.108")` |
| 4 | **DNS Staging anlegen** | `cf_dns_upsert(domain, "staging", "A", "88.99.38.75")` |
| 5 | **DNS Aliases anlegen** | Für jede Alias-Domain: A-Record → Prod |
| 6 | **SSL Prod** | `ssl_obtain(domains="<domain>")` |
| 7 | **SSL Staging** | `ssl_obtain(domains="staging.<domain>")` auf Dev Desktop |
| 8 | **Nginx Prod** | Template generieren + deployen |
| 9 | **Nginx Staging** | Template generieren + deployen auf Dev Desktop |
| 10 | **docker-compose.prod.yml** | Port aus ports.yaml einsetzen |
| 11 | **Health-Endpoints** | `/livez/` + `/healthz/` prüfen |
| 12 | **Port-Audit** | `port_audit.py` muss grün sein |
| 13 | **Outline Steckbrief** | Repo-Steckbrief mit allen Domains + Ports |

### 4.6 Port-Audit als Gate

```
/ship Workflow:
  Step 0 → port_audit.py --check <repo>
    ✅ Port stimmt mit ports.yaml überein → weiter
    ❌ Port-Konflikt oder unregistriert → ABBRUCH
```

### 4.7 Staging-Secrets-Strategie

| Aspekt | Staging | Production |
|--------|---------|------------|
| **Datei** | `.env.staging` | `.env.prod` |
| **SECRET_KEY** | Eigener Wert (nicht identisch mit Prod!) | Eigener Wert |
| **DATABASE_URL** | Eigene DB auf Staging-Server | Eigene DB auf Prod-Server |
| **DJANGO_ALLOWED_HOSTS** | `staging.<domain>` | `<domain>` |
| **CSRF_TRUSTED_ORIGINS** | `https://staging.<domain>` | `https://<domain>` |
| **DEBUG** | `false` (Staging = Prod-like!) | `false` |
| **Speicherort** | `/opt/<repo>/.env.staging` auf 88.99.38.75 | `/opt/<repo>/.env.prod` auf 88.198.191.108 |

**Regel:** Staging-Secrets sind **immer separate Werte** — niemals Prod-Secrets kopieren.
Ausnahme: GHCR-Token und API-Keys für externe Services können geteilt werden.

---

## 5. Consequences

### 5.1 Positive

- **Klare Trennung**: Staging auf 88.99.38.75, Production auf 88.198.191.108
- **Kein Port-Chaos**: Gleiche Ports auf beiden Servern, ports.yaml als Single Source of Truth
- **Automatisches Onboarding**: Neuer Hub bekommt alles automatisch
- **DNS-Konsistenz**: Alle `staging.*` zeigen auf den gleichen Server
- **Multi-Domain handled**: Primary Domain bekommt Staging, Aliases nur Prod
- **Port-Audit als Gate**: Kein Deploy ohne registrierten Port

### 5.2 Negative

- **Kosten**: Staging-Server läuft permanent (CPX62 = ~€35/Monat, bereits vorhanden)
- **Daten**: Staging braucht eigene Test-Daten (kein Prod-DB-Sync vorerst)
- **SSL**: Jeder Hub braucht 2 Zertifikate (Prod + Staging)

### 5.3 Risiken

- **R-01**: Dev Desktop Reboot → Staging down (Mitigierung: systemd auto-start)
- **R-02**: DNS-Propagation bei Zone-Wechsel (Mitigierung: Low TTL während Migration)

### 5.4 Confirmation

Compliance wird durch folgende automatische Checks verifiziert:

1. **`port_audit.py --check-all`** — Prüft alle Ports in `ports.yaml` auf Konflikte
2. **`/drift-check`** — Erkennt Abweichungen zwischen ports.yaml und Server-Zustand
3. **DNS-Audit** — Alle `staging.*` DNS-Records müssen auf 88.99.38.75 zeigen
4. **`/session-start` Step 0.6** — Deploy-Status-Scan aller Apps inkl. Staging
5. **`/ship` Step 0** — Port-Audit als Pre-Deploy-Gate

---

## 6. Open Questions

| # | Frage | Status | Entscheidung |
|---|-------|--------|--------------|
| Q-01 | Wie werden Staging-Datenbanken initial befüllt? | Offen | Optionen: leere DB mit Fixtures, Anonymisierter Prod-Dump, Manuell |
| Q-02 | Let's Encrypt Rate-Limits bei vielen `staging.*` Domains? | Geklärt | Max 50 Certs/Woche pro registrierte Domain — bei 22 Hubs kein Problem |
| Q-03 | Staging-Deploy-Trigger: manuell, CI, oder Workflow? | Offen | Phase 4: eigener `/ship-staging` Workflow |
| Q-04 | Resource-Limits auf Dev Desktop (32GB RAM) für 22 Hubs + IDE? | Offen | Monitoring nötig; ggf. nur aktive Hubs auf Staging deployen |
| Q-05 | Soll ADR-063 als `Superseded` markiert werden? | Ja | ADR-157 ersetzt die Staging-Strategie vollständig |

---

## 7. Implementation Plan

### Migration Tracking

| Phase | Task | Status | Target |
|-------|------|--------|--------|
| 1 | DNS-Leichen löschen (5 Records gelöscht) | ✅ 2026-04-03 | Sofort |
| 1 | Alle staging.* DNS → 88.99.38.75 (12 Updates) | ✅ 2026-04-03 | Sofort |
| 1 | Port-Konflikt risk-hub 8099→8108 in ports.yaml | ✅ 2026-04-03 | Sofort |
| 2 | ports.yaml Schema erweitern (domain_aliases, server_*) | ☐ | Q2 2026 |
| 2 | Alle 22 Hubs in ports.yaml vervollständigen | ✅ 2026-04-03 | Q2 2026 |
| 2 | port_audit.py: Multi-Server + --next-free | ☐ | Q2 2026 |
| 3 | /onboard-repo: automatische Port-Vergabe | ☐ | Q3 2026 |
| 3 | DNS-Erstellung via Cloudflare MCP automatisieren | ☐ | Q3 2026 |
| 3 | Nginx-Template-Generator (Prod + Staging) | ☐ | Q3 2026 |
| 3 | Port-Audit als Gate in /ship | ☐ | Q3 2026 |
| 4 | docker-compose + .env.staging für jeden Hub | ☐ | Q3 2026 |
| 4 | /ship-staging Workflow erstellen | ☐ | Q3 2026 |
| 4 | Staging-Health-Checks in /session-start | ☐ | Q3 2026 |
| 4 | ADR-063 als Superseded markieren | ✅ 2026-04-03 | Nach Phase 1 |

### Phase 1: DNS-Aufräumung (sofort)

1. Alle `staging.*` DNS-Records auf 88.99.38.75 umbiegen
2. DNS-Leichen (alte IPs) löschen
3. Port-Konflikt risk-hub/tax-hub fixen

### Phase 2: ports.yaml erweitern

1. Schema um `domain_aliases`, `server_prod`, `server_staging` erweitern
2. Alle 22 Hubs vervollständigen (staging_port = prod_port)
3. `port_audit.py` erweitern: Multi-Server-Support, --next-free Flag

### Phase 3: Onboarding-Workflow updaten

1. `/onboard-repo` um automatische Port-Vergabe erweitern
2. DNS-Erstellung automatisieren (Cloudflare MCP)
3. Nginx-Template-Generator für Prod + Staging
4. Port-Audit als Gate in `/ship` einbauen

### Phase 4: Staging-Deploys

1. docker-compose + .env.staging für jeden Hub
2. Staging-Deploy-Workflow (analog /ship, aber Ziel = 88.99.38.75)
3. Staging-Health-Checks in `/session-start`

---

## 8. Validation

- [ ] Alle `staging.*` DNS → 88.99.38.75
- [ ] Keine DNS-Records mit unbekannten IPs
- [ ] Kein Port-Konflikt in ports.yaml
- [ ] port_audit.py grün für alle Hubs
- [ ] Mindestens 1 Hub (Pilot) auf Staging deployed + erreichbar
- [ ] Onboarding-Workflow getestet mit neuem Hub

---

## 9. More Information

- **ADR-063**: Staging Environment Strategy — **wird durch dieses ADR amended/superseded**
- **ADR-021**: Unified Deployment Pipeline — Port-Konventionen, Deploy-Pfade
- **ADR-075**: Split Deployment Execution — MCP read-only, Server-side writes
- **ADR-106**: Port-Audit — `ports.yaml` als Single Source of Truth
- **ADR-156**: Reliable Deployment Pipeline — Job-Estimation, Error-Logging
- **ADR-045**: Secrets Management — `.env.prod` / `.env.staging` Konvention
- **ADR-061**: Hardcoding Elimination — Staging als Voraussetzung
- **12-Factor App**: https://12factor.net/config
