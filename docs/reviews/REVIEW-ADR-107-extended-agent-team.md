# Review: ADR-107 + Implementierungs-Inputs — Extended Agent Team

**Reviewer**: Cascade (Principal IT-Architekt)
**Datum**: 2026-03-08
**Input-Dateien**:
- `docs/adr/ADR-107-extended-agent-team-deployment-agent.md`
- `inputs/agent team/roles.py`
- `inputs/agent team/breaking_change_detector.py`
- `inputs/agent team/deployment_log.py`
- `inputs/agent team/cd.yml`
- `inputs/agent team/test_roles_and_detector.py`
- `inputs/agent team/agent_team_config.yaml`

---

## 1. Review-Tabelle

| # | Befund | Datei | Schwere | Korrektur |
|---|--------|-------|---------|----------|
| **B-1** | `migrate --check` ist kein Dry-Run — erkennt keine Breaking Changes | ADR-107 §4.3 | **BLOCKER** | `breaking_change_detector.py` bereits im Input. In ADR-107 §4.3 explizit als Pflichtschritt (Step 2a) dokumentieren. |
| **B-2** | Rollback-Strategie undifferenziert — Migration bereits angewendet vs. nicht angewendet nicht unterschieden | ADR-107 §4.3 | **BLOCKER** | `RollbackPolicy` in `roles.py` korrekt implementiert (Tier 1/2/3). ADR-Text muss Tier-Konzept abbilden. |
| **B-3** | `BaseAgentRole`, `DeploymentAgentConfig`, `ReviewAgentConfig` haben keine gemeinsame Protocol-Schnittstelle — `ROLE_REGISTRY` typed als Union | `roles.py` Z. 423 | **BLOCKER** | `AgentRoleProtocol` (Protocol) einführen — `ROLE_REGISTRY: dict[AgentRole, AgentRoleProtocol]`. |
| **C-1** | Shell-Skripte: `wrap_script` korrekt aufgerufen, aber Rollback-Script ohne expliziten Error-Exit bei fehlender Tag-Info | `roles.py` Z. 234–247 | **CRITICAL** | `build_rollback_script` via `wrap_script` ✅. Rollback-Step in `cd.yml` ohne expliziten Exit-1 wenn kein PREV_TAG. |
| **C-2** | SSH Setup schreibt Key via `echo ... > file` ohne `umask 077` — Race condition bei parallelen Jobs | `cd.yml` Z. 181 | **CRITICAL** | `umask 077` vor Key-Write setzen (Fix unten). |
| **C-3** | `detect_breaking_changes` nutzt `DATABASE_URL_STAGING` — wenn Staging down, blockiert Prod-Deploy | `cd.yml` Z. 100 | **CRITICAL** | `sqlmigrate` braucht keine echte DB — SQLite In-Memory in CI reicht. |
| **M-1** | `agent_team_config.yaml` hat Placeholder-Werte, kein Validation-Schema | `agent_team_config.yaml` Z. 18–21 | MEDIUM | Pydantic-Validator `validate_agent_config.py` ergänzen. |
| **M-2** | `cd.yml` `deploy`-Job: `if: always()` ohne explizite `gate2_approval`-Abhängigkeit — Verhalten implizit | `cd.yml` Z. 165–172 | MEDIUM | `needs` um `gate2_approval` erweitern, `result == 'success' \|\| result == 'skipped'` explizit. |
| **M-3** | Review Agent Override ohne Audit-Trail — `/override-review` schreibt kein Log | `roles.py` Z. 301 | MEDIUM | `ReviewLog` Model (produktionsreif unten) als AuditStore. |
| **M-4** | `get_deployment_gate_level` gibt `level=2` für breaking UND safe zurück — semantisch unklar | `breaking_change_detector.py` Z. 246–264 | MEDIUM | Return-Typ: `(gate_level: int, auto_eligible: bool, reason: str)`. |
| **L-1** | `ROLE_REGISTRY` Modul-Level-Dict — nicht thread-safe bei Runtime-Änderungen | `roles.py` Z. 423 | LOW | Read-only nach Init akzeptieren oder `RoleRegistry`-Singleton. |
| **L-2** | `UniqueConstraint` Status-Liste nicht synchron mit `DeploymentStatus` Enum | `deployment_log.py` Z. 211–215 | LOW | `[s.value for s in _ACTIVE_STATUSES]` statt hardcoded Strings. |
| **L-3** | `get_pending_migrations` und `analyse_migration` verwenden `shell=True` — Injection-Risiko | `breaking_change_detector.py` Z. 151 | LOW | `shlex.split(manage_py) + [...]` + `shell=False`. |
| **L-4** | Tests importieren ohne Package-Prefix — nur lauffähig im inputs-Ordner | `test_roles_and_detector.py` Z. 15 | LOW | `from orchestrator_mcp.agent_team.roles import ...` |
| **I-1** | `build_rollback_script` erwartet `previous_image_tag`, aber `cd.yml` ermittelt Tag via Heuristik | `cd.yml` Z. 262 | INFO | Tag vor Pull in GitHub Output-Variable schreiben (Fix unten). |
| **I-2** | ADR-107 §5: Checkboxen nicht aktualisiert | ADR-107 §5 | INFO | Changelog-Eintrag + `[x]` wo erledigt. |

