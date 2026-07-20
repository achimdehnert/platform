---
description: ADR-Fleet-Audit — Inventar, Cross-Repo-Konsistenz und Optimierungs-Backlog über alle ADR-tragenden Repos
mode: read-only
---

# /adr-fleet-audit — ADR-Analyse & Optimierung über die gesamte Flotte

> **Wann:** Monatlich, vor Governance-Reviews, nach größeren ADR-Wellen oder Repo-Onboardings.
> **Wann NICHT:**
> - Einzelnes Repo / einzelner ADR-Korpus in der Tiefe → `/adr-health` (iil-adrfw-Auditors, Health-Score)
> - Kanonizität EINES Themas klären (Supersession-Kette, Naming-Kollision) → `/adr-curator`
> - Generisches Fleet-Audit (Infra, CI, Deps — nicht ADR-spezifisch) → `/platform-audit`
> - Einzelnen ADR reviewen → `/adr-review`

## Verwendung

```
/adr-fleet-audit [--orgs <org1,org2>] [--skip-remote]
```

| Argument | Beschreibung | Default |
|----------|-------------|---------|
| `--orgs` | Org-Scope für Remote-Abgleich | Auto: Owner aller lokalen Clone-Remotes |
| `--skip-remote` | Nur lokale Clones auditieren (offline/schnell) | aus |

Analyse ist **read-only**. Schreibaktionen (Klasse A, siehe Phase 4) nur in einem
ADR-233-Session-Worktree des Platform-Repos und **nie ohne Freigabe-Block**.

---

## Step 0: Kontext ermitteln (NIEMALS hardcoden)

Alle Werte zur Laufzeit bestimmen — keine Repo-Zahlen, Owner-Namen oder ADR-Nummern
aus dem Gedächtnis oder aus früheren Audit-Reports übernehmen:

```bash
GH_DIR="${GITHUB_DIR:-$HOME/github}"
PLATFORM="$GH_DIR/platform"                      # SSoT laut User-CLAUDE.md
ADR_DIR="$PLATFORM/docs/adr"
NEXT_FREE=$(grep -oE 'Next free ADR number:[^0-9]*[0-9]+' "$ADR_DIR/INDEX.md" | grep -oE '[0-9]+' | head -1)
```

**Org-Scope** (falls `--orgs` nicht gesetzt) aus den Remotes der lokalen Clones ableiten —
das schließt automatisch alle aktiv bearbeiteten Orgs ein und fremde/Legacy-Orgs aus:

```bash
for d in "$GH_DIR"/*/; do git -C "$d" remote get-url origin 2>/dev/null; done \
  | sed -E 's#\.git$##; s#.*[:/]([^/]+)/[^/]+$#\1#' | sort -u
```

---

## Phase 0 — Inventar (find/grep + Remote-Abgleich, NIE aus einem Index)

1. **Lokales Inventar** aller ADR-Dateien (Werkzeug: `tools/adr/adr_inventory.py <out.json>`,
   Auswertung: `tools/adr/adr_analyze.py`); pro Datei extrahieren:
   `repo, datei, adr_nummer, titel, status, date, supersedes, superseded_by, impl`.
   Ablage als JSON im Scratchpad.

   ```bash
   find "$GH_DIR"/*/docs/adr -maxdepth 1 -name "*.md" -not -name "INDEX.md"
   ```

