# ADR-009: Centralized Deployment Architecture

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Version** | 2.0 |
| **Date** | 2026-02-03 |
| **Author** | Achim Dehnert |
| **Reviewers** | Architecture Review |
| **Supersedes** | ADR-009 v1.0, ADR-010 (consolidated) |
| **Related** | ADR-008 (Infrastructure Services), PLATFORM_ARCHITECTURE_MASTER.md |

---

## 1. Executive Summary

This ADR establishes a **centralized deployment architecture** for the BF Agent Platform using GitHub Reusable Workflows. The approach reduces ~8000 lines of duplicated CI/CD code to ~500 lines while maintaining app autonomy and production stability.

**Key Decisions:**
1. Reusable GitHub Workflows in `platform` repository (primary)
2. Deferred `deployment-core` Python package (Phase 3)
3. Mandatory Emergency Bypass per application
4. Expand/Contract pattern for database migrations

---

## 2. Context

### 2.1 Platform Landscape

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BF AGENT PLATFORM - DEPLOYMENT MAP                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐  │
│  │  BF Agent   │   │ Travel-Beat │   │   MCP-Hub   │   │  Risk-Hub   │  │
│  │ ───────────│   │ ───────────│   │ ───────────│   │ ───────────│  │
│  │ ~5x/day    │   │ ~10x/day   │   │ ~3x/day    │   │ ~2x/day    │  │
│  │ Django+PG  │   │ Django+PG  │   │ FastAPI+PG │   │ Django+PG  │  │
│  │ CRITICAL   │   │ CRITICAL   │   │ STANDARD   │   │ STANDARD   │  │
│  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘  │
│                                                                          │
│  ┌─────────────┐   ┌─────────────┐                                      │
│  │   CAD-Hub   │   │    Docs     │   Total: ~22 deploys/day             │
│  │ ───────────│   │ ───────────│   Infrastructure: Hetzner Cloud       │
│  │ ~2x/day    │   │ ~5x/day    │   Registry: GitHub Container Registry │
│  │ Django+PG  │   │ Static     │                                        │
│  │ STANDARD   │   │ LOW        │                                        │
│  └─────────────┘   └─────────────┘                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Current Pain Points

| Problem | Impact | Frequency |
|---------|--------|-----------|
| Duplicated workflow code (~8000 LOC) | 4h+ per cross-cutting change | Monthly |
| Configuration drift between apps | Inconsistent security posture | Ongoing |
| No shared auto-healer learnings | Same errors repeat | Weekly |
| No unified deployment observability | Blind troubleshooting | Daily |
| DB migration rollback failures | Production incidents | 2/month |

### 2.3 Requirements

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| R1 | Reduce workflow duplication by >80% | CRITICAL | Maintainability |
| R2 | Maintain app deployment autonomy | CRITICAL | Team independence |
| R3 | Zero additional infrastructure services | HIGH | Operational simplicity |
| R4 | Safe DB migration rollback | HIGH | Production stability |
| R5 | Emergency bypass capability | HIGH | Incident response |
| R6 | Unified deployment metrics | MEDIUM | Observability |
| R7 | AI-assisted error analysis | LOW | Future enhancement |

---

## 3. Decision

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           platform repository                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  .github/workflows/                                                          │
│  ├── _ci-python.yml           # Lint, Test, Coverage                        │
│  ├── _build-docker.yml        # Build, Tag, Push to GHCR                    │
│  ├── _security-scan.yml       # Trivy, Gitleaks, SAST                       │
│  ├── _migrate-db.yml          # Expand/Contract migrations                  │
│  ├── _deploy-hetzner.yml      # SSH deploy with health checks               │
│  ├── _rollback.yml            # Automated rollback                          │
│  └── validate-workflows.yml   # PR validation for workflow changes          │
│                                                                              │
│  docs/                                                                       │
│  └── deployment/                                                             │
│      ├── runbook.md           # Operational procedures                       │
│      ├── troubleshooting.md   # Common issues & solutions                   │
│      └── emergency.md         # Emergency procedures                         │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                   uses: achimdehnert/platform/.github/workflows/@v1
                                   │
       ┌───────────────────────────┼───────────────────────────┐
       ▼                           ▼                           ▼
  ┌──────────┐               ┌──────────┐               ┌──────────┐
  │ App Repo │               │ App Repo │               │ App Repo │
  ├──────────┤               ├──────────┤               ├──────────┤
  │ deploy.yml (~50 LOC)     │ deploy.yml (~50 LOC)     │ deploy.yml (~50 LOC)
  │ deploy-emergency.yml     │ deploy-emergency.yml     │ deploy-emergency.yml
  │ ✓ Uses platform @v1      │ ✓ Uses platform @v1      │ ✓ Uses platform @v1
  └──────────┘               └──────────┘               └──────────┘
