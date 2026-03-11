---
status: accepted
date: 2026-02-26
implemented: partial
decision-makers: Achim Dehnert
consulted: –
informed: –
supersedes: –
relates-to: ADR-022, ADR-042, ADR-054, ADR-056, ADR-057, ADR-061, ADR-071, ADR-089
repo: platform
implementation_status: implemented
implementation_evidence:
  - "platform/.github/workflows/: reusable CI/CD pipelines"
---

# ADR-090: Use Hybrid Matrix CI/CD Pipeline for Python + PostgreSQL → Docker Deploy

| Attribut       | Wert                                                        |
|----------------|-------------------------------------------------------------|
| **Status**     | **Accepted** (v5 — Implementation-Hardened)                 |
| **Scope**      | Platform-wide — all Django repos                            |
| **Erstellt**   | 2026-02-26                                                  |
| **Autor**      | Achim Dehnert                                               |
| **Relates to** | ADR-022, ADR-042, ADR-054, ADR-056, ADR-057, ADR-061, ADR-071, ADR-089 |

---

## 1. Context

### 1.1 Problem

Deployment-Fehler sind die teuersten Fehler. Sie betreffen echte User,
brauchen manuelle SSH-Intervention und sind schwer zu debuggen.
Aus der travel-beat bfagent-llm Integration (2026-02-26) wurden
4 verkettete Deployment-Fehler identifiziert, die alle durch
automatisierte Prüfungen verhindert worden wären:

| # | Fehler | Hätte verhindert durch |
|---|--------|----------------------|
| 1 | Falscher `app_label` in AppConfig | Stage ③ Migration-Graph-Check |
| 2 | Fehlende `related_name` → E304 | Stage ②b Django System Check |
| 3 | pip Cache liefert stale Wheel | Stage ⑤ Wheel-Content-Verification |
| 4 | Django 5.0 Auto-Discovery versagt | Stage ③ AppConfig-Label-Check |

### 1.2 Decision Drivers

- **Fehlervermeidung:** 4 verkettete Deploy-Fehler in einem einzigen Release (travel-beat 2026-02-26)
- **CI-Kosten:** Self-Hosted Runner vorhanden (ADR-042), ~3.300 Min/Monat Einsparung
- **Geschwindigkeit:** Lint-Fehler sollen in <30s erkannt werden, nicht nach 4min Postgres-Setup
- **Sicherheit:** Keine Secrets in YAML (ADR-061), kein `StrictHostKeyChecking=no` (ADR-042)
- **Rollback-Fähigkeit:** SHA-getaggte Images für deterministisches Rollback (ADR-056 R2)
- **Compliance:** MADR 4.0 Format, ADR-059 Drift Detector kompatibel
- **Concurrency-Safety:** Kein paralleler Deploy auf denselben Server (v4)
- **Datenintegrität:** DB-Backup vor jeder Migration (v4)

---

## 2. Considered Options

### Option A: Lineare Pipeline (② → ③ → ④ → ⑤ → ⑥)

Jede Stage wartet auf die vorherige. Einfach, aber langsam.

### Option B: Voll-parallele Matrix (② ‖ ③ → ④ → ⑤ → ⑥)

Python-Tests und Postgres-Tests starten gleichzeitig.
Spart CI-Zeit, verschwendet aber teure Postgres-Minuten bei trivialen Lint-Fehlern.

### Option C: Hybrid Matrix — Fast Gate + parallele Heavy Jobs

Billige Checks (<30s) als Gate, dann teure Jobs parallel.
Kombiniert Kostenkontrolle mit maximaler Parallelität.

---

## 3. Decision Outcome

**Gewählt: Option C — Hybrid Matrix**

### 3.1 Pros and Cons

| | Option A (Linear) | Option B (Voll-Parallel) | **Option C (Hybrid)** |
|---|---|---|---|
| **CI-Zeit** | ~12.5min | ~7min | **~10min** |
| **Bei Lint-Fail** | 3min verschwendet | 4min verschwendet (Postgres!) | **0.5min** |
| **Komplexität** | Niedrig | Mittel | **Mittel** |
| **Kosten** | Hoch (sequentiell) | Mittel (Postgres bei Lint-Fail) | **Niedrig** |
| **Rollback** | Kein SHA-Tag | Kein SHA-Tag | **SHA-7 Tags** |

### 3.2 Consequences

**Good:**
- Lint-Fehler werden in <30s erkannt → schnelles Entwickler-Feedback
- Teure Postgres-Jobs starten nur wenn Code grundsätzlich valide ist
- SHA-7 Image-Tags ermöglichen deterministisches Rollback
- AppConfig + Migration-Graph Checks verhindern die travel-beat Fehlerklasse
- Concurrency-Control verhindert Race Conditions bei schnellen Pushes (v4)
- DB-Backup vor Migration schützt vor Datenverlust (v4)
- Reusable Workflow eliminiert Drift zwischen Repos (v4)

