---
status: "proposed"
date: 2026-02-20
decision-makers: [Achim Dehnert]
consulted: []
informed: []
---

# Adopt deployment pre-flight validation and pipeline hardening to eliminate systematic onboarding failures

> **Input**: `docs/adr/inputs/ADR-056-deployment-preflight-concept.md` (Trading-Hub session post-mortem, 2026-02-20)

---

## Context and Problem Statement

A single deployment session for `trading-hub` produced **9 workflow runs, 43 minutes of debugging, and 0% first-try success rate** before achieving a working deployment. Root-cause analysis identified four recurring failure classes (A: GitHub permissions, B: cross-repo dependencies, C: workflow design, D: infrastructure drift) that reproduce identically on every new app onboarding.

These are not one-off mistakes — they are **structural gaps** in the platform deployment architecture:

- No pre-flight validation before the first CI run
- No documented onboarding checklist
- `platform_context` shared package not available in CI
- Reusable workflow inputs not validated before execution
- No deployment success metrics to detect systemic degradation

**Cost of status quo**: Each new app onboarding costs ~43 minutes of avoidable debugging. With 7+ apps and growing, this compounds.

---

## Decision Drivers

* **Reliability**: First-try success rate must reach >85% for new app onboardings
* **Developer experience**: Failures should be caught locally before the first CI push
* **Maintainability**: Fix once in `platform`, all apps benefit
* **Security**: Pre-flight checks must not introduce new secret exposure vectors
* **Proportionality**: Solutions must match the scale of a 1–3 person team on a single VPS

---

## Considered Options

1. **Status quo** — fix failures reactively per-app as they occur
2. **Pre-flight validation script** — `validate-deployment-readiness.sh` catches classes A, B, D before first push
3. **Inline workflow templates** — replace reusable workflow calls with fully inline `ci-cd.yml` per app, eliminating class C
4. **`platform_context` as versioned package** — publish to GitHub Packages, eliminating class B permanently
5. **Self-hosted runner on dev-server** — eliminates SSH/secrets for deploy, improves build cache
6. **GitOps (ArgoCD/Flux)** — declarative, pull-based deployment replacing push-based GitHub Actions

---

## Decision Outcome

**Chosen options: 2 + 3 + 4 (combined, phased)**, because:

- Option 2 eliminates the majority of failures (classes A + D, 56%+) with 4 hours of effort.
- Option 3 eliminates class C failures by removing the reusable-workflow/normal-job mixing anti-pattern. Reusable workflows are **retained** for established apps (risk-hub, travel-beat, weltenhub) — new apps use inline templates until stable.
- Option 4 eliminates class B permanently and is the correct long-term solution for `platform_context`.
- Option 5 (self-hosted runner) is deferred — high value but requires runner maintenance discipline. Evaluate in Q3.
- Option 6 (GitOps) is deferred — justified only at >10 apps. Evaluate Q3/Q4.
- Option 1 is rejected — the pattern has already reproduced across trading-hub, cad-hub, and others.

### Confirmation

Compliance is verified by:

1. **Pre-flight script**: `scripts/validate-deployment-readiness.sh` exits non-zero on any class A/B/D failure — runnable locally and as first CI job.
2. **Onboarding checklist**: New app PRs must reference a closed `new-app-onboarding` GitHub Issue with all boxes checked.
3. **Metrics**: First-try success rate tracked via GitHub Actions API — target >85% within 30 days of M1+M2 rollout.
4. **ADR-054 Architecture Guardian**: Checks new `ci-cd.yml` files for `inputs.*` usage at push-trigger (class C pattern).

### Consequences

* Good, because class A failures (56% of all failures) are eliminated by a single pre-flight check.
* Good, because inline templates remove the reusable-workflow mixing anti-pattern without breaking existing apps.
* Good, because `platform_context` as a versioned package makes CI reproducible and removes the vendor/ workaround.
* Good, because the pre-flight script is runnable locally — failures are caught before the first push.
* Bad, because inline templates mean CI logic is duplicated across repos until a migration to composite actions is done.
* Bad, because `platform_context` packaging requires a publish pipeline and version discipline.
* Bad, because the pre-flight script must be kept in sync with the actual server layout (port registry, `.env.prod` required fields).

---

## Pros and Cons of the Options

### Option 1 — Status quo

* Good, because zero effort.
* Bad, because the same 43-minute debugging cycle repeats for every new app.
* Bad, because failure classes are undocumented and invisible until they hit.

### Option 2 — Pre-flight validation script

* Good, because catches 78% of failures (classes A + D) before the first CI run.
* Good, because runnable locally and in CI as a gate.
* Good, because already partially implemented (`scripts/validate-deployment-readiness.sh` exists in `platform`).
* Bad, because must be maintained as server layout evolves.
* Bad, because class B and C failures require additional measures.

### Option 3 — Inline workflow templates

* Good, because eliminates class C (workflow design) failures completely.
* Good, because no cross-repo `allowed_actions` dependency.
* Good, because easier to debug — full workflow visible in the app repo.
* Bad, because duplicates CI logic across repos (mitigated by composite actions in future).
* Bad, because existing apps using reusable workflows must not be migrated without testing.

### Option 4 — `platform_context` as versioned package

* Good, because eliminates class B (dependency) failures permanently.
* Good, because version-pinned — reproducible in CI and locally.
* Good, because removes vendor/ copies from all repos.
* Bad, because requires a publish workflow and semver discipline.
* Bad, because GHCR package registry requires `packages: read` token in consuming repos.

### Option 5 — Self-hosted runner

* Good, because Docker layer cache reduces build time from ~8 min to ~2 min.
* Good, because no SSH secrets needed for deploy (runner is on the server).
* Bad, because runner maintenance overhead for a small team.
* Bad, because security isolation requires Docker-in-Docker or ephemeral runners.
* **Deferred to Q3.**