```

### 3.2 Deployment Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT PIPELINE STAGES                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. BUILD PHASE                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐                 │
│  │  LINT    │──▶│  TEST    │──▶│  BUILD   │──▶│  SCAN    │                 │
│  │ ruff/mypy│   │ pytest   │   │ docker   │   │ trivy    │                 │
│  │  <2min   │   │  <5min   │   │  <8min   │   │  <3min   │                 │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘                 │
│                                                                              │
│  2. DEPLOY PHASE (Expand/Contract Pattern)                                   │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │ BACKUP   │──▶│ EXPAND   │──▶│ DEPLOY   │──▶│ VERIFY   │──▶│ CONTRACT │  │
│  │ DB state │   │ add cols │   │ rolling  │   │ health   │   │ rm cols  │  │
│  │  <1min   │   │  <2min   │   │  <5min   │   │  <2min   │   │ MANUAL   │  │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └──────────┘  │
│       │              │              │              │                         │
│       │              │              │              ▼                         │
│       │              │              │         ┌──────────┐                   │
│       │              │              └────────▶│ ROLLBACK │◀── ON FAILURE    │
│       │              │                        │ auto/man │                   │
│       │              │                        └──────────┘                   │
│       ▼              ▼                                                       │
│  [State saved]  [Backward compatible]                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Rejected Alternatives

| Option | Description | Rejection Reason |
|--------|-------------|------------------|
| **A: Centralized Service** | Dedicated deployment orchestrator | Infrastructure overhead, SPOF, overkill for ~22 deploys/day |
| **B: Status Quo** | Keep per-app workflows | Growing maintenance burden, no shared learning |
| **D: ArgoCD/FluxCD** | Full GitOps platform | Kubernetes-centric, Hetzner VPS incompatible |

---

## 4. Technical Specification

### 4.1 Reusable Workflow Definitions

#### 4.1.1 `_ci-python.yml`

```yaml
# platform/.github/workflows/_ci-python.yml
name: CI Python (Reusable)
on:
  workflow_call:
    inputs:
      python_version:
        type: string
        default: "3.12"
      coverage_threshold:
        type: number
        default: 70
      enable_mypy:
        type: boolean
        default: true
      test_command:
        type: string
        default: "pytest tests/ -v --cov"
    outputs:
      coverage:
        description: "Test coverage percentage"
        value: ${{ jobs.test.outputs.coverage }}

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv pip install ruff mypy
      - run: ruff check .
      - if: ${{ inputs.enable_mypy }}
        run: mypy . --ignore-missing-imports

  test:
    runs-on: ubuntu-latest
    needs: [lint]
    outputs:
      coverage: ${{ steps.cov.outputs.coverage }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - id: cov
        run: |
          ${{ inputs.test_command }} --cov-report=json
          COVERAGE=$(jq '.totals.percent_covered' coverage.json)
          echo "coverage=$COVERAGE" >> $GITHUB_OUTPUT
      - name: Coverage Gate
        run: |
          if (( $(echo "${{ steps.cov.outputs.coverage }} < ${{ inputs.coverage_threshold }}" | bc -l) )); then
            echo "❌ Coverage ${{ steps.cov.outputs.coverage }}% below threshold ${{ inputs.coverage_threshold }}%"
            exit 1
          fi
```

#### 4.1.2 `_build-docker.yml`

```yaml
# platform/.github/workflows/_build-docker.yml
name: Build Docker (Reusable)
on:
  workflow_call:
    inputs:
      dockerfile:
        type: string
        default: "Dockerfile"
      platforms:
        type: string
        default: "linux/amd64"
      push:
        type: boolean
        default: true
    outputs:
      image_tag:
        description: "Full image tag"
        value: ${{ jobs.build.outputs.image_tag }}
      digest:
        description: "Image digest"
        value: ${{ jobs.build.outputs.digest }}

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image_tag: ${{ steps.meta.outputs.tags }}
      digest: ${{ steps.build.outputs.digest }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=sha,prefix=
            type=ref,event=branch
            type=semver,pattern={{version}}
      
      - name: Build and push
        id: build
        uses: docker/build-push-action@v6
        with:
          context: .
          file: ${{ inputs.dockerfile }}
          platforms: ${{ inputs.platforms }}
          push: ${{ inputs.push }}
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

#### 4.1.3 `_migrate-db.yml`

```yaml
# platform/.github/workflows/_migrate-db.yml
name: DB Migration (Reusable)
on:
  workflow_call:
    inputs:
      app_name:
        type: string
        required: true
      direction:
        type: string
        required: true
        # "expand" = add columns/tables (backward compatible)
        # "contract" = remove columns/tables (after deploy verified)
        # "check" = verify compatibility only
      migration_command:
        type: string
        default: "python manage.py migrate"
    outputs:
      migration_id:
        value: ${{ jobs.migrate.outputs.migration_id }}
      compatibility:
        value: ${{ jobs.migrate.outputs.compatibility }}

jobs:
  migrate:
    runs-on: ubuntu-latest
    outputs:
      migration_id: ${{ steps.run.outputs.migration_id }}
      compatibility: ${{ steps.check.outputs.compatibility }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Check backward compatibility
        id: check
        run: |
          # Analyze pending migrations for breaking changes
          # Breaking = DROP COLUMN, ALTER COLUMN NOT NULL, RENAME
          COMPAT="compatible"
          # ... migration analysis logic
          echo "compatibility=$COMPAT" >> $GITHUB_OUTPUT
      
      - name: Abort if not compatible and direction=expand
        if: ${{ steps.check.outputs.compatibility != 'compatible' && inputs.direction == 'expand' }}
        run: |
          echo "❌ Migration not backward compatible. Use expand/contract pattern."
          echo "See: https://martinfowler.com/bliki/ParallelChange.html"
          exit 1
      
      - name: Run migration
        if: ${{ inputs.direction != 'check' }}
        id: run
        env:
          SSH_HOST: ${{ secrets.HETZNER_HOST }}
          SSH_USER: ${{ secrets.HETZNER_USER }}
          SSH_KEY: ${{ secrets.HETZNER_SSH_KEY }}
        run: |
          # SSH to server and run migration
          MIGRATION_ID=$(date +%Y%m%d%H%M%S)
          echo "migration_id=$MIGRATION_ID" >> $GITHUB_OUTPUT
```

#### 4.1.4 `_deploy-hetzner.yml`

```yaml
# platform/.github/workflows/_deploy-hetzner.yml
name: Deploy Hetzner (Reusable)
on:
  workflow_call:
    inputs:
      app_name:
        type: string
        required: true
      deploy_path:
        type: string
        required: true
      health_url:
        type: string
        required: true
      compose_file:
        type: string
        default: "docker-compose.prod.yml"
      rollback_on_failure:
        type: boolean
        default: true
      health_check_retries:
        type: number
        default: 5
      health_check_interval:
        type: number
        default: 10
    outputs:
      deployment_id:
        value: ${{ jobs.deploy.outputs.deployment_id }}
      previous_version:
        value: ${{ jobs.deploy.outputs.previous_version }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    outputs:
      deployment_id: ${{ steps.deploy.outputs.deployment_id }}
      previous_version: ${{ steps.save_state.outputs.previous_version }}
    steps:
      - name: Save current state
        id: save_state
        run: |
          # SSH to get current version for rollback
          PREV=$(ssh ${{ secrets.HETZNER_USER }}@${{ secrets.HETZNER_HOST }} \
            "cat ${{ inputs.deploy_path }}/.current_version 2>/dev/null || echo 'none'")
          echo "previous_version=$PREV" >> $GITHUB_OUTPUT
      
      - name: Deploy
        id: deploy
        run: |
          DEPLOYMENT_ID="${{ github.sha }}-$(date +%s)"
          ssh ${{ secrets.HETZNER_USER }}@${{ secrets.HETZNER_HOST }} << EOF
            cd ${{ inputs.deploy_path }}
            echo "${{ github.sha }}" > .current_version
            docker compose -f ${{ inputs.compose_file }} pull
            docker compose -f ${{ inputs.compose_file }} up -d --remove-orphans
          EOF
          echo "deployment_id=$DEPLOYMENT_ID" >> $GITHUB_OUTPUT
      
      - name: Health check
        id: health
        run: |
          for i in $(seq 1 ${{ inputs.health_check_retries }}); do
            if curl -sf "${{ inputs.health_url }}" > /dev/null; then
              echo "✅ Health check passed on attempt $i"
              exit 0
            fi
            echo "⏳ Attempt $i failed, waiting ${{ inputs.health_check_interval }}s..."
            sleep ${{ inputs.health_check_interval }}
          done
          echo "❌ Health check failed after ${{ inputs.health_check_retries }} attempts"
          exit 1
      
      - name: Rollback on failure
        if: ${{ failure() && inputs.rollback_on_failure }}
        run: |
          echo "🔄 Rolling back to ${{ steps.save_state.outputs.previous_version }}"
          ssh ${{ secrets.HETZNER_USER }}@${{ secrets.HETZNER_HOST }} << EOF
            cd ${{ inputs.deploy_path }}
            # Restore previous image tag
            sed -i "s/IMAGE_TAG=.*/IMAGE_TAG=${{ steps.save_state.outputs.previous_version }}/" .env.prod
            docker compose -f ${{ inputs.compose_file }} up -d --force-recreate
          EOF
```

### 4.2 Emergency Bypass (Mandatory per App)

```yaml
# <app>/.github/workflows/deploy-emergency.yml
name: "⚠️ Emergency Deploy (Bypass Platform)"
on:
  workflow_dispatch:
    inputs:
      confirm_bypass:
        description: 'Type EMERGENCY to confirm platform bypass'
        required: true
      reason:
        description: 'Reason for emergency deployment'
        required: true

jobs:
  emergency-deploy:
    if: inputs.confirm_bypass == 'EMERGENCY'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Log emergency deployment
        run: |
          echo "⚠️ EMERGENCY DEPLOYMENT TRIGGERED"
          echo "Reason: ${{ inputs.reason }}"
          echo "Triggered by: ${{ github.actor }}"
          echo "Time: $(date -u)"
          # TODO: Send alert to Slack/PagerDuty
      
      - name: Direct deploy (no platform dependency)
        env:
          SSH_HOST: ${{ secrets.HETZNER_HOST }}
          SSH_USER: ${{ secrets.HETZNER_USER }}
          SSH_KEY: ${{ secrets.HETZNER_SSH_KEY }}
        run: |
          ssh $SSH_USER@$SSH_HOST << 'EOF'
            cd /opt/${{ github.event.repository.name }}
            docker compose pull
            docker compose up -d --force-recreate
          EOF
      
      - name: Verify deployment
        run: |
          sleep 30
          curl -sf "https://${{ github.event.repository.name }}.iil.pet/health/" || {
            echo "❌ Emergency deploy failed health check"
            exit 1
          }
          echo "✅ Emergency deployment completed"
```

### 4.3 App Integration Example

```yaml
# travel-beat/.github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]
  workflow_dispatch:

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

  security:
    needs: [build]
    uses: achimdehnert/platform/.github/workflows/_security-scan.yml@v1
    with:
      image_ref: ${{ needs.build.outputs.image_tag }}
    secrets: inherit

  migrate-expand:
    needs: [security]
    uses: achimdehnert/platform/.github/workflows/_migrate-db.yml@v1
    with:
      app_name: travel-beat
      direction: expand
    secrets: inherit

  deploy:
    needs: [migrate-expand]
    uses: achimdehnert/platform/.github/workflows/_deploy-hetzner.yml@v1
    with:
      app_name: travel-beat
      deploy_path: /opt/travel-beat
      health_url: https://drifttales.com/health/
      rollback_on_failure: true
    secrets: inherit

  notify:
    needs: [deploy]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Slack notification
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "${{ needs.deploy.result == 'success' && '✅' || '❌' }} travel-beat deploy: ${{ needs.deploy.result }}",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Travel-Beat Deployment*\nStatus: ${{ needs.deploy.result }}\nCommit: ${{ github.sha }}\nActor: ${{ github.actor }}"
                  }
                }
              ]
            }
```

---

## 5. Risk Assessment

### 5.1 Risk Matrix

| Risk | Probability | Impact | Score | Mitigation |
|------|-------------|--------|-------|------------|
| Platform workflow bug blocks all apps | Medium | Critical | **HIGH** | Emergency bypass + workflow validation CI |
| DB migration breaks rollback | High | Critical | **CRITICAL** | Expand/contract pattern + compat check |
| Secret leak during transition | Low | Critical | **MEDIUM** | Phased migration, org-level secrets |
| Extended rollout causes inconsistency | Medium | High | **HIGH** | App-by-app migration with soak testing |
| GitHub Actions outage | Low | High | **MEDIUM** | Emergency bypass documented |

### 5.2 Rollback Decision Tree

```
Health Check Failed?
│
├─ NO → Continue
│
└─ YES
   │
   ├─ Migration ran in this deploy?
   │  │
   │  ├─ NO → Rollback containers (automatic)
   │  │
   │  └─ YES → Check DB backward compatibility
   │     │
   │     ├─ COMPATIBLE → Rollback containers only
   │     │
   │     └─ NOT COMPATIBLE
   │        │
   │        └─ 🚨 CRITICAL ALERT
   │           - Manual intervention required
   │           - Page on-call engineer
   │           - Do NOT auto-rollback (data loss risk)
```

---

## 6. Implementation Plan

### 6.1 Timeline Overview

```
Week 1-2: Preparation & Foundation
Week 3-4: Pilot (Travel-Beat)
Week 5-6: Gradual Rollout
Week 7-8: Stabilization & Enhancements
Week 9-10: Buffer & Documentation
```

### 6.2 Phase 0: Preparation (Week 1)

| Day | Task | Owner | Deliverable | Exit Criteria |
|-----|------|-------|-------------|---------------|
| 1 | Create platform workflow directory | Dev | `.github/workflows/` | PR reviewed |
| 1 | Document deployment inventory | Dev | `docs/deployment-inventory.md` | All apps listed |
| 2 | Create workflow validation CI | Dev | `validate-workflows.yml` | Runs on PR |
| 3 | Create `_ci-python.yml` | Dev | Workflow file | 10 successful test runs |
| 4 | Create `_build-docker.yml` | Dev | Workflow file | 10 successful test runs |
| 5 | Integration test (test repo) | Dev | End-to-end pass | CI+Build work together |

**Exit Criteria:**
- [ ] All workflow files pass yamllint + actionlint
- [ ] Test repository successfully uses both workflows
- [ ] No production systems touched

### 6.3 Phase 1: Pilot Migration (Week 2-4)

| Day | Task | Owner | Deliverable | Exit Criteria |
|-----|------|-------|-------------|---------------|
| 1-3 | Create `_deploy-hetzner.yml` | Dev | Workflow file | Syntax valid |
| 4-5 | Create `_migrate-db.yml` | Dev | Workflow + compat check | Tests pass |
| 6-7 | Create `_rollback.yml` | Dev | Workflow file | Tested in isolation |
| 8 | Shadow deploy Travel-Beat | Dev | Comparison report | Results match existing |
| 9-10 | Soak test (10 deploys) | Dev | Success log | 100% success rate |
| 11-12 | Production cutover Travel-Beat | Dev | Merged PR | Live on platform workflows |
| 13-14 | Monitoring period | Ops | Incident report | Zero incidents |

**Exit Criteria:**
- [ ] Travel-Beat running fully on platform workflows
- [ ] Zero rollbacks required during soak test
- [ ] Health check response time unchanged (±10%)
- [ ] Team sign-off obtained

### 6.4 Phase 2: Gradual Rollout (Week 5-6)

| App | Days | Risk Level | Notes |
|-----|------|------------|-------|
| MCP-Hub | 1-2 | Low | Lowest traffic, good test |
| Docs | 3 | Low | Static site, simple |
| Risk-Hub | 4-5 | Medium | Has DB dependencies |
| CAD-Hub | 6-7 | Medium | Standard migration |
| BFAgent | 8-10 | High | Critical path, extra validation |

**Per-App Checklist:**
- [ ] Create migration PR
- [ ] Shadow deploy minimum 3x
- [ ] Team approval
- [ ] Production cutover
- [ ] 24h monitoring window
- [ ] Sign-off

### 6.5 Phase 3: Enhancements (Week 7-8)

| Feature | Priority | Effort | Dependencies |
|---------|----------|--------|--------------|
| Slack notifications | P0 | 1d | Webhook configured |
| Deployment metrics (JSON logs) | P0 | 2d | Log aggregation |
| DB migration rollback scripts | P1 | 3d | Phase 2 complete |
| `deployment-core` Python package | P2 | 5d | Stable workflows |
| Prometheus metrics | P2 | 5d | Monitoring stack |

### 6.6 Phase 4: Buffer & Documentation (Week 9-10)

- Complete runbook documentation
- Training sessions for team
- Address any deferred issues
- Final ADR update with learnings

---

## 7. Success Metrics

### 7.1 Quantitative KPIs

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Workflow LOC per app | ~800 | <100 | `find . -name "*.yml" \| xargs wc -l` |
| Deployment success rate | 92% | >98% | GitHub Actions stats |
| Mean time to deploy | 12 min | <8 min | Workflow duration |
| Mean time to rollback | 15 min | <3 min | Rollback workflow duration |
| Migration-caused incidents | 2/month | 0/month | Incident tracker |
| Time to onboard new app | 4 hours | <1 hour | Developer time |

### 7.2 Qualitative Checkpoints

- [ ] All apps using platform reusable workflows
- [ ] Emergency bypass tested quarterly
- [ ] Zero "it works on my machine" incidents
- [ ] Deployment runbook eliminated (fully automated)
- [ ] Positive developer feedback (survey >4/5)

---

## 8. Open Questions

| # | Question | Options | Decision | Rationale |
|---|----------|---------|----------|-----------|
| 1 | Build `deployment-core` package now? | Yes / Later | **Later (Phase 3)** | Start simple, add complexity when needed |
| 2 | Where to store org-level secrets? | Platform repo / GitHub org | **GitHub org secrets** | Single source of truth |
| 3 | Manual approval for production? | Yes / No | **No (auto with notification)** | Current state works, adds friction |
| 4 | Branch protection on platform? | Yes / No | **Yes (1 approval)** | Workflows affect all apps |
| 5 | Staging env for workflow testing? | Dedicated / Shared | **Dedicated test repo** | Safe experimentation |

---

## 9. Consequences

### 9.1 Positive

- **~90% reduction in workflow code** per app (800 → ~50 lines)
- **Single source of truth** for deployment policies
- **Shared learning**: Auto-healer improvements benefit all apps
- **Safer migrations**: Expand/contract pattern prevents rollback failures
- **Easier onboarding**: New apps inherit best practices
- **Consistent security**: All apps get same scanning

### 9.2 Negative

- **Coupling to platform repo**: Apps depend on platform workflows
- **Version coordination**: Breaking changes require careful rollout
- **Learning curve**: Team needs to understand reusable workflow patterns

### 9.3 Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking changes | Semantic versioning (`@v1`, `@v2`), changelog |
| Platform repo unavailable | Emergency bypass per app, GitHub HA |
| Override needed | Apps can add custom steps after calling reusable |
| Learning curve | Documentation, training sessions |

---

## 10. References

- [GitHub Reusable Workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [Expand/Contract Pattern](https://martinfowler.com/bliki/ParallelChange.html)
- [Platform Architecture Master](../PLATFORM_ARCHITECTURE_MASTER.md)
- [docs-infrastructure Pattern](../docs-infrastructure/README.md) (immutable releases)

---

## 11. Changelog

| Date | Version | Author | Change |
|------|---------|--------|--------|
| 2026-02-02 | 1.0 | Achim Dehnert | Initial draft |
| 2026-02-02 | 1.1 | Review | Critical review (ADR-010) |
| 2026-02-03 | 2.0 | Architecture Review | Consolidated, added expand/contract, realistic timeline |

---

## 12. Approval

| Role | Name | Date | Decision |
|------|------|------|----------|
| Owner | Achim Dehnert | | ☐ Approved / ☐ Revise |
| Dev Lead | | | ☐ Approved / ☐ Revise |
| Ops | | | ☐ Approved / ☐ Revise |
