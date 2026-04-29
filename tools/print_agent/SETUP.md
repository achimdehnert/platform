# print_agent — Repo-Setup Guide

> SSoT: `achimdehnert/platform/tools/print_agent/`
> Lokaler Pfad: `${GITHUB_DIR:-$HOME/github}/platform/tools/print_agent/`

---

## Schnellstart (neues Repo einrichten)

### 1. Pflicht: `.windsurf/workflows/create-pdf.md` anlegen

```markdown
---
description: Markdown → PDF (Design: <DESIGN_KEY>)
---
# /create-pdf

**SSoT:** achimdehnert/platform → tools/print_agent/

## Schritt 1 — Design + Pfad bestimmen
Design: `<DESIGN_KEY>` (fest für dieses Repo, z.B. meiki / iil / ttz)
Output: `<REPO_ROOT>/docs/pdf/`

## Schritt 2 — PDF erzeugen
// turbo
```bash
PRINT_AGENT="${GITHUB_DIR:-$HOME/github}/platform/tools/print_agent/print_agent.py"
python3 "$PRINT_AGENT" \
  "<vollständiger_md_pfad>" \
  "<repo_root>/docs/pdf/" \
  --design <DESIGN_KEY> \
  [--designs <repo_root>/docs/pdf/designs.yaml] \
  [--extra-css <repo_root>/docs/pdf/extra.css]
```

## Schritt 3 — Commit
```bash
git add docs/pdf/<name>.pdf && git commit -m "docs: PDF aktualisiert"
```
```

---

### 2. `.gitignore` anpassen (wenn PDFs versioniert werden sollen)

```gitignore
*.pdf
!docs/pdf/*.pdf
```

---

### 3. `project-facts.md` ergänzen

```markdown
## PDF / Dokumentation
- **PDF_DESIGN**: `meiki`          ← Design-Key (meiki | iil | ttz | custom)
- **PDF_OUTPUT**: `docs/pdf/`      ← Ausgabepfad (relativ)
- **PDF_VERSIONED**: `true`        ← PDFs in Git versionieren?
```

---

## Repo-spezifisches Design (ohne platform-SSoT zu ändern)

### Option A — Nur Farben/Werte überschreiben: `docs/pdf/designs.yaml`

Format identisch zu `print_designs.yaml`. Überschreibt nur die angegebenen Keys:

```yaml
designs:
  meiki:
    primary: "#005A8E"          # Nur Primärfarbe anpassen
    header_left: "LRA Musterstadt · MEiKI"
```

Aufruf:
```bash
python3 "$PRINT_AGENT" input.md docs/pdf/ \
  --design meiki \
  --designs docs/pdf/designs.yaml
```

### Option B — Komplett neues Design (eigener Key)

```yaml
designs:
  musterstadt:
    primary: "#2B4A8C"
    bg_light: "#F0F4FC"
    border: "#BFCCE0"
    border_dark: "#8099CC"
    row_even: "#F0F4FC"
    row_odd: "#FFFFFF"
    gantt_bg: "#E8EDF7"
    flow_s1: "#2B4A8C"
    flow_s2: "#4A6BAA"
    flow_s3: "#6B8CC8"
    header_left: "Landkreis Musterstadt · Pilotprojekt"
    footer_text: "Vertraulich · nur für interne Verwendung"
    meta_template: "meiki"
    llm_context: "Bayerischer Landkreis, Verwaltungsdigitalisierung"
```

Aufruf:
```bash
python3 "$PRINT_AGENT" input.md docs/pdf/ \
  --design musterstadt \
  --designs docs/pdf/designs.yaml
```

### Option C — Nur CSS-Erweiterungen: `docs/pdf/extra.css`

Wird **nach** `base.css` geladen — nur Ergänzungen, kein Override von Basis-Klassen:

```css
/* Repo-spezifisch: Seitenbreite für Anhänge */
.appendix-table { font-size: 7pt; }

/* Eigenes Wasserzeichen */
@page { @bottom-center { content: "ENTWURF — nicht zur Weitergabe"; color: #ccc; } }
```

Aufruf:
```bash
python3 "$PRINT_AGENT" input.md docs/pdf/ \
  --design meiki \
  --extra-css docs/pdf/extra.css
```

---

## Verfügbare Code-Fences

| Fence | DSL-Schlüssel | Verwendung |
|-------|--------------|------------|
| ` ```gantt ` | `Monat \| Sprint \| KW-Start \| KW-Ende` | Zeitpläne |
| ` ```flow ` | `entry/s1/s2/s3/target` | Workflow-Stufen |
| ` ```tree ` | Einrückung + ` -- Kommentar` | Datei-/Paketstruktur |
| ` ```arch ` | `title/row/split/left/right` | Komponentendiagramme |
| ` ```layer ` | `top/bridge/left/right` | Schichtenmodelle |

**Regel:** Kein ASCII-Art in ` ``` ` Blöcken — immer Fence-Typen verwenden.

---

## Frontmatter (pro MD-Dokument)

```markdown
---
stand: 2026-04-29
zielgruppe: IT-Fachkräfte, Lenkungskreis
---
# Titel des Dokuments
```

---

## Hardcoding-Verbote

| ❌ Verboten | ✅ Richtig |
|---|---|
| `color: #003366` in CSS | `color: var(--primary)` |
| `<div class="flow-diagram">` in MD | ` ```flow ` Fence |
| Lokale Kopie von `print_agent.py` editieren | Nur `docs/pdf/designs.yaml` + `docs/pdf/extra.css` |
| `--designs` Pfad hardcoded in Script | Immer via `$GITHUB_DIR` Variable |

---

## Checkliste (vor erstem PDF-Einsatz)

- [ ] `.windsurf/workflows/create-pdf.md` zeigt auf `platform/tools/print_agent/`
- [ ] `project-facts.md` enthält `PDF_DESIGN` + `PDF_OUTPUT`
- [ ] `.gitignore`: `!docs/pdf/*.pdf` (wenn versioniert)
- [ ] Kein ASCII-Art in MD-Quellen
- [ ] Kein HTML-Block (`<div>`) direkt in MD
- [ ] Test: `python3 $PRINT_AGENT <md> docs/pdf/ --design <key>` → Exit 0
