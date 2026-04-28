---
description: project-facts.md aus platform SSoT in Ziel-Repo pushen
---

# /sync-project-facts — SSoT Sync

Liest `platform/.windsurf/project-facts/{repo}.md` und pusht als
`.windsurf/project-facts.md` in das Ziel-Repo via GitHub API.

**Verwendung:** `/sync-project-facts <repo>` (z.B. `meiki-hub`, `travel-beat`)

---

## Schritt 1 — Quelldatei lesen

Lies die SSoT-Datei aus dem platform-Repo:

```
Pfad: /home/devuser/github/platform/.windsurf/project-facts/<repo>.md
```

Falls die Datei nicht existiert: Abbrechen und User informieren — erst anlegen!

## Schritt 2 — Ziel-Repo und Owner bestimmen

Prüfe ob das Repo unter `achimdehnert` oder einer anderen Org liegt:
- meiki-hub → owner: `meiki-lra`
- alle anderen → owner: `achimdehnert`

## Schritt 3 — In Ziel-Repo pushen (GitHub API)

// turbo
Nutze `mcp0_push_files` um die Datei zu pushen:

```
owner: <owner>
repo: <repo>
branch: main
files:
  - path: .windsurf/project-facts.md
    content: <Inhalt aus Schritt 1>
message: "chore: sync project-facts.md from platform SSoT [auto]"
```

## Schritt 4 — Lokal aktualisieren

// turbo
```bash
cp /home/devuser/github/platform/.windsurf/project-facts/<repo>.md \
   /home/devuser/github/<repo>/.windsurf/project-facts.md
```

## Schritt 5 — Bestätigung

Melde dem User:
- ✅ GitHub: `<owner>/<repo>/.windsurf/project-facts.md` aktualisiert
- ✅ Lokal: `/home/devuser/github/<repo>/.windsurf/project-facts.md` aktualisiert
- 📝 SSoT: `platform/.windsurf/project-facts/<repo>.md`
