# Agent Handover — Platform Infra Context

**Pflicht-Lektüre beim Session-Start jedes Coding-Agents.**
Enthält alle Infra-Zugänge, MCP-Tool-Mappings und Deploy-Targets.

---

## 1. MCP-Server & ihre Fähigkeiten

| MCP-Server | Windsurf-Prefix | Zweck |
|---|---|---|
| `deployment-mcp` | `mcp5_` | SSH, Docker, Git, DB, DNS, SSL auf Hetzner |
| `orchestrator` | `mcp11_` | Agent-Team, Task-Planung, QA-Loop, Kosten |
| `platform-context` | `mcp12_` | ADR-Compliance, Banned-Patterns, Architektur |
| `github` | `mcp8_` | Issues, PRs, Repos, Branches, Reviews |
| `cloudflare-api` | `mcp_cloudflare_` | DNS, Zones, Tunnels, Security |

---

## 2. Hetzner Infrastructure

| Rolle | Host | IP | User |
|---|---|---|---|
| **Prod-Server** | `hetzner-prod` | `88.198.191.108` | `deploy` |
| **Dev-Server** | `hetzner-dev` | via ProxyJump hetzner-prod | `deploy` |

**SSH-Zugang:** via `deployment-mcp` -> `mcp5_ssh_manage`
- Read-only auf Prod direkt; Deploys via `scripts/ship.sh` oder CI/CD
- `mcp5_ssh_manage(host="hetzner-prod", command="...")`

**Docker:** via `mcp5_docker_manage`
- `action="compose_ps"`, `action="compose_up"`, `action="compose_logs"`

---

## 3. Deploy Targets (alle auf 88.198.191.108)

| Repo | Pfad | Health-URL | Domain |
|---|---|---|---|
| `coach-hub` | `/opt/coach-hub` | `https://kiohnerisiko.de/healthz/` | kiohnerisiko.de |
| `billing-hub` | `/opt/billing-hub` | `https://billing.iil.pet/healthz/` | billing.iil.pet |
| `travel-beat` | `/opt/travel-beat` | `https://drifttales.de/healthz/` | drifttales.de |
| `weltenhub` | `/opt/weltenhub` | `https://weltenforger.com/healthz/` | weltenforger.com |
| `trading-hub` | `/opt/trading-hub` | `https://ai-trades.de/healthz/` | ai-trades.de |
| `cad-hub` | `/opt/cad-hub` | `https://nl2cad.de/healthz/` | nl2cad.de |
| `pptx-hub` | `/opt/pptx-hub` | `https://prezimo.de/healthz/` | prezimo.de |
| `risk-hub` | `/opt/risk-hub` | `https://risk-hub.iil.pet/healthz/` | risk-hub.iil.pet |
| `ausschreibungs-hub` | `/opt/ausschreibungs-hub` | `https://bieterpilot.de/healthz/` | bieterpilot.de |

**Deploy-Workflow:** immer via `mcp11_deploy_check` prüfen, nie direkt docker auf Prod.

---

## 4. Cloudflare

**Zugang:** via `cloudflare-api` MCP-Server (API-Keys hinterlegt in Windsurf-Secrets)

Verwaltete Domains:
- `iil.pet` — Platform-Domains (billing, risk-hub, mcp-hub)
- `kiohnerisiko.de` — coach-hub
- `drifttales.de` — travel-beat
- `weltenforger.com` — weltenhub
- `ai-trades.de` — trading-hub
- `nl2cad.de` — cad-hub
- `prezimo.de` — pptx-hub
- `bieterpilot.de` — ausschreibungs-hub

**Tunnel:** Cloudflare Tunnels für alle Prod-Domains aktiv.
DNS-Änderungen via `mcp_cloudflare_` Tools — kein manueller Zugang nötig.

---

## 5. GitHub

**Org/User:** `achimdehnert`
**Zugang:** via `github` MCP-Server (`mcp8_`)

