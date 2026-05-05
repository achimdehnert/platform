---
description: Markdown → PDF mit Design-Switcher (meiki | iil | ttz)
---
# /create-pdf — IIL Print Agent

Erzeugt ein PDF aus einer Markdown-Datei mit dem passenden Corporate Design.

**Verwendung:**
- `/create-pdf <pfad_zur_md>` — erkennt Design automatisch aus Dateiname/Pfad
- `/create-pdf <pfad_zur_md> --design iil` — Design explizit angeben

**Verfügbare Designs:** `meiki` (Standard) · `iil` · `ttz`
**SSoT:** `achimdehnert/platform` → `tools/print_agent/` (lokal: `${GITHUB_DIR:-~/github}/platform/tools/print_agent/`)

---

## Schritt 1 — Datei und Design bestimmen

Wenn der User einen vollständigen Pfad angibt: direkt verwenden.
Sonst: Datei im aktiven Repo suchen (typisch `docs/`, `docs/adr/`, `docs/04-entscheidungsunterlagen/`).

**Design-Auto-Erkennung** (wenn nicht explizit angegeben):
- Pfad enthält `ttz-hub` oder `ttz` → `--design iil` (IIL liefert an TTZ)
- Pfad enthält `meiki-hub` oder `meiki` → `--design meiki`
- Dateiname enthält `Angebot` oder `angebot` → `--design iil`
- Sonst → `--design iil`

**Output-Verzeichnis (Spiegel-Logik):**

Die PDF-Ausgabe spiegelt die `docs/`-Struktur in `pdfs/`:
```
docs/02-prozesshandbuch/pilotierung/plan.md
  → pdfs/02-prozesshandbuch/pilotierung/plan.pdf
```

Bestimmung:
1. Relativen Pfad der MD-Datei innerhalb von `docs/` ermitteln
2. `docs/` durch `pdfs/` ersetzen → Output-Verzeichnis
3. `mkdir -p` auf das Output-Verzeichnis

```
MD_PATH  = <vollständiger_pfad_zur_md_datei>
REPO_ROOT = git rev-parse --show-toplevel
REL_PATH  = ${MD_PATH#$REPO_ROOT/docs/}       # z.B. 02-prozesshandbuch/pilotierung/plan.md
OUT_DIR   = $REPO_ROOT/pdfs/$(dirname $REL_PATH)
```

- Wenn MD **nicht** unter `docs/` liegt → Output = Verzeichnis der MD-Datei
- Fallback: `~/pdf-output/`

## Schritt 2 — PDF erzeugen

// turbo
```bash
PRINT_AGENT="${GITHUB_DIR:-$HOME/github}/platform/tools/print_agent/print_agent.py"
REPO_ROOT="$(git -C "$(dirname "<vollständiger_pfad_zur_md_datei>")" rev-parse --show-toplevel)"
REL_PATH="${<vollständiger_pfad_zur_md_datei>#$REPO_ROOT/docs/}"
OUT_DIR="$REPO_ROOT/pdfs/$(dirname "$REL_PATH")"
mkdir -p "$OUT_DIR"
python3 "$PRINT_AGENT" \
  "<vollständiger_pfad_zur_md_datei>" \
  "$OUT_DIR" \
  --design <design>
```

Der Agent ruft **gpt-4o-mini** auf (~$0.00005/Dokument) für Executive Summary + Keywords.
Fallback: Ohne API-Key wird das PDF ohne LLM-Anreicherung erzeugt.

## Schritt 3 — Ergebnis prüfen

// turbo
```bash
ls -lh "$OUT_DIR/<name>.pdf"
```

## Schritt 4 — Ausgabe

Teile dem User mit:
- ✅ PDF-Pfad: `file://<output_verzeichnis>/<name>.pdf`
- Design, Dateigröße
- Hinweis: MD-Datei bearbeiten → Schritt 2 erneut ausführen