---

## 2. Bewertung

| Kategorie | Score | Begründung |
|-----------|-------|------------|
| **Architektur-Klarheit** | 5/5 | Rollen, Gates, Entscheidungsbaum klar und operationalisierbar |
| **Sicherheit** | 3/5 | C-2 (SSH Key), L-3 (shell=True) — beide behebbar |
| **Platform-Compliance** | 5/5 | BigAutoField, public_id, tenant_id, soft_delete, UniqueConstraint, i18n vollständig |
| **Testabdeckung** | 4/5 | SQL-Klassifikation, Router, RollbackPolicy vollständig. Fehlend: ReviewLog-Tests |
| **Implementierbarkeit** | 4/5 | Alle Dateien produktionsreif bis auf 3 Blocker |
| **Idempotenz** | 4/5 | `wrap_script` ✅, Migration-Script ✅. Rollback-Script: Tag-Persistenz fehlt |

**Gesamt-Empfehlung**: **Accept with mandatory fixes** — 3 Blocker vor Merge in `main` beheben.

---

## 3. Implementierungsplan

### Phase 1 — Blocker beheben (vor Merge, 1 Tag)

```
orchestrator_mcp/agent_team/
├── roles.py                        # B-3: AgentRoleProtocol
├── breaking_change_detector.py     # L-3: shell=False; M-4: auto_eligible
└── tests/test_roles_and_detector.py # L-4: package-relative imports

.github/workflows/cd.yml            # C-2: umask 077; C-3: SQLite; M-2: explicit needs
```

### Phase 2 — Core-Implementierung (Sprint 1, 3 Tage)

```
orchestrator_mcp/
├── agent_team/
│   ├── roles.py                    # Produktionsreif (nach Blocker-Fix)
│   ├── breaking_change_detector.py
│   └── deployment_executor.py      # NEU: Service-Layer Deploy-Lifecycle
├── models/
│   ├── deployment_log.py           # Django Model (produktionsreif)
│   └── review_log.py               # NEU (unten vollständig)
└── migrations/0001_deployment_log.py
```

### Phase 3 — GitHub Actions (Sprint 1, 1 Tag)

```
.github/workflows/
├── cd.yml          # Produktionsreif nach Phase-1-Fixes
└── pr-review.yml   # NEU: Review Agent PR-Trigger
```

### Phase 4 — Config-Rollout (Sprint 2, 2 Tage)

```
agent_team_config.yaml           # Pro Repo befüllen
scripts/validate_agent_config.py # NEU: M-1 Pydantic-Validator
```

### Phase 5 — orchestrator_mcp Integration (Sprint 2, 3 Tage)

```
orchestrator_mcp/
├── tools.py       # agent_team_status + agent_plan_task erweitern
└── agent_team/planner.py  # Deployment-Tasks routen
```

---

## 4. Produktionsreife Korrekturen

### Fix B-3 — `AgentRoleProtocol` in `roles.py`

```python
# Nach Imports, vor BaseAgentRole:
from typing import Protocol, runtime_checkable

@runtime_checkable
class AgentRoleProtocol(Protocol):
    role: AgentRole
    gate_level: GateLevel
    description: str

    def can_auto_execute(self) -> bool: ...


# Z. 423 — ROLE_REGISTRY Typing:
ROLE_REGISTRY: dict[AgentRole, AgentRoleProtocol] = { ... }
```

### Fix C-2 — SSH Key Write (`cd.yml` Z. 179–188)

