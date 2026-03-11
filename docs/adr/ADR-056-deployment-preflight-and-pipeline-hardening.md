---
status: "accepted"
date: 2026-02-20
amended: 2026-02-20
decision-makers: [Achim Dehnert]
consulted: []
informed: []
implementation_status: implemented
---

# Adopt deployment pre-flight validation and pipeline hardening to eliminate systematic onboarding failures

> **Input**: `docs/adr/inputs/ADR-056-deployment-preflight-concept.md` (Trading-Hub session post-mortem, 2026-02-20)
> **Amendment**: Review findings applied 2026-02-20 — see §4 for changes.

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
3. **Inline workflow templates** — replace reusable workflow calls with fully inline `ci-cd.yml` per app, eliminating class C (conscious deviation from ADR-021 §2.5 for new apps only — see §2.2)
4. **`platform_context` as versioned package** — publish to GitHub Packages (GHCR), eliminating class B permanently
5. **Self-hosted runner on dev-server** — already implemented; eliminates SSH/secrets for deploy, improves build cache via persistent Docker layer cache
6. **GitOps (ArgoCD/Flux)** — declarative, pull-based deployment replacing push-based GitHub Actions (deferred — see ADR-06x)

---

## Decision Outcome

**Chosen options: 2 + 3 + 4 + 5 (combined, phased)**, because:

- Option 2 eliminates the majority of failures (classes A + D, 56%+) with 4 hours of effort.
- Option 3 eliminates class C failures by removing the reusable-workflow/normal-job mixing anti-pattern. Reusable workflows are **retained** for established apps (risk-hub, travel-beat, weltenhub) — new apps use inline templates until stable. This is a conscious deviation from ADR-021 §2.5 for new apps only.
- Option 4 eliminates class B permanently. Published to GHCR (GitHub Packages) — consistent with `ghcr.io/achimdehnert/` registry strategy.
- Option 5 (self-hosted runner) is **already implemented** on `88.198.191.108` — no SSH secrets needed for deploy jobs running on the self-hosted runner.
- Option 6 (GitOps) is deferred — justified only at >10 apps. Tracked as ADR-06x (future).
- Option 1 is rejected — the pattern has already reproduced across trading-hub, cad-hub, and others.

### Confirmation

Compliance is verified by:

1. **Pre-flight script**: `scripts/validate-deployment-readiness.sh` exits non-zero on any class A/B/D failure — runnable locally and as first CI job.
2. **Onboarding checklist**: New app PRs must reference a closed `new-app-onboarding` GitHub Issue with all boxes checked.
3. **Metrics**: First-try success rate tracked via GitHub Actions API — target >85% within 30 days of M1+M2 rollout.
4. **ADR-054 Architecture Guardian**: Checks new `ci-cd.yml` files for `inputs.*` usage at push-trigger (class C pattern).
5. **SHA-tag verification**: `docker manifest inspect ghcr.io/achimdehnert/<app>:<sha7>` must succeed after each build job.

### Consequences

* Good, because class A failures (56% of all failures) are eliminated by a single pre-flight check.
* Good, because inline templates remove the reusable-workflow mixing anti-pattern without breaking existing apps.
* Good, because `platform_context` as a versioned GHCR package makes CI reproducible and removes the vendor/ workaround.
* Good, because the pre-flight script is runnable locally — failures are caught before the first push.
* Good, because self-hosted runner eliminates SSH key management for deploy jobs and provides persistent Docker layer cache.
* Bad, because inline templates mean CI logic is duplicated across repos until a migration to composite actions is done.
* Bad, because `platform_context` packaging requires a publish workflow and semver discipline.
* Bad, because the pre-flight script must be kept in sync with the actual server layout (port registry, `.env.prod` required fields).
* Bad, because SOPS-encrypted `.env.prod` files require the pre-flight script to handle decryption before field-checking (see §2.1 note).

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

### Option 3 — Inline workflow templates (conscious deviation from ADR-021 §2.5)

* Good, because eliminates class C (workflow design) failures completely.
* Good, because no cross-repo `allowed_actions` dependency.
* Good, because easier to debug — full workflow visible in the app repo.
* Bad, because duplicates CI logic across repos (mitigated by composite actions in future).
* Bad, because existing apps using reusable workflows must not be migrated without testing.
* **Note**: This deviates from ADR-021 §2.5 (three-stage reusable pipeline) intentionally for new apps. Existing apps retain reusable workflows. Migration to composite actions tracked in §3.

