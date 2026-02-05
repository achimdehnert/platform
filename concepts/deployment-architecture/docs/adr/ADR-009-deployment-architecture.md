# ADR-009: Centralized Deployment Architecture

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-02 |
| **Author** | Achim Dehnert |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-008 (Infrastructure Services) |

---

## 1. Context

### 1.1 Current State

The BF Agent Platform consists of multiple applications deployed to Hetzner Cloud:

| Application | Repository | Deployment Frequency |
|-------------|------------|---------------------|
| BF Agent | achimdehnert/bfagent | ~5x/day |
| Travel-Beat | achimdehnert/travel-beat | ~10x/day |
| MCP Hub | achimdehnert/mcp-hub | ~3x/day |
| Risk-Hub | achimdehnert/risk-hub | ~2x/day |
| CAD-Hub | achimdehnert/cad-hub | ~2x/day |

Each application maintains its own CI/CD workflows with significant duplication:

```
travel-beat/.github/workflows/
├── ci.yml              # ~120 lines
├── cd-production.yml   # ~130 lines  
├── deploy.yml          # ~525 lines (full pipeline)
└── security.yml        # ~45 lines

bfagent/.github/workflows/
├── ci.yml              # ~115 lines (90% identical)
├── cd-production.yml   # ~125 lines (85% identical)
└── security.yml        # ~45 lines (100% identical)

# Total: ~1600 lines duplicated across 5 repos = ~8000 lines
```

### 1.2 Pain Points

1. **Maintenance Burden**: Changes to deployment logic require updates in 5+ repositories
2. **Inconsistency Risk**: Drift between deployment configurations across apps
3. **No Shared Learning**: Auto-healer improvements benefit only one app
4. **Limited Observability**: No unified view of deployment health across platform
5. **Error Pattern Blindness**: Same errors occur repeatedly without learning

### 1.3 Requirements

| Requirement | Priority | Notes |
|-------------|----------|-------|
| Reduce workflow duplication | HIGH | DRY principle |
| Maintain app autonomy | HIGH | Apps can override defaults |
| Zero additional infrastructure | MEDIUM | No new services to maintain |
| AI-assisted error analysis | MEDIUM | Claude integration for self-healing |
| Unified deployment metrics | LOW | Future Prometheus integration |

---

## 2. Decision

### 2.1 Architecture Choice

**We adopt a Hybrid Architecture (Option C)** combining:

1. **Reusable GitHub Workflows** in `platform` repository
2. **Shared Python Package** (`deployment-core`) for complex logic
3. **Enhanced Deployment MCP** for manual orchestration

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          platform repository                             │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  .github/workflows/                                               │   │
│  │  ├── _ci-python.yml          # Reusable: Lint, Test, Security    │   │
│  │  ├── _build-docker.yml       # Reusable: Build & Push to GHCR    │   │
│  │  ├── _deploy-hetzner.yml     # Reusable: SSH Deploy + Rollback   │   │
│  │  └── _security-scan.yml      # Reusable: Trivy, Gitleaks         │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  packages/deployment-core/                                        │   │
│  │  ├── deployment_core/                                             │   │
│  │  │   ├── health/          # Deep health check probes              │   │
│  │  │   ├── healing/         # AI-powered error analysis             │   │
│  │  │   ├── rollback/        # Smart rollback strategies             │   │
│  │  │   ├── notify/          # Unified notifications                 │   │
│  │  │   └── scripts/         # Shared bash scripts                   │   │
│  │  └── pyproject.toml                                               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    uses: achimdehnert/platform/.github/workflows/
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
   ┌─────────┐                ┌─────────┐                ┌─────────┐
   │ BFAgent │                │Travel-B.│                │ MCP-Hub │
   │─────────│                │─────────│                │─────────│
   │ 15 lines│                │ 15 lines│                │ 15 lines│
   │ workflow│                │ workflow│                │ workflow│
   └─────────┘                └─────────┘                └─────────┘
```

### 2.2 Rejected Alternatives

#### Option A: Centralized Deployment Service

```
❌ Rejected because:
- Adds infrastructure complexity (new service to maintain)
- Single Point of Failure
- Overkill for current scale (~20 deploys/day total)
- Requires additional hosting costs
```

#### Option B: Status Quo (Decentralized)

```
❌ Rejected because:
- Growing maintenance burden with each new app
- No knowledge sharing between apps
- Inconsistent deployment policies
```

---

## 3. Implementation

### 3.1 Reusable Workflows

Location: `platform/.github/workflows/`

| Workflow | Purpose | Inputs |
|----------|---------|--------|
| `_ci-python.yml` | Lint, test, security scan | python_version, coverage_threshold |
| `_build-docker.yml` | Build & push to GHCR | dockerfile, target, platforms |
| `_deploy-hetzner.yml` | SSH deploy with rollback | app_name, deploy_path, health_url |
| `_security-scan.yml` | Trivy, Gitleaks | scan_type, severity |

### 3.2 deployment-core Package

```python
# packages/deployment-core/deployment_core/__init__.py
from .health import HealthChecker, HTTPProbe, TCPProbe, CommandProbe
from .healing import ErrorAnalyzer, AutoFixer, HetznerPatterns
from .rollback import RollbackManager, RollbackStrategy
from .notify import Notifier, SlackNotifier, EmailNotifier

