# Implementation Proposal: Centralized Deployment Architecture

| Document | Value |
|----------|-------|
| **Type** | Implementation Proposal |
| **Status** | Ready for Review |
| **Date** | 2026-02-02 |
| **Related ADR** | ADR-010 |
| **Estimated Effort** | 6 weeks (30 person-days) |

---

## 1. Scope

This proposal defines the **concrete implementation steps** for migrating to centralized deployment workflows. It is designed to be **reviewable** with clear acceptance criteria for each deliverable.

### 1.1 In Scope

- ✅ Reusable GitHub Workflows (`_ci-python.yml`, `_build-docker.yml`, `_deploy-hetzner.yml`)
- ✅ Migration of 5 applications (Travel-Beat, BFAgent, MCP-Hub, Risk-Hub, CAD-Hub)
- ✅ Database migration safety checks
- ✅ Automated rollback mechanism
- ✅ Emergency bypass workflows

### 1.2 Out of Scope (Phase 2+)

- ❌ `deployment-core` Python package (defer to later)
- ❌ AI-powered auto-healer (defer to later)
- ❌ Canary/Blue-Green deployments (defer to later)
- ❌ Multi-region support (defer to later)

---

## 2. Deliverables & Pull Requests

### 2.1 PR Structure

```
platform/
├── PR #1: Foundation
│   ├── .github/workflows/_ci-python.yml
│   ├── .github/workflows/validate-workflows.yml
│   └── docs/deployment-architecture.md
│
├── PR #2: Build Workflow
│   └── .github/workflows/_build-docker.yml
│
├── PR #3: Deploy Workflow
│   ├── .github/workflows/_deploy-hetzner.yml
│   └── .github/workflows/_rollback.yml
│
└── PR #4: Migration Safety
    └── .github/workflows/_migrate-db.yml

travel-beat/
└── PR #5: Pilot Migration
    ├── .github/workflows/deploy.yml (rewritten)
    └── .github/workflows/deploy-emergency.yml (new)
```

---

## 3. PR #1: Foundation

### 3.1 Files to Create

#### `.github/workflows/_ci-python.yml`

```yaml
# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  REUSABLE WORKFLOW: Python CI                                              ║
# ║  Version: 1.0.0                                                            ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

name: Python CI

on:
  workflow_call:
    inputs:
      python_version:
        description: 'Python version to use'
        type: string
        default: '3.12'
      coverage_threshold:
        description: 'Minimum test coverage percentage'
        type: number
        default: 70
      working_directory:
        description: 'Working directory for commands'
        type: string
        default: '.'
      requirements_file:
        description: 'Path to requirements.txt'
        type: string
        default: 'requirements.txt'
      run_security_scan:
        description: 'Run Bandit security scan'
        type: boolean
        default: true
      skip_tests:
        description: 'Skip test execution (emergency only)'
        type: boolean
        default: false
    outputs:
      coverage:
        description: 'Test coverage percentage'
        value: ${{ jobs.test.outputs.coverage }}
      passed:
        description: 'Whether all checks passed'
        value: ${{ jobs.summary.outputs.passed }}

jobs:
  lint:
    name: "Lint"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python_version }}
          cache: 'pip'
      
      - name: Install linters
        run: pip install ruff black isort
      
      - name: Ruff
        run: ruff check ${{ inputs.working_directory }} --output-format=github
        continue-on-error: true
      
      - name: Black (check only)
        run: black --check ${{ inputs.working_directory }}
        continue-on-error: true

  security:
    name: "Security"
    runs-on: ubuntu-latest
    if: ${{ inputs.run_security_scan }}
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python_version }}
          cache: 'pip'
      
      - name: Install security tools
        run: pip install bandit safety
      
      - name: Bandit scan
        run: |
          bandit -r ${{ inputs.working_directory }} \
            -ll -ii \
            -x '**/tests/**,**/test_*.py' \
            -f json -o bandit-report.json || true
          
          if [ -f bandit-report.json ]; then
            HIGH=$(jq '.metrics._totals."SEVERITY.HIGH" // 0' bandit-report.json)
            CRITICAL=$(jq '.metrics._totals."SEVERITY.CRITICAL" // 0' bandit-report.json 2>/dev/null || echo 0)
            if [ "$HIGH" -gt 0 ] || [ "$CRITICAL" -gt 0 ]; then
              echo "::warning::Found $HIGH high and $CRITICAL critical severity issues"
            fi
          fi
      
      - name: Safety check
        run: |
          if [ -f "${{ inputs.requirements_file }}" ]; then
            safety check -r ${{ inputs.requirements_file }} || true
          fi

  test:
    name: "Test"
    runs-on: ubuntu-latest
    if: ${{ !inputs.skip_tests }}
    outputs:
      coverage: ${{ steps.coverage.outputs.percentage }}
    services:
      postgres:
        image: postgres:16-alpine
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
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python_version }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r ${{ inputs.requirements_file }}
          pip install pytest pytest-django pytest-cov pytest-xdist
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: ci-test-secret-key-not-for-production
          DJANGO_ENV: test
        run: |
          pytest \
            --cov=${{ inputs.working_directory }} \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=${{ inputs.coverage_threshold }} \
            -n auto \
            -v
      
      - name: Extract coverage
        id: coverage
        run: |
          COVERAGE=$(python -c "import xml.etree.ElementTree as ET; tree = ET.parse('coverage.xml'); print(int(float(tree.getroot().attrib['line-rate']) * 100))")
          echo "percentage=$COVERAGE" >> $GITHUB_OUTPUT
      
      - uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: false

  summary:
    name: "Summary"
    needs: [lint, security, test]
    if: always()
    runs-on: ubuntu-latest
    outputs:
      passed: ${{ steps.check.outputs.passed }}
    steps:
      - name: Check results
        id: check
        run: |
          if [ "${{ needs.lint.result }}" == "failure" ] || \
             [ "${{ needs.test.result }}" == "failure" ]; then
            echo "passed=false" >> $GITHUB_OUTPUT
            exit 1
          fi
          echo "passed=true" >> $GITHUB_OUTPUT
```