### Option 4 — `platform_context` as versioned GHCR package

* Good, because eliminates class B (dependency) failures permanently.
* Good, because version-pinned — reproducible in CI and locally.
* Good, because removes vendor/ copies from all repos.
* Good, because GHCR is consistent with `ghcr.io/achimdehnert/` registry strategy (no separate PyPI mirror needed).
* Bad, because requires a publish workflow and semver discipline.
* Bad, because consuming repos need `packages: read` token and `--extra-index-url` in pip config.

### Option 5 — Self-hosted runner (already implemented)

* Good, because Docker layer cache reduces build time from ~8 min to ~2 min.
* Good, because no SSH secrets needed for deploy (runner runs directly on `88.198.191.108`).
* Good, because already operational — no additional setup required.
* Bad, because runner maintenance overhead for a small team.
* Bad, because security isolation requires Docker-in-Docker or ephemeral runners for untrusted PRs.

### Option 6 — GitOps (ArgoCD/Flux) — deferred as ADR-06x

* Good, because declarative, auditable, automatic rollback.
* Bad, because high initial investment — justified only at >10 apps.
* Bad, because requires Kubernetes or equivalent — conflicts with current Docker Compose setup.
* **Deferred**: Evaluate Q3/Q4 when app count exceeds 10. Tracked as ADR-06x.

---

## More Information