**Bad:**
- Höhere Workflow-Komplexität als lineare Pipeline
- Coverage-Merge erfordert Artifact-Passing zwischen Jobs
- Self-Hosted Runner muss gewartet werden (ADR-042)
- Environment Protection erfordert initiales GitHub-Setup pro Repo (v4)

### 3.3 Confirmation

Die Pipeline-Compliance wird verifiziert durch:
1. `ruff check . && ruff format --check .` in ②a blockiert bei Lint-Fehler
2. `python manage.py migrate --check` in ③ erkennt pending/inkonsistente Migrations
3. `python manage.py check --deploy` in ③ erkennt E304, AppConfig-Fehler
4. Coverage ≥ 80% wird in ④ als Gate enforced
5. `/livez/` + `/healthz/` in ⑥ verifizieren laufende Applikation + DB-Verbindung
6. SHA-7 Rollback in ⑦ verifiziert durch erneuten Health-Check
7. `concurrency:` Block verhindert parallele Deploys (v4)
8. DB-Backup existiert vor jeder Migration (v4)

---

## 4. Die 7-Stufen-Pipeline

```
                    ① Local (pre-push)
                          │
                    ②a Fast Checks (<30s)
                    ruff, format, audit
                          │
                ┌─────────┴─────────┐
                │                   │
          ②b Python Tests    ③ Postgres Tests
          unit + wheels      migration graph
          coverage A         integration
                             coverage B
                │                   │
                └─────────┬─────────┘
                          │
                    ④ Quality Gate
                    coverage merge ≥80%
                          │
                ┌── ⑤ Build + Push ──┐
                │   Docker → GHCR    │ environment: production
                │   (SHA-7 + latest) │ (manual approval)
                └────────────────────┘
                          │
                    ⑥ Migrate + Verify
                    DB-backup → migrations → health → smoke
                          │
                    ⑦ Error Handling
                    rollback (SHA-7) + notify
```

---

## 5. Vollständiger Workflow

### 5.0 Workflow-Rahmen

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline (ADR-090)

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  packages: write

# v5: Concurrency-Control — cancel stale CI, protect deploys via environment
concurrency:
  group: ci-${{ github.repository }}-${{ github.ref }}
  cancel-in-progress: true  # Stale CI-Runs bei neuem Push sofort canceln

env:
  DEPLOY_IMAGE: ${{ vars.DEPLOY_IMAGE }}
  DEPLOY_DOCKERFILE: ${{ vars.DEPLOY_DOCKERFILE }}
  DEPLOY_CONTAINER: ${{ vars.DEPLOY_CONTAINER }}
  DEPLOY_SERVER_PATH: ${{ vars.DEPLOY_SERVER_PATH }}
  DEPLOY_PORT: ${{ vars.DEPLOY_PORT }}
  DEPLOY_MIGRATE_CMD: ${{ vars.DEPLOY_MIGRATE_CMD }}
```

**v5 Concurrency-Regeln** (gefixt nach 137-hub Implementation):
- `cancel-in-progress: true` — stale CI-Runs werden bei neuem Push sofort gecancelt
- Concurrency-Gruppe inkludiert `${{ github.ref }}` → PRs und main haben separate Gruppen
- **Deploy-Safety** wird NICHT durch Concurrency gelöst, sondern durch `environment: production`
  (GitHub verhindert parallele Deployments zum selben Environment automatisch)
- v4-Bug: `cancel-in-progress: false` auf Workflow-Level blockierte neue CI-Runs hinter
  alten (mit stale Code), was bei schnellen Fix-Commits zu langen Wartezeiten führte

### 5.1 Stage ① Development (Lokal)

**Ziel:** Erste Verteidigungslinie noch vor `git push`.

**Pre-Commit Hooks** (kanonisches Template aus ADR-071):

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: check-added-large-files
        args: ['--maxkb=500']
      - id: detect-private-key
      - id: check-merge-conflict
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: check-ast
      - id: debug-statements
      - id: no-commit-to-branch
        args: ['--branch', 'main']

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.0
    hooks:
      - id: gitleaks

  - repo: local
    hooks:
      - id: bf-commit-msg
        name: BF Commit Message Format
        entry: scripts/check-commit-msg.sh
        language: script
        stages: [commit-msg]
```

**Lokale Tests:**

```bash
pytest tests/unit/ -x --tb=short
```

**Gate:** Pre-commit MUSS pass. Commit wird blockiert.

---

### 5.2 Stage ②a Fast Checks (CI — <30s)

