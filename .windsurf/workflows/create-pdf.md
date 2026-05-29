---
description: Markdown → PDF mit Design-Switcher (meiki | iil | ttz) — Datei oder Ordner
---
# /create-pdf — IIL Print Agent

Erzeugt ein PDF aus einer Markdown-Datei (oder allen `.md` eines Ordners) mit dem passenden Corporate Design.

**Verwendung:**
- `/create-pdf <pfad_zur_md>` — einzelne Datei, Design-Auto-Erkennung
- `/create-pdf <pfad_zum_folder>` — **alle** `.md`-Dateien im Ordner (rekursiv)
- `/create-pdf <pfad> --design iil` — Design explizit angeben

**Verfügbare Designs:** `meiki` (Standard) · `iil` · `ttz`
**SSoT:** `achimdehnert/platform` → `tools/print_agent/` (lokal: `${GITHUB_DIR:-~/github}/platform/tools/print_agent/`)

---

## Schritt 1 — Input-Typ, Datei(en) und Design bestimmen

**Erst prüfen: Datei oder Ordner?**
- `[ -f "$INPUT" ]` → Single-File-Modus (Schritt 2a)
- `[ -d "$INPUT" ]` → Folder-Modus: alle `*.md` rekursiv via `find "$INPUT" -type f -name '*.md'` (Schritt 2b)
- sonst: Fehler an User, mit Suche im aktiven Repo (typisch `docs/`, `docs/adr/`, `docs/04-entscheidungsunterlagen/`)

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

## Schritt 2a — PDF erzeugen (Single-File-Modus)

// turbo
```bash
PRINT_AGENT="${GITHUB_DIR:-$HOME/github}/platform/tools/print_agent/print_agent.py"
MD_PATH="<vollständiger_pfad_zur_md_datei>"
REPO_ROOT="$(git -C "$(dirname "$MD_PATH")" rev-parse --show-toplevel)"
REL_PATH="${MD_PATH#$REPO_ROOT/docs/}"
OUT_DIR="$REPO_ROOT/pdfs/$(dirname "$REL_PATH")"
mkdir -p "$OUT_DIR"
python3 "$PRINT_AGENT" "$MD_PATH" "$OUT_DIR" --design <design>
```

## Schritt 2b — PDFs erzeugen (Folder-Modus)

Schleife über alle `.md` im Ordner (rekursiv), Output-Verzeichnis pro Datei spiegeln.
Fehler einer einzelnen Datei stoppt die Schleife **nicht** — am Ende Zusammenfassung.

// turbo
```bash
PRINT_AGENT="${GITHUB_DIR:-$HOME/github}/platform/tools/print_agent/print_agent.py"
FOLDER="<vollständiger_pfad_zum_folder>"
DESIGN="<design>"
REPO_ROOT="$(git -C "$FOLDER" rev-parse --show-toplevel 2>/dev/null || echo "$FOLDER")"

OK=0; FAIL=0; FAILED_FILES=()
while IFS= read -r -d '' MD_PATH; do
  REL_PATH="${MD_PATH#$REPO_ROOT/docs/}"
  if [ "$REL_PATH" = "$MD_PATH" ]; then
    OUT_DIR="$(dirname "$MD_PATH")"        # MD nicht unter docs/ → daneben ablegen
  else
    OUT_DIR="$REPO_ROOT/pdfs/$(dirname "$REL_PATH")"
  fi
  mkdir -p "$OUT_DIR"
  if python3 "$PRINT_AGENT" "$MD_PATH" "$OUT_DIR" --design "$DESIGN"; then
    OK=$((OK+1))
  else
    FAIL=$((FAIL+1)); FAILED_FILES+=("$MD_PATH")
  fi
done < <(find "$FOLDER" -type f -name '*.md' -print0 | sort -z)

echo "── Zusammenfassung ── erstellt: $OK · fehlgeschlagen: $FAIL"
for f in "${FAILED_FILES[@]}"; do echo "  ❌ $f"; done
```

Der Agent ruft **gpt-4o-mini** auf (~$0.00005/Dokument) für Executive Summary + Keywords.
Fallback: Ohne API-Key wird das PDF ohne LLM-Anreicherung erzeugt.

## Schritt 3 — Ergebnis prüfen

// turbo
```bash
# Single-File-Modus:
ls -lh "$OUT_DIR/<name>.pdf"

# Folder-Modus: alle erzeugten PDFs unter pdfs/ auflisten
find "$REPO_ROOT/pdfs" -type f -name '*.pdf' -newer "$PRINT_AGENT" -printf '%p  %s bytes\n' | sort
```

## Schritt 4 — Ausgabe

**Single-File:**
- ✅ PDF-Pfad: `file://<output_verzeichnis>/<name>.pdf`
- Design, Dateigröße
- Hinweis: MD-Datei bearbeiten → Schritt 2a erneut ausführen

**Folder:**
- ✅ Anzahl erzeugter PDFs, Wurzelpfad (`pdfs/...`)
- ❌ Liste fehlgeschlagener Dateien (falls vorhanden)
- Design, Gesamt-Größe
- Hinweis: Einzelne Datei neu erzeugen → Schritt 2a auf diese Datei