#### `.github/workflows/validate-workflows.yml`

```yaml
# Validates reusable workflows before merge
name: Validate Workflows

on:
  pull_request:
    paths:
      - '.github/workflows/_*.yml'

jobs:
  validate:
    name: "Validate Syntax"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install yamllint
        run: pip install yamllint
      
      - name: Lint workflow files
        run: |
          yamllint -d "{extends: relaxed, rules: {line-length: {max: 120}}}" \
            .github/workflows/_*.yml
      
      - name: Validate workflow syntax
        run: |
          for file in .github/workflows/_*.yml; do
            echo "Validating $file..."
            # Check for required 'on: workflow_call'
            if ! grep -q "workflow_call" "$file"; then
              echo "::error file=$file::Missing 'on: workflow_call' trigger"
              exit 1
            fi
          done
          echo "✅ All workflows valid"
```

### 3.2 Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | `_ci-python.yml` passes yamllint | `yamllint .github/workflows/_ci-python.yml` |
| 2 | Workflow has `on: workflow_call` | Manual review |
| 3 | All inputs documented | Manual review |
| 4 | Outputs defined for downstream jobs | Manual review |
| 5 | Test workflow in isolated repo | 3 successful runs |

### 3.3 Review Checklist

```markdown
## PR Review Checklist

- [ ] Workflow syntax valid (yamllint passes)
- [ ] All inputs have descriptions and defaults
- [ ] Outputs are documented
- [ ] Error handling present (continue-on-error where appropriate)
- [ ] Secrets not hardcoded
- [ ] Version pinned for actions (e.g., `@v4` not `@main`)
- [ ] Tested in isolation
```

---

## 4. PR #3: Deploy Workflow

### 4.1 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Rollback trigger | Automatic on health failure | Minimizes MTTR |
| Health check retries | 10 × 10s = 100s window | Allows slow startup |
| State storage | JSON file on server | Simple, no external deps |
| Deployment lock | File-based mutex | Prevents concurrent deploys |

### 4.2 `.github/workflows/_deploy-hetzner.yml`