**Ziel:** Billigstes Gate — blockiert teure Jobs bei trivialen Fehlern.

```yaml
  fast-checks:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Tools
        run: |
          set -euo pipefail
          pip install ruff pip-audit

      - name: Lint
        run: ruff check . --output-format=github

      - name: Format Check
        run: ruff format --check .

      - name: Security Audit
        run: pip-audit --strict --desc -r requirements/base.txt
```

**Gate:** Alle 3 Checks grün → ②b und ③ starten parallel.
Fail → Pipeline stoppt sofort (kein Postgres-Container gestartet).

---

### 5.3 Stage ②b Python Tests (CI — parallel)

**Ziel:** Unit-Tests + Wheel-Verification ohne DB-Abhängigkeit.

```yaml
  python-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    needs: fast-checks
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Dependencies
        run: |
          set -euo pipefail
          pip install -r requirements/base.txt
          if ls requirements/wheels/*.whl 1>/dev/null 2>&1; then
            pip install requirements/wheels/*.whl
          fi
          pip install pytest pytest-cov

      - name: Unit Tests + Coverage
        run: |
          set -euo pipefail
          pytest tests/unit/ --cov=src --cov-report= -q
          # --cov-report= produces .coverage file (no XML)

      # ADR-089 Invariante 7+10: Wheel-Package-Checks
      - name: Verify Platform Wheels
        run: |
          set -euo pipefail
          for whl in requirements/wheels/*.whl; do
            [ -f "$whl" ] || continue
            echo "=== Checking $whl ==="
            python -c "
          import zipfile, sys
          z = zipfile.ZipFile('$whl')
          inits = [f for f in z.namelist() if f.endswith('django_app/__init__.py')]
          for init in inits:
              content = z.read(init).decode()
              if 'AppConfig' in content and 'label' not in content:
                  print(f'FAIL: {init} has AppConfig without explicit label!')
                  sys.exit(1)
              print(f'OK: {init}')
          "
          done

      - name: Upload Coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage-python
          path: .coverage
          retention-days: 7
```

**Gate:** Tests grün, Wheels valide.

---

### 5.4 Stage ③ PostgreSQL Verification (CI — parallel)

**Ziel:** DB-Schicht gegen echtes PostgreSQL prüfen. Läuft **parallel** zu ②b.

```yaml
  postgres-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    needs: fast-checks          # ← same dependency as ②b → parallel!
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5

    env:
      DATABASE_URL: postgres://test_user:test_pass@localhost:5432/test_db

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Dependencies
        run: |
          set -euo pipefail
          pip install -r requirements/base.txt
          if ls requirements/wheels/*.whl 1>/dev/null 2>&1; then
            pip install requirements/wheels/*.whl
          fi
          pip install pytest pytest-cov pytest-django

      # ADR-089 R-13: Verify AppConfig discovery BEFORE migrations
      - name: AppConfig Label Check
        run: |
          set -euo pipefail
          python -c "
          import django, os
          os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
          django.setup()
          from django.apps import apps
          errors = []
          for ac in apps.get_app_configs():
              if 'bfagent' in ac.name and ac.__class__.__name__ == 'AppConfig':
                  errors.append(f'{ac.name}: uses default AppConfig (label={ac.label})')
          if errors:
              for e in errors:
                  print(f'FAIL: {e}')
              exit(1)
          print('OK: All custom apps use explicit AppConfig classes')
          "

      # Migration Graph Consistency (catches NodeNotFoundError BEFORE deploy)
      - name: Migration Graph Check
        run: |
          set -euo pipefail
          python manage.py migrate --check --dry-run 2>&1 || {
            echo "FAIL: Migration graph inconsistent!"
            python manage.py showmigrations --list 2>&1 | grep -E '\[X\]|\[ \]'
            exit 1
          }

      - name: Run Migrations
        run: |
          set -euo pipefail
          python manage.py migrate --noinput

      - name: Django System Check
        run: |
          set -euo pipefail
          python manage.py check --deploy --fail-level WARNING

      - name: Integration Tests
        run: |
          set -euo pipefail
          pytest tests/integration/ --cov=src --cov-report= -q

      - name: Upload Coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage-postgres
          path: .coverage
          retention-days: 7
```

**django-tenants Variante:**

```yaml
      - name: Migration Check (django-tenants)
        run: |
          set -euo pipefail
          python manage.py migrate_schemas --shared --check
          python manage.py migrate_schemas --tenant --check
```

**Gate:** Migrations konsistent, System-Check grün, Integration-Tests pass.

---

### 5.5 Stage ④ Quality Gate

**Ziel:** Merged Coverage aus ②b + ③ muss ≥ 80% sein.

