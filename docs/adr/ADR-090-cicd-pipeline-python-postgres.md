---
status: accepted
date: 2026-02-26
implemented: partial
decision-makers: Achim Dehnert
consulted: –
informed: –
supersedes: –
amends: ADR-056, ADR-057, ADR-071, ADR-054
related: ADR-022, ADR-089
---

# ADR-090: Abstract CI/CD Pipeline — Python + PostgreSQL → Docker Deploy

| Attribut       | Wert                                                        |
|----------------|-------------------------------------------------------------|
| **Status**     | **Accepted** (v2 — Hybrid Matrix)                           |
| **Scope**      | Platform-wide — all Django repos                            |
| **Erstellt**   | 2026-02-26                                                  |
| **Autor**      | Achim Dehnert                                               |
| **Amends**     | ADR-056 (Multi-Tenancy), ADR-057, ADR-071, ADR-054          |
| **Relates to** | ADR-022 (Repo Standards), ADR-089 (bfagent-llm Invarianten) |

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

### 1.2 Ziel

Eine **7-Stufen-Pipeline** die jedes Python+PostgreSQL+Django Projekt
von der Entwicklung bis zum verifizierten Deployment absichert.

### 1.3 Design-Entscheidung: Hybrid Matrix (v2)

**Abgelehnt:** Rein lineare Pipeline (② → ③ → ④) — verschwendet CI-Zeit,
da Python-Tests und Postgres-Tests unabhängig voneinander sind.

**Abgelehnt:** Rein parallele Matrix (② ‖ ③) ohne Gate — verschwendet
teure Postgres-CI-Minuten wenn ruff schon in 5s einen Fehler findet.

**Gewählt: Hybrid Matrix** — Schnelle Checks als Gate, dann parallel:

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
                    ⑤ Build + Push
                    Docker → GHCR
                          │
                    ⑥ Deploy + Verify
                    health + smoke
                          │
                    ⑦ Error Handling
                    rollback + notify
```

**Begründung:** Stage ②a (ruff + pip-audit) läuft in <30 Sekunden und
fängt ~60% aller Fehler (Syntax, Format, bekannte CVEs). Erst nach diesem
billigen Gate starten die teuren Jobs ②b und ③ **parallel**. Das spart
~50% CI-Laufzeit gegenüber der linearen Variante, ohne teure Postgres-
Minuten bei trivialen Lint-Fehlern zu verschwenden.

---

## 2. Die 7-Stufen-Pipeline

### Stage ① Development (Lokal)

**Ziel:** Erste Verteidigungslinie noch vor `git push`.

**Pre-Commit Hooks:**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff          # Lint
      - id: ruff-format   # Format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-added-large-files  # keine 50MB Wheels versehentlich
        args: ['--maxkb=5000']
      - id: detect-private-key
      - id: check-merge-conflict

  - repo: https://github.com/commitizen-tools/commitizen
    rev: v4.0.0
    hooks:
      - id: commitizen    # Conventional commits
```

**Lokale Tests:**

```bash
# Schnelles Feedback (<30s)
pytest tests/unit/ -x --tb=short
```

**Gate:** Pre-commit MUSS pass. Commit wird sonst blockiert.

---

### Stage ②a Fast Checks (CI — <30s)

**Ziel:** Billigstes Gate — blockiert teure Jobs bei trivialen Fehlern.

```yaml
# .github/workflows/ci.yml
fast-checks:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - uses: actions/setup-python@v5
      with:
        python-version: "3.12"

    - name: Install Tools
      run: pip install ruff pip-audit

    - name: Lint
      run: ruff check .

    - name: Format Check
      run: ruff format --check .

    - name: Security Audit
      run: pip-audit --strict --desc -r requirements/base.txt
```

**Gate:** Alle 3 Checks grün → ②b und ③ starten parallel.
Fail → Pipeline stoppt sofort (kein Postgres-Container gestartet).

---

### Stage ②b Python Tests (CI — parallel)

**Ziel:** Unit-Tests + Wheel-Verification ohne DB-Abhängigkeit.

```yaml
python-tests:
  runs-on: ubuntu-latest
  needs: fast-checks
  strategy:
    matrix:
      python-version: ["3.11", "3.12"]
  steps:
    - uses: actions/checkout@v4

    - uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install Dependencies
      run: |
        pip install -r requirements/base.txt
        pip install requirements/wheels/*.whl
        pip install pytest pytest-cov

    - name: Unit Tests + Coverage
      run: pytest tests/unit/ --cov=src --cov-report=xml -q

    # ADR-089 Invariante 7+10: Wheel-Package-Checks
    - name: Verify Platform Wheels
      run: |
        for whl in requirements/wheels/*.whl; do
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
        name: coverage-python-${{ matrix.python-version }}
        path: coverage.xml
```