```yaml
# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  REUSABLE WORKFLOW: Hetzner Deployment                                     ║
# ║  Version: 1.0.0                                                            ║
# ║  Features: Rolling update, health checks, automatic rollback               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

name: Deploy to Hetzner

on:
  workflow_call:
    inputs:
      app_name:
        description: 'Application identifier (e.g., travel-beat)'
        type: string
        required: true
      deploy_path:
        description: 'Deployment directory on server'
        type: string
        required: true
      health_url:
        description: 'Health check endpoint URL'
        type: string
        required: true
      compose_file:
        description: 'Docker Compose filename'
        type: string
        default: 'docker-compose.prod.yml'
      image_tag:
        description: 'Docker image tag (default: git SHA)'
        type: string
        default: ''
      health_retries:
        description: 'Number of health check attempts'
        type: number
        default: 10
      health_interval:
        description: 'Seconds between health checks'
        type: number
        default: 10
      enable_rollback:
        description: 'Auto-rollback on failure'
        type: boolean
        default: true
    secrets:
      DEPLOY_HOST:
        required: true
      DEPLOY_USER:
        required: true
      DEPLOY_SSH_KEY:
        required: true
    outputs:
      deployment_id:
        description: 'Unique deployment identifier'
        value: ${{ jobs.deploy.outputs.deployment_id }}
      status:
        description: 'Final deployment status'
        value: ${{ jobs.verify.outputs.status }}

jobs:
  # ─────────────────────────────────────────────────────────────────────────
  # PRE-DEPLOYMENT: Acquire lock, backup state
  # ─────────────────────────────────────────────────────────────────────────
  prepare:
    name: "Prepare"
    runs-on: ubuntu-latest
    outputs:
      previous_tag: ${{ steps.state.outputs.previous_tag }}
      deployment_id: ${{ steps.state.outputs.deployment_id }}
    steps:
      - name: Acquire deployment lock
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            LOCK_FILE="${{ inputs.deploy_path }}/.deploy.lock"
            
            # Check for existing lock
            if [ -f "$LOCK_FILE" ]; then
              LOCK_AGE=$(($(date +%s) - $(stat -c %Y "$LOCK_FILE")))
              if [ $LOCK_AGE -lt 600 ]; then
                echo "::error::Deployment in progress (lock age: ${LOCK_AGE}s)"
                exit 1
              fi
              echo "::warning::Stale lock detected, removing"
            fi
            
            # Acquire lock
            echo "${{ github.sha }}" > "$LOCK_FILE"
      
      - name: Capture current state
        id: state
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            cd ${{ inputs.deploy_path }}
            
            # Get current image tag
            APP_ENV=$(echo "${{ inputs.app_name }}" | tr '[:lower:]-' '[:upper:]_')
            PREV_TAG=$(grep "${APP_ENV}_IMAGE_TAG" .env.prod 2>/dev/null | cut -d= -f2 || echo "unknown")
            
            # Generate deployment ID
            DEPLOY_ID="${{ inputs.app_name }}-$(date +%Y%m%d%H%M%S)"
            
            echo "previous_tag=$PREV_TAG"
            echo "deployment_id=$DEPLOY_ID"

  # ─────────────────────────────────────────────────────────────────────────
  # DEPLOYMENT: Rolling update
  # ─────────────────────────────────────────────────────────────────────────
  deploy:
    name: "Deploy"
    needs: [prepare]
    runs-on: ubuntu-latest
    outputs:
      deployment_id: ${{ needs.prepare.outputs.deployment_id }}
    steps:
      - name: Determine image tag
        id: tag
        run: |
          TAG="${{ inputs.image_tag }}"
          if [ -z "$TAG" ]; then
            TAG="${GITHUB_SHA::7}"
          fi
          echo "tag=$TAG" >> $GITHUB_OUTPUT
      
      - name: Execute deployment
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            set -euo pipefail
            cd ${{ inputs.deploy_path }}
            
            # Update image tag
            APP_ENV=$(echo "${{ inputs.app_name }}" | tr '[:lower:]-' '[:upper:]_')
            sed -i "s/^${APP_ENV}_IMAGE_TAG=.*/${APP_ENV}_IMAGE_TAG=${{ steps.tag.outputs.tag }}/" .env.prod
            
            # Pull images
            docker compose -f ${{ inputs.compose_file }} pull
            
            # Rolling update (scale up, then down)
            WEB_SERVICE="${{ inputs.app_name }}-web"
            docker compose -f ${{ inputs.compose_file }} up -d --no-deps --scale ${WEB_SERVICE}=2 ${WEB_SERVICE} || \
              docker compose -f ${{ inputs.compose_file }} up -d --no-deps ${WEB_SERVICE}
            
            sleep 10
            
            docker compose -f ${{ inputs.compose_file }} up -d --no-deps --scale ${WEB_SERVICE}=1 ${WEB_SERVICE} || true
            
            # Update workers
            docker compose -f ${{ inputs.compose_file }} up -d --remove-orphans
            
            # Log deployment
            echo '{"id":"${{ needs.prepare.outputs.deployment_id }}","sha":"${{ steps.tag.outputs.tag }}","previous":"${{ needs.prepare.outputs.previous_tag }}","time":"'$(date -Iseconds)'","status":"deployed"}' >> deployments.log

  # ─────────────────────────────────────────────────────────────────────────
  # VERIFICATION: Health checks
  # ─────────────────────────────────────────────────────────────────────────
  verify:
    name: "Verify"
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
          URL="${{ inputs.health_url }}"
          RETRIES=${{ inputs.health_retries }}
          INTERVAL=${{ inputs.health_interval }}
          
          for i in $(seq 1 $RETRIES); do
            echo "Health check $i/$RETRIES: $URL"
            
            HTTP_CODE=$(curl -sf -o /dev/null -w '%{http_code}' "$URL" 2>/dev/null || echo "000")
            
            if [ "$HTTP_CODE" = "200" ]; then
              echo "✅ Health check passed"
              echo "status=healthy" >> $GITHUB_OUTPUT
              exit 0
            fi
            
            echo "HTTP $HTTP_CODE - retrying in ${INTERVAL}s"
            sleep $INTERVAL
          done
          
          echo "❌ Health check failed after $RETRIES attempts"
          echo "status=unhealthy" >> $GITHUB_OUTPUT
          exit 1

  # ─────────────────────────────────────────────────────────────────────────
  # ROLLBACK: Automatic on failure
  # ─────────────────────────────────────────────────────────────────────────
  rollback:
    name: "Rollback"
    needs: [prepare, deploy, verify]
    if: ${{ failure() && inputs.enable_rollback }}
    runs-on: ubuntu-latest
    steps:
      - name: Execute rollback
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            set -euo pipefail
            cd ${{ inputs.deploy_path }}
            
            PREV_TAG="${{ needs.prepare.outputs.previous_tag }}"
            echo "🔄 Rolling back to $PREV_TAG"
            
            # Restore previous tag
            APP_ENV=$(echo "${{ inputs.app_name }}" | tr '[:lower:]-' '[:upper:]_')
            sed -i "s/^${APP_ENV}_IMAGE_TAG=.*/${APP_ENV}_IMAGE_TAG=$PREV_TAG/" .env.prod
            
            # Rollback
            docker compose -f ${{ inputs.compose_file }} pull
            docker compose -f ${{ inputs.compose_file }} up -d --force-recreate
            
            # Log rollback
            echo '{"id":"rollback-'$(date +%s)'","to":"'$PREV_TAG'","from":"${{ github.sha }}","time":"'$(date -Iseconds)'","status":"rolled_back"}' >> deployments.log
            
            echo "✅ Rollback complete"

  # ─────────────────────────────────────────────────────────────────────────
  # CLEANUP: Release lock
  # ─────────────────────────────────────────────────────────────────────────
  cleanup:
    name: "Cleanup"
    needs: [verify]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Release lock
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            rm -f "${{ inputs.deploy_path }}/.deploy.lock"
```