```yaml
  quality-gate:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    needs: [python-tests, postgres-tests]
    steps:
      - uses: actions/checkout@v4

      - name: Download Coverage Reports
        uses: actions/download-artifact@v4
        with:
          pattern: coverage-*
          path: coverage-reports/

      - name: Merge + Check Threshold
        run: |
          set -euo pipefail
          pip install coverage
          coverage combine coverage-reports/coverage-python/.coverage \
                           coverage-reports/coverage-postgres/.coverage
          TOTAL=$(coverage report --format=total)
          echo "## Coverage: ${TOTAL}%" >> "$GITHUB_STEP_SUMMARY"
          coverage report --fail-under=80
          coverage xml -o coverage-merged.xml
```

**Gate:** Coverage ≥ 80% oder Pipeline blockiert.

---

### 5.6 Stage ⑤ Deployment Definition

**Ziel:** Sicheres, verifiziertes Docker-Image bauen und pushen.

```yaml
  deploy-build:
    runs-on: [self-hosted, hetzner]
    timeout-minutes: 5
    needs: quality-gate
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    # v4: Environment Protection — erfordert manuelles Approval in GitHub
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Setup SSH
        run: |
          set -euo pipefail
          mkdir -p ~/.ssh
          echo "${{ secrets.DEPLOY_SSH_KEY }}" > ~/.ssh/id_ed25519
          chmod 600 ~/.ssh/id_ed25519
          ssh-keyscan -H ${{ secrets.DEPLOY_HOST }} >> ~/.ssh/known_hosts

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Pre-Flight Validation
        run: |
          set -euo pipefail
          ssh -o ConnectTimeout=5 \
            ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} "echo OK"

      # ADR-089 Invariante 9: Wheel version matches code
      - name: Wheel Freshness Check
        run: |
          set -euo pipefail
          for whl in requirements/wheels/*.whl; do
            [ -f "$whl" ] || continue
            PKG=$(basename "$whl" | sed 's/-[0-9].*//')
            VERSION=$(basename "$whl" | sed 's/.*-\([0-9][^-]*\)-.*/\1/')
            echo "Wheel: $PKG v$VERSION"
          done

      - name: Save Previous Image SHA
        id: pre_deploy
        run: |
          set -euo pipefail
          CURRENT_SHA=$(ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} \
            "docker inspect --format='{{index .Config.Labels \"org.opencontainers.image.revision\"}}' \
            ${{ env.DEPLOY_CONTAINER }}" 2>/dev/null || echo "unknown")
          echo "previous_sha=${CURRENT_SHA}" >> "$GITHUB_OUTPUT"

      - name: Docker Build
        run: |
          set -euo pipefail
          docker build \
            --no-cache \
            --label "org.opencontainers.image.revision=${GITHUB_SHA::7}" \
            --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
            --build-arg GIT_SHA=${GITHUB_SHA::7} \
            -f ${{ env.DEPLOY_DOCKERFILE }} \
            -t ${{ env.DEPLOY_IMAGE }}:${GITHUB_SHA::7} \
            -t ${{ env.DEPLOY_IMAGE }}:latest \
            .

      - name: Docker Push
        run: |
          set -euo pipefail
          docker push ${{ env.DEPLOY_IMAGE }}:${GITHUB_SHA::7}
          docker push ${{ env.DEPLOY_IMAGE }}:latest
          echo "## Pushed: ${{ env.DEPLOY_IMAGE }}:${GITHUB_SHA::7}" >> "$GITHUB_STEP_SUMMARY"
    outputs:
      previous_sha: ${{ steps.pre_deploy.outputs.previous_sha }}
      deploy_sha: ${{ github.sha }}
```

**v4 Environment Protection:**
- GitHub Environment `production` muss im Repo konfiguriert werden
  (Settings → Environments → New → `production`)
- Optional: Required Reviewers aktivieren → manuelles Approval vor Deploy
- Optional: Wait Timer (z.B. 5 Minuten Wartezeit vor Deploy)
- Secrets können Environment-spezifisch sein (z.B. `DEPLOY_SSH_KEY` nur in `production`)

**Gate:** Image mit SHA-7 Tag UND latest gepusht. Previous SHA gespeichert.

---

### 5.7 Stage ⑥ Migrate + Deploy Verify

**Ziel:** DB-Backup, Migrations VOR App-Start, dann Health + Smoke.

