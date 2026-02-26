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
| **Status**     | **Accepted** (v1)                                           |
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
| 2 | Fehlende `related_name` → E304 | Stage ② Django System Check |
| 3 | pip Cache liefert stale Wheel | Stage ⑤ Wheel-Content-Verification |
| 4 | Django 5.0 Auto-Discovery versagt | Stage ③ AppConfig-Label-Check |

### 1.2 Ziel

Eine **7-Stufen-Pipeline** die jedes Python+PostgreSQL+Django Projekt
von der Entwicklung bis zum verifizierten Deployment absichert.

---

## 2. Die 7-Stufen-Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEVELOPMENT → PRODUCTION                      │
│                                                                  │
│  ① Local    ② Python CI   ③ Postgres CI   ④ Gate   ⑤ Build     │
│  pre-commit  ruff+audit    migrations      80%     Docker+GHCR  │
│  unit tests  unit tests    integration     merge   pre-flight   │
│              dep scan      contract               wheel verify  │
│                            schema check                         │
│                                                                  │
│                          ⑥ Deploy Verify    ⑦ Error Handling    │
│                          health + smoke     rollback + notify   │
└─────────────────────────────────────────────────────────────────┘
```

---

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

### Stage ② Python Verification (CI)

**Ziel:** Reine Code-Qualität ohne DB-Abhängigkeit.

```yaml
# .github/workflows/ci.yml (Stage 2)
python-verify:
  runs-on: ubuntu-latest
  strategy:
    matrix:
      python-version: ["3.11", "3.12"]
  steps:
    - uses: actions/checkout@v4

    - name: Lint + Format
      run: ruff check . && ruff format --check .

    - name: Type Check (optional)
      run: mypy src/ --ignore-missing-imports

    - name: Security Audit
      run: pip-audit --strict --desc

    - name: Unit Tests + Coverage
      run: pytest tests/unit/ --cov=src --cov-report=xml

    # ADR-089 Invariante 7+10: Wheel-Package-Checks
    - name: Verify Platform Wheels
      run: |
        for whl in requirements/wheels/*.whl; do
          echo "=== Checking $whl ==="
          python -c "
          import zipfile, sys
          z = zipfile.ZipFile('$whl')
          # Check: __init__.py with AppConfig exists
          inits = [f for f in z.namelist() if f.endswith('django_app/__init__.py')]
          for init in inits:
              content = z.read(init).decode()
              if 'AppConfig' in content and 'label' not in content:
                  print(f'FAIL: {init} has AppConfig without explicit label!')
                  sys.exit(1)
              print(f'OK: {init}')
          "
        done
```

**Gate:** Alle Checks grün. Coverage-Report wird gespeichert.

---

### Stage ③ PostgreSQL Verification (CI)

**Ziel:** DB-Schicht gegen echtes PostgreSQL prüfen.

```yaml
# .github/workflows/ci.yml (Stage 3)
postgres-verify:
  runs-on: ubuntu-latest
  needs: python-verify
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

    # ADR-089 R-13: Verify AppConfig discovery BEFORE migrations
    - name: AppConfig Label Check
      run: |
        python -c "
        import django, os
        os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
        os.environ['DATABASE_URL'] = 'postgres://test_user:test_pass@localhost/test_db'
        django.setup()
        from django.apps import apps
        for ac in apps.get_app_configs():
            if ac.__class__.__name__ == 'AppConfig' and ac.label != ac.name.split('.')[-1]:
                continue  # Standard Django apps
            if 'bfagent' in ac.name and ac.__class__.__name__ == 'AppConfig':
                print(f'FAIL: {ac.name} uses default AppConfig (label={ac.label})')
                exit(1)
        print('OK: All custom apps use explicit AppConfig classes')
        "

    # Migration Graph Consistency (catches NodeNotFoundError BEFORE deploy)
    - name: Migration Graph Check
      run: |
        python manage.py migrate --check --dry-run 2>&1 || {
          echo "FAIL: Migration graph inconsistent!"
          python manage.py showmigrations --list 2>&1 | grep -E '\[X\]|\[ \]'
          exit 1
        }

    - name: Run Migrations
      run: python manage.py migrate --noinput

    - name: Django System Check
      run: python manage.py check --deploy --fail-level WARNING

    - name: Integration Tests
      run: pytest tests/integration/ --cov=src --cov-append --cov-report=xml

    # Schema snapshot for drift detection
    - name: Schema Snapshot
      run: |
        python manage.py inspectdb > /tmp/schema_snapshot.py
        echo "Schema snapshot saved ($(wc -l < /tmp/schema_snapshot.py) lines)"
```

**django-tenants Variante:**

```yaml
    - name: Migration Check (django-tenants)
      run: |
        python manage.py migrate_schemas --shared --check
        python manage.py migrate_schemas --tenant --check
```

**Gate:** Alle Migrations konsistent, System-Check grün, Integration-Tests pass.

---

### Stage ④ Quality Gate

**Ziel:** Merged Coverage ≥ 80%.

```yaml
quality-gate:
  needs: [python-verify, postgres-verify]
  steps:
    - name: Merge Coverage
      run: |
        coverage combine
        TOTAL=$(coverage report --format=total)
        echo "Coverage: ${TOTAL}%"
        if [ "$TOTAL" -lt 80 ]; then
          echo "FAIL: Coverage ${TOTAL}% < 80% threshold"
          exit 1
        fi
```

**Gate:** Coverage ≥ 80% oder Pipeline blockiert.

---

### Stage ⑤ Deployment Definition

**Ziel:** Sicheres, verifiziertes Docker-Image bauen und pushen.

```yaml
deploy-build:
  needs: quality-gate
  if: github.ref == 'refs/heads/main'
  steps:
    # Pre-Flight: Can we even deploy?
    - name: Pre-Flight Validation
      run: |
        # SSH probe
        ssh -o ConnectTimeout=5 root@88.198.191.108 "echo OK" || {
          echo "FAIL: SSH to server unreachable"; exit 1
        }

    # ADR-089 Invariante 9: Wheel version matches code
    - name: Wheel Freshness Check
      run: |
        for whl in requirements/wheels/*.whl; do
          PKG=$(basename "$whl" | sed 's/-[0-9].*//')
          VERSION=$(basename "$whl" | sed 's/.*-\([0-9][^-]*\)-.*/\1/')
          echo "Wheel: $PKG v$VERSION"
          # Verify wheel content matches source (if source available)
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
          .

    - name: Docker Push
      run: |
        docker push ${{ env.IMAGE }}:${GITHUB_SHA::7}
        docker push ${{ env.IMAGE }}:latest
        echo "Pushed: ${{ env.IMAGE }}:${GITHUB_SHA::7}"
