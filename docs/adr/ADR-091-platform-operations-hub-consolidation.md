---
status: accepted
date: 2026-02-27
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: ["ADR-050-platform-decomposition-hub-landscape.md"]
related: ["ADR-050-platform-decomposition-hub-landscape.md", "ADR-075-deployment-execution-strategy.md", "ADR-042-dev-environment-deploy-workflow.md", "ADR-048-htmx-playbook.md"]
implementation_status: implemented
implementation_evidence:
  - "dev-hub/apps/operations/: Models, Services, Views, Admin, URLs deployed"
  - "devhub.iil.pet/operations/ → 200 (live)"
  - "Windsurf Cleanup, Container Logs, Operation History, Server Status"
  - "control-center: Container offline (nicht mehr aktiv)"
  - "platform/admin: Prototyp gelöscht (2026-03-11)"
---

# ADR-091: Platform Operations Hub Consolidation

## Context and Problem Statement

Es existieren drei überlappende UI-Systeme für Platform-Management:

| System | URL | Status | Funktion |
|--------|-----|--------|----------|
| **dev-hub** | devhub.iil.pet | ✅ Produktiv | Developer Portal, Catalog, Health, TechDocs, ADR |
| **control-center** | control-center.iil.pet | ✅ Produktiv | Tenant/User Management, AI Config |
| **platform/admin** | — | ⚠️ Prototyp | Mock Dashboard (localStorage) |

**Probleme:**

1. **Fragmentierung**: Drei separate UIs für verwandte Funktionen
2. **Redundanz**: Health-Monitoring in dev-hub, aber Server-Ops nirgends
3. **Prototyp-Altlast**: `platform/admin` ist nur localStorage-Mock, keine echte Funktion
4. **Fehlende Operations**: Windsurf-Cleanup, Deploy-Trigger, Logs nur via CLI/Makefile

**Ziel**: Ein konsolidiertes Operations Hub mit allen Platform-Management-Funktionen.

---

## Decision Drivers

- **Single Source of Truth**: Ein Portal für alle Platform-Operationen
- **ADR-050 Konformität**: dev-hub ist bereits als "Central Management & Documentation" definiert
- **Minimaler Aufwand**: Bestehende Infrastruktur nutzen (dev-hub hat Celery, Health, Multi-Tenancy)
- **Sofortige Wirkung**: Windsurf-Cleanup und Deploy-Trigger als Quick Wins
- **Langfristige Wartbarkeit**: Keine Prototypen in Production

---

## Considered Options

### Option 1: dev-hub erweitern (gewählt)

dev-hub bekommt eine neue App `operations` für Server-Operationen.
control-center wird später migriert. platform/admin wird gelöscht.

**Pro:**
- dev-hub hat bereits Celery, Health-Polling, Multi-Tenancy
- ADR-050 definiert dev-hub als zentrales Portal
- Minimaler Aufwand — nur eine neue App

**Contra:**
- control-center muss später migriert werden (Phase 2)

### Option 2: control-center erweitern

control-center (BFAgent) bekommt Operations-Features.

**Pro:**
- Bereits Auth + Tenant Management

**Contra:**
- Kein Celery, kein Health-Polling
- Widerspricht ADR-050 (dev-hub ist das zentrale Portal)
- BFAgent ist Book Factory, nicht Platform Management

### Option 3: Neues Portal erstellen

Komplett neues "Platform Control Center" bauen.

**Pro:**
- Sauberer Start

**Contra:**
- Maximaler Aufwand
- Ignoriert existierende Infrastruktur
- Widerspricht ADR-050

---

## Decision Outcome

**Gewählt: Option 1** — dev-hub als konsolidiertes Platform Operations Hub.

### Positive Consequences

- Ein Portal für alle Platform-Operationen (devhub.iil.pet)
- Windsurf-Cleanup, Deploy-Trigger, Logs im Browser statt CLI
- Celery-Tasks für async Operations (kein Timeout-Problem)
- Health-Dashboard bereits vorhanden — Operations ergänzt es

### Negative Consequences

- control-center Migration erfordert separaten Aufwand (Phase 2)
- Kurzfristig zwei Portale parallel (dev-hub + control-center)

---

## Implementation Details

### Phase D1: Operations App (Sofort)

Neue Django-App `operations` in dev-hub:

```
dev-hub/apps/operations/
├── __init__.py
├── admin.py
├── apps.py
├── models.py           # Server, Operation, OperationLog
├── services.py         # WindsurfService, DeployService, LogService
├── views.py            # HTMX Views
├── urls.py
├── tasks.py            # Celery Tasks
└── templates/
    └── operations/
        ├── dashboard.html
        ├── windsurf.html
        ├── deploy.html
        └── logs.html
```

#### Models

```python
# operations/models.py
from django.db import models
from core.models import TenantAwareModel

class Server(TenantAwareModel):
    """Platform server (hetzner-dev, hetzner-prod, hetzner-odoo)."""
    name = models.CharField(max_length=50, unique=True)
    hostname = models.CharField(max_length=100)
    ssh_host = models.CharField(max_length=100)  # SSH config alias
    is_active = models.BooleanField(default=True)

class Operation(TenantAwareModel):
    """Tracked operation (deploy, cleanup, backup)."""
    class Type(models.TextChoices):
        WINDSURF_CLEAN = "windsurf_clean", "Windsurf Cleanup"
        WINDSURF_FORCE = "windsurf_force", "Windsurf Force"
        DEPLOY = "deploy", "Deploy"
        BACKUP = "backup", "Backup"
        LOGS = "logs", "Logs"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=Type.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    parameters = models.JSONField(default=dict)  # e.g., {"app": "travel-beat"}
    output = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    triggered_by = models.CharField(max_length=100)  # User or "celery_beat"
```

#### Services

```python
# operations/services.py
import asyncio
import subprocess
from typing import Literal

class WindsurfService:
    """Windsurf cleanup operations via SSH."""

    @staticmethod
    async def get_status(server: str) -> dict:
        """Get Windsurf session status."""
        cmd = f"ssh {server} 'pgrep -af workspace_id -u deploy 2>/dev/null | grep -oP \"workspace_id \\K[^ ]+\" | sort -u'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        workspaces = [ws.strip() for ws in result.stdout.strip().split('\n') if ws.strip()]
        return {"workspaces": workspaces, "count": len(workspaces)}

    @staticmethod
    async def cleanup(server: str, mode: Literal["clean", "force", "workspace"] = "clean", workspace: str = None) -> dict:
        """Execute Windsurf cleanup."""
        if mode == "workspace" and workspace:
            cmd = f"ssh {server} 'bash ~/fix-windsurf-remote.sh --workspace={workspace}'"
        elif mode == "force":
            cmd = f"ssh {server} 'bash ~/fix-windsurf-remote.sh --force'"
        else:
            cmd = f"ssh {server} 'bash ~/fix-windsurf-remote.sh --clean'"
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
        }

class DeployService:
    """Deploy operations via GitHub Actions."""

    @staticmethod
    async def trigger_deploy(app: str, tag: str = "latest") -> dict:
        """Trigger deploy via GitHub Actions workflow_dispatch."""
        # Uses GitHub API to trigger infra-deploy workflow
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.github.com/repos/achimdehnert/infra-deploy/actions/workflows/deploy-service.yml/dispatches",
                headers={
                    "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json",
                },
                json={
                    "ref": "main",
                    "inputs": {"service": app, "image_tag": tag},
                },
            )
        return {"success": response.status_code == 204, "status_code": response.status_code}

class LogService:
    """Log viewing via deployment-mcp or SSH."""

    @staticmethod
    async def get_container_logs(server: str, container: str, lines: int = 100) -> str:
        """Get container logs via SSH."""
        cmd = f"ssh {server} 'docker logs --tail {lines} {container} 2>&1'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout
```

#### Views (HTMX)

```python
# operations/views.py
from django.views.generic import TemplateView
from core.views.base import TenantMixin, HTMXMixin

class OperationsDashboardView(TenantMixin, HTMXMixin, TemplateView):
    template_name = "operations/dashboard.html"
    partial_template_name = "operations/partials/dashboard_content.html"

class WindsurfView(TenantMixin, HTMXMixin, TemplateView):
    template_name = "operations/windsurf.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get Windsurf status for all servers
        context["servers"] = [
            {"name": "hetzner-dev", "status": WindsurfService.get_status("hetzner-dev")},
        ]
        return context

    def post(self, request, *args, **kwargs):
        """Handle cleanup action."""
        mode = request.POST.get("mode", "clean")
        workspace = request.POST.get("workspace")
        result = WindsurfService.cleanup("hetzner-dev", mode, workspace)
        # Return HTMX partial with result
        ...
```

#### Celery Tasks

```python
# operations/tasks.py
from celery import shared_task
from .services import WindsurfService

@shared_task
def windsurf_cleanup_task(server: str, mode: str = "clean"):
    """Async Windsurf cleanup (for scheduled or long-running ops)."""
    return WindsurfService.cleanup(server, mode)
```