```yaml
  deploy-verify:
    runs-on: [self-hosted, hetzner]
    timeout-minutes: 5
    needs: deploy-build
    steps:
      - name: Setup SSH
        run: |
          set -euo pipefail
          mkdir -p ~/.ssh
          echo "${{ secrets.DEPLOY_SSH_KEY }}" > ~/.ssh/id_ed25519
          chmod 600 ~/.ssh/id_ed25519
          ssh-keyscan -H ${{ secrets.DEPLOY_HOST }} >> ~/.ssh/known_hosts

      - name: Pull New Image
        run: |
          set -euo pipefail
          ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} "
            cd ${{ env.DEPLOY_SERVER_PATH }} && \
            docker compose -f docker-compose.prod.yml pull
          "

      # v4: DB-Backup vor Migration — Safety Net bei Schema-Änderungen
      - name: Backup Database
        run: |
          set -euo pipefail
          BACKUP_FILE="${{ vars.DEPLOY_APP_NAME }}-pre-${GITHUB_SHA::7}-$(date +%Y%m%d-%H%M%S).sql.gz"
          ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} "
            mkdir -p /opt/backups && \
            docker exec ${{ vars.DEPLOY_DB_CONTAINER }} \
              pg_dump -U \${POSTGRES_USER:-postgres} \${POSTGRES_DB:-app} \
              | gzip > /opt/backups/${BACKUP_FILE} && \
            echo 'Backup OK: /opt/backups/${BACKUP_FILE} ('$(du -h /opt/backups/${BACKUP_FILE} | cut -f1)')'
          "

      # Migrations BEFORE app starts serving requests (S6 fix)
      - name: Run Migrations (before app start)
        run: |
          set -euo pipefail
          ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} "
            cd ${{ env.DEPLOY_SERVER_PATH }} && \
            docker compose -f docker-compose.prod.yml run --rm \
              ${{ vars.DEPLOY_WEB_SERVICE }} ${{ env.DEPLOY_MIGRATE_CMD }}
          "

      - name: Start App
        run: |
          set -euo pipefail
          ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} "
            cd ${{ env.DEPLOY_SERVER_PATH }} && \
            docker compose -f docker-compose.prod.yml up -d --force-recreate
          "

      - name: Wait for Liveness (max 150s)
        run: |
          set -euo pipefail
          for i in $(seq 1 30); do
            HTTP_STATUS=$(ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} \
              "curl -sf -o /dev/null -w '%{http_code}' \
              http://localhost:${{ env.DEPLOY_PORT }}/livez/" 2>/dev/null || echo "000")
            [ "$HTTP_STATUS" = "200" ] && break
            echo "Waiting for /livez/... ($i/30, status=$HTTP_STATUS)"
            sleep 5
          done
          [ "$HTTP_STATUS" = "200" ] || { echo "FAIL: /livez/ timeout"; exit 1; }
          echo "OK: /livez/ → 200"

      - name: Readiness Check
        run: |
          set -euo pipefail
          HTTP_STATUS=$(ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} \
            "curl -sf -o /dev/null -w '%{http_code}' \
            http://localhost:${{ env.DEPLOY_PORT }}/healthz/")
          [ "$HTTP_STATUS" = "200" ] || { echo "FAIL: /healthz/ returned $HTTP_STATUS"; exit 1; }
          echo "OK: /healthz/ → 200 (DB + services connected)"

      - name: Log Check
        run: |
          set -euo pipefail
          ERRORS=$(ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} \
            "docker logs ${{ env.DEPLOY_CONTAINER }} --tail 50 2>&1 \
            | grep -c 'ERROR\|CRITICAL'" || echo "0")
          [ "$ERRORS" = "0" ] || echo "::warning::$ERRORS errors in recent container logs"

      - name: Post-Deploy Summary
        run: |
          echo "## Deploy Success ✅" >> "$GITHUB_STEP_SUMMARY"
          echo "- **App:** ${{ vars.DEPLOY_APP_NAME }}" >> "$GITHUB_STEP_SUMMARY"
          echo "- **Image:** ${{ env.DEPLOY_IMAGE }}:${GITHUB_SHA::7}" >> "$GITHUB_STEP_SUMMARY"
          echo "- **Liveness:** /livez/ → 200" >> "$GITHUB_STEP_SUMMARY"
          echo "- **Readiness:** /healthz/ → 200" >> "$GITHUB_STEP_SUMMARY"
```

**v4 DB-Backup Regeln:**
- Backup wird **vor** jeder Migration erstellt
- Dateiname enthält App-Name, Git-SHA und Timestamp für Eindeutigkeit
- Gespeichert in `/opt/backups/` auf dem Server
- Bei Rollback (Stage ⑦) kann das Backup manuell restored werden
- Cleanup: `find /opt/backups -name '*.sql.gz' -mtime +30 -delete` (Cron)

**Gate:** Backup OK, Migrations OK, Liveness 200, Readiness 200, keine kritischen Log-Fehler.

---

### 5.8 Stage ⑦ Error Handling + Rollback

**Ziel:** Bei Failure deterministischer Rollback via SHA-7 Tag + Benachrichtigung.