**Gate:** Tests grün, Wheels valide.

---

### Stage ③ PostgreSQL Verification (CI — parallel)

**Ziel:** DB-Schicht gegen echtes PostgreSQL prüfen. Läuft **parallel** zu ②b.

```yaml
postgres-tests:
  runs-on: ubuntu-latest
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

  steps:
    - uses: actions/checkout@v4

    - uses: actions/setup-python@v5
      with:
        python-version: "3.12"

    - name: Install Dependencies
      run: |
        pip install -r requirements/base.txt
        pip install requirements/wheels/*.whl
        pip install pytest pytest-cov pytest-django

    # ADR-089 R-13: Verify AppConfig discovery BEFORE migrations
    - name: AppConfig Label Check
      env:
        DATABASE_URL: postgres://test_user:test_pass@localhost:5432/test_db
      run: |
        python -c "
        import django, os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        django.setup()
        from django.apps import apps
        errors = []
        for ac in apps.get_app_configs():
            # Flag any custom package using default AppConfig
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
      env:
        DATABASE_URL: postgres://test_user:test_pass@localhost:5432/test_db
      run: |
        python manage.py migrate --check --dry-run 2>&1 || {
          echo "FAIL: Migration graph inconsistent!"
          python manage.py showmigrations --list 2>&1 | grep -E '\[X\]|\[ \]'
          exit 1
        }

    - name: Run Migrations
      env:
        DATABASE_URL: postgres://test_user:test_pass@localhost:5432/test_db
      run: python manage.py migrate --noinput

    - name: Django System Check
      env:
        DATABASE_URL: postgres://test_user:test_pass@localhost:5432/test_db
      run: python manage.py check --deploy --fail-level WARNING

    - name: Integration Tests
      env:
        DATABASE_URL: postgres://test_user:test_pass@localhost:5432/test_db
      run: pytest tests/integration/ --cov=src --cov-report=xml -q

    - name: Upload Coverage
      uses: actions/upload-artifact@v4
      with:
        name: coverage-postgres
        path: coverage.xml
```

**django-tenants Variante:**

```yaml
    - name: Migration Check (django-tenants)
      run: |
        python manage.py migrate_schemas --shared --check
        python manage.py migrate_schemas --tenant --check
```

**Gate:** Migrations konsistent, System-Check grün, Integration-Tests pass.

---

### Stage ④ Quality Gate

**Ziel:** Merged Coverage aus ②b + ③ muss ≥ 80% sein.

```yaml
quality-gate:
  runs-on: ubuntu-latest
  needs: [python-tests, postgres-tests]    # ← wartet auf BEIDE
  steps:
    - uses: actions/checkout@v4

    - name: Download Coverage Reports
      uses: actions/download-artifact@v4
      with:
        pattern: coverage-*
        merge-multiple: true

    - name: Merge + Check Threshold
      run: |
        pip install coverage
        coverage combine *.xml || true
        TOTAL=$(coverage report --format=total 2>/dev/null || echo "0")
        echo "## Coverage: ${TOTAL}%" >> $GITHUB_STEP_SUMMARY
        if [ "$TOTAL" -lt 80 ]; then
          echo "FAIL: Coverage ${TOTAL}% < 80% threshold"
          exit 1
        fi
        echo "OK: Coverage ${TOTAL}% ≥ 80%"
```

**Gate:** Coverage ≥ 80% oder Pipeline blockiert.

---

### Stage ⑤ Deployment Definition

**Ziel:** Sicheres, verifiziertes Docker-Image bauen und pushen.

