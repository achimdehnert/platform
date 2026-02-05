# ADR-010: Centralized Deployment Architecture - Critical Review & Implementation

| Metadata | Value |
|----------|-------|
| **Status** | Draft - Pending Review |
| **Date** | 2026-02-02 |
| **Author** | Deployment Architecture Review |
| **Reviewers** | Achim Dehnert, Team |
| **Supersedes** | Refines ADR-009 |
| **Review Deadline** | 2026-02-09 |

---

## Executive Summary

ADR-009 proposes a hybrid deployment architecture with reusable GitHub workflows. This review identifies **critical gaps** and proposes a **phased implementation** that prioritizes production stability over feature completeness.

**Verdict**: The core concept is sound, but the timeline is unrealistic and key failure modes are unaddressed.

---

## 1. Critical Review of ADR-009

### 1.1 Strengths ✅

| Aspect | Assessment |
|--------|------------|
| **Reusable Workflows** | Correct approach - native GitHub, no infra overhead |
| **DRY Principle** | Valid - 8000 LOC reduction is achievable |
| **App Autonomy** | Well-designed - apps can override defaults |
| **Version Tagging** | `@v1`, `@v2` enables safe rollout |

### 1.2 Critical Gaps ❌

| Gap | Severity | Impact |
|-----|----------|--------|
| **No Canary Deployment** | HIGH | All-or-nothing deploys increase blast radius |
| **Missing Blue-Green Support** | MEDIUM | No instant rollback capability |
| **DB Migration Rollback Absent** | CRITICAL | Contract phase not implemented |
| **Secrets Rotation Undefined** | HIGH | No procedure for compromised credentials |
| **Multi-Region Ignored** | LOW | Future scalability blocked |
| **Monitoring Blind Spot** | HIGH | No deployment metrics/alerts |
| **4-Week Timeline Unrealistic** | HIGH | No buffer for integration issues |

### 1.3 Architectural Concerns

#### 1.3.1 Single Point of Failure

```
❌ PROBLEM: Platform repo becomes critical path for ALL deployments

If platform/.github/workflows/_deploy-hetzner.yml has a bug:
  → ALL 5 apps cannot deploy
  → Potential 4-8 hour outage during fix + release cycle
```

**Mitigation Required**: 
- Emergency bypass mechanism per app
- Workflow validation pipeline before merge

#### 1.3.2 Secret Sprawl

```
❌ PROBLEM: ADR-009 assumes `secrets: inherit` is sufficient

Current state:
  - 5 repos × 8 secrets = 40 secret instances
  - No rotation schedule
  - No audit trail for secret access
```

**Mitigation Required**:
- Centralized secrets in platform repo (org-level secrets)
- Documented rotation procedure
- Secret access logging

#### 1.3.3 Database Migration Risk

```
❌ PROBLEM: Expand/Contract pattern mentioned but not enforced

Current travel-beat/deploy.yml:
  - Runs migrations AFTER container update
  - No backward compatibility check
  - No contract phase implementation

FAILURE SCENARIO:
  1. Migration adds NOT NULL column
  2. New container starts, writes to new column
  3. Rollback to old container
  4. Old container crashes (unknown column)
```

**Mitigation Required**:
- Pre-deployment migration compatibility check
- Mandatory expand → deploy → contract sequence
- Migration rollback scripts

---

## 2. Revised Architecture

