---
description: Kompletter Test-Run für ein Repo — Lint, Django Check, Migration, pytest, Hardcoding
---

# /teste-repo — Vollständiger Test-Run

**Aufruf:**
- `/teste-repo` → aktives Repo im Workspace (Cascade ermittelt aus Kontext)
- `/teste-repo xyz` → explizites Repo `xyz`

**Was geprüft wird:**
1. Repo-Validierung
2. Lint (ruff)
3. Django System Check (`manage.py check`)
4. Migration Check (`manage.py migrate --check`)
5. Test-Dependencies installieren (`requirements-test.txt`)
6. pytest: Unit + Integration + Smoke + Coverage
7. Hardcoding Guard (`check_hardcoded_urls.py`)

Alle Schritte in einem einzigen Python-Script — kein Zustand zwischen Shell-Blöcken,
kein `$1`-Problem, keine Silent-Fails.

---

## Schritt 0: Repo-Pfad bestimmen

**Cascade: Ermittle REPO_ARG jetzt:**
- Slash-Command mit Argument (`/teste-repo coach-hub`) → REPO_ARG = `coach-hub`
- Slash-Command ohne Argument (`/teste-repo`) → REPO_ARG = Name des aktiven Workspace-Repos
- Absoluter Pfad möglich: `/teste-repo /home/adehnert/CascadeProjects/coach-hub`

Setze REPO_ARG in Schritt 1 ein.

---

## Schritt 1: Test-Run starten

// turbo
```bash
set -euo pipefail
PLATFORM_DIR="${GITHUB_DIR:-$HOME/CascadeProjects}/platform"
[ -d "$HOME/CascadeProjects/platform" ] && PLATFORM_DIR="$HOME/CascadeProjects/platform"

python3 "$PLATFORM_DIR/scripts/teste_repo.py" "<REPO_ARG>"
```

> Cascade: Ersetze `<REPO_ARG>` mit dem in Schritt 0 ermittelten Wert
> (Name relativ zu `$GITHUB_DIR` oder absoluter Pfad).

---

## Was das Script prüft

| Schritt | Verhalten bei Fehler |
|---------|---------------------|
| Repo-Validierung | FAIL — bricht ab |
| Lint (ruff) | FAIL — zeigt alle Probleme |
| Django Check | FAIL — zeigt Error-Level Findings |
| Migration Check | WARN bei SQLite, FAIL bei ausstehenden Migrationen |
| Test-Dependencies | FAIL wenn `pip install` schlägt fehl |
| pytest | WARN wenn kein `tests/`-Verzeichnis + zeigt Scaffold-Fix-Befehl |
| Hardcoding Guard | WARN bei Violations (kein FAIL — Budget-basiert) |

Exit-Code: `0` = alles OK oder nur WARNs · `1` = mindestens ein FAIL