```yaml
- name: "Setup SSH"
  run: |
    set -euo pipefail
    umask 077
    mkdir -p ~/.ssh
    printf '%s\n' "${{ secrets.DEPLOY_SSH_PRIVATE_KEY }}" > ~/.ssh/deploy_key
    chmod 600 ~/.ssh/deploy_key
    cat >> ~/.ssh/config << 'SSHEOF'
Host ${{ secrets.HETZNER_HOST }}
  User deploy
  IdentityFile ~/.ssh/deploy_key
  StrictHostKeyChecking accept-new
  ServerAliveInterval 30
  ConnectTimeout 15
SSHEOF
```

### Fix C-3 — CI-DB für Migration-Analyse (`cd.yml` Z. 98–103)

```yaml
- name: "Analyse pending migrations"
  id: detect
  env:
    DATABASE_URL: "sqlite:///tmp/ci_analysis.db"
    DJANGO_SETTINGS_MODULE: "config.settings.ci"
  run: |
    set -euo pipefail
    python - << 'EOF'
    ...
    EOF
```

### Fix M-2 — Explizite CD-Job-Abhängigkeiten (`cd.yml` Z. 162–172)

```yaml
deploy:
  name: "Deploy — Deployment Agent"
  runs-on: ubuntu-latest
  needs: [gate_check, detect_breaking_changes, gate2_approval]
  if: |
    always() &&
    needs.gate_check.outputs.should_deploy == 'true' &&
    (
      needs.gate2_approval.result == 'success' ||
      needs.gate2_approval.result == 'skipped'
    )
```

### Fix I-1 — Previous Image Tag persistent (`cd.yml`)

```yaml
# Vor Step 1 einfügen:
- name: "Step 0 — Save current image tag for rollback"
  id: save_tag
  run: |
    set -euo pipefail
    PREV_TAG=$(ssh ${{ secrets.HETZNER_HOST }} \
      "docker inspect ${{ vars.SERVICE_NAME }} \
       --format '{{index .Config.Image}}' 2>/dev/null || echo ''")
    echo "previous_tag=${PREV_TAG}" >> "$GITHUB_OUTPUT"

# Step 6 anpassen:
- name: "Step 6 — Rollback on failure"
  if: failure()
  env:
    PREV_TAG: ${{ steps.save_tag.outputs.previous_tag }}
  run: |
    set -euo pipefail
    if [ -z "${PREV_TAG}" ]; then
      echo "ERROR: No previous tag — manual intervention required"
      exit 1
    fi
    ssh ${{ secrets.HETZNER_HOST }} << ENDSSH
    set -euo pipefail
    cd /opt/app
    sed -i "s|image:.*|image: ${PREV_TAG}|" docker-compose.prod.yml
    docker compose -f docker-compose.prod.yml up -d \
      --no-deps --force-recreate ${{ vars.SERVICE_NAME }}
    echo "Rollback to ${PREV_TAG} complete"
    ENDSSH
```

### Fix L-3 — `shell=False` in `breaking_change_detector.py`

```python
import shlex

def get_pending_migrations(
    manage_py: str = "python manage.py",
    cwd: Path | None = None,
) -> list[tuple[str, str]]:
    cmd = shlex.split(manage_py) + ["migrate", "--plan"]
    result = subprocess.run(
        cmd, shell=False, capture_output=True, text=True, cwd=cwd,
    )
    ...

def analyse_migration(app_label, migration_name, manage_py="python manage.py", cwd=None):
    cmd = shlex.split(manage_py) + ["sqlmigrate", app_label, migration_name]
    result = subprocess.run(
        cmd, shell=False, capture_output=True, text=True, cwd=cwd,
    )
```

### Fix L-2 — `UniqueConstraint` synchron mit Enum (`deployment_log.py`)

```python
_ACTIVE_STATUSES = [
    DeploymentLog.Status.PENDING,
    DeploymentLog.Status.PRE_CHECK,
    DeploymentLog.Status.MIGRATING,
    DeploymentLog.Status.DEPLOYING,
    DeploymentLog.Status.HEALTH_CHECKING,
]

class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["tenant_id", "service_name"],
            condition=models.Q(status__in=[s.value for s in _ACTIVE_STATUSES]),
            name="unique_active_deployment_per_service",
        ),
    ]
```

### Neues File — `orchestrator_mcp/models/review_log.py`