### 2.1 Deployment Flow (Corrected)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT PIPELINE v2                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │ 1. LINT  │──▶│ 2. TEST  │──▶│ 3. BUILD │──▶│ 4. SCAN  │──▶│ 5. STAGE │  │
│  │ + SAST   │   │ + COVER  │   │ + CACHE  │   │ + TRIVY  │   │ (opt.)   │  │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └────┬─────┘  │
│                                                                    │        │
│  ┌──────────────────────────────────────────────────────────────────┘        │
│  │                                                                           │
│  ▼                                                                           │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │6. EXPAND │──▶│7. DEPLOY │──▶│8. VERIFY │──▶│9. CONTRT │──▶│10. AUDIT │  │
│  │ (migrate)│   │ (rolling)│   │ (health) │   │ (migrate)│   │ (log)    │  │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └──────────┘   └──────────┘  │
│       │              │              │                                        │
│       │              │              ▼                                        │
│       │              │         ┌──────────┐                                  │
│       │              │         │ ROLLBACK │◀──── ON FAILURE                  │
│       │              │         │ (auto)   │                                  │
│       │              │         └──────────┘                                  │
│       │              │                                                       │
│       ▼              ▼                                                       │
│  [DB Backup]    [State Save]                                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Workflow Responsibility Matrix

| Workflow | Owner | Inputs | Outputs | SLA |
|----------|-------|--------|---------|-----|
| `_ci-python.yml` | Platform | python_version, coverage | pass/fail, coverage% | <5min |
| `_build-docker.yml` | Platform | dockerfile, platforms | image_tag, digest | <10min |
| `_security-scan.yml` | Platform | severity, image_ref | sarif, pass/fail | <3min |
| `_migrate-db.yml` | Platform | direction, app_name | migration_id, status | <5min |
| `_deploy-hetzner.yml` | Platform | app_name, health_url | deployment_id | <15min |
| `_rollback.yml` | Platform | deployment_id | rollback_id | <3min |

### 2.3 Emergency Bypass

Each app MUST maintain a minimal fallback workflow:

```yaml
# travel-beat/.github/workflows/deploy-emergency.yml
name: Emergency Deploy (Bypass Platform)
on:
  workflow_dispatch:
    inputs:
      confirm_bypass:
        description: 'Type BYPASS to confirm'
        required: true

jobs:
  deploy:
    if: inputs.confirm_bypass == 'BYPASS'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Direct deploy (no platform dependency)
        run: |
          # Inline deployment logic - last resort only
          ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} << 'EOF'
            cd /opt/travel-beat
            docker compose pull && docker compose up -d
          EOF
```

---

## 3. Risk Assessment

### 3.1 Risk Matrix

| Risk | Probability | Impact | Score | Mitigation |
|------|-------------|--------|-------|------------|
| Platform workflow bug blocks all apps | Medium | Critical | **HIGH** | Emergency bypass + validation pipeline |
| Migration breaks rollback | High | Critical | **CRITICAL** | Mandatory compat check |
| Secret leak during transition | Low | Critical | **MEDIUM** | Phased secret migration |
| Extended rollout causes inconsistency | Medium | High | **HIGH** | App-by-app migration with validation |
| GitHub Actions outage | Low | High | **MEDIUM** | MCP fallback documented |

### 3.2 Rollback Decision Tree

```
Health Check Failed?
├── YES
│   ├── Migration ran?
│   │   ├── YES → Check DB backward compat
│   │   │   ├── Compatible → Rollback containers only
│   │   │   └── NOT Compatible → ALERT: Manual intervention required
│   │   └── NO → Rollback containers
│   └── Attempt rollback
│       ├── Success → Log & notify
│       └── Failure → CRITICAL ALERT → On-call
└── NO → Continue
```

---

## 4. Revised Implementation Plan

### 4.1 Phase 0: Preparation (Week 1)

**Goal**: Establish foundation without touching production

| Day | Task | Owner | Deliverable | Acceptance Criteria |
|-----|------|-------|-------------|---------------------|
| 1 | Create `platform/.github/workflows/` structure | Dev | Directory + README | PR reviewed |
| 1 | Document current deployment inventory | Dev | `docs/deployment-inventory.md` | All apps listed |
| 2 | Create `_ci-python.yml` draft | Dev | Workflow file | Syntax valid |
| 2 | Add workflow validation pipeline | Dev | `.github/workflows/validate-workflows.yml` | Runs on PR |
| 3 | Test `_ci-python.yml` in isolation | Dev | Test repo | 10 successful runs |
| 4 | Create `_build-docker.yml` draft | Dev | Workflow file | Syntax valid |
| 5 | Integration test both workflows | Dev | Combined test | End-to-end pass |

