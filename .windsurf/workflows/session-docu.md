---
description: Documentation audit, generation and sync — unified docs across all repos
---

# /session-docu

> Unified Documentation Workflow (ADR-158)
> Analog zu `/ship` (Deploy) und `/session-start` (Kontext), aber für Dokumentation.
> Review-Fix K-02: --generate ist IMMER --dry-run by default.
> Commit erfolgt nur mit explizitem --commit Flag.

## Verwendung

```
/session-docu [REPO|all] [--generate] [--audit] [--sync] [--commit] [--fail-under SCORE]
```

### Flags

| Flag | Beschreibung | Default |
|------|-------------|---------|
| `REPO` | Repo-Slug (z.B. `risk-hub`) oder `all` für alle Repos | aktuelles Repo |
| `--audit` | Docstring-Coverage + DIATAXIS-Compliance prüfen | always on |
| `--generate` | Reference-Docs generieren (AI-basiert, DRY-RUN) | dry-run |
| `--commit` | Generierte Docs committen (nur nach `--generate` + Review) | off |
| `--sync` | Outline Deep-Links synchronisieren (unidirektional) | off |
| `--fail-under` | Exit 1 wenn Health Score < SCORE | 0 (kein Gate) |

**WICHTIG:** `--generate` ohne `--commit` = Dry-Run. Zeigt was generiert würde, schreibt nichts.
Erst nach manuellem Review: `/session-docu --generate --commit`

---

## Phase 0: Scope bestimmen

### 0.1 Repo erkennen

// turbo
```bash
REPO_NAME=$(basename $(git rev-parse --show-toplevel 2>/dev/null) 2>/dev/null || echo "platform")
echo "Target Repo: $REPO_NAME"
git status --short | head -5
```

### 0.2 Bestehende Doku-Struktur scannen

// turbo
```bash
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
echo "=== Documentation Structure ==="
for f in README.md CORE_CONTEXT.md AGENT_HANDOVER.md docs/audience.yaml; do
  [ -f "$REPO_ROOT/$f" ] && echo "  OK $f" || echo "  MISSING $f"
done
for d in docs/tutorials docs/guides docs/reference docs/explanation docs/adr; do
  [ -d "$REPO_ROOT/$d" ] && echo "  OK $d/ ($(find $REPO_ROOT/$d -name '*.md' | wc -l) files)" || echo "  MISSING $d/"
done
```

---

## Phase 1: Audit (immer)

### 1.1 Health Score berechnen

// turbo
```bash
bash platform/scripts/docu-audit.sh ${REPO_PATH}
```

### 1.2 Audience Navigator Konfiguration prüfen

```
Falls docs-agent installiert:
  docs-agent validate-audience ${REPO_PATH}/docs/audience.yaml

Falls nicht: YAML manuell lesen und gegen Schema prüfen:
  - schema_version: 1 vorhanden?
  - Mindestens 1 Audience definiert?
  - Alle Sources haben type-Feld?
  - Kein AGENT_HANDOVER.md in operator (M-04)?
  - Outline sources nutzen collections[] statt query (H-02)?
```

### 1.3 ADR-046 Violations prüfen

```
Prüfe docs/ gegen ADR-046 Regeln:
- R-02: Keine Binaries in Git (pdf, docx, zip)
- R-03: Build-Output gitignored (_build/, build/)
- R-04: Kein Code in docs/ (außer conf.py)
- R-07: ADR-Dateiname: ADR-{NNN}-{kebab-case}.md
- R-08: Keine Sonderzeichen in Dateinamen
```

**Output:** Health Score (0-100) + Liste offener Findings.

---

## Phase 2: Generate (--generate, DRY-RUN Default)

### 2.1 Reference-Docs generieren

```
Für jedes Django-Model, URL-Pattern und Settings-Variable im Repo:

docs/reference/models.md  — Model-Name, Felder, Typen, Constraints
docs/reference/api.md     — URL-Patterns, Views, HTTP-Methoden
docs/reference/config.md  — Environment-Variablen, Defaults, Required

DRY-RUN: Zeigt Diff gegen bestehende Dateien, schreibt nichts.
```

### 2.2 Review-Checkpoint

```
Generierte Docs (DRY-RUN):
  docs/reference/models.md        [NEU, 847 Zeilen]
  docs/reference/api.md           [GEAENDERT, +23/-5 Zeilen]
  docs/reference/config.md        [UNVERAENDERT — kein Commit noetig]

Ueberprüfe die Aenderungen. Um zu committen: /session-docu --generate --commit
```

---

## Phase 3: Commit (nur mit --commit)