__all__ = [
    "HealthChecker", "HTTPProbe", "TCPProbe", "CommandProbe",
    "ErrorAnalyzer", "AutoFixer", "HetznerPatterns", 
    "RollbackManager", "RollbackStrategy",
    "Notifier", "SlackNotifier", "EmailNotifier",
]
```

### 3.3 App Integration

After migration, app workflows become minimal:

```yaml
# travel-beat/.github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  ci:
    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@main
    with:
      python_version: "3.12"
      coverage_threshold: 70
    secrets: inherit

  build:
    needs: [ci]
    uses: achimdehnert/platform/.github/workflows/_build-docker.yml@main
    with:
      dockerfile: docker/Dockerfile
    secrets: inherit

  deploy:
    needs: [build]
    uses: achimdehnert/platform/.github/workflows/_deploy-hetzner.yml@main
    with:
      app_name: travel-beat
      deploy_path: /opt/travel-beat
      health_url: https://travel-beat.iil.pet/health/
      compose_file: docker-compose.prod.yml
      enable_auto_healer: true
    secrets: inherit
```

---

## 4. Migration Plan

### Phase 1: Foundation (Week 1)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | Create `deployment-core` package structure | `pyproject.toml`, base classes |
| 3-4 | Implement HealthChecker with probes | `health/` module with tests |
| 5 | Implement ErrorAnalyzer (refactor auto-healer) | `healing/` module |

### Phase 2: Reusable Workflows (Week 2)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | Create `_ci-python.yml` | Tested with Travel-Beat |
| 3 | Create `_build-docker.yml` | Tested with Travel-Beat |
| 4-5 | Create `_deploy-hetzner.yml` | Tested with Travel-Beat |

### Phase 3: App Migration (Week 3)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Migrate Travel-Beat | Fully using reusable workflows |
| 2 | Migrate BFAgent | Fully using reusable workflows |
| 3 | Migrate MCP-Hub | Fully using reusable workflows |
| 4-5 | Migrate remaining hubs | All apps migrated |

### Phase 4: Enhancements (Week 4)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | Claude Auto-Healer integration | AI-powered error analysis |
| 3-4 | Deployment MCP enhancements | `trigger_auto_fix` tool |
| 5 | Documentation & ADR finalization | Complete docs |

---

## 5. Consequences

### 5.1 Positive

- **~90% reduction in workflow code** per app (525 → 50 lines)
- **Single source of truth** for deployment policies
- **Shared learning**: Auto-healer improvements benefit all apps
- **Easier onboarding**: New apps inherit best practices
- **Consistent security**: All apps get same security scanning

### 5.2 Negative

- **Coupling to platform repo**: Apps depend on platform workflows
- **Version coordination**: Breaking changes require careful rollout
- **Learning curve**: Team needs to understand reusable workflow patterns

### 5.3 Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking changes | Semantic versioning on workflow tags (`@v1`, `@v2`) |
| Platform repo unavailable | GitHub's high availability; workflows cached |
| Override needed | Apps can still define custom steps after calling reusable |

---

## 6. Metrics & Success Criteria

### 6.1 Quantitative

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Workflow lines per app | ~800 | <100 | Line count |
| Time to add new app | ~4 hours | <30 min | Developer time |
| Deployment success rate | ~92% | >98% | GitHub Actions stats |
| MTTR (Mean Time to Recovery) | ~15 min | <5 min | Rollback time |

### 6.2 Qualitative

- [ ] All apps using reusable workflows
- [ ] Auto-healer successfully resolves >50% of common errors
- [ ] Zero deployment-related incidents from configuration drift
- [ ] Positive developer feedback on maintenance burden

---

## 7. References

- [GitHub Reusable Workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [Platform Architecture Master](../PLATFORM_ARCHITECTURE_MASTER.md)
- [Hetzner Deployment Prompt](../../concepts/hetzner_deployment_prompt.md)
- [ADR-008: Infrastructure Services](./ADR-008-infrastructure-services.md)

---

## 8. Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-02-02 | Achim Dehnert | Initial draft |