**Exit Criteria**: 
- [ ] All workflow files pass yamllint
- [ ] Test repository successfully uses both workflows
- [ ] No production systems touched

### 4.2 Phase 1: Pilot Migration (Week 2-3)

**Goal**: Migrate ONE app (Travel-Beat) with full validation

| Day | Task | Owner | Deliverable | Acceptance Criteria |
|-----|------|-------|-------------|---------------------|
| 1-2 | Create `_deploy-hetzner.yml` | Dev | Workflow file | Syntax valid |
| 3 | Create `_migrate-db.yml` with compat check | Dev | Workflow file | Includes backward compat |
| 4 | Shadow deploy: Run platform workflow alongside existing | Dev | Comparison report | Results match |
| 5 | Create travel-beat migration PR | Dev | `travel-beat#xxx` | Draft PR |
| 6-7 | Soak test: Run 10 deploys via platform workflow | Dev | Success log | 100% success rate |
| 8 | Production cutover: Travel-Beat | Dev | Merged PR | Live deployment |
| 9-10 | Monitor for 48 hours | Ops | Incident report | Zero incidents |

**Exit Criteria**:
- [ ] Travel-Beat running fully on platform workflows
- [ ] Zero rollbacks required
- [ ] Health check response time unchanged
- [ ] Team sign-off obtained

### 4.3 Phase 2: Gradual Rollout (Week 4-5)

**Goal**: Migrate remaining apps one at a time

| App | Day | Risk Level | Notes |
|-----|-----|------------|-------|
| MCP-Hub | 1-2 | Low | Lowest traffic |
| Risk-Hub | 3-4 | Medium | Has DB dependencies |
| BFAgent | 5-7 | High | Critical path, extra validation |
| CAD-Hub | 8-9 | Medium | Standard migration |

**Per-App Checklist**:
- [ ] Create migration PR
- [ ] Shadow deploy minimum 3x
- [ ] Team approval
- [ ] Production cutover
- [ ] 24h monitoring window
- [ ] Sign-off

### 4.4 Phase 3: Enhancements (Week 6+)

**Goal**: Add advanced features after stable baseline

| Feature | Priority | Effort | Dependencies |
|---------|----------|--------|--------------|
| DB migration rollback scripts | P0 | 3d | Phase 2 complete |
| Slack notifications | P1 | 1d | Webhook configured |
| Deployment metrics (Prometheus) | P2 | 5d | Monitoring stack |
| Canary deployment support | P2 | 5d | Load balancer access |
| Blue-green deployment | P3 | 8d | Infra changes |

---

## 5. Success Metrics

### 5.1 Quantitative KPIs

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Workflow LOC per app | 800 | <100 | `wc -l` |
| Deployment success rate | 92% | >98% | GitHub Actions stats |
| Mean time to deploy | 12 min | <8 min | Workflow duration |
| Mean time to rollback | 15 min | <3 min | Rollback workflow duration |
| Migration-caused incidents | 2/month | 0/month | Incident tracker |

### 5.2 Qualitative Checkpoints

- [ ] All team members can deploy any app
- [ ] New app onboarding < 1 hour
- [ ] Zero "it works on my machine" incidents
- [ ] Deployment runbook eliminated (automated)

---

## 6. Open Questions for Review

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Should `deployment-core` Python package be built? | Yes / No / Later | **Later** - Start with workflows only |
| 2 | Where to store org-level secrets? | Platform repo / GitHub org secrets | **GitHub org secrets** |
| 3 | Who approves production deploys? | Auto / Manual gate | **Auto with notification** (current state) |
| 4 | Should we enforce branch protection on platform? | Yes / No | **Yes** - Require 1 approval |
| 5 | Staging environment for workflow testing? | Dedicated / Shared | **Dedicated test repo** |

