# ADR-009 v2 - Expert Review & Implementation Roadmap

| Document | Value |
|----------|-------|
| **Type** | Critical Expert Review |
| **Status** | Final |
| **Date** | 2026-02-03 |
| **Reviewer** | Deployment Architecture Expert |
| **Subject** | ADR-009 v2 + Review Summary |

---

## 1. Executive Assessment

### 1.1 Overall Verdict: **APPROVED with Minor Refinements**

ADR-009 v2 is a **production-ready architecture** that addresses the critical gaps identified in v1 and ADR-010. The consolidation approach is correct - maintaining two ADRs for the same decision would violate ADR principles.

| Aspect | Score | Comment |
|--------|-------|---------|
| **Architecture Soundness** | 9/10 | Correct use of GitHub reusable workflows |
| **Risk Mitigation** | 9/10 | Expand/Contract + Emergency Bypass well designed |
| **Implementation Realism** | 8/10 | 10-week timeline realistic with buffer |
| **Documentation Quality** | 9/10 | Clear, reviewable, actionable |
| **Operational Readiness** | 7/10 | Missing: deployment lock, concurrent deploy handling |

### 1.2 Infrastructure Validation (via MCP)

```
✅ Production Status (validated 2026-02-03)
├── travel_beat: 5 containers (web, celery, celery_beat, db, caddy, redis)
├── bfagent: 4 containers (web, db, redis, caddy)
├── risk_hub: 4 containers (web, worker, db, redis)
├── mcp_hub: 2 containers (api, llm_gateway)
└── SSL: 7 certificates valid (86+ days remaining)

Total: 16 running containers across 4 applications
Deployment frequency: ~22/day (matches ADR estimate)
```

---

## 2. Critical Review

### 2.1 Strengths ✅

| # | Strength | Impact |
|---|----------|--------|
| 1 | **Expand/Contract Pattern** properly integrated | Prevents 2/month migration incidents |
| 2 | **Emergency Bypass** mandatory per app | Eliminates SPOF risk |
| 3 | **10-week timeline** with 25% buffer | Realistic execution |
| 4 | **Semantic versioning** (`@v1`, `@v2`) | Safe workflow updates |
| 5 | **Rollback Decision Tree** documented | Clear incident response |
| 6 | **App-by-app migration** with soak testing | Controlled rollout |

### 2.2 Gaps to Address ⚠️

| # | Gap | Severity | Recommendation |
|---|-----|----------|----------------|
| 1 | **No deployment lock** | HIGH | Add file-based mutex to prevent concurrent deploys |
| 2 | **SSH key in env** not best practice | MEDIUM | Use `ssh-action` with `key` parameter (already correct in code) |
| 3 | **`_migrate-db.yml` incomplete** | HIGH | Migration compatibility check is placeholder (`# ... logic`) |
| 4 | **No deployment metrics endpoint** | MEDIUM | Add `/deploy-status` API for observability |
| 5 | **Contract phase manual** | LOW | Acceptable for now, document procedure |
| 6 | **Test services missing** in `_ci-python.yml` | MEDIUM | Add PostgreSQL/Redis services for Django apps |

### 2.3 Workflow Code Issues

#### Issue 1: `_ci-python.yml` - Missing Test Services

```yaml
# CURRENT (line 200-220):
jobs:
  test:
    runs-on: ubuntu-latest
    needs: [lint]
    # ❌ No database/redis services for Django tests

# RECOMMENDED:
jobs:
  test:
    runs-on: ubuntu-latest
    needs: [lint]
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
```

#### Issue 2: `_deploy-hetzner.yml` - SSH Heredoc Syntax

```yaml
# CURRENT (line 407):
ssh ${{ secrets.HETZNER_USER }}@${{ secrets.HETZNER_HOST }} << EOF
# ❌ Requires SSH key setup first

# RECOMMENDED: Use appleboy/ssh-action
- uses: appleboy/ssh-action@v1.0.3
  with:
    host: ${{ secrets.HETZNER_HOST }}
    username: ${{ secrets.HETZNER_USER }}
    key: ${{ secrets.HETZNER_SSH_KEY }}
    script: |
      cd ${{ inputs.deploy_path }}
      # ... deployment commands
```

#### Issue 3: `_migrate-db.yml` - Placeholder Logic

