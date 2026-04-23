---
description: Generate reference docs (models, api, config) for the active workspace repo
---

# /docu-repo-active — Reference-Docs für aktuelles Repo generieren

Generiert `docs/reference/models.md`, `api.md` und `config.md` für das Repo
des aktuellen Workspaces. Nutzt AST-Analyse (kein Django-Import nötig).

## Schritte

### 1. Repo erkennen

Ermittle das Git-Root des aktuellen Workspaces:

// turbo
```bash
git -C "$PWD" rev-parse --show-toplevel
```

Merke dir den Pfad als `REPO_PATH` und den Ordnernamen als `REPO_NAME`.

### 2. Vorschau (Dry Run)

Zeige welche Dateien sich ändern würden:

```bash
cd ${GITHUB_DIR:-$HOME/github}/platform && python -m docs_agent.cli reference "$REPO_PATH" --dry-run
```

Falls `docs_agent` nicht direkt aufrufbar ist, nutze den Pfad:

```bash
PYTHONPATH=${GITHUB_DIR:-$HOME/github}/platform/packages/docs-agent/src python -m docs_agent.cli reference "$REPO_PATH" --dry-run
```

### 3. User-Bestätigung

Frage den User:
- "Sollen die Reference-Docs geschrieben werden?" (--commit)
- Zeige die Zusammenfassung: wie viele Models, Endpoints, Settings gefunden

### 4. Schreiben (wenn bestätigt)

```bash
PYTHONPATH=${GITHUB_DIR:-$HOME/github}/platform/packages/docs-agent/src python -m docs_agent.cli reference "$REPO_PATH" --commit
```

### 5. Git Status prüfen

// turbo
```bash
git -C "$REPO_PATH" status --short docs/reference/
```

### 6. Optional: Commit

Falls Änderungen vorhanden, frage ob committed werden soll:

```bash
git -C "$REPO_PATH" add docs/reference/ && git -C "$REPO_PATH" commit -m "docs: update reference docs (models, api, config)"
```

## Hinweise

- Erstellt bis zu 3 Dateien unter `docs/reference/`: `models.md`, `api.md`, `config.md`
- `git_utils` prüft Idempotenz: nur bei echten Änderungen wird geschrieben
- Alle Dateien tragen `<!-- AUTO-GENERATED -->` Header — nicht manuell editieren
- Funktioniert für Django-Projekte (apps/) und Python-Packages (src/)