---

## 5. PR #5: Pilot Migration (Travel-Beat)

### 5.1 New `deploy.yml`

```yaml
# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  TRAVEL-BEAT CI/CD (Using Platform Reusable Workflows)                     ║
# ║  Migrated: 2026-02-XX                                                      ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      skip_tests:
        description: 'Skip tests (emergency only)'
        type: boolean
        default: false

jobs:
  ci:
    name: "CI"
    uses: achimdehnert/platform/.github/workflows/_ci-python.yml@v1
    with:
      python_version: "3.12"
      coverage_threshold: 70
      working_directory: "apps/"
      skip_tests: ${{ inputs.skip_tests || false }}
    secrets: inherit

  build:
    name: "Build"
    needs: [ci]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    uses: achimdehnert/platform/.github/workflows/_build-docker.yml@v1
    with:
      dockerfile: "docker/Dockerfile"
      scan_image: true
    secrets: inherit

  deploy:
    name: "Deploy"
    needs: [build]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    uses: achimdehnert/platform/.github/workflows/_deploy-hetzner.yml@v1
    with:
      app_name: travel-beat
      deploy_path: /opt/travel-beat
      health_url: https://drifttales.com/health/
      compose_file: docker-compose.prod.yml
      enable_rollback: true
    secrets:
      DEPLOY_HOST: ${{ secrets.HETZNER_HOST }}
      DEPLOY_USER: ${{ secrets.HETZNER_USER }}
      DEPLOY_SSH_KEY: ${{ secrets.HETZNER_SSH_KEY }}
```

