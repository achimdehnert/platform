---
description: Kompletter Test-Run für ein Repo — Lint, Unit, Integration, Smoke, Hardcoding
---

# /teste-repo — Vollständiger Test-Run

Testet ein Repo komplett:
1. Lint (ruff)
2. Django System Check (manage.py check)
3. Unit + Integration Tests (pytest)
4. Smoke Test (alle Views HTTP 200/302)
5. Hardcoding Guard (check_hardcoded_urls.py)

**Aufruf:**
- `/teste-repo` → aktives Repo im Workspace
- `/teste-repo xyz` → Repo `xyz` unter `$GITHUB_DIR`

---

## Schritt 0: Repo ermitteln

Bestimme `REPO_NAME` und `REPO_DIR`:

```python
import os
from pathlib import Path

# Aus Slash-Command-Argument oder aktivem Workspace ableiten
repo_name = "<REPO_NAME_ODER_LEER>"  # Cascades aktives Repo wenn leer

github_dir = Path(os.environ.get("GITHUB_DIR", Path.home() / "github"))
repo_dir = github_dir / repo_name

print(f"Teste: {repo_name}")
print(f"Pfad:  {repo_dir}")
print(f"Existiert: {repo_dir.exists()}")
```

---

## Schritt 1: Lint — ruff

// turbo
```bash
set -euo pipefail
REPO_DIR="${GITHUB_DIR:-$HOME/github}/${1:-$(basename $PWD)}"
echo "=== LINT: $REPO_DIR ==="
cd "$REPO_DIR"
if [ -f ".venv/bin/ruff" ]; then
  .venv/bin/ruff check . --output-format=concise 2>&1 | tail -20
elif command -v ruff &>/dev/null; then
  ruff check . --output-format=concise 2>&1 | tail -20
else
  echo "ruff nicht gefunden — überspringe Lint"
fi
echo "=== LINT DONE ==="
```

---

## Schritt 2: Django System Check

// turbo
```bash
set -euo pipefail
REPO_DIR="${GITHUB_DIR:-$HOME/github}/${1:-$(basename $PWD)}"
cd "$REPO_DIR"

if [ ! -f "manage.py" ] && [ ! -f "src/manage.py" ]; then
  echo "Kein manage.py — kein Django-Repo, System Check übersprungen"
  exit 0
fi

MANAGE="python manage.py"
[ -f "src/manage.py" ] && MANAGE="python src/manage.py"
[ -f ".venv/bin/python" ] && MANAGE=".venv/bin/$MANAGE"

echo "=== DJANGO CHECK ==="
USE_POSTGRES=0 SECRET_KEY=test-ci $MANAGE check --fail-level ERROR 2>&1
echo "=== DJANGO CHECK DONE ==="
```

---

## Schritt 3: Tests — pytest (Unit + Integration + Smoke)

// turbo
```bash
set -euo pipefail
REPO_DIR="${GITHUB_DIR:-$HOME/github}/${1:-$(basename $PWD)}"
cd "$REPO_DIR"

if [ ! -d "tests" ]; then
  echo "Kein tests/-Verzeichnis — Test-Scaffold fehlt noch."
  echo "Fix: gh workflow run scaffold-tests.yml -f repo_name=$(basename $REPO_DIR)"
  exit 0
fi

PYTEST=".venv/bin/pytest"
[ ! -f "$PYTEST" ] && PYTEST="pytest"

echo "=== PYTEST ==="
USE_POSTGRES=0 SECRET_KEY=test-ci \
  $PYTEST tests/ \
    -v \
    --tb=short \
    --no-header \
    -q \
    --co -q 2>/dev/null | head -5  # Zeige zuerst was gefunden wird

USE_POSTGRES=0 SECRET_KEY=test-ci \
  $PYTEST tests/ \
    -v \
    --tb=short \
    --no-header \
    --cov \
    --cov-report=term-missing:skip-covered \
    -x \
    2>&1 | tail -40
echo "=== PYTEST DONE ==="
```

---

## Schritt 4: Hardcoding Guard

// turbo
```bash
set -euo pipefail
REPO_DIR="${GITHUB_DIR:-$HOME/github}/${1:-$(basename $PWD)}"
PLATFORM_DIR="${GITHUB_DIR:-$HOME/github}/platform"
[ -d "${HOME}/CascadeProjects/platform" ] && PLATFORM_DIR="${HOME}/CascadeProjects/platform"

echo "=== HARDCODING GUARD ==="
python3 "$PLATFORM_DIR/scripts/check_hardcoded_urls.py" \
  "$REPO_DIR" \
  --category VERMEIDBAR \
  --summary \
  2>&1
echo "=== HARDCODING GUARD DONE ==="
```

---

## Schritt 5: Zusammenfassung

Cascade fasst die Ergebnisse zusammen:

```text
Teste-Repo Report: <repo_name>
================================
Lint:             ✅ / ⚠️ N Warnings / ❌ N Errors
Django Check:     ✅ / ❌ Fehler
Tests:            ✅ N passed / ⚠️ N skipped / ❌ N failed
Coverage:         XX%
Hardcoding:       ✅ 0 Violations / ⚠️ N Violations (Budget: M)

Nächste Schritte:
  - [nur wenn Tests fehlen]: gh workflow run scaffold-tests.yml -f repo_name=<name>
  - [nur wenn Coverage < 80%]: Unit-Tests ergänzen
  - [nur wenn Violations > 0]: Hardcoded Werte fixen
```