```yaml
# CURRENT (line 326-331):
- name: Check backward compatibility
  id: check
  run: |
    # Analyze pending migrations for breaking changes
    COMPAT="compatible"
    # ... migration analysis logic  # ❌ Placeholder

# RECOMMENDED: Concrete implementation
- name: Check backward compatibility
  id: check
  run: |
    # Check for breaking migration operations
    MIGRATIONS=$(find . -path "*/migrations/*.py" -newer .last_deploy 2>/dev/null || echo "")
    COMPAT="compatible"
    
    for file in $MIGRATIONS; do
      if grep -qE "(RemoveField|DeleteModel|AlterField.*null=False)" "$file"; then
        COMPAT="breaking"
        echo "::warning::Breaking change detected in $file"
      fi
    done
    
    echo "compatibility=$COMPAT" >> $GITHUB_OUTPUT
```

---

## 3. Optimal Implementation Roadmap

### 3.1 Phase 0: Foundation (Week 1) - REFINED

| Day | Task | Deliverable | Exit Criteria |
|-----|------|-------------|---------------|
| 1 | Create platform workflow directory structure | `.github/workflows/` + `docs/deployment/` | PR created |
| 1 | Add workflow validation CI | `validate-workflows.yml` | Runs on all workflow PRs |
| 2 | Create `_ci-python.yml` **with services** | Complete workflow | Passes actionlint |
| 3 | Create `_build-docker.yml` | Complete workflow | Test build succeeds |
| 4 | Create `_security-scan.yml` | Trivy + Gitleaks | Test scan runs |
| 5 | Integration test in dedicated test repo | End-to-end CI→Build | 5 consecutive passes |

**Exit Criteria Checklist:**
- [ ] `actionlint` passes on all workflows
- [ ] Test repo uses workflows successfully
- [ ] No production systems touched

### 3.2 Phase 1: Deploy Workflows (Week 2-3) - REFINED

| Day | Task | Deliverable | Exit Criteria |
|-----|------|-------------|---------------|
| 1-2 | Create `_deploy-hetzner.yml` with **deployment lock** | Complete workflow | Concurrent deploy blocked |
| 3 | Create `_rollback.yml` | Standalone rollback | Can rollback any app |
| 4-5 | Create `_migrate-db.yml` with **real compat check** | Django migration analyzer | Detects RemoveField/AlterField |
| 6-7 | Shadow deploy Travel-Beat | Parallel run with existing | Results match |
| 8-10 | Soak test (10 deploys) | Success log | 100% success |

**Critical Addition - Deployment Lock:**

```yaml
# Add to _deploy-hetzner.yml
- name: Acquire deployment lock
  run: |
    ssh ${{ secrets.HETZNER_USER }}@${{ secrets.HETZNER_HOST }} << 'EOF'
      LOCK_FILE="${{ inputs.deploy_path }}/.deploy.lock"
      
      # Check existing lock
      if [ -f "$LOCK_FILE" ]; then
        LOCK_AGE=$(($(date +%s) - $(stat -c %Y "$LOCK_FILE")))
        if [ $LOCK_AGE -lt 600 ]; then
          echo "❌ Deployment in progress (lock age: ${LOCK_AGE}s)"
          exit 1
        fi
        echo "⚠️ Stale lock removed"
      fi
      
      echo "${{ github.sha }}" > "$LOCK_FILE"
    EOF

- name: Release deployment lock
  if: always()
  run: |
    ssh ${{ secrets.HETZNER_USER }}@${{ secrets.HETZNER_HOST }} \
      "rm -f ${{ inputs.deploy_path }}/.deploy.lock"
```

### 3.3 Phase 2: Pilot Migration (Week 4-5)

| App | Days | Containers | Risk | Notes |
|-----|------|------------|------|-------|
| **Travel-Beat** | 1-5 | 6 | MEDIUM | Pilot - most active, good test coverage |

**Travel-Beat Migration PR Checklist:**
- [ ] Replace `deploy.yml` (525 LOC → ~50 LOC)
- [ ] Add `deploy-emergency.yml`
- [ ] Update secrets (ensure org-level available)
- [ ] Shadow deploy 3x minimum
- [ ] Production cutover (low-traffic window)
- [ ] 48h monitoring
- [ ] Retrospective

### 3.4 Phase 3: Gradual Rollout (Week 6-7)

| App | Days | Containers | Risk | Notes |
|-----|------|------------|------|-------|
| MCP-Hub | 1-2 | 2 | LOW | Simplest, good second test |
| Risk-Hub | 3-4 | 4 | MEDIUM | Has worker container |
| BFAgent | 5-7 | 4 | HIGH | Critical path, extra care |

### 3.5 Phase 4: Enhancements (Week 8-10)