**Line count**: ~50 (down from 525)

### 5.2 Migration Checklist

```markdown
## Travel-Beat Migration Checklist

### Pre-Migration
- [ ] Platform workflows merged and tagged `@v1`
- [ ] Test workflow in fork/test repo
- [ ] Backup current deploy.yml
- [ ] Verify secrets available

### Migration
- [ ] Create PR with new deploy.yml
- [ ] Run shadow deploy (both old + new)
- [ ] Compare results
- [ ] Merge PR during low-traffic window

### Post-Migration
- [ ] Monitor first 5 deployments
- [ ] Verify rollback works (test failure)
- [ ] Update documentation
- [ ] Team notification
```

---

## 6. Timeline

```
Week 1: Foundation (PR #1, #2)
├── Day 1-2: _ci-python.yml
├── Day 3-4: _build-docker.yml  
└── Day 5: Integration testing

Week 2: Deploy Workflow (PR #3)
├── Day 1-3: _deploy-hetzner.yml
├── Day 4: _rollback.yml
└── Day 5: End-to-end testing

Week 3: Pilot Migration (PR #5)
├── Day 1-2: Travel-Beat migration
├── Day 3-5: Soak testing + monitoring

Week 4-5: Remaining Apps
├── MCP-Hub, Risk-Hub, BFAgent, CAD-Hub
└── One app per 2 days

Week 6: Stabilization
├── Bug fixes
├── Documentation
└── Retrospective
```

---

## 7. Sign-off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Author | | 2026-02-02 | |
| Tech Lead | | | [ ] |
| DevOps | | | [ ] |
| Product | | | [ ] |

---

## Appendix: Rollback Test Script

```bash
#!/bin/bash
# test-rollback.sh - Verify rollback mechanism works

set -euo pipefail

APP="travel-beat"
DEPLOY_PATH="/opt/$APP"

echo "=== Rollback Test ==="

# 1. Get current state
CURRENT=$(grep IMAGE_TAG $DEPLOY_PATH/.env.prod | cut -d= -f2)
echo "Current: $CURRENT"

# 2. Deploy broken image (simulate failure)
echo "Deploying 'broken' image..."
sed -i "s/IMAGE_TAG=.*/IMAGE_TAG=nonexistent/" $DEPLOY_PATH/.env.prod
docker compose -f $DEPLOY_PATH/docker-compose.prod.yml up -d 2>/dev/null || true

# 3. Wait for health check to fail
sleep 30

# 4. Verify rollback triggered
AFTER=$(grep IMAGE_TAG $DEPLOY_PATH/.env.prod | cut -d= -f2)
if [ "$AFTER" = "$CURRENT" ]; then
  echo "✅ Rollback successful: $AFTER"
else
  echo "❌ Rollback failed: expected $CURRENT, got $AFTER"
  # Manual restore
  sed -i "s/IMAGE_TAG=.*/IMAGE_TAG=$CURRENT/" $DEPLOY_PATH/.env.prod
  docker compose -f $DEPLOY_PATH/docker-compose.prod.yml up -d
  exit 1
fi
```