Alle Repos: `bfagent`, `billing-hub`, `cad-hub`, `coach-hub`, `dev-hub`,
`illustration-hub`, `mcp-hub`, `nl2cad`, `odoo-hub`, `platform`, `pptx-hub`,
`risk-hub`, `trading-hub`, `travel-beat`, `wedding-hub`, `weltenhub`, `137-hub`,
`ausschreibungs-hub`

Package-Repos (PyPI): `aifw`, `authoringfw`, `promptfw`, `weltenfw`,
`illustration-fw`, `testkit`, `platform` (django-tenancy)

---

## 6. Stripe / Payment Agent

**Zugang:** Stripe API-Keys in Windsurf-Secrets + `/opt/billing-hub/.env` auf Prod

| Was | Wert |
|---|---|
| billing-hub Prod | `/opt/billing-hub` auf 88.198.191.108 |
| Health-URL | `https://billing.iil.pet/healthz/` |
| Stripe Webhook | `POST https://billing.iil.pet/api/webhook/stripe/` |
| Keys Prod | `/opt/billing-hub/.env` (STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET) |
| Keys lokal | `billing-hub/.env` (nie committen — in Windsurf-Secrets) |

**Price IDs: noch ausstehend** — müssen im Stripe Dashboard angelegt werden.
Danach sofort ausführen:
```bash
# via mcp5_ssh_manage:
cd /opt/billing-hub
docker compose -f docker-compose.prod.yml exec web \
  python manage.py setup_plans --stripe-monthly=price_xxx --stripe-yearly=price_xxx
```

**Payment Agent aktivieren:** `mcp11_get_payment_context()` — liefert vollständigen Stripe-Kontext.

**Regeln:**
- STRIPE_SECRET_KEY NIEMALS im Code oder in Logs
- Gate-2 vor jeder Stripe-Konfigurationsanderung
- Webhook-Signatur muss verifiziert werden (STRIPE_WEBHOOK_SECRET)
- Nach jeder Änderung: `mcp11_deploy_check(action='health', repo='billing-hub')`

---

## 7. MCP-Tool Quick-Reference für Deployment

```python
# Health-Check eines Repos
mcp11_deploy_check(action="health", repo="weltenhub")

# Container-Status auf Prod
mcp11_deploy_check(action="status", repo="weltenhub")

# SSH-Command auf Prod (read-only)
mcp5_ssh_manage(host="hetzner-prod", action="execute",
                command="docker compose -f /opt/weltenhub/docker-compose.prod.yml ps")

# Docker Compose Logs
mcp5_docker_manage(host="hetzner-prod", action="compose_logs",
                   path="/opt/weltenhub", service="web", tail=50)

# DNS-Eintrag prüfen (Cloudflare)
mcp_cloudflare_dns_list(zone="weltenforger.com")

# GitHub PR kommentieren
mcp8_add_issue_comment(owner="achimdehnert", repo="weltenhub",
                       issue_number=42, body="Deploy status: ...")

# Stripe-Kontext für Payment Agent
mcp11_get_payment_context()
```

---

## 8. Wichtige Regeln

- **Prod-Server WRITE:** Nur via `scripts/ship.sh` oder GitHub Actions CI/CD
- **Direkte DB-Änderungen auf Prod:** NIEMALS — nur via Migrations
- **API-Keys (Hetzner, Cloudflare, Stripe):** Alle in Windsurf-Secrets — nie im Code
- **Gate-2 Deployments + Stripe-Config:** Immer `mcp11_request_approval` vorher
- **Nach jedem Deploy:** `mcp11_deploy_check(action="health", repo=...)` ausführen

---

## 9. Session-Start Checklist (Agent)

```
1. Diese Datei lesen (AGENT_HANDOVER.md im platform Root) ✓
2. mcp11_agent_team_status() -> aktueller Team-Stand (8 Rollen inkl. Payment Agent)
3. mcp11_deploy_check(action='targets') -> Deploy-Konfiguration
4. mcp11_get_infra_context() -> vollständiger Infra-Kontext
5. mcp11_get_payment_context() -> Stripe-Kontext (bei Billing-Tasks)
6. Offene Issues prüfen: mcp8_list_issues(owner='achimdehnert', repo=<repo>)
```
