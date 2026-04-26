---
description: Neues Repo mit .windsurf-Konfiguration ausstatten (Rules, Workflows, project-facts)
---

# /onboarding-new-repo

**Trigger:** Neues Repo wird erstellt und soll in den Platform-Ökosystem integriert werden.

> **Lesson Learned (meiki-docs, 2025):** Nicht jedes Repo ist ein Code-Repo.
> Docs-Repos, Infra-Repos und Packages haben unterschiedliche Bedarf.
> `project-facts.md` ist der einzige File der individuell angepasst werden muss.

---

## Step 1: Repo-Typ bestimmen

| Typ | Kennzeichen | Beispiele |
|-----|-------------|----------|
| **Django App** | `manage.py`, `apps/`, Docker, DB | bfagent, travel-beat, weltenhub |
| **Python Package** | `pyproject.toml`, kein `manage.py` | aifw, promptfw, authoringfw |
| **Docs Repo** | Nur Markdown, kein Python | meiki-docs |
| **Infra Repo** | Scripts, Dockerfiles, kein App-Code | infra-deploy |

---

## Step 2: Rules aus platform kopieren

```bash
GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"
TARGET_REPO="<repo-name>"
SOURCE="$GITHUB_DIR/platform/.windsurf"
TARGET="$GITHUB_DIR/$TARGET_REPO/.windsurf"

mkdir -p "$TARGET/rules" "$TARGET/workflows" "$TARGET/templates"

# Basis-Rules (alle Repos)
for f in platform-principles.md mcp-tools.md reviewer.md; do
  cp "$SOURCE/rules/$f" "$TARGET/rules/$f"
done

# Je nach Typ weitere Rules:
# Django App:       + django-models-views.md, htmx-templates.md, testing.md, docker-deployment.md
# Python Package:   + testing.md, iil-packages.md
# Docs Repo:        nur Basis-Rules genügt
# Infra Repo:       + docker-deployment.md

# Templates (alle Repos)
cp "$SOURCE/templates/ai-task.yaml" "$TARGET/templates/"
cp "$SOURCE/templates/project-facts-template.md" "$TARGET/templates/"
```

---

## Step 3: project-facts.md anpassen (PFLICHT — einzige Individuälanpassung)

```bash
cp "$SOURCE/templates/project-facts-template.md" "$TARGET/rules/project-facts.md"
# Dann editieren:
```

**Pflichtfelder für alle Typen:**
- Repo-Name + GitHub-URL
- Typ (Django App | Python Package | Docs Repo | Infra)
- Branch + Push-Methode

**Zusätzlich für Django Apps:**
- Umgebungen (local/staging/prod Ports + Health URLs)
- Docker-Container-Namen
- DB-Name + DB-User
- Settings-Module
- HTMX-Detection-Methode

**Für Docs-Repos (meiki-docs Pattern):**
- Kein Docker, kein Django, kein `.env`
- ADR-Pfad explizit benennen
- Nächste ADR-Nummer dokumentieren
- Nicht-anwendbare Rules als inaktiv kennzeichnen

---

## Step 4: Workflows kopieren / anpassen

**Code-Repos (Django App, Package):** Alle Workflows 1:1 relevant.
```bash
cp -r "$SOURCE/workflows/" "$TARGET/workflows/"
```

**Nicht-Code-Repos (Docs, Infra):** Workflows als vereinfachte Stubs kopieren
mit Verweis auf `platform/.windsurf/workflows/` für die vollständige Version.

Bei Docs-Repos — angepasste Versionen erstellen für:
- `session-start.md` — ohne Platform-Infrastruktur-Steps
- `session-ende.md` — nur Git-Sync, kein Docker/Server
- `adr.md` — mit repo-spezifischem ADR-Pfad
- `workflow-index.md` — nur relevante Workflows listen

---

## Step 5: Zum GitHub pushen

Option A — via GitHub MCP (bevorzugt bei neuen/privaten Repos):

```
mcp1_push_files(
  owner: "<owner>",
  repo: "<repo-name>",
  branch: "main",
  message: "feat(windsurf): onboarding — add .windsurf rules + workflows from platform",
  files: [
    {path: ".windsurf/rules/project-facts.md",        content: "<angepasst>"},
    {path: ".windsurf/rules/platform-principles.md",  content: "<1:1 kopiert>"},
    {path: ".windsurf/rules/mcp-tools.md",            content: "<1:1 kopiert>"},
    {path: ".windsurf/rules/reviewer.md",             content: "<1:1 kopiert>"},
    {path: ".windsurf/templates/ai-task.yaml",        content: "<1:1 kopiert>"},
    ...  # alle Workflows
  ]
)
```

Option B — lokal via Git:
```bash
cd "$GITHUB_DIR/$TARGET_REPO"
git add .windsurf/
git commit -m "feat(windsurf): onboarding — add .windsurf rules + workflows from platform"
git push
```

---

## Step 6: repo-registry.yaml aktualisieren

Damit `session-start` + `sync-workflows.sh` das neue Repo erkennen:

```bash
# platform/scripts/repo-registry.yaml:
# Neuen Eintrag hinzufügen:
# - name: <repo-name>
#   type: <docs|django|package|infra>
#   owner: <github-owner>
```

```
mcp1_get_file_contents(owner: "achimdehnert", repo: "platform", path: "scripts/repo-registry.yaml")
# Inhalt anpassen + zurückschreiben
```

---

## Step 7: Verifizieren

| # | Check |
|---|-------|
| 1 | `.windsurf/rules/project-facts.md` vorhanden + angepasst |
| 2 | `.windsurf/rules/platform-principles.md` vorhanden |
| 3 | `.windsurf/rules/mcp-tools.md` vorhanden |
| 4 | `.windsurf/rules/reviewer.md` vorhanden |
| 5 | `.windsurf/workflows/workflow-index.md` vorhanden |
| 6 | `.windsurf/workflows/adr.md` vorhanden (falls ADRs geplant) |
| 7 | `.windsurf/templates/ai-task.yaml` vorhanden |
| 8 | `scripts/repo-registry.yaml` aktualisiert |
| 9 | Erster `session-start` in neuem Repo erfolgreich |

---

## Referenz-Implementierungen

| Repo | Typ | Besonderheit |
|------|-----|--------------|
| `meiki-docs` | Docs | Erstes Onboarding außerhalb des Platform-Ökosystems (2025) |
| `bfagent` | Django App | Multi-Agent, Celery, pgvector |
| `travel-beat` | Django App | Multi-Tenancy, Content-Store |
| `aifw` | Python Package | LLM-Router, PyPI-Publikation |

---

## Commit-Message-Konvention

```
feat(windsurf): onboarding — add .windsurf rules + workflows from platform
```