```python
"""
orchestrator_mcp/models/review_log.py

AuditStore for Review Agent — Fix M-3.
Platform-standards: BigAutoField, public_id, tenant_id, soft_delete, i18n.
"""
from __future__ import annotations
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class ReviewLog(models.Model):

    class Status(models.TextChoices):
        PENDING    = "pending",    _("Pending")
        RUNNING    = "running",    _("Running")
        PASSED     = "passed",     _("Passed")
        FAILED     = "failed",     _("Failed")
        OVERRIDDEN = "overridden", _("Overridden")

    id        = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False,
        verbose_name=_("Public ID"),
    )
    tenant_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Tenant ID"),
    )

    repository = models.CharField(max_length=255, verbose_name=_("Repository"))
    pr_number  = models.PositiveIntegerField(verbose_name=_("PR Number"))
    pr_author  = models.CharField(max_length=100, verbose_name=_("PR Author"))
    git_sha    = models.CharField(max_length=40, verbose_name=_("Git SHA"))

    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING, db_index=True,
        verbose_name=_("Status"),
    )

    blocking_issues = models.JSONField(default=list, verbose_name=_("Blocking Issues"))
    warning_issues  = models.JSONField(default=list, verbose_name=_("Warning Issues"))
    check_results   = models.JSONField(default=dict, verbose_name=_("Check Results"))

    override_by     = models.CharField(
        max_length=100, blank=True, default="", verbose_name=_("Override By")
    )
    override_reason = models.TextField(
        blank=True, default="", verbose_name=_("Override Reason")
    )

    started_at   = models.DateTimeField(auto_now_add=True, verbose_name=_("Started At"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Completed At"))
    deleted_at   = models.DateTimeField(
        null=True, blank=True, db_index=True, verbose_name=_("Deleted At")
    )
    created_at   = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at   = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name        = _("Review Log")
        verbose_name_plural = _("Review Logs")
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["repository", "pr_number"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "repository", "pr_number"],
                condition=models.Q(status__in=["pending", "running"]),
                name="unique_active_review_per_pr",
            ),
        ]

    def __str__(self) -> str:
        return f"Review {self.public_id} [PR#{self.pr_number}] — {self.status}"
```

---

## 5. Alternativer Ansatz: GitHub Deployments API statt AuditStore-API

### Problem
`curl` auf `AUDIT_API_URL` in Step 7 erfordert externen Service zur Deployment-Zeit — Single Point of Failure.

### Alternative: Native GitHub Deployments API

```yaml
- name: "Create GitHub Deployment"
  uses: actions/github-script@v7
  with:
    script: |
      const dep = await github.rest.repos.createDeployment({
        owner: context.repo.owner, repo: context.repo.repo,
        ref: '${{ needs.gate_check.outputs.sha }}',
        environment: 'production', auto_merge: false,
        required_contexts: [],
      });
      core.setOutput('deployment_id', dep.data.id);

- name: "Update Deployment Status"
  if: always()
  uses: actions/github-script@v7
  with:
    script: |
      await github.rest.repos.createDeploymentStatus({
        owner: context.repo.owner, repo: context.repo.repo,
        deployment_id: ${{ steps.create_deployment.outputs.deployment_id }},
        state: '${{ job.status }}' === 'success' ? 'success' : 'failure',
        environment_url: 'https://${{ vars.APP_HOST }}',
      });
```

**Trade-off**:
- ✅ Kein externer Service, keine extra Secrets, native GitHub UI
- ✅ Deployment-History direkt im Repo sichtbar
- ❌ Kein `tenant_id`, keine Migration-Details im Standard-Schema
- ❌ Keine ORM-Queries via Operations Hub (ADR-091)

**Empfehlung**: Beide parallel — GitHub Deployments API als primärer Audit-Trail, `DeploymentLog` für strukturierte Queries.

---

## 6. Nächste Schritte (priorisiert)

1. **Blocker B-3 + C-2 + C-3** in Input-Files fixen → nach `orchestrator_mcp/agent_team/` deployen
2. **`review_log.py`** erstellen + idempotente Migration schreiben
3. **`cd.yml`** Fix I-1 (Previous-Tag) + M-2 (explizite needs)
4. **`validate_agent_config.py`** — Pydantic-Schema für M-1
5. **ADR-107 §4.3** — Tier-Rollback und `breaking_change_detector` als Pflichtschritt dokumentieren

---

*Review erstellt von Cascade (Tech Lead) — ADR-107 v2026-03-08*