- **Input document**: `docs/adr/inputs/ADR-056-deployment-preflight-concept.md`
- **Related ADRs**: ADR-021 (unified deployment — §2.5 deviation noted), ADR-022 (code quality tooling), ADR-045 (SOPS secrets), ADR-053 (deployment MCP robustness), ADR-054 (architecture guardian), ADR-055 (cross-app bug management)
- **Deferred**: ADR-06x (GitOps evaluation — Q3/Q4)
- **Existing script**: `scripts/validate-deployment-readiness.sh` (already in `platform` — extend, don't replace)
- **Existing template**: `.github/ISSUE_TEMPLATE/new-app-onboarding.yml` (already in `platform` — extend with deployment prerequisites)

---

## 2. Implementation Details

### 2.1 Pre-Flight Validation Script (M1)

Extend `scripts/validate-deployment-readiness.sh` with these checks:

| Check | Failure Class | Command |
| --- | --- | --- |
| GitHub Actions permissions ≠ `local_only` | A | `gh api /repos/{owner}/{repo}/actions/permissions` |
| Required secrets present (`DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`) | A | `gh secret list` |
| Dockerfile exists at declared path | B | `test -f <dockerfile>` |
| No cross-repo `COPY` in Dockerfile | B | `grep -n "COPY packages/" Dockerfile` |
| Compose image name matches build output | D | Parse both files |
| SSH connection to `$DEPLOY_HOST` | D | `ssh -o ConnectTimeout=5 $DEPLOY_USER@$DEPLOY_HOST exit` |
| `deploy_path` exists on server | D | SSH probe |
| `.env.prod` present on server | D | SSH probe (plain) or `sops -d` probe if SOPS-encrypted |
| Nginx config present for app | D | SSH probe |
| `platform_context` importable | B | `python -c "import platform_context"` |

> **SOPS note**: If `.env.prod` is SOPS-encrypted (ADR-045), the pre-flight script must run `sops -d .env.prod | grep REQUIRED_KEY` instead of plain `grep`. The script detects SOPS files via `sops --config .sops.yaml filestatus`.

**Integration**: Run as first job in `ci-cd.yml` with `continue-on-error: false`. Also runnable locally:
```bash
bash scripts/validate-deployment-readiness.sh <app_name>
```

### 2.2 Inline Workflow Template (M3)

> **Conscious deviation from ADR-021 §2.5**: New apps use fully inline `ci-cd.yml` instead of the three-stage reusable workflow pattern. This eliminates class C failures caused by mixing reusable and normal jobs. Existing apps retain their reusable workflow setup. Migration to composite actions is tracked in §3.

New apps use this template:

```yaml
# .github/workflows/ci-cd.yml — inline template for new apps
# Conscious deviation from ADR-021 §2.5 — see ADR-056 §2.2
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
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Validate deployment readiness
        run: bash scripts/validate-deployment-readiness.sh ${{ github.event.repository.name }}
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          DEPLOY_HOST: ${{ secrets.DEPLOY_HOST }}
          DEPLOY_USER: ${{ secrets.DEPLOY_USER }}
          DEPLOY_SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}

  ci:
    name: CI
    needs: [preflight]
    runs-on: self-hosted
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
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Set short SHA
        id: sha
        run: echo "sha7=$(git rev-parse --short=7 HEAD)" >> $GITHUB_OUTPUT
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: |
            ghcr.io/achimdehnert/${{ github.event.repository.name }}:latest
            ghcr.io/achimdehnert/${{ github.event.repository.name }}:${{ steps.sha.outputs.sha7 }}

  deploy:
    name: Deploy
    needs: [build]
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Deploy via Docker Compose
        run: |
          cd /opt/${{ github.event.repository.name }}
          docker compose -f docker-compose.prod.yml pull
          docker compose -f docker-compose.prod.yml up -d --force-recreate
      - name: Health check
        run: |
          sleep 10
          curl --fail --silent --max-time 10 \
            http://localhost:$(docker compose -f /opt/${{ github.event.repository.name }}/docker-compose.prod.yml port web 8000 | cut -d: -f2)/livez/ \
            || (docker compose -f /opt/${{ github.event.repository.name }}/docker-compose.prod.yml logs --tail=50 && exit 1)
```

**Anti-patterns eliminated**:
- No `inputs.*` at push-trigger
- No mixing of reusable workflow jobs with normal jobs
- No `allowed_actions: local_only` dependency
- No hardcoded server IP (self-hosted runner runs on server directly)
- SHA-tag pushed alongside `latest` for rollback capability
- Health check via `/livez/` after deploy with automatic log dump on failure

### 2.3 `platform_context` as GHCR Package (M4)

Publish `platform_context` to GitHub Packages (GHCR):

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

CI jobs need `packages: read` in `permissions:` to pull the package.

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
| Extend `validate-deployment-readiness.sh` with all class A/B/D checks | 🔴 Not started | Script exists, needs extension per §2.1 |
| Extend `new-app-onboarding.yml` Issue Template with deployment prerequisites | 🔴 Not started | Template exists in `.github/ISSUE_TEMPLATE/` |
| Publish `platform_context` 0.2.0 to GHCR | 🔴 Not started | `.whl` already in `requirements/wheels/` |
| trading-hub: migrate to inline `ci-cd.yml` template | 🔴 Not started | Apply §2.2 template |
| Add `actionlint` check to `_ci-python.yml` reusable workflow | 🔴 Not started | Catches class C for existing apps |
| Self-hosted runner on `88.198.191.108` | ✅ Done | Operational — all new templates use `runs-on: self-hosted` |
| Migrate existing apps from reusable to composite actions | 🔵 Deferred | After inline templates proven stable |
| Deployment metrics dashboard (M5) | 🔵 Deferred | Q2 — after M1+M2 rollout |
| GitOps evaluation (M8) | 🔵 Deferred | ADR-06x — Q3/Q4 when >10 apps |

---

## 4. Review Amendments (2026-02-20)

Applied after review against `docs/templates/adr-review-checklist.md`:

| # | Finding | Fix applied |
| --- | --- | --- |
| R1 | Server IP `88.198.191.108` hardcoded in inline template | Replaced with `runs-on: self-hosted` — IP no longer needed |
| R2 | Only `latest` tag pushed — no rollback possible | Added SHA-tag (`sha7`) alongside `latest` in build job |
| R3 | No health check after deploy | Added `/livez/` curl check with log dump on failure |
| R4 | Self-hosted runner status wrong ("Deferred Q3") | Updated to "already implemented" throughout |
| R5 | `DEPLOY_HOST`/`DEPLOY_USER` missing from inline template | Added to preflight env block; self-hosted runner makes them optional for deploy job |
| R6 | Inline template not marked as ADR-021 §2.5 deviation | Added explicit note in §2.2 header and Considered Options |
| R7 | SOPS compatibility of pre-flight script unclear | Added SOPS note in §2.1 |
| R8 | GitOps deferred without ADR placeholder | Added "ADR-06x" reference throughout |
