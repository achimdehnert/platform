---
description: Documentation audit, generation and sync — unified docs across all repos
---

# /session-docu

> Unified Documentation Workflow (ADR-158)
> Analog zu `/ship` (Deploy) und `/session-start` (Kontext), aber für Dokumentation.
> Erzeugt, prüft und synchronisiert Dokumentation über alle Systeme.

**Usage:** `/session-docu [repo|all]`
- Ohne Argument: aktuelles Repo
- `all`: alle Platform-Repos durchlaufen

---

## Phase 0: Scope bestimmen

### 0.1 Repo erkennen

// turbo
```bash
REPO_NAME=$(basename $(git rev-parse --show-toplevel 2>/dev/null) 2>/dev/null || echo "platform")
echo "📦 Target Repo: $REPO_NAME"
git status --short | head -5
```

→ Bei Argument `all`: Loop über alle Repos aus repos.json.
→ Bei einzelnem Repo: nur dieses Repo bearbeiten.

### 0.2 Bestehende Doku-Struktur scannen

// turbo
```bash
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
echo "=== Documentation Structure ==="
echo "--- Top-level docs ---"
for f in README.md CORE_CONTEXT.md AGENT_HANDOVER.md docs/audience.yaml; do
  [ -f "$REPO_ROOT/$f" ] && echo "  ✅ $f" || echo "  ❌ $f (missing)"
done
echo "--- DIATAXIS dirs ---"
for d in docs/tutorials docs/guides docs/reference docs/explanation docs/adr; do
  [ -d "$REPO_ROOT/$d" ] && echo "  ✅ $d/ ($(find $REPO_ROOT/$d -name '*.md' | wc -l) files)" || echo "  ❌ $d/ (missing)"
done
echo "--- Violations ---"
find "$REPO_ROOT/docs/" -name "*.py" ! -name "conf.py" 2>/dev/null | head -5
find "$REPO_ROOT/docs/" -name "*.pdf" -o -name "*.docx" -o -name "*.zip" 2>/dev/null | head -5
```

→ Ergebnis dient als Baseline für den Health Score.

---

## Phase 1: Audit — Docstring-Coverage & DIATAXIS-Compliance

### 1.1 Docstring-Coverage prüfen (kein LLM, rein AST)

Falls `docs-agent` installiert:
```bash
cd $(git rev-parse --show-toplevel)
docs-agent audit . --scope docstrings 2>/dev/null || echo "⚠️ docs-agent nicht installiert — manueller Scan"
```

Falls nicht installiert, manueller Scan via Cascade:
```
Lies die Python-Dateien im apps/ oder src/ Verzeichnis.
Zähle: Klassen, Funktionen, Methoden MIT vs. OHNE Docstring.
Berechne Coverage-Prozent.
```

### 1.2 DIATAXIS-Compliance prüfen

```
Prüfe ob docs/ die DIATAXIS-Quadranten abdeckt:
- tutorials/  → Learning-oriented (Getting Started, Walkthroughs)
- guides/     → Task-oriented (Deployment, Migration, Debugging)
- reference/  → Information-oriented (Models, API, Config) — AI-generiert
- explanation/ oder adr/ → Understanding-oriented (ADRs, Architektur)

Bewertung:
  4/4 Quadranten = ✅ DIATAXIS-compliant
  3/4 = ⚠️ Partial
  ≤2/4 = ❌ Non-compliant
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

### 1.4 Ergebnis zusammenfassen

```
╔══════════════════════════════════════════════╗
║         DOCUMENTATION AUDIT: <repo>          ║
╠══════════════════════════════════════════════╣
║ Docstring Coverage:     63%  (Ziel: ≥60%)   ║
║ DIATAXIS Compliance:    3/4  ⚠️ Partial      ║
║ ADR-046 Violations:     0    ✅              ║
║ Reference-Docs:         stale (14d)  ⚠️      ║
║ audience.yaml:          missing  ❌           ║
║                                              ║
║ Documentation Health Score:  62/100          ║
╚══════════════════════════════════════════════╝
```

---

## Phase 2: Generate — Reference-Docs erzeugen

> Nur wenn `--generate` Flag oder User bestätigt.
> Reference-Docs sind AI-generiert und werden in `docs/reference/` geschrieben.

### 2.1 Models Reference (`docs/reference/models.md`)

```
Für jedes Django-Model im Repo:
1. Lies models.py via AST (oder Read-Tool)
2. Extrahiere: Model-Name, Felder, Typen, Constraints, Meta, Docstring
3. Generiere Markdown-Tabelle:

## ModelName

> Docstring des Models

| Feld | Typ | Beschreibung | Constraints |
|------|-----|--------------|-------------|
| name | CharField(200) | ... | unique |
```

### 2.2 API Reference (`docs/reference/api.md`)

```
Für jede URL-Pattern im Repo:
1. Lies urls.py (alle Apps)
2. Extrahiere: URL-Pattern, View-Name, HTTP-Methoden, Beschreibung
3. Generiere:

## API Endpoints

| URL | View | Methods | Description |
|-----|------|---------|-------------|
| /api/v1/items/ | ItemListView | GET, POST | ... |
```

### 2.3 Config Reference (`docs/reference/config.md`)

```
Für jede Environment-Variable:
1. Lies settings.py + .env.example
2. Extrahiere: Variable, Default, Beschreibung, Required
3. Generiere:

## Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| SECRET_KEY | — | ✅ | Django secret key |
| DATABASE_URL | — | ✅ | PostgreSQL connection |
```

### 2.4 Generierte Docs committen

```bash
cd $(git rev-parse --show-toplevel)
git add docs/reference/
git diff --cached --stat
# User-Bestätigung vor Commit
git commit -m "docs: regenerate reference docs [session-docu $(date +%Y-%m-%d)]"
```

---

## Phase 3: Sync — Cross-System Konsistenz prüfen

### 3.1 ADR Sync: GitHub ↔ Outline

```
mcp3_search_knowledge:
  query: "ADR-"
  collection: null  (alle Collections)
  limit: 50

Vergleiche mit lokalen ADRs in docs/adr/:
- Neue ADRs in GitHub → melde "⚠️ ADR-158 nicht in Outline"
- Veraltete ADRs in Outline → melde "⚠️ ADR-020 in Outline hat alten Status"
```

### 3.2 Outline Runbooks: Vollständigkeit prüfen

```
mcp3_search_knowledge:
  query: "Runbook"
  collection: "Runbooks"
  limit: 20

Prüfe ob kritische Runbooks existieren:
- [ ] Deploy Troubleshooting
- [ ] Database Backup/Restore
- [ ] SSL Certificate Renewal
- [ ] DNS/Cloudflare Config
- [ ] MCP Server Restart
```

### 3.3 dev-hub TechDocs: Sync-Status prüfen

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

→ Melde Repos mit `build_status=FAILED` oder `last_synced > 48h`.

### 3.4 Sync-Report

```
╔══════════════════════════════════════════════╗
║           SYNC STATUS REPORT                 ║
╠══════════════════════════════════════════════╣
║ GitHub ADRs:      157 total, 3 not in Outline║
║ Outline Runbooks: 12 total, 2 missing        ║
║ dev-hub TechDocs: 10/10 repos synced ✅      ║
║ Reference-Docs:   5/18 repos generated       ║
║ audience.yaml:    3/18 repos configured      ║
╚══════════════════════════════════════════════╝
```

---

## Phase 4: Report — Documentation Health Score

### 4.1 Health Score berechnen

```
Score-Formel (gewichtet, 0-100):