```

**Gate:** Image hat SHA-7 Tag UND latest. Beide gepusht.

---

### Stage ⑥ Deployment Verification

**Ziel:** Nach `docker compose up` verifizieren dass alles läuft.

```yaml
deploy-verify:
  needs: deploy-build
  steps:
    - name: Server Pull + Recreate
      run: |
        ssh root@88.198.191.108 "
          cd ${{ env.SERVER_PATH }} && \
          docker compose -f docker-compose.prod.yml pull && \
          docker compose -f docker-compose.prod.yml up -d --force-recreate
        "

    - name: Wait for Health
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
```

**Gate:** Health 200, Migrations OK, keine kritischen Fehler in Logs.

---

### Stage ⑦ Error Handling + Rollback

**Ziel:** Bei Failure automatisch rollback + benachrichtigen.

```yaml
rollback:
  needs: deploy-verify
  if: failure()
  steps:
    - name: Collect Failure Logs
      run: |
        ssh root@88.198.191.108 \
          "docker logs ${{ env.CONTAINER }} --tail 100" > /tmp/failure_logs.txt

    - name: Rollback to Previous Image
      run: |
        PREV_TAG=$(ssh root@88.198.191.108 \
          "docker inspect ${{ env.CONTAINER }} --format='{{.Config.Image}}'" \
          | grep -oP ':\K[^:]+$')
        echo "Rolling back from $PREV_TAG to previous..."
        ssh root@88.198.191.108 "
          cd ${{ env.SERVER_PATH }} && \
          docker compose -f docker-compose.prod.yml down && \
          docker compose -f docker-compose.prod.yml up -d
        "

    - name: Notify
      run: |
        echo "DEPLOYMENT FAILED for ${{ env.APP_NAME }}"
        echo "Rollback executed. Check /tmp/failure_logs.txt"
        # Future: Slack/Discord webhook notification
```

---

## 3. Per-App Configuration

Jedes Repo definiert seine Pipeline-Variablen in einer `.github/deploy.env`:

```bash
# .github/deploy.env — from registry/repos.yaml
APP_NAME=travel-beat
DOCKERFILE=docker/Dockerfile
IMAGE=ghcr.io/achimdehnert/travel-beat
CONTAINER=travel_beat_web
SERVER_PATH=/opt/travel-beat
PORT=8089
MIGRATE_CMD="python manage.py migrate_schemas --tenant"
MULTI_TENANT=true
```

Source of truth bleibt `platform/registry/repos.yaml`.

---

## 4. Implementierungsprioritäten

| Prio | Stage | Aufwand | Wert | Status |
|------|-------|---------|------|--------|
| 1 | ③ Migration Graph Check | 1h | **Verhindert NodeNotFoundError** | ⏳ |
| 2 | ② Wheel Verification | 1h | **Verhindert stale Wheel deploys** | ⏳ |
| 3 | ⑤ Build + Push mit SHA-Tag | 2h | Rollback-fähige Images | ⏳ |
| 4 | ⑥ Health + Smoke | 2h | Automatische Verification | ⏳ |
| 5 | ① Pre-commit | 30min | Schnelles lokales Feedback | ⏳ |
| 6 | ④ Coverage Gate | 1h | Qualitätssicherung | ⏳ |
| 7 | ⑦ Rollback | 3h | Automatische Fehlerbehandlung | ⏳ |

---

## 5. Lessons Learned (travel-beat 2026-02-26)

Diese Pipeline hätte **alle 4 Fehler** des travel-beat Deployments verhindert:

1. **Stage ③** `AppConfig Label Check` hätte erkannt dass Django die
   Default-AppConfig nutzt statt `BfagentLlmConfig`
2. **Stage ②** `Django System Check` hätte den E304 Reverse Accessor
   Clash erkannt
3. **Stage ⑤** `Wheel Freshness Check` hätte erkannt dass das Wheel
   den alten Code enthält (kein `label` im `__init__.py`)
4. **Stage ⑤** `Docker Build` mit `&&` Chaining hätte verhindert dass
   ein fehlgeschlagener Build trotzdem gepusht wird

---

## 6. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-26 | Achim Dehnert | v1: Initial — 7-Stufen-Pipeline aus ADR-056/057/071/054 + Lessons Learned |