2. **Remote-Abgleich** (Abdeckungsbeweis „ALLE Repos", entfällt bei `--skip-remote`):
   pro Org `gh repo list <org> --limit 300 --json name,isArchived` gegen `ls "$GH_DIR"`
   diffen. Jedes remote-only Repo per Tree-Scan auf ADR-Pfade prüfen:

   ```bash
   gh api "repos/$OWNER/$REPO/git/trees/$(gh api repos/$OWNER/$REPO --jq .default_branch)?recursive=1" \
     --jq '.tree[].path' | grep -iE 'adr'
   ```

   Treffer → Bestand ins Inventar aufnehmen (als `remote-only` markiert); kein Treffer →
   im Report als „ADR-frei bestätigt" listen. **Owner immer aus dem Remote auflösen**
   (`git remote get-url origin`), nie annehmen.

3. **Clone-Frische + Archiv-Status:** für ADR-tragende Repos `git fetch` +
   `git rev-list HEAD..origin/<default-branch> --count` — Nachzügler im Report listen
   (NICHT ungefragt pullen; veraltete Clones relativieren alle Folge-Befunde des Repos).
   Zusätzlich je Clone-Remote `gh api repos/<owner>/<repo> --jq .isArchived` —
   **archivierte Repos im Report und in jedem Befund markieren**: deren ADRs sind
   eingefroren (Remote read-only, kein Push/PR möglich), Fix-Wellen müssen sie
   ausklammern (Lehre 2026-07-04: bfagent war seit 2026-06-03 archiviert, F-1-PR
   scheiterte erst am Push).

4. **Abdeckungsbeweis in den Report:** Inventar-Zeilen == find-Zählung; Remote-Diff == 0
   unerklärte Repos; Zahlen ausschreiben.

## Phase 1 — Health pro Repo (delegieren, nicht duplizieren)

- **Platform-Korpus:** `/adr-health` (deckt Schema, Supersession-Hygiene, Redundanz,
  Konflikte, Staleness via iil-adrfw ab — hier nichts nachbauen).
- **Sub-Repo-Korpora** (parallelisierbar, ein Agent pro Repo): Minimal-Check —
  1. Frontmatter: `status` + `date` + Titel vorhanden? Status im Vokabular des
     iil-adrfw-Schemas: `draft|proposed|accepted|deprecated|superseded|rejected|experimental|void`
     (autoritativ: `iil-adrfw validate docs/adr/` — exit 0 = ok, Suggestions sind non-blocking;
     exit 1 nur bei echten Schema-Fehlern)? Abweichler mit `datei:zeile`.
     ⚠ Bekannte Schema-Lücke (2026-07-04): ADR-211-Klickdummy-Felder (`class`, `conforms_to`,
     `sunset_after`, …) und gelebte Konventionen (`amendments:`, `accepted:`, `ratified:`)
     schlagen an `additionalProperties: false` fehl — solche Treffer sind Schema-Backlog,
     KEINE Repo-Schuld.
  2. Struktur: MADR-Grundgerüst (Context/Decision/Consequences)? Leere Skelette/Template-Reste?
  3. Staleness: `proposed` > 90 Tage; `accepted` ohne Implementierungsspur > 180 Tage.
  4. Doppelte Nummern **innerhalb** des Repos (Lücken sind kein Befund).

## Phase 2 — Cross-Repo-Konsistenz (Barrier: erst nach vollständigem Inventar)

1. **Scope-Verletzungen:** Sub-Repo-ADRs mit cross-cutting Wirkung (≥2 Repos, externe
   Service-Grenze, Security/Data-Sovereignty) gehören laut `~/.claude/policies/adr-threshold.md`
   nach platform → Kandidaten listen, nicht verschieben.
2. **Duplikate über Repos:** gleiches Thema in ≥2 Repos entschieden? Widersprüche?
   Kanonizität nach `/adr-curator`-Methodik bewerten.
3. **Supersession-Ketten fleet-weit:** jedes `superseded` braucht ein existierendes Ziel,
   jedes `supersedes` ein Gegenstück mit passendem Status — gebrochene Ketten mit beiden Enden.
4. **Pinned-/Mirror-Drift:** existiert neben dem Platform-Clone ein Pinned-/Mirror-Checkout
   (z. B. `platform-pinned`), vollständiger `diff -rq` beider `docs/adr/`; Ursache benennen,
   Unprüfbares als **Hypothese** kennzeichnen.
5. **Referenz-Integrität:** `grep -rE 'ADR-[0-9]+' --include='*.md'` in allen Repos →
   Verweise auf platform-ADRs, die fehlen oder superseded sind.

## Phase 3 — Optimierungs-Backlog (jeder Befund genau EINE Klasse)

| Klasse | Bedeutung | Beispiele |
|--------|-----------|-----------|
| **A** | mechanisch, gate-frei — nur in platform | Status-Typos normalisieren, fehlende Frontmatter-Felder, `python3 "$PLATFORM/scripts/gen_adr_index.py"` |
| **B** | inhaltlich, braucht Review | Ketten reparieren, Duplikate mergen, ADR nach platform heben, stale `proposed` → `void`, Clones aktualisieren |
| **C** | Architektur-Entscheidung nötig | Widersprüche zwischen Repos, Pinned-Mechanik |

Sub-Repo-Commits sind **NICHT** Klasse A — jede Änderung außerhalb platform ist mindestens B.

## Phase 4 — Report, Action Board, Freigabe

1. Report → `"$ADR_DIR/reviews/ADR-FLEET-AUDIT-$(date +%F).md"`
   (Inventar-Summary inkl. Remote-Abgleich, Befunde mit Evidenz, Backlog A/B/C).
2. Antwort als **Action Board** (siehe Output-Format).
3. Klasse-A-Fixes: nur nach Nutzer-Go, nur im ADR-233-Session-Worktree
   (`tools/repo-session.sh start`), Commit `chore(adr): normalize frontmatter + regenerate index`,
   **kein Push ohne Freigabe**. Klasse B/C: nur vorschlagen — genau EIN Freigabe-Block am Ende.

---

## Output-Format

```markdown
# ADR-Fleet-Audit — <YYYY-MM-DD>

**Abdeckung:** <N> lokale Repos mit ADRs (<M> Dateien, find-verifiziert) ·
<K> Orgs remote abgeglichen · <R> remote-only Repos geprüft (davon <X> mit ADR-Bestand) ·
<S> Clones hinter origin

| # | Item | Repo | Klasse | Evidenz | Status | Next Step |
|---|------|------|--------|---------|--------|-----------|
| F-1 | <Befund> | <repo> | A/B/C | <datei:zeile bzw. Kommando> | 🟢/🔵/🟡/✅ | <imperativ + Owner du/ich/CI> |

**Verifiziert:** <was geprüft wurde> · **Nicht verifiziert:** <Lücken + billigster Check>

## Freigabe-Block
- [ ] Klasse A ausführen (platform, Session-Worktree, kein Push)
- [ ] <B/C-Items einzeln>
```

`#`-IDs sind über Folge-Turns stabil.

## Anti-Patterns

- ❌ Owner/Org-Namen, Repo-Zahlen oder ADR-Nummern hardcoden oder aus einem früheren Report übernehmen
- ❌ Inventar aus `INDEX.md` oder Gedächtnis ableiten statt aus `find` + `gh repo list`
- ❌ ADR-Dateien löschen/umbenennen oder neue ADR-Nummern vergeben (Nummern werden zur Merge-Zeit allokiert, ADR-228)
- ❌ Sub-Repo-Edits, Pulls, Pushes oder Klonen ohne expliziten Freigabe-Block
- ❌ `INDEX.md` von Hand editieren (nur `scripts/gen_adr_index.py`)
- ❌ Platform-Haupt-Tree anfassen — Klasse-A-Fixes nur im ADR-233-Session-Worktree
- ❌ Befund ohne `datei:zeile`/Kommando-Evidenz; Generalisierung ohne Gegenbeispiel-Check; Unprüfbares ohne Hypothese-Label
- ❌ Neues ADR als „Fix" vorschlagen, wo CHANGELOG/PR genügt (`adr-threshold.md`)

## Changelog

- 2026-07-04 (3): Status-Vokabular auf das echte iil-adrfw-Schema korrigiert (+rejected,
  +experimental); `iil-adrfw validate` als autoritativer Check verankert (Exit-Code-Semantik
  verifiziert); Schema-Lücke ADR-211-Felder dokumentiert; Werkzeuge nach `tools/adr/`
  persistiert (Inventar/Analyse/Frontmatter-Migration, erprobt in F-1/F-1b: 82 ADRs).

- 2026-07-04 (2): Phase 0.3 prüft zusätzlich den Archiv-Status der Clone-Remotes —
  archivierte Repos werden markiert und aus Fix-Wellen ausgeklammert (bfagent-Lücke
  im ersten Lauf: Archivierung fiel erst beim Push auf).

- 2026-07-04: Initial. Fleet-Orchestrator komplementär zu `/adr-health` (Einzel-Korpus-Tiefe)
  und `/platform-audit` (generisch). Entstanden aus manuellem Fleet-Audit-Prompt
  (Session 2026-07-04): Remote-Abgleich achimdehnert+iilgmbh ergab 8 remote-only Repos
  ohne ADRs; Org-Scope daher dynamisch aus Clone-Remotes statt hartkodierter Org-Liste.