```bash
# Nur wenn --commit explizit gesetzt ist
cd $(git rev-parse --show-toplevel)
git add docs/reference/
git diff --cached --stat
git commit -m "docs: update reference docs via docs-agent [skip ci]"
```

**Commit-Message enthält:**
- Generator-Version + Timestamp
- Welche Dateien geändert wurden
- `[skip ci]` um Docs-Commit-Loop zu vermeiden

---

## Phase 4: Sync (--sync)

### 4.1 Outline Deep-Links aktualisieren

```
KEIN Content-Copy: Nur Link-Sync (unidirektional, Review-Fix K-01)

mcp3_search_knowledge:
  query: "Runbook"
  collection: "Runbooks"
  limit: 20

Prüfe ob kritische Runbooks existieren:
- [ ] Deploy Troubleshooting
- [ ] Database Backup/Restore
- [ ] SSL Certificate Renewal
- [ ] DNS/Cloudflare Config
```

**Was dieser Sync NICHT tut:**
- Kopiert keinen ADR-Inhalt nach Outline (GitHub ist kanonische Quelle)
- Überschreibt keine Outline-Dokumente
- Erstellt keine Outline-Seiten

### 4.2 dev-hub TechDocs: Sync-Status prüfen

```
mcp0_ssh_manage:
  action: exec
  host: 88.198.191.108
  command: "docker exec devhub_web python manage.py shell -c \"
    from apps.techdocs.models import DocSite;
    for s in DocSite.objects.all():
      print(f'{s.slug}: {s.build_status} | last_synced: {s.last_synced} | pages: {s.pages.count()}')
  \""
```

---

## Phase 5: Report

### 5.1 Health Score speichern

```
mcp1_agent_memory(
  operation: "upsert",
  agent: "cascade",
  entry: {
    entry_id: "DOCU-HEALTH-<REPO-UPPERCASE>",
    entry_type: "repo_context",
    agent: "cascade",
    title: "Documentation Health: <repo> — Score: XX/100",
    content: "<vollständiger Report>",
    tags: ["documentation", "health-score", "<repo>"]
  }
)
```

### 5.2 Report anzeigen

```
Documentation Health Report — <repo>
  Health Score:     72/100 (trend seit letztem Scan)
  Docstring-Cov.:   58% (Ziel: >=60%)
  Reference-Docs:   Aktuell (vor 2 Tagen generiert)
  DIATAXIS:         3/4 Quadranten (fehlt: tutorials/)
  Audience YAML:    konfiguriert

  Offene Findings:
  - MEDIUM: tutorials/ fehlt — DIATAXIS unvollstaendig
  - MEDIUM: Docstring-Coverage 58% < 60% Ziel
```

---

## Phase 6: Fix (nur wenn User explizit bestätigt)

### 6.1 Fehlende DIATAXIS-Verzeichnisse anlegen

```bash
mkdir -p docs/{tutorials,guides,reference,explanation}
```

### 6.2 Fehlende audience.yaml erstellen

Generiere eine Standard-`audience.yaml` basierend auf vorhandener Struktur.

### 6.3 CORE_CONTEXT.md generieren (falls fehlend)

```
Nutze get_project_facts() + Code-Analyse um CORE_CONTEXT.md zu generieren:
- Tech-Stack, Architektur-Überblick, Dateipfade, Abhängigkeiten
```

### 6.4 Ergebnis committen

```bash
git add docs/ CORE_CONTEXT.md
git commit -m "docs: session-docu improvements [$(date +%Y-%m-%d)]"
# Push nur nach User-Bestätigung
```

---

## Sync-Richtungen (alle unidirektional, K-01)

| Richtung | Trigger | Kanonische Quelle |
|----------|---------|-------------------|
| GitHub ADRs → dev-hub | Celery hourly | GitHub |
| GitHub docs/ → dev-hub TechDocs | Celery daily | GitHub |
| Outline Runbooks → dev-hub (Links) | `--sync` | Outline |
| Reference-Docs → GitHub | `--generate --commit` | AI-generiert |
| Error-Patterns → Outline Lessons | `/session-ende` | pgvector |

**Grundregel: KEINE bidirektionalen Syncs. Jede Info hat genau eine Quelle.**

---

## Regeln

- **`--generate` = Dry-Run Default** — Commit nur mit explizitem `--commit` (K-02)
- **Kein Auto-Commit** ohne User-Bestätigung
- **Kein Löschen** von bestehenden Docs — nur Ergänzen
- **Outline ist read-only** — nur Lesen und Deep-Linking (K-01)
- **Reference-Docs haben Header**: `<!-- AUTO-GENERATED by /session-docu — DO NOT EDIT MANUALLY -->`
- **Score-History** in pgvector für Trend-Analyse über Sessions
