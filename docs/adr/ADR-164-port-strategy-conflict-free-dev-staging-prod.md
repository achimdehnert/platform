---
parent: Decisions
nav_order: 164
title: "ADR-164: Unified Port Strategy — Conflict-free dev, staging, and production port assignments"
status: accepted
date: 2026-04-18
deciders: Achim Dehnert
consulted: Cascade AI
informed: []
related: ["ADR-106-port-audit.md", "ADR-157-staging-production-split-and-port-governance.md"]
implementation_status: partial
---

# Unified Port Strategy — Conflict-free dev, staging, and production port assignments

<!-- Drift-Detector-Felder
staleness_months: 6
drift_check_paths:
  - infra/ports.yaml
  - iil-reflex/reflex/dashboard.py
-->

---

## 1. Context and Problem Statement

ADR-157 established the 3-server architecture (dev/staging/prod) with the principle
"same port, different server" for staging = prod. However, **development ports were
never formally assigned**, leading to:

1. **Port collisions in dev compose files**: trading-hub, wedding-hub, and bfagent all
   used `8000:8000` locally — only one could run at a time
2. **Dashboard false positives**: The reflex dashboard showed apps as "healthy" that
   weren't running — because another app occupied the same port
3. **Compose drift**: 6 repos had `docker-compose.prod.yml` ports that didn't match
   `ports.yaml` (ausschreibungs-hub=8095 vs 137-hub=8095, research-hub=8098 vs 8104,
   tax-hub=8104 vs 8099, writing-hub=8095 vs 8097, risk-hub=8001, trading-hub=8000)
4. **No dev column** in `ports.yaml` — developers had no reference for local ports
5. **No infra ports** documented — Authentik, Outline, Grafana, MinIO had no entries

## 2. Decision Drivers

- **D-01**: Every app MUST be runnable simultaneously on localhost without port conflicts
- **D-02**: `ports.yaml` must be the single source of truth for ALL environments
- **D-03**: Dashboard, compose files, and server state must all agree on ports
- **D-04**: Port ranges must be predictable and leave room for growth

## 3. Decision

### 3.1 Port Range Strategy

```
Range         Purpose                              Example
─────────────────────────────────────────────────────────────────
3000-3199     Infrastructure UIs                   Grafana 3000, Outline 3100
4000-4099     Finance Infra (IB Gateway)           IB 4001-4002
5432-5499     PostgreSQL (compose-internal only)    —
6379-6399     Redis (compose-internal only)         —
8000-8019     Reserved / Legacy                    llm-mcp 8001
8020-8069     Standalone Tools                     pptx-hub 8020, odoo 8069
8080-8109     App-Hubs Block A (main products)     risk-hub 8090, billing 8092
8110-8199     App-Hubs Block B (expansion)         Next free: 8110
9000-9099     Auth + Object Storage                Authentik 9000, MinIO 9010
```

### 3.2 Three Principles

1. **dev = staging = prod port** (default) — same port number everywhere
2. **Staging = Prod port on different server** (ADR-157 — unchanged)
3. **One hub, one port, all environments** — no ranges, no offsets

### 3.3 Canonical Port List

| Port | Hub | Container | Prod Domain |
|------|-----|-----------|-------------|
| 8007 | coach-hub | coach_hub_web | coach-hub.iil.pet |
| 8020 | pptx-hub | pptx_hub_web | prezimo.de |
| 8069 | odoo | odoo_web | odoo.iil.pet |
| 8081 | weltenhub | weltenhub_web | weltenforger.com |
| 8085 | dev-hub | devhub_web | dev-hub.iil.pet |
| 8088 | trading-hub | trading_hub_web | ai-trades.de |
| 8089 | travel-beat | travel_beat_web | drifttales.com |
| 8090 | risk-hub | risk_hub_web | schutztat.de |
| 8091 | bfagent | bfagent_web | iil.pet |
| 8092 | billing-hub | billing-hub-web | billing.iil.pet |
| 8093 | wedding-hub | wedding_hub_web | wedding-hub.iil.pet |
| 8094 | cad-hub | cad_hub_web | nl2cad.de |
| 8095 | 137-hub | hub137_web | 137herz.ai |
| 8096 | illustration-hub | illustration_web | illustration.iil.pet |
| 8097 | writing-hub | writing_hub_web | writing.iil.pet |
| 8098 | research-hub | research_hub_web | research.iil.pet |
| 8099 | tax-hub | tax_hub_web | tax.iil.pet |
| 8100 | learn-hub | learn-hub-web-1 | learn.iil.pet |
| 8101 | ausschreibungs-hub | ausschreibungs_hub_web | bieterpilot.de |
| 8102 | doc-hub | iil_dochub_web | docs.iil.pet |
| 8103 | recruiting-hub | recruiting_hub_web | hr.iil.pet |
| 8107 | dms-hub | dms_hub_web | dms.iil.pet |