README.md vorhanden + >500 Zeichen:        10% ✅/❌
CORE_CONTEXT.md vorhanden:                  10% ✅/❌
docs/adr/ mit ≥1 ADR:                      10% ✅/❌
DIATAXIS-Struktur (≥3 Quadranten):          15% ✅/⚠️/❌
Docstring-Coverage:                         20% (0-100%)
Reference-Docs aktuell (<7 Tage):           15% ✅/❌
audience.yaml konfiguriert:                 10% ✅/❌
Keine Banned Files in docs/:                10% ✅/❌
```

### 4.2 Score in pgvector Memory speichern

```
mcp2_agent_memory_upsert:
  entry_key: "docu-health:<repo>"
  entry_type: context
  title: "Documentation Health: <repo> — Score: XX/100"
  content: "<vollständiger Report>"
  tags: ["documentation", "health-score", "<repo>"]
```

### 4.3 Bei `all`: Aggregierten Report erstellen

```
╔══════════════════════════════════════════════════════╗
║        PLATFORM DOCUMENTATION HEALTH                 ║
╠══════════════════════════════════════════════════════╣
║ Repo              │ Score │ Coverage │ DIATAXIS │ Ref║
║───────────────────┼───────┼──────────┼──────────┼────║
║ platform          │ 82    │ 71%      │ 4/4  ✅  │ ✅ ║
║ risk-hub          │ 68    │ 55%      │ 3/4  ⚠️  │ ❌ ║
║ travel-beat       │ 61    │ 48%      │ 2/4  ❌  │ ❌ ║
║ dev-hub           │ 75    │ 63%      │ 3/4  ⚠️  │ ✅ ║
║ ...               │       │          │          │    ║
║───────────────────┼───────┼──────────┼──────────┼────║
║ AVERAGE           │ 64    │ 52%      │          │    ║
╚══════════════════════════════════════════════════════╝
```

---

## Phase 5: Fix — Automatische Verbesserungen (optional)

> Nur wenn User bestätigt. Nicht automatisch.

### 5.1 Fehlende DIATAXIS-Verzeichnisse anlegen

```bash
mkdir -p docs/{tutorials,guides,reference,explanation}
```

### 5.2 Fehlende audience.yaml erstellen

Generiere eine Standard-`audience.yaml` basierend auf vorhandener Struktur.

### 5.3 CORE_CONTEXT.md generieren (falls fehlend)

```
Nutze get_project_facts() + Code-Analyse um eine CORE_CONTEXT.md zu generieren:
- Tech-Stack
- Architektur-Überblick
- Wichtige Dateipfade
- Abhängigkeiten
```

### 5.4 Ergebnis committen + pushen

```bash
git add docs/ CORE_CONTEXT.md audience.yaml
git commit -m "docs: session-docu improvements [$(date +%Y-%m-%d)]"
# Push nur nach User-Bestätigung
```

---

## Entscheidungsbaum

```
/session-docu aufgerufen
    │
    ├─ Scope = einzelnes Repo oder `all`?
    │   ├─ Einzeln → Phase 0-4 für dieses Repo
    │   └─ All → Loop über alle Repos aus repos.json
    │
    ├─ Phase 1 (Audit) → IMMER ausführen
    │   → Health Score < 50? → ⚠️ User warnen, Fix vorschlagen
    │
    ├─ Phase 2 (Generate) → Nur wenn:
    │   ├─ --generate Flag ODER
    │   ├─ Reference-Docs >7 Tage alt ODER
    │   └─ User bestätigt
    │
    ├─ Phase 3 (Sync) → IMMER ausführen
    │   → Divergenz gefunden? → User informieren
    │
    ├─ Phase 4 (Report) → IMMER ausführen
    │   → Score in pgvector speichern
    │
    └─ Phase 5 (Fix) → Nur wenn User explizit bestätigt
```

---

## Regeln

- **Kein Auto-Commit** ohne User-Bestätigung (außer Reference-Docs mit --generate)
- **Kein Löschen** von bestehenden Docs — nur Ergänzen
- **Outline ist read-only** in diesem Workflow — nur Lesen und Verlinken
- **Reference-Docs haben Header**: `<!-- AUTO-GENERATED by /session-docu — DO NOT EDIT MANUALLY -->`
- **Score-History** in pgvector für Trend-Analyse über Sessions