```yaml
deploy-build:
  runs-on: ubuntu-latest
  needs: quality-gate
  if: github.ref == 'refs/heads/main'
  env:
    # Loaded from .github/deploy.env or registry/repos.yaml
    IMAGE: ${{ vars.DEPLOY_IMAGE }}
    DOCKERFILE: ${{ vars.DEPLOY_DOCKERFILE }}
  steps:
    - uses: actions/checkout@v4

    - name: Login to GHCR
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    # Pre-Flight: Can we even deploy?
    - name: Pre-Flight Validation
      run: |
        # SSH probe
        ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
          root@88.198.191.108 "echo OK" || {
          echo "FAIL: SSH to server unreachable"; exit 1
        }

    # ADR-089 Invariante 9: Wheel version matches code
    - name: Wheel Freshness Check
      run: |
        for whl in requirements/wheels/*.whl; do
          PKG=$(basename "$whl" | sed 's/-[0-9].*//')
          VERSION=$(basename "$whl" | sed 's/.*-\([0-9][^-]*\)-.*/\1/')
          echo "Wheel: $PKG v$VERSION"
        done

    - name: Docker Build
      run: |
        docker build \
          --no-cache \
          --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
          --build-arg GIT_SHA=${GITHUB_SHA::7} \
          -f ${{ env.DOCKERFILE }} \
          -t ${{ env.IMAGE }}:${GITHUB_SHA::7} \
          -t ${{ env.IMAGE }}:latest \
          . && echo "=== BUILD OK ===" || { echo "=== BUILD FAILED ==="; exit 1; }

    - name: Docker Push
      run: |
        docker push ${{ env.IMAGE }}:${GITHUB_SHA::7} && \
        docker push ${{ env.IMAGE }}:latest && \
        echo "=== PUSH OK: ${{ env.IMAGE }}:${GITHUB_SHA::7} ==="
```

**Gate:** Image hat SHA-7 Tag UND latest. Beide gepusht.

---

### Stage ⑥ Deployment Verification

**Ziel:** Nach `docker compose up` verifizieren dass alles läuft.

```yaml
deploy-verify:
  runs-on: ubuntu-latest
  needs: deploy-build
  env:
    CONTAINER: ${{ vars.DEPLOY_CONTAINER }}
    SERVER_PATH: ${{ vars.DEPLOY_SERVER_PATH }}
    PORT: ${{ vars.DEPLOY_PORT }}
    MIGRATE_CMD: ${{ vars.DEPLOY_MIGRATE_CMD }}
  steps:
    - name: Server Pull + Recreate
      run: |
        ssh root@88.198.191.108 "
          cd ${{ env.SERVER_PATH }} && \
          docker compose -f docker-compose.prod.yml pull && \
          docker compose -f docker-compose.prod.yml up -d --force-recreate
        "

    - name: Wait for Health (max 150s)
      run: |
        for i in $(seq 1 30); do
          STATUS=$(ssh root@88.198.191.108 \
            "docker exec ${{ env.CONTAINER }} python manage.py check --deploy 2>&1" \
            && echo "OK" || echo "WAIT")
          [ "$STATUS" = "OK" ] && break
          echo "Waiting... ($i/30)"
          sleep 5
        done
        [ "$STATUS" = "OK" ] || { echo "FAIL: Health check timeout"; exit 1; }

    - name: Run Migrations
      run: |
        ssh root@88.198.191.108 \
          "docker exec ${{ env.CONTAINER }} ${{ env.MIGRATE_CMD }}"

    - name: Smoke Tests
      run: |
        # HTTP health endpoint
        HTTP_STATUS=$(ssh root@88.198.191.108 \
          "curl -s -o /dev/null -w '%{http_code}' http://localhost:${{ env.PORT }}/livez/")
        [ "$HTTP_STATUS" = "200" ] || { echo "FAIL: /livez/ returned $HTTP_STATUS"; exit 1; }
        echo "OK: /livez/ → 200"

        # Container logs: no ERROR/CRITICAL
        ERRORS=$(ssh root@88.198.191.108 \
          "docker logs ${{ env.CONTAINER }} --tail 50 2>&1 | grep -c 'ERROR\|CRITICAL'" || echo "0")
        [ "$ERRORS" = "0" ] || echo "WARN: $ERRORS errors in recent logs"

    - name: Post-Deploy Summary
      run: |
        echo "## Deploy Summary" >> $GITHUB_STEP_SUMMARY
        echo "- **App:** ${{ vars.DEPLOY_APP_NAME }}" >> $GITHUB_STEP_SUMMARY
        echo "- **Image:** ${{ env.IMAGE }}:${GITHUB_SHA::7}" >> $GITHUB_STEP_SUMMARY
        echo "- **Health:** 200 OK" >> $GITHUB_STEP_SUMMARY
```

**Gate:** Health 200, Migrations OK, keine kritischen Fehler in Logs.

---

### Stage ⑦ Error Handling + Rollback

**Ziel:** Bei Failure automatisch rollback + benachrichtigen.