### Phase D2: Tenant/User Migration (Später)

Migriere Tenant/User Management von control-center nach dev-hub.

| Feature | Von | Nach |
|---------|-----|------|
| Tenant CRUD | control-center | dev-hub/core |
| User CRUD | control-center | dev-hub/core |
| Plan Management | control-center | dev-hub/core |
| Role Management | control-center | dev-hub/core |

### Phase D3: Deprecation

| System | Aktion | Zeitpunkt |
|--------|--------|-----------|
| platform/admin | Löschen | Sofort nach ADR-091 accepted |
| control-center | Redirect auf dev-hub | Nach Phase D2 |

---

## UI Design

### Operations Dashboard

```
┌─────────────────────────────────────────────────────────────────────────┐
│  dev-hub — Operations                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │ hetzner-dev     │  │ hetzner-prod    │  │ hetzner-odoo    │         │
│  │   ✅ Online     │  │   ✅ Online     │  │   ✅ Online     │         │
│  │ Windsurf: 2     │  │ Services: 7     │  │ Odoo: ✅        │         │
│  │ [Clean] [Logs]  │  │ [Deploy] [Logs] │  │ [Status]        │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│                                                                         │
│  ━━━ Quick Actions ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                         │
│  [🧹 Windsurf Clean]  [🚀 Deploy App]  [📋 View Logs]  [💾 Backup]     │
│                                                                         │
│  ━━━ Recent Operations ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                         │
│  10:30  ✅ Windsurf cleanup (hetzner-dev) — 2 stale processes          │
│  10:15  ✅ Deploy travel-beat (sha-abc1234)                            │
│  09:45  ✅ Deploy bfagent (sha-def5678)                                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Windsurf Page

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Windsurf Remote-SSH Management                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Server: hetzner-dev                                                    │
│                                                                         │
│  ━━━ Active Sessions ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                         │
│  ✔ file_home_deploy_projects_platform                                  │
│  ✔ file_home_deploy_projects_travel_beat                               │
│                                                                         │
│  ━━━ Cleanup Actions ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                         │
│  [🧹 Sanft]     Nur stale Prozesse (>1h), aktive Sessions bleiben      │
│  [🎯 Workspace] Nur einen Workspace bereinigen: [platform ▼]           │
│  [⚠️ Force]     ALLE Prozesse killen (Notfall)                         │
│                                                                         │
│  ━━━ Output ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ [INFO]  Sanfter Modus: Nur stale Prozesse (>1h) werden bereinigt│   │
│  │ [INFO]  Keine stale Prozesse gefunden.                          │   │
│  │ ✅ Cleanup abgeschlossen.                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Migration Tracking

| Schritt | Abhängigkeit | Status | Datum |
|---------|-------------|--------|-------|
| ADR-091 erstellen | — | ✅ done | 2026-02-27 |
| `operations` App Struktur erstellen | ADR-091 accepted | ✅ done | 2026-02-27 |
| Models + Migrations | App Struktur | ✅ done | 2026-02-27 |
| Services implementieren | Models | ✅ done | 2026-02-27 |
| Views + Templates | Services | ✅ done | 2026-02-27 |
| Celery Tasks | Services | ✅ done | 2026-02-27 |
| SSH-Keys im Container mounten | Deployment | ⬜ pending | — |
| Sidebar-Link in dev-hub | Views | ⬜ pending | — |
| Migrations ausführen + deployen | All code done | ⬜ pending | — |
| platform/admin löschen | ADR-091 accepted | ⬜ pending | — |
| Phase D2: Tenant Migration | Phase D1 complete | ⬜ pending | — |

---

## ADR-075 Ausnahme: Windsurf-Cleanup

ADR-075 definiert: "Write-Operationen werden ausschließlich über GitHub Actions ausgeführt."

**Windsurf-Cleanup ist eine explizite Ausnahme:**

| Kriterium | Windsurf-Cleanup | Deployment |
|-----------|------------------|------------|
| Dauer | <60s | 2-5min |
| Interaktivität | Hoch (sofortiges Feedback) | Niedrig |
| Frequenz | Ad-hoc bei Problemen | Geplant |
| Rollback nötig | Nein | Ja |
| Audit-Trail kritisch | Nein | Ja |

**Begründung**: GitHub Actions Startup-Latenz (~30s) wäre für eine interaktive
Troubleshooting-Operation kontraproduktiv. Windsurf-Cleanup ist Maintenance,
nicht Deployment.

---

## Security Considerations

### Authentifizierung & Autorisierung

| Aspekt | Implementierung |
|--------|----------------|
| UI-Zugriff | Django Auth (Login required) |
| Operations-Berechtigung | `is_staff` oder custom Permission |
| Audit-Trail | `Operation` Model mit `triggered_by` |

### Required Secrets (ADR-045 Compliance)

| Secret | Purpose | ADR-045 Pattern |
|--------|---------|----------------|
| `GITHUB_TOKEN` | GitHub Actions Trigger für Deploy | `read_secret("GITHUB_TOKEN", required=True)` |

**Hinzufügen zu `secrets.enc.env`:**
```bash
sops -e --input-type dotenv --output-type dotenv /dev/stdin \
    <<< "GITHUB_TOKEN=ghp_xxx" \
    >> secrets.enc.env