### Option 6 — GitOps (ArgoCD/Flux)

* Good, because declarative, auditable, automatic rollback.
* Bad, because high initial investment — justified only at >10 apps.
* Bad, because requires Kubernetes or equivalent — conflicts with current Docker Compose setup.
* **Deferred to Q3/Q4 evaluation.**

---

## More Information

- **Input document**: `docs/adr/inputs/ADR-056-deployment-preflight-concept.md`
- **Related ADRs**: ADR-021 (unified deployment), ADR-022 (code quality tooling), ADR-053 (deployment MCP robustness), ADR-054 (deployment preflight validation), ADR-055 (cross-app bug management)
- **Existing script**: `scripts/validate-deployment-readiness.sh` (already in `platform` — extend, don't replace)
- **Existing template**: `.github/ISSUE_TEMPLATE/new-app-onboarding.yml` (already in `platform` — extend with deployment prerequisites)
- **Self-hosted runner**: Deferred — see §2 open questions
- **GitOps**: Deferred — evaluate Q3/Q4 when app count exceeds 10

---

## 2. Implementation Details

### 2.1 Pre-Flight Validation Script (M1)

Extend `scripts/validate-deployment-readiness.sh` with these checks:

| Check | Failure Class | Command |
| --- | --- | --- |
| GitHub Actions permissions ≠ `local_only` | A | `gh api /repos/{owner}/{repo}/actions/permissions` |
| Required secrets present | A | `gh secret list` |
| Dockerfile exists at declared path | B | `test -f <dockerfile>` |
| No cross-repo `COPY` in Dockerfile | B | `grep -n "COPY packages/" Dockerfile` |
| Compose image name matches build output | D | Parse both files |
| SSH connection to `88.198.191.108` | D | `ssh -o ConnectTimeout=5 root@88.198.191.108 exit` |
| `deploy_path` exists on server | D | SSH probe |
| `.env.prod` present on server | D | SSH probe |
| Nginx config present for app | D | SSH probe |
| `platform_context` importable | B | `python -c "import platform_context"` |

**Integration**: Run as first job in `ci-cd.yml` with `continue-on-error: false`. Also runnable locally: `bash scripts/validate-deployment-readiness.sh <app_name>`.

### 2.2 Inline Workflow Template (M3)

New apps use this pattern instead of reusable workflow calls:

```yaml
# .github/workflows/ci-cd.yml — inline template for new apps
name: CI/CD Pipeline

permissions:
  contents: read
  packages: write

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  preflight:
    name: Pre-Flight Validation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate deployment readiness
        run: bash scripts/validate-deployment-readiness.sh ${{ github.event.repository.name }}
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          DEPLOY_SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}

  ci:
    name: CI
    needs: [preflight]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python manage.py check
      - run: pytest --tb=short

  build:
    name: Build & Push
    needs: [ci]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/achimdehnert/${{ github.event.repository.name }}:latest

  deploy:
    name: Deploy
    needs: [build]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Add known hosts
        run: ssh-keyscan 88.198.191.108 >> ~/.ssh/known_hosts
      - name: Deploy
        env:
          DEPLOY_SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}
        run: |
          eval $(ssh-agent -s)
          echo "$DEPLOY_SSH_KEY" | ssh-add -
          ssh root@88.198.191.108 "cd /opt/${{ github.event.repository.name }} && \
            docker compose -f docker-compose.prod.yml pull && \
            docker compose -f docker-compose.prod.yml up -d --force-recreate"
```

**Anti-patterns eliminated**:
- No `inputs.*` at push-trigger
- No mixing of reusable workflow jobs with normal jobs
- No `allowed_actions: local_only` dependency

### 2.3 `platform_context` as Package (M4)

Publish `platform_context` to GitHub Packages:

```toml
# platform/pyproject.toml
[project]
name = "platform-context"
version = "0.2.0"

[tool.hatch.publish.index]
url = "https://ghcr.io/achimdehnert/platform"
```

Consuming repos add to `requirements.txt`:
```
platform-context==0.2.0 --extra-index-url https://ghcr.io/achimdehnert/platform
```

### 2.4 Failure Class Reference

| Class | Symptom | Pre-Flight Check |
| --- | --- | --- |
| A: PERMISSION | `startup_failure`, 0 jobs, no logs | `allowed_actions != local_only` |
| B: DEPENDENCY | `ModuleNotFoundError` in test step | `python -c "import platform_context"` |
| C: WORKFLOW | `startup_failure` with valid YAML | `actionlint` + no `inputs.*` at push |
| D: DRIFT | `502 Bad Gateway`, backup errors | SSH probe + `.env.prod` field check |

---

## 3. Migration Tracking

| Item | Status | Notes |
| --- | --- | --- |
| Extend `validate-deployment-readiness.sh` with all class A/B/D checks | 🔴 Not started | Script exists, needs extension |
| Extend `new-app-onboarding.yml` Issue Template with deployment prerequisites | 🔴 Not started | Template exists in `.github/ISSUE_TEMPLATE/` |
| Publish `platform_context` 0.2.0 to GitHub Packages | 🔴 Not started | `platform_context-0.2.0-py3-none-any.whl` already in `requirements/wheels/` |
| trading-hub: migrate to inline `ci-cd.yml` template | 🔴 Not started | Current state unknown |
| Add `actionlint` check to `_ci-python.yml` reusable workflow | 🔴 Not started | Catches class C for existing apps |
| Deployment metrics dashboard (M5) | 🔵 Deferred | Q2 |
| Self-hosted runner (M7) | 🔵 Deferred | Q3 |
| GitOps evaluation (M8) | 🔵 Deferred | Q3/Q4 |