```yaml
  rollback:
    runs-on: [self-hosted, hetzner]
    timeout-minutes: 5
    needs: deploy-verify
    if: failure()
    steps:
      - name: Setup SSH
        run: |
          set -euo pipefail
          mkdir -p ~/.ssh
          echo "${{ secrets.DEPLOY_SSH_KEY }}" > ~/.ssh/id_ed25519
          chmod 600 ~/.ssh/id_ed25519
          ssh-keyscan -H ${{ secrets.DEPLOY_HOST }} >> ~/.ssh/known_hosts

      - name: Collect Failure Logs
        run: |
          set -euo pipefail
          ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} \
            "docker logs ${{ env.DEPLOY_CONTAINER }} --tail 100" 2>&1 \
            | tee /tmp/failure_logs.txt

      - name: Rollback to Previous Image
        run: |
          set -euo pipefail
          PREV_SHA="${{ needs.deploy-build.outputs.previous_sha }}"
          if [ "$PREV_SHA" = "unknown" ] || [ -z "$PREV_SHA" ]; then
            echo "WARN: No previous SHA found — cannot rollback automatically"
            exit 1
          fi
          echo "Rolling back to ${{ env.DEPLOY_IMAGE }}:${PREV_SHA}..."
          ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} "
            cd ${{ env.DEPLOY_SERVER_PATH }} && \
            IMAGE_TAG=${PREV_SHA} docker compose -f docker-compose.prod.yml pull && \
            IMAGE_TAG=${PREV_SHA} docker compose -f docker-compose.prod.yml up -d --force-recreate
          "

      - name: Verify Rollback
        run: |
          set -euo pipefail
          sleep 15
          HTTP_STATUS=$(ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} \
            "curl -sf -o /dev/null -w '%{http_code}' \
            http://localhost:${{ env.DEPLOY_PORT }}/livez/" 2>/dev/null || echo "000")
          [ "$HTTP_STATUS" = "200" ] || { echo "FAIL: Rollback health check failed!"; exit 1; }
          echo "OK: Rollback verified — /livez/ → 200"

      - name: Notify
        if: always()
        run: |
          set -euo pipefail
          echo "## 🔴 Deployment FAILED — Rollback Executed" >> "$GITHUB_STEP_SUMMARY"
          echo "- **Rolled back to:** ${{ needs.deploy-build.outputs.previous_sha }}" >> "$GITHUB_STEP_SUMMARY"
          echo "- **DB Backup available** in /opt/backups/" >> "$GITHUB_STEP_SUMMARY"
          curl -sf -X POST "${{ secrets.SLACK_WEBHOOK_URL }}" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"🔴 Deployment FAILED: ${{ vars.DEPLOY_APP_NAME }} — Rollback to ${{ needs.deploy-build.outputs.previous_sha }}. DB backup in /opt/backups/. <${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|Logs>\"}" \
            || echo "WARN: Slack notification failed (webhook not configured?)"
```

---

## 6. Reusable Workflow (v4)

Statt in jedem Repo eine Kopie der Pipeline zu pflegen, kann ein **Reusable Workflow**
im `platform` Repository definiert werden:

### 6.1 Template in platform

```yaml
# platform/.github/workflows/ci-cd-template.yml
name: CI/CD Template (ADR-090)

on:
  workflow_call:
    inputs:
      app_name:
        required: true
        type: string
      dockerfile:
        required: true
        type: string
      image:
        required: true
        type: string
      container:
        required: true
        type: string
      web_service:
        required: true
        type: string
      server_path:
        required: true
        type: string
      port:
        required: true
        type: string
      migrate_cmd:
        required: true
        type: string
      db_container:
        required: true
        type: string
    secrets:
      DEPLOY_SSH_KEY:
        required: true
      DEPLOY_HOST:
        required: true
      DEPLOY_USER:
        required: true
      SLACK_WEBHOOK_URL:
        required: false

# ... (alle Jobs wie in §5 definiert, mit inputs.* statt vars.*)
```

### 6.2 Nutzung in Consumer-Repos

```yaml
# travel-beat/.github/workflows/ci-cd.yml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  pipeline:
    uses: achimdehnert/platform/.github/workflows/ci-cd-template.yml@main
    with:
      app_name: travel-beat
      dockerfile: docker/Dockerfile
      image: ghcr.io/achimdehnert/travel-beat
      container: travel_beat_web
      web_service: travel-beat-web
      server_path: /opt/travel-beat
      port: "8089"
      migrate_cmd: "python manage.py migrate_schemas --tenant"
      db_container: travel_beat_db
    secrets: inherit
```