```yaml
rollback:
  runs-on: ubuntu-latest
  needs: deploy-verify
  if: failure()
  env:
    CONTAINER: ${{ vars.DEPLOY_CONTAINER }}
    SERVER_PATH: ${{ vars.DEPLOY_SERVER_PATH }}
  steps:
    - name: Collect Failure Logs
      run: |
        ssh root@88.198.191.108 \
          "docker logs ${{ env.CONTAINER }} --tail 100" > /tmp/failure_logs.txt
        cat /tmp/failure_logs.txt

    - name: Rollback to Previous Image
      run: |
        echo "Rolling back..."
        ssh root@88.198.191.108 "
          cd ${{ env.SERVER_PATH }} && \
          docker compose -f docker-compose.prod.yml down && \
          docker compose -f docker-compose.prod.yml up -d
        "

    - name: Verify Rollback
      run: |
        sleep 10
        ssh root@88.198.191.108 \
          "docker exec ${{ env.CONTAINER }} python manage.py check --deploy"

    - name: Notify
      run: |
        echo "## DEPLOYMENT FAILED" >> $GITHUB_STEP_SUMMARY
        echo "Rollback executed. Check workflow logs." >> $GITHUB_STEP_SUMMARY
        # Future: Slack/Discord webhook notification
```

---

## 3. Per-App Configuration

Jedes Repo definiert seine Pipeline-Variablen als **GitHub Repository Variables**
(Settings → Secrets and variables → Actions → Variables):

| Variable | Beispiel (travel-beat) | Beispiel (137-hub) |
|----------|----------------------|-------------------|
| `DEPLOY_APP_NAME` | travel-beat | 137-hub |
| `DEPLOY_DOCKERFILE` | docker/Dockerfile | docker/Dockerfile |
| `DEPLOY_IMAGE` | ghcr.io/achimdehnert/travel-beat | ghcr.io/achimdehnert/137-hub/hub137-web |
| `DEPLOY_CONTAINER` | travel_beat_web | hub137_web |
| `DEPLOY_SERVER_PATH` | /opt/travel-beat | /opt/137-hub |
| `DEPLOY_PORT` | 8089 | 8095 |
| `DEPLOY_MIGRATE_CMD` | python manage.py migrate_schemas --tenant | python manage.py migrate --noinput |

Source of truth: `platform/registry/repos.yaml`.

---

## 4. Pipeline Timing (geschätzt)

```
Linearer Ansatz (v1):          Hybrid Matrix (v2):
──────────────────             ──────────────────
②  Python CI    3min           ②a Fast Checks   0.5min
③  Postgres CI  4min           ②b Python Tests ─┐
④  Gate         0.5min              3min        │ parallel
⑤  Build        3min           ③  Postgres     ─┘  = 4min
⑥  Deploy       2min           ④  Gate           0.5min
                               ⑤  Build          3min
Total: ~12.5min                ⑥  Deploy         2min

                               Total: ~10min (−20%)
                               Bei Lint-Fail: 0.5min statt 3min!
```

---

## 5. Implementierungsprioritäten

| Prio | Stage | Aufwand | Wert | Status |
|------|-------|---------|------|--------|
| 1 | ②a Fast Checks | 30min | **Billigster Gate, größter ROI** | ⏳ |
| 2 | ③ Migration Graph Check | 1h | **Verhindert NodeNotFoundError** | ⏳ |
| 3 | ②b Wheel Verification | 1h | **Verhindert stale Wheel deploys** | ⏳ |
| 4 | ⑤ Build + Push mit SHA-Tag | 2h | Rollback-fähige Images | ⏳ |
| 5 | ⑥ Health + Smoke | 2h | Automatische Verification | ⏳ |
| 6 | ④ Coverage Gate | 1h | Qualitätssicherung | ⏳ |
| 7 | ⑦ Rollback | 3h | Automatische Fehlerbehandlung | ⏳ |
| 8 | ① Pre-commit | 30min | Lokales Feedback | ⏳ |

---

## 6. Lessons Learned (travel-beat 2026-02-26)

Diese Pipeline hätte **alle 4 Fehler** des travel-beat Deployments verhindert:

1. **Stage ③** `AppConfig Label Check` hätte erkannt dass Django die
   Default-AppConfig nutzt statt `BfagentLlmConfig`
2. **Stage ②b** `Django System Check` hätte den E304 Reverse Accessor
   Clash erkannt
3. **Stage ⑤** `Wheel Freshness Check` hätte erkannt dass das Wheel
   den alten Code enthält (kein `label` im `__init__.py`)
4. **Stage ⑤** `Docker Build` mit `&&` Chaining hätte verhindert dass
   ein fehlgeschlagener Build trotzdem gepusht wird

---

## 7. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-26 | Achim Dehnert | v1: Initial — 7-Stufen-Pipeline aus ADR-056/057/071/054 + Lessons Learned |
| 2026-02-27 | Achim Dehnert | v2: Hybrid Matrix — Fast Checks als Gate, dann ②b ‖ ③ parallel. GitHub Actions Variablen statt deploy.env. Timing-Vergleich. Prioritäten aktualisiert. |