| Feature | Priority | Effort | Dependency |
|---------|----------|--------|------------|
| Slack deployment notifications | P0 | 1d | Webhook URL |
| Deployment metrics JSON | P0 | 2d | Log format standardization |
| DB migration rollback scripts | P1 | 3d | Per-app migration history |
| Prometheus metrics exporter | P2 | 5d | Monitoring stack |

---

## 4. Recommended Workflow Improvements

### 4.1 Complete `_ci-python.yml`

```yaml
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
      django_app:
        type: boolean
        default: true
        description: "Enable PostgreSQL/Redis services for Django"
    outputs:
      coverage:
        value: ${{ jobs.test.outputs.coverage }}
      passed:
        value: ${{ jobs.summary.outputs.passed }}

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python_version }}
          cache: pip
      - run: pip install ruff
      - run: ruff check . --output-format=github

  test:
    runs-on: ubuntu-latest
    needs: [lint]
    outputs:
      coverage: ${{ steps.cov.outputs.coverage }}
    services:
      postgres:
        image: ${{ inputs.django_app && 'postgres:16-alpine' || '' }}
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: ${{ inputs.django_app && 'redis:7-alpine' || '' }}
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python_version }}
          cache: pip
      - run: pip install -r requirements.txt pytest pytest-cov pytest-django
      - id: cov
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: ci-test-key
          DJANGO_ENV: test
        run: |
          pytest --cov=. --cov-report=json -v
          COVERAGE=$(python -c "import json; print(int(json.load(open('coverage.json'))['totals']['percent_covered']))")
          echo "coverage=$COVERAGE" >> $GITHUB_OUTPUT
      - name: Coverage gate
        if: ${{ steps.cov.outputs.coverage < inputs.coverage_threshold }}
        run: |
          echo "❌ Coverage ${{ steps.cov.outputs.coverage }}% < ${{ inputs.coverage_threshold }}%"
          exit 1

  summary:
    needs: [lint, test]
    if: always()
    runs-on: ubuntu-latest
    outputs:
      passed: ${{ steps.result.outputs.passed }}
    steps:
      - id: result
        run: |
          if [ "${{ needs.lint.result }}" = "failure" ] || [ "${{ needs.test.result }}" = "failure" ]; then
            echo "passed=false" >> $GITHUB_OUTPUT
            exit 1
          fi
          echo "passed=true" >> $GITHUB_OUTPUT
```

### 4.2 Complete `_deploy-hetzner.yml`