**Vorteile:**
- **DRY:** Pipeline-Logik existiert genau einmal in `platform`
- **Kein Drift:** Alle Repos nutzen automatisch die neueste Version
- **Einfaches Onboarding:** Neues Repo = 20 Zeilen YAML
- **Zentrale Updates:** Fix in `platform` → alle Repos profitieren

**Implementierung:** Phase 2, nachdem die Pipeline in einem Repo (137-hub) validiert ist.

---

## 7. Per-App Configuration

Jedes Repo definiert seine Pipeline-Variablen als **GitHub Repository Variables**
(Settings → Secrets and variables → Actions → Variables):

| Variable | Beispiel (travel-beat) | Beispiel (137-hub) |
|----------|----------------------|-------------------|
| `DEPLOY_APP_NAME` | travel-beat | 137-hub |
| `DEPLOY_DOCKERFILE` | docker/Dockerfile | docker/Dockerfile |
| `DEPLOY_IMAGE` | ghcr.io/achimdehnert/travel-beat | ghcr.io/achimdehnert/137-hub/hub137-web |
| `DEPLOY_CONTAINER` | travel_beat_web | hub137_web |
| `DEPLOY_WEB_SERVICE` | travel-beat-web | hub137-web |
| `DEPLOY_DB_CONTAINER` | travel_beat_db | hub137_db |
| `DEPLOY_SERVER_PATH` | /opt/travel-beat | /opt/137-hub |
| `DEPLOY_PORT` | 8089 | 8095 |
| `DEPLOY_MIGRATE_CMD` | python manage.py migrate_schemas --tenant | python manage.py migrate --noinput |

**Secrets** (Repository-Level oder Environment-Level):

| Secret | Beschreibung |
|--------|-------------|
| `DEPLOY_SSH_KEY` | ed25519 Private Key für Server-Zugriff |
| `DEPLOY_HOST` | Server IP (z.B. `88.198.191.108`) |
| `DEPLOY_USER` | SSH User (z.B. `root`) |
| `SLACK_WEBHOOK_URL` | Optional: Slack Incoming Webhook |

**GitHub Environment** (v4):

| Setting | Wert |
|---------|------|
| Name | `production` |
| Required Reviewers | Optional (empfohlen für kritische Apps) |
| Wait Timer | Optional (z.B. 0–5 Minuten) |
| Deployment Branches | `main` only |

Source of truth: `platform/registry/repos.yaml`.

---

## 8. Pipeline Timing (geschätzt)

```
Linearer Ansatz (v1):          Hybrid Matrix (v4):
──────────────────             ──────────────────
②  Python CI    3min           ②a Fast Checks   0.5min
③  Postgres CI  4min           ②b Python Tests ─┐
④  Gate         0.5min              3min        │ parallel
⑤  Build        3min           ③  Postgres     ─┘  = 4min
⑥  Deploy       2min           ④  Gate           0.5min
                               ⑤  Build          3min (+ approval wait)
Total: ~12.5min                ⑥  Deploy         2min (inkl. backup)

                               Total: ~10min (−20%) + approval
                               Bei Lint-Fail: 0.5min statt 3min!
                               Max Job-Timeout: 5min (v4)
```

---

## 9. Implementierungsprioritäten

| Prio | Stage | Aufwand | Wert | Status |
|------|-------|---------|------|--------|
| 1 | ②a Fast Checks | 30min | **Billigster Gate, größter ROI** | ⏳ |
| 2 | ③ Migration Graph + AppConfig Check | 1h | **Verhindert NodeNotFoundError** | ⏳ |
| 3 | ②b Wheel Verification | 1h | **Verhindert stale Wheel deploys** | ⏳ |
| 4 | ⑤ Build + Push + Environment | 2h | Rollback-fähige Images + Approval | ⏳ |
| 5 | ⑥ Backup + Migrate-first + Health | 2h | Datenintegrität + keine App mit altem Schema | ⏳ |
| 6 | ④ Coverage Gate | 1h | Qualitätssicherung | ⏳ |
| 7 | ⑦ SHA-Rollback + Slack | 3h | Automatische Fehlerbehandlung | ⏳ |
| 8 | ① Pre-commit (kanonisch) | 30min | Lokales Feedback | ⏳ |
| 9 | Reusable Workflow Template | 3h | DRY über alle Repos | ⏳ |

---

## 10. Lessons Learned (travel-beat 2026-02-26)

Diese Pipeline hätte **alle 4 Fehler** des travel-beat Deployments verhindert:

1. **Stage ③** `AppConfig Label Check` hätte erkannt dass Django die
   Default-AppConfig nutzt statt `BfagentLlmConfig`
2. **Stage ②b** Wheel Verification hätte erkannt dass das Wheel
   den alten Code enthält (kein `label` im `__init__.py`)
