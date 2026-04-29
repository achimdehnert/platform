---
description: Markdown → PDF (Design: iil) — platform Meta-Repo
---
# /create-pdf — IIL Print Agent

Erzeugt ein PDF aus einer Markdown-Datei mit dem IIL Corporate Design.

**SSoT:** `achimdehnert/platform` → `tools/print_agent/` (lokal: `${GITHUB_DIR:-$HOME/github}/platform/tools/print_agent/`)

**Design:** `iil` (platform = IIL Meta-Repo)
**Output:** `docs/pdf/`

---

## Schritt 1 — Datei bestimmen

Wenn der User einen vollständigen Pfad angibt: direkt verwenden.
Sonst: Datei in `docs/` suchen.

## Schritt 2 — PDF erzeugen

// turbo
```bash
PRINT_AGENT="${GITHUB_DIR:-$HOME/github}/platform/tools/print_agent/print_agent.py"
python3 "$PRINT_AGENT" \
  "<vollständiger_pfad_zur_md_datei>" \
  "${GITHUB_DIR:-$HOME/github}/platform/docs/pdf/" \
  --design iil
```

## Schritt 3 — Ergebnis prüfen

// turbo
```bash
ls -lh "${GITHUB_DIR:-$HOME/github}/platform/docs/pdf/"
```

## Schritt 4 — Ausgabe

Teile dem User mit:
- ✅ PDF-Pfad: `docs/pdf/<name>.pdf`
- Design `iil`, Dateigröße
