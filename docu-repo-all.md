---
description: Generate reference docs (models, api, config) for ALL repos under ~/github
---

# /docu-repo-all — Reference-Docs für ALLE Repos generieren

Batch-Generierung von `docs/reference/models.md`, `api.md` und `config.md`
für alle Python/Django-Repos. Nutzt `registry/repos.yaml` als Source of Truth,
Fallback auf Directory-Scan.

## Schritte

### 1. Vorschau (Dry Run)

Zeige welche Repos betroffen wären und was sich ändern würde:

```bash
PYTHONPATH=/home/devuser/github/platform/packages/docs-agent/src python -m docs_agent.cli reference-all /home/devuser/github --dry-run
```

### 2. Ergebnis-Tabelle auswerten

Der Befehl zeigt eine Rich-Tabelle mit:
- Repo-Name, Anzahl Models, Endpoints, Settings
- Files Changed pro Repo
- Status (updated / up to date / ERROR)

Fasse das Ergebnis für den User zusammen:
- Wie viele Repos gescannt
- Wie viele hätten Änderungen
- Etwaige Errors

### 3. User-Bestätigung

Frage den User:
- "Sollen die Reference-Docs für alle N Repos geschrieben werden?"
- Optional: "--skip <repos>" oder "--only-django" anbieten

### 4. Schreiben (wenn bestätigt)

```bash
PYTHONPATH=/home/devuser/github/platform/packages/docs-agent/src python -m docs_agent.cli reference-all /home/devuser/github --commit
```

### 5. Varianten anbieten

Falls der User nicht alles will, Optionen zeigen:

**Nur Django-Projekte (mit apps/ oder manage.py):**
```bash
PYTHONPATH=/home/devuser/github/platform/packages/docs-agent/src python -m docs_agent.cli reference-all /home/devuser/github --only-django --commit
```

**Bestimmte Repos überspringen:**
```bash
PYTHONPATH=/home/devuser/github/platform/packages/docs-agent/src python -m docs_agent.cli reference-all /home/devuser/github --skip odoo-hub,testkit --commit
```

**JSON-Output (für CI/Scripting):**
```bash
PYTHONPATH=/home/devuser/github/platform/packages/docs-agent/src python -m docs_agent.cli reference-all /home/devuser/github --output json
```

### 6. Git Status prüfen

// turbo
```bash
cd /home/devuser/github && for d in */docs/reference; do repo=$(dirname $(dirname "$d")); changes=$(git -C "$repo" status --short docs/reference/ 2>/dev/null); [ -n "$changes" ] && echo "=== $repo ===" && echo "$changes"; done
```

### 7. Optional: Batch-Commit

Falls gewünscht, alle Repos mit Änderungen committen:

```bash
cd /home/devuser/github && for d in */docs/reference; do repo=$(dirname $(dirname "$d")); changes=$(git -C "$repo" status --short docs/reference/ 2>/dev/null); if [ -n "$changes" ]; then git -C "$repo" add docs/reference/ && git -C "$repo" commit -m "docs: update reference docs (models, api, config)"; echo "Committed: $repo"; fi; done
```

### 8. Optional: Batch-Push

```bash
cd /home/devuser/github && for d in */docs/reference; do repo=$(dirname $(dirname "$d")); if git -C "$repo" log origin/main..HEAD --oneline 2>/dev/null | grep -q "reference docs"; then git -C "$repo" push origin main && echo "Pushed: $repo"; fi; done
```

## Repo-Erkennung

1. **Primär**: `platform/registry/repos.yaml` (Single Source of Truth)
2. **Fallback**: Alle Unterordner von `${GITHUB_DIR:-$HOME/github}/` mit Python-Inhalten
3. **Filter**: Repos ohne `*.py`, `pyproject.toml`, `apps/` oder `src/` werden übersprungen
4. **`--only-django`**: Nur Repos mit `apps/` oder `manage.py`

## Hinweise

- Alle generierten Dateien tragen `<!-- AUTO-GENERATED -->` Header
- `git_utils` sorgt für Idempotenz — nur echte Änderungen werden geschrieben
- Bei ~33 Repos dauert der Scan ca. 10-30 Sekunden (reine AST-Analyse)
- Kein Django-Import nötig — funktioniert ohne laufenden Server