---

## 7. Decision Required

### 7.1 Approve / Reject / Revise

```
[ ] APPROVED - Proceed with Phase 0
[ ] APPROVED WITH CONDITIONS - List conditions: _______________
[ ] REVISE - Address feedback: _______________
[ ] REJECTED - Reason: _______________
```

### 7.2 Reviewer Sign-off

| Reviewer | Role | Date | Decision |
|----------|------|------|----------|
| Achim Dehnert | Owner | | |
| ___________ | Dev | | |
| ___________ | Ops | | |

---

## 8. Appendix

### A. Current vs Proposed Workflow Comparison

**Current (travel-beat/deploy.yml)**:
```yaml
# 525 lines
# Responsibilities: lint, test, build, scan, migrate, deploy, verify, rollback, audit
# Issues:
#   - All logic in one file
#   - App-specific hardcoding (drifttales.com)
#   - No reusability
```

**Proposed (travel-beat/deploy.yml)**:
```yaml
# ~50 lines
name: Deploy
on:
  push:
    branches: [main]

jobs:
  ci:
    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@v1
    with:
      python_version: "3.12"
      coverage_threshold: 70
    secrets: inherit

  build:
    needs: [ci]
    uses: achimdehnert/platform/.github/workflows/_build-docker.yml@v1
    with:
      dockerfile: docker/Dockerfile
    secrets: inherit

  migrate:
    needs: [build]
    uses: achimdehnert/platform/.github/workflows/_migrate-db.yml@v1
    with:
      app_name: travel-beat
      direction: expand
    secrets: inherit

  deploy:
    needs: [migrate]
    uses: achimdehnert/platform/.github/workflows/_deploy-hetzner.yml@v1
    with:
      app_name: travel-beat
      deploy_path: /opt/travel-beat
      health_url: https://drifttales.com/health/
    secrets: inherit
```

### B. Rollback Procedure (Current Gap)

```bash
#!/bin/bash
# deploy/scripts/rollback.sh - MISSING FROM CURRENT IMPLEMENTATION

set -euo pipefail

APP_NAME="${1:?Usage: rollback.sh <app_name> [deployment_id]}"
DEPLOYMENT_ID="${2:-$(tail -1 /opt/$APP_NAME/deployments.log | jq -r '.id')}"

# 1. Get previous state
PREV=$(jq -r "select(.id == \"$DEPLOYMENT_ID\") | .previous" /opt/$APP_NAME/deployments.log)

# 2. Check DB compatibility
COMPAT=$(docker exec ${APP_NAME}_web python manage.py check_migration_compat --target=$PREV)
if [ "$COMPAT" != "compatible" ]; then
    echo "❌ CRITICAL: Database not compatible with rollback target"
    echo "Manual intervention required. Contact on-call."
    exit 1
fi

# 3. Execute rollback
sed -i "s/^.*IMAGE_TAG=.*/${APP_NAME^^}_IMAGE_TAG=$PREV/" /opt/$APP_NAME/.env.prod
docker compose -f /opt/$APP_NAME/docker-compose.prod.yml up -d --force-recreate

# 4. Verify
sleep 10
curl -sf "https://$(grep DOMAIN /opt/$APP_NAME/.env.prod | cut -d= -f2)/health/" || {
    echo "❌ Rollback failed health check"
    exit 1
}

echo "✅ Rollback to $PREV completed"
```

### C. References

- [GitHub Reusable Workflows Documentation](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [Expand/Contract Pattern](https://martinfowler.com/bliki/ParallelChange.html)
- [ADR-009: Original Proposal](./ADR-009-deployment-architecture.md)
- [Current travel-beat/deploy.yml](https://github.com/achimdehnert/travel-beat/blob/main/.github/workflows/deploy.yml)

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-02-02 | Review | Initial critical review |