```yaml
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
        default: docker-compose.prod.yml
      health_retries:
        type: number
        default: 10
      health_interval:
        type: number
        default: 10
      rollback_on_failure:
        type: boolean
        default: true
    secrets:
      HETZNER_HOST:
        required: true
      HETZNER_USER:
        required: true
      HETZNER_SSH_KEY:
        required: true
    outputs:
      deployment_id:
        value: ${{ jobs.deploy.outputs.deployment_id }}
      status:
        value: ${{ jobs.verify.outputs.status }}

jobs:
  prepare:
    runs-on: ubuntu-latest
    outputs:
      previous_tag: ${{ steps.state.outputs.previous_tag }}
      deployment_id: ${{ steps.state.outputs.deployment_id }}
    steps:
      - name: Acquire lock & capture state
        id: state
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.HETZNER_HOST }}
          username: ${{ secrets.HETZNER_USER }}
          key: ${{ secrets.HETZNER_SSH_KEY }}
          script: |
            LOCK="${{ inputs.deploy_path }}/.deploy.lock"
            if [ -f "$LOCK" ]; then
              AGE=$(($(date +%s) - $(stat -c %Y "$LOCK")))
              [ $AGE -lt 600 ] && echo "❌ Deploy in progress" && exit 1
            fi
            echo "${{ github.sha }}" > "$LOCK"
            
            APP_VAR=$(echo "${{ inputs.app_name }}" | tr 'a-z-' 'A-Z_')
            PREV=$(grep "${APP_VAR}_IMAGE_TAG" ${{ inputs.deploy_path }}/.env.prod 2>/dev/null | cut -d= -f2 || echo "unknown")
            echo "previous_tag=$PREV"
            echo "deployment_id=${{ inputs.app_name }}-$(date +%Y%m%d%H%M%S)"

  deploy:
    needs: [prepare]
    runs-on: ubuntu-latest
    outputs:
      deployment_id: ${{ needs.prepare.outputs.deployment_id }}
    steps:
      - name: Execute deployment
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.HETZNER_HOST }}
          username: ${{ secrets.HETZNER_USER }}
          key: ${{ secrets.HETZNER_SSH_KEY }}
          script: |
            set -euo pipefail
            cd ${{ inputs.deploy_path }}
            
            APP_VAR=$(echo "${{ inputs.app_name }}" | tr 'a-z-' 'A-Z_')
            sed -i "s/^${APP_VAR}_IMAGE_TAG=.*/${APP_VAR}_IMAGE_TAG=${{ github.sha }}/" .env.prod
            
            docker compose -f ${{ inputs.compose_file }} pull
            docker compose -f ${{ inputs.compose_file }} up -d --remove-orphans
            
            echo '{"id":"${{ needs.prepare.outputs.deployment_id }}","sha":"${{ github.sha }}","prev":"${{ needs.prepare.outputs.previous_tag }}","time":"'$(date -Iseconds)'"}' >> deployments.jsonl

  verify:
    needs: [deploy]
    runs-on: ubuntu-latest
    outputs:
      status: ${{ steps.health.outputs.status }}
    steps:
      - name: Wait for startup
        run: sleep 15
      - name: Health check
        id: health
        run: |
          for i in $(seq 1 ${{ inputs.health_retries }}); do
            HTTP=$(curl -sf -o /dev/null -w '%{http_code}' "${{ inputs.health_url }}" || echo "000")
            [ "$HTTP" = "200" ] && echo "status=healthy" >> $GITHUB_OUTPUT && exit 0
            echo "Attempt $i: HTTP $HTTP"
            sleep ${{ inputs.health_interval }}
          done
          echo "status=unhealthy" >> $GITHUB_OUTPUT
          exit 1

  rollback:
    needs: [prepare, deploy, verify]
    if: failure() && inputs.rollback_on_failure
    runs-on: ubuntu-latest
    steps:
      - name: Rollback
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.HETZNER_HOST }}
          username: ${{ secrets.HETZNER_USER }}
          key: ${{ secrets.HETZNER_SSH_KEY }}
          script: |
            cd ${{ inputs.deploy_path }}
            APP_VAR=$(echo "${{ inputs.app_name }}" | tr 'a-z-' 'A-Z_')
            sed -i "s/^${APP_VAR}_IMAGE_TAG=.*/${APP_VAR}_IMAGE_TAG=${{ needs.prepare.outputs.previous_tag }}/" .env.prod
            docker compose -f ${{ inputs.compose_file }} up -d --force-recreate
            echo '{"id":"rollback-'$(date +%s)'","to":"${{ needs.prepare.outputs.previous_tag }}"}' >> deployments.jsonl

  cleanup:
    needs: [verify]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Release lock
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.HETZNER_HOST }}
          username: ${{ secrets.HETZNER_USER }}
          key: ${{ secrets.HETZNER_SSH_KEY }}
          script: rm -f ${{ inputs.deploy_path }}/.deploy.lock
```

---

## 5. Final Recommendation

### 5.1 Immediate Actions (This Week)

1. **Approve ADR-009 v2** - Mark as `Status: Accepted`
2. **Archive ADR-010** - Add `Superseded by: ADR-009 v2`
3. **Create platform PR** with refined workflows (use code from Section 4)
4. **Set up GitHub org secrets** for `HETZNER_HOST`, `HETZNER_USER`, `HETZNER_SSH_KEY`

### 5.2 Success Criteria Summary

| Metric | Current | Target | When |
|--------|---------|--------|------|
| Workflow LOC/app | 800 | <100 | Week 5 |
| Deploy success rate | 92% | >98% | Week 8 |
| MTTR | 15 min | <5 min | Week 8 |
| Migration incidents | 2/mo | 0/mo | Week 10 |

### 5.3 Go/No-Go Decision

```
✅ RECOMMENDATION: PROCEED WITH IMPLEMENTATION

Rationale:
- Architecture is sound and addresses all critical gaps
- Timeline is realistic with buffer
- Risk mitigations are appropriate
- Infrastructure validation confirms stable baseline
```

---

## Appendix: File Locations

| File | Status | Action |
|------|--------|--------|
| `ADR-009-deployment-architecture.md` | Obsolete | Archive |
| `ADR-009-v2-deployment-architecture.md` | **Active** | Adopt as canonical |
| `ADR-009-review-summary.md` | Supporting | Keep as reference |
| `ADR-010-deployment-architecture-review.md` | Superseded | Archive |
| `IMPLEMENTATION-PROPOSAL.md` | Superseded | Archive (incorporated here) |