```

### SSH-Konfiguration (ADR-045: SSH keys stay as FILES)

dev-hub läuft auf `88.198.191.108` (hetzner-prod) und braucht SSH-Zugriff auf:
- `hetzner-dev` (46.225.113.1) — Windsurf-Cleanup
- `hetzner-prod` (88.198.191.108) — Logs, Status

**Architektur:**
```
┌─────────────────────────────────────────────────────────────────┐
│  hetzner-prod (88.198.191.108)                                │
│  ├── dev-hub Container (devhub_web)                           │
│  │   └── SSH ───────────────────────────────────────────────┐   │
│  ├── Self-hosted GitHub Runner                                │   │
│  └── /home/deploy/.ssh/ (Host)                                │   │
└─────────────────────────────────────────────────────────────────┘   │
                                                                    │
┌─────────────────────────────────────────────────────────────────┘   │
│  hetzner-dev (46.225.113.1)                                   │───┘
│  ├── Windsurf Remote-SSH (User: deploy)                       │
│  └── fix-windsurf-remote.sh                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Voraussetzungen (ADR-045 konform):**
1. SSH-Key als FILE auf Host (`chmod 600`) — nie in SOPS
2. Read-only Mount in Container
3. `known_hosts` für alle Server

**Deployment-Anpassung:**
```yaml
# docker-compose.prod.yml
devhub-web:
  volumes:
    # SSH-Keys als Files mounten (ADR-045: SSH keys stay as FILES)
    - /home/deploy/.ssh/id_ed25519:/app/.ssh/id_ed25519:ro
    - /home/deploy/.ssh/known_hosts:/app/.ssh/known_hosts:ro
    - /home/deploy/.ssh/config:/app/.ssh/config:ro
  environment:
    - HOME=/app  # Damit SSH ~/.ssh findet
```

### Rate-Limiting

Destruktive Operationen (Force-Kill) sollten rate-limited sein:
- Max 1 Force-Cleanup pro Server pro 5 Minuten
- Implementierung via Django Cache oder Celery Rate-Limit

---

## Risks and Mitigations

| Risiko | Schwere | Wahrscheinlichkeit | Mitigation |
|--------|---------|-------------------|-----------|
| SSH-Timeout bei Operations | MEDIUM | LOW | Celery Tasks für lange Ops, 120s Timeout |
| Zwei Portale parallel (Verwirrung) | LOW | MEDIUM | Klare Kommunikation: dev-hub = Operations |
| control-center Migration komplex | MEDIUM | MEDIUM | Phase D2 separat planen |
| SSH-Key Exposure | HIGH | LOW | Read-only Mount, restricted Permissions |
| Unbefugte Force-Kills | MEDIUM | LOW | `is_staff` Permission, Audit-Trail |

---

## Confirmation Criteria

- [ ] `operations` App in dev-hub deployed
- [ ] Windsurf Cleanup via UI funktioniert
- [ ] Deploy Trigger via UI funktioniert
- [ ] Logs Viewer via UI funktioniert
- [ ] platform/admin gelöscht
- [ ] Operations-Link in dev-hub Sidebar

---

## Appendix: Deprecation von platform/admin

Das Verzeichnis `platform/admin/` enthält nur einen localStorage-basierten Prototyp:

```
platform/admin/
├── admin.js      # localStorage Mock-Daten
├── index.html    # Dashboard (Mock)
├── styles.css    # Shared Styles
├── tenants.html  # Tenant-Liste (Mock)
└── users.html    # User-Liste (Mock)
```

**Aktion**: Nach ADR-091 accepted löschen. Keine Migration nötig — war nie produktiv.
