---
description: Markdown → PDF mit Profil-Switcher (iil-extern | db-hybrid | db-intern) oder LEGACY-Design (meiki | iil | ttz | db)
---
# /create-pdf — IIL Print Agent

Erzeugt PDFs aus Markdown mit Profil-aware Corporate Design.

**Verwendung:**
- `/create-pdf <pfad>` — Auto-Erkennung
- `/create-pdf <pfad> --profile db-intern` — Profile explizit (empfohlen)
- `/create-pdf <pfad> --design iil` — LEGACY-Pfad

**Verfügbare Profile (empfohlen):** `iil-extern`, `db-hybrid`, `db-intern`
**LEGACY-Designs (bleiben funktional):** `meiki`, `iil`, `ttz`, `db`

**SSoT:**
- Render-Engine: `achimdehnert/platform` → `tools/print_agent/`
- Profile + Assets: `achimdehnert/design-hub` (private) → `profiles/`, `assets/`, `templates/`

> ⚠ **Lizenz-Constraints (siehe `design-hub/LICENSE_NOTES.md`):**
> - `db-intern`: volle DB-CI (DBNeoScreen + DB-Logo) — **nur** für DB-interne
>   Dokumente im aktiven Auftragsverhältnis IIL ↔ DB
> - `db-hybrid`: DB-Logo erlaubt (Adressat-Marker), **keine** DB-Type — für
>   Übergabe-Dokumente IIL → DB
> - `iil-extern`: **keine** DB-Assets — Standard für externe Kommunikation

---

## Schritt 1 — Input + Profile bestimmen

**Erst prüfen: Datei oder Ordner?**
- `[ -f "$INPUT" ]` → Single-File-Modus (Schritt 2a)
- `[ -d "$INPUT" ]` → Folder-Modus: alle `*.md` rekursiv (Schritt 2b)
- sonst: Fehler an User

### Profile-Auto-Erkennung (neue Logik — bevorzugt):

| Kontext | Empfohlenes Profile |
|---|---|
| Dateiname enthält `Angebot`/`angebot` | `iil-extern` (extern, immer IIL-CD) |
| Pfad enthält `bahn-hub` und Datei ist NICHT für Übergabe | `db-intern` (volle DB-CI) |
| Pfad enthält `bahn-hub` und Dateiname enthält `uebergabe`/`handover`/`abschluss` | `db-hybrid` |
| Pfad enthält `ttz-hub`, `meiki-hub`, `nl2iot-hub` | `iil-extern` |
| Sonst | `iil-extern` |

### LEGACY-Design-Erkennung (fallback wenn `--design` gesetzt):

- `bahn-hub` → `db`
- `ttz-hub`/`ttz` → `iil` (IIL liefert an TTZ)
- `meiki-hub`/`meiki` → `meiki`
- Sonst → `iil`

### Output-Verzeichnis (Spiegel-Logik):

`docs/` → `pdfs/`:
```
docs/02-prozesshandbuch/pilotierung/plan.md
  → pdfs/02-prozesshandbuch/pilotierung/plan.pdf
```

```
MD_PATH  = <vollständiger_pfad_zur_md_datei>
REPO_ROOT = git rev-parse --show-toplevel
REL_PATH  = ${MD_PATH#$REPO_ROOT/docs/}
OUT_DIR   = $REPO_ROOT/pdfs/$(dirname $REL_PATH)
```

- MD **nicht** unter `docs/` → Output = Verzeichnis der MD-Datei
- Fallback: `~/pdf-output/`

---

## Schritt 2a — Single-File (Profile-Mode bevorzugt)

// turbo
```bash
PRINT_AGENT="${GITHUB_DIR:-$HOME/github}/platform/tools/print_agent/print_agent.py"
MD_PATH="<vollständiger_pfad_zur_md_datei>"
REPO_ROOT="$(git -C "$(dirname "$MD_PATH")" rev-parse --show-toplevel)"
REL_PATH="${MD_PATH#$REPO_ROOT/docs/}"
OUT_DIR="$REPO_ROOT/pdfs/$(dirname "$REL_PATH")"
mkdir -p "$OUT_DIR"

# Bevorzugt: --profile (mit Lizenz-Compliance-Check)
python3 "$PRINT_AGENT" "$MD_PATH" "$OUT_DIR" --profile <profile>

# LEGACY-Fallback (nur wenn --design explizit angegeben):
# python3 "$PRINT_AGENT" "$MD_PATH" "$OUT_DIR" --design <design>
```