Next free port: **8110**

### 3.4 ports.yaml Extended Schema

```yaml
services:
  risk-hub:
    prod: 8090          # Host port on production server
    staging: 8090       # Host port on staging server (= prod)
    dev: 8090           # Host port on localhost / dev desktop
    container_name: risk_hub_web
    domain_prod: schutztat.de
    domain_staging: staging.schutztat.de
    domain_aliases: [schutztat.com, kiohnerisiko.de]
    repo: achimdehnert/risk-hub
    compose_drift: "..."  # optional — notes if compose file needs fixing
```

New fields vs ADR-157:
- **`dev`**: explicit development port (was implicit/missing)
- **`container_name`**: Docker container name for health checks
- **`compose_drift`**: tracks known mismatches between compose file and this registry

### 3.5 Compose Drift — Required Fixes

| Repo | File | Current Port | Correct Port | Issue |
|------|------|-------------|-------------|-------|
| ausschreibungs-hub | docker-compose.prod.yml | 8095 | 8101 | Conflicts with 137-hub |
| writing-hub | docker-compose.yml | 8095 | 8097 | Wrong dev port |
| risk-hub | docker-compose.yml | 8001 | 8090 | Wrong dev port |
| trading-hub | docker-compose.yml | 8000 | 8088 | Conflicts with bfagent |
| wedding-hub | docker-compose.yml | 8000 | 8093 | Conflicts with bfagent |
| tax-hub | docker-compose.prod.yml | 8104 | 8099 | Swapped with research |
| research-hub | docker-compose.prod.yml | 8098 | 8098 | OK in file, server runs 8104 (redeploy) |

### 3.6 Validation Chain

```
ports.yaml  ──→  port_audit.py --check-all   (CI gate)
ports.yaml  ──→  reflex dashboard HUBS[]      (must match dev port)
ports.yaml  ──→  docker-compose.*.yml ports:  (must match env port)
ports.yaml  ──→  server docker ps             (must match prod port)
```

## 4. Consequences

### 4.1 Positive

- **Zero port conflicts**: Every hub has a unique port across all environments
- **Single source of truth**: `ports.yaml` governs compose, dashboard, server, and docs
- **Predictable growth**: Block B (8110-8199) has 90 free slots for new hubs
- **Dashboard accuracy**: Health checks no longer produce false positives

### 4.2 Negative

- **6 compose files need updating** (tracked in compose_drift fields)
- **Dev compose files can't use simple `8000:8000`** anymore — each must use its assigned port

### 4.3 Risks

- **R-01**: Developers forget to check ports.yaml before adding new services
  - Mitigation: port_audit.py as CI gate in /ship workflow
- **R-02**: Compose drift accumulates if fixes are deferred
  - Mitigation: compose_drift field in ports.yaml makes drift visible

## 5. Confirmation

- [x] ports.yaml updated with dev column for all 22 hubs
- [x] ports.yaml has infra section (Authentik, Outline, Grafana, MinIO)
- [x] reflex dashboard HUBS[] matches ports.yaml dev ports (20/20)
- [x] No port collisions in ports.yaml (verified by test_should_have_unique_ports)
- [ ] 6 compose drift fixes deployed (tracked, not yet applied)
- [ ] port_audit.py validates dev column

## 6. More Information

- **ADR-106**: Port Audit — introduced `ports.yaml` as source of truth
- **ADR-157**: 3-Server Architecture — staging=prod ports on separate servers
- **`infra/ports.yaml`**: The canonical port registry
- **`iil-reflex/reflex/dashboard.py`**: Local dashboard consuming dev ports