3. **Stage ③** `Django System Check` hätte den E304 Reverse Accessor
   Clash erkannt
4. **Stage ⑤** `Docker Build` mit `set -euo pipefail` hätte verhindert
   dass ein fehlgeschlagener Build trotzdem gepusht wird

---

## 11. More Information

- ADR-042: Self-Hosted Runner Setup auf Hetzner Dev-Server
- ADR-056: Multi-Tenancy Deploy Patterns (migrate_schemas)
- ADR-057: Test-Stufen und Coverage-Schwellen
- ADR-061: Secret-Management (keine Hardcoded Credentials)
- ADR-071: Ruff Config + Pre-Commit kanonisches Template
- ADR-089: bfagent-llm Invarianten 7-10 (AppConfig, Wheels)

---

## 12. Review-Protokoll

| # | Befund | Risiko | Status |
|---|--------|--------|--------|
| K1 | `StrictHostKeyChecking=no` | KRITISCH | ✅ v3 — `ssh-keyscan` + Secret |
| K2 | Hardcoded IP + root | KRITISCH | ✅ v3 — `DEPLOY_HOST` + `DEPLOY_USER` Secrets |
| K3 | ubuntu-latest statt self-hosted | KRITISCH | ✅ v3 — Deploy-Jobs auf `[self-hosted, hetzner]` |
| K4 | permissions Block fehlt | KRITISCH | ✅ v3 — `packages: write` ergänzt |
| K5 | Coverage combine mit XML | KRITISCH | ✅ v3 — `.coverage` Dateien + `coverage combine` |
| S1 | MADR 4.0 Sections fehlen | SCHWER | ✅ v3 — Decision Drivers, Options, Pros/Cons, Consequences, Confirmation |
| S2 | Pre-commit abweichend | SCHWER | ✅ v3 — Kanonisches Template (ADR-071) |
| S3 | Ruff v0.8.0 veraltet | SCHWER | ✅ v3 — v0.15.0 |
| S4 | Rollback nicht idempotent | SCHWER | ✅ v3 — SHA-7 basierter Rollback |
| S5 | set -euo pipefail fehlt | SCHWER | ✅ v3 — In allen run-Blöcken |
| S6 | Migration nach App-Start | SCHWER | ✅ v3 — `docker compose run --rm` vor `up -d` |
| S7 | Wheel-Install-Syntax | SCHWER | ✅ v3 — Glob-Guard mit `ls` Check |
| S8 | Vollständiger Workflow fehlt | SCHWER | ✅ v3 — §5.0 Workflow-Rahmen |
| M1 | Python-Matrix unnötig | MODERAT | ✅ v3 — Nur 3.12 |
| M2 | ruff ohne output-format | MODERAT | ✅ v3 — `--output-format=github` |
| M3 | Keine Slack-Notification | MODERAT | ✅ v3 — Webhook in ⑦ |
| M4 | Nur /livez/, kein /healthz/ | MODERAT | ✅ v3 — Beide Endpoints |
| M5 | pre-commit-hooks veraltet | MODERAT | ✅ v3 — v6.0.0 |
| M6 | maxkb=5000 zu hoch | MODERAT | ✅ v3 — 500 KB |
| O1 | Kein Concurrency-Control | HOCH | ✅ v4 — `concurrency:` Block, ⚠️ v5 — cancel-in-progress:true |
| O2 | Keine Job-Timeouts | HOCH | ✅ v4 — `timeout-minutes: 5` auf allen Jobs |
| O3 | Kein DB-Backup vor Migration | HOCH | ✅ v4 — pg_dump vor migrate |
| O4 | Kein Reusable Workflow | MITTEL | ✅ v4 — Template in §6 definiert |
| O5 | Keine Environment Protection | MITTEL | ✅ v4 — `environment: production` |

---

## 13. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-26 | Achim Dehnert | v1: Initial — 7-Stufen-Pipeline aus ADR-056/057/071/054 + Lessons Learned |
| 2026-02-27 | Achim Dehnert | v2: Hybrid Matrix — Fast Checks Gate, dann ②b ‖ ③ parallel |
| 2026-02-27 | Achim Dehnert | v3: Post-Review — 19 Befunde (5K, 8S, 6M) gefixt. MADR 4.0 compliant. |
| 2026-02-27 | Achim Dehnert | v4: Hardened — Concurrency-Control, 5min Job-Timeouts, DB-Backup vor Migration, Reusable Workflow Template, GitHub Environment Protection, Artifact Retention. |
| 2026-02-27 | Achim Dehnert | v5: Implementation-Hardened — Concurrency-Bug gefixt (cancel-in-progress:true + ref-basierte Gruppe), Requirements-Trennung (prod vs dev), ruff src-Config, Pillow CVE-2026-25990. |