---

## Schritt 2b — Folder-Modus (rekursiv)

Schleife über alle `.md` im Ordner. Fehler einer Datei stoppt nicht.

// turbo
```bash
PRINT_AGENT="${GITHUB_DIR:-$HOME/github}/platform/tools/print_agent/print_agent.py"
FOLDER="<vollständiger_pfad_zum_folder>"
PROFILE="<profile>"   # iil-extern | db-hybrid | db-intern
REPO_ROOT="$(git -C "$FOLDER" rev-parse --show-toplevel 2>/dev/null || echo "$FOLDER")"

OK=0; FAIL=0; FAILED_FILES=()
while IFS= read -r -d '' MD_PATH; do
  REL_PATH="${MD_PATH#$REPO_ROOT/docs/}"
  if [ "$REL_PATH" = "$MD_PATH" ]; then
    OUT_DIR="$(dirname "$MD_PATH")"
  else
    OUT_DIR="$REPO_ROOT/pdfs/$(dirname "$REL_PATH")"
  fi
  mkdir -p "$OUT_DIR"
  if python3 "$PRINT_AGENT" "$MD_PATH" "$OUT_DIR" --profile "$PROFILE"; then
    OK=$((OK+1))
  else
    FAIL=$((FAIL+1)); FAILED_FILES+=("$MD_PATH")
  fi
done < <(find "$FOLDER" -type f -name '*.md' -print0 | sort -z)

echo "── Zusammenfassung ── erstellt: $OK · fehlgeschlagen: $FAIL · Profile: $PROFILE"
for f in "${FAILED_FILES[@]}"; do echo "  ❌ $f"; done
```

Der Agent ruft Cerebras (Default) oder Groq (Fallback) für Executive Summary + Keywords auf.
Fallback ohne API-Key: PDF ohne LLM-Anreicherung.

---

## Schritt 3 — Ergebnis prüfen

// turbo
```bash
ls -lh "$OUT_DIR/<name>.pdf"
find "$REPO_ROOT/pdfs" -type f -name '*.pdf' -newer "$PRINT_AGENT" -printf '%p  %s bytes\n' | sort
```

---

## Schritt 4 — Ausgabe

**Single-File:**
- ✅ PDF-Pfad: `file://<output_verzeichnis>/<name>.pdf`
- Profile, Dateigröße, Lizenz-Status (allowed_assets-Hinweis)
- Hinweis: bei Profile-Wechsel → Schritt 2a erneut

**Folder:**
- ✅ Anzahl PDFs, Wurzelpfad, Profile
- ❌ Liste fehlgeschlagener Dateien
- Hinweis: einzelne Datei neu → Schritt 2a

---

## Lizenz-Compliance (automatisch durch `--profile`)

Wenn `--profile X` gesetzt ist, **prüft der Renderer automatisch**:
- `allowed_assets`-Map aus `design-hub/profiles/X.yaml`
- Vor jedem Asset-Pfad-Lookup wird der Bucket (`assets/db/`, `assets/iil/`, `assets/shared/`) gegen die Map abgeglichen
- Bei Verstoß: `AssertionError` mit `LICENSE_NOTES.md`-Verweis — kein PDF wird erzeugt

Beim LEGACY-`--design`-Pfad gibt es **keinen** Compliance-Check.
→ Aus diesem Grund: **`--profile` ist der empfohlene Pfad** für alle
neuen Aufrufe.

---

## Migration LEGACY → Profile

| Alt (`--design`) | Neu (`--profile`) | Wann |
|---|---|---|
| `--design iil` (ttz/meiki-Empfänger) | `--profile iil-extern` | sofort |
| `--design db` (intern, bahn-hub) | `--profile db-intern` | Auftragsverhältnis aktiv |
| `--design db` (Übergabe an DB) | `--profile db-hybrid` | bei Übergabe-Doku |
| `--design meiki` (Lenkungskreis) | `--profile iil-extern` (interim) | bis meiki-extern-Profile da |
| `--design ttz` | `--profile iil-extern` (interim) | bis ttz-extern-Profile da |

---

## Changelog

- 2026-05-26: `--profile` als bevorzugte API. Lizenz-Compliance-Check eingebaut. design-hub als SSoT für Profile+Assets+Templates.
- (älter): nur `--design` mit print_designs.yaml in platform/tools/print_agent/.
