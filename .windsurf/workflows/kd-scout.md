---
description: Codebase analysieren, KD-Kandidaten aus Routen/UCs ableiten, je Flow brownfield/greenfield entscheiden — read-only Scout, Hand-off an /klickdummy (KONZ-008)
mode: read-only
---

# /kd-scout — Klickdummy-Discovery + brownfield/greenfield-Entscheidung

> **Wann:** Vor dem ersten Klickdummy in einem Repo (oder vor einer neuen KD-Welle):
> „Welche Flows lohnen einen KD, und ist das brownfield oder greenfield?" Liefert eine
> belegte Flow-Landkarte + Entscheidung + Zuschnitt, dann Hand-off.
> **Wann NICHT:** Du weißt schon *welchen* KD du baust → direkt `/klickdummy` (write, Scaffold).
> Suche ob ein KD schon existiert → `/klickdummy-search` (Cross-Repo). Reines UX-Refactor
> einer bestehenden App ohne KD → `/repo-ux-opt` Modus A. Dieser Skill **baut nichts** — er
> entscheidet und übergibt.

## Verwendung

```
/kd-scout [<repo>] [--flow <freitext>] [--limit <n>]
```

| Argument | Pflicht | Default | Bedeutung |
|---|---|---|---|
| `<repo>` | nein | aktuelles Repo (Git-Root) | Ziel-Repo (Slug), z. B. `travel-beat` |
| `--flow` | nein | (alle) | auf eine User-Journey / einen Bereich fokussieren |
| `--limit` | nein | `4` | max. Anzahl KD-Kandidaten im Report |

## Step 0: Repo-Kontext aus project-facts.md (PFLICHT — kein Hardcoding)

Aus `.windsurf/rules/project-facts.md` (always_on) des Ziel-Repos lesen — **nichts raten**:

```
- REPO_OWNER / REPO_NAME
- TYPE            (django | fastapi | node | static | ...)
- HTMX_DETECTION  (request.htmx | request.headers.get("HX-Request") == "true" | none)
- LOCAL_APPS      (Apps-/Modul-Liste)
- PROD_URL / PORT
```

Fehlt die Datei → `python3 $GITHUB_DIR/platform/scripts/gen_project_facts.py --repo <repo>`
(oder lokal `.windsurf/rules/project-facts.md` lesen). Kein project-facts ⇒ Felder mit
`[TODO: project-facts fehlt]` markieren, nicht weglassen.

## Step 1: Ist-Zustand erheben (read-only, belegt)

Jede Aussage muss einen Datei-/Routen-Beleg tragen (Evidenz-Disziplin):

1. **Routen/Screens** — *alle* Route-Definitionsstellen finden, nicht nur die offensichtliche:
   ```
   find <repo> -name urls.py            # Django
   grep -rnE "path\(|re_path\(|@router|app\.(get|post)" <repo>/<apps>
   ```
   HTMX-/Fragment-Routen sind **Teil-Screens** — mit aufnehmen (`*_fragment`, Partials).
2. **Domäne** — Kern-Models/Datenstrukturen je App (`grep -E "^class .*Model" .../models*.py`).
3. **Personas/Rollen** — Auth-Rollen, Permission-Checks, Tenant-/Plan-Gating.
4. **Use Cases** — `docs/use-cases/`, `UC-NNN`, `screens[].use_cases[]` falls vorhanden.
5. **Bestehende KDs** — `klickdummy/`-Pfad, Spec-YAML/`story.yaml`, `?demo=`, genesor/lineage-Refs.
   Fund ⇒ Kandidat ist **erweitern**, nicht neu droppen.

**Output Step 1:** Landkarte `Flow → {Route existiert?} → {Persona} → {UC-Bezug}`.

## Step 2: Brownfield/Greenfield je Flow (billigster Check zuerst)

Entscheidungs-Signal = **existiert für den Ziel-Flow schon eine implementierte Route/View?**

| Signal | Entscheidung | Vorgehen | Typisches I2-Pattern |
|---|---|---|---|
| Route + View existieren, Flow läuft | **BROWNFIELD** | Spec **aus dem Code** extrahieren (URL-Parser + View/Template) → Spec = SoR → Off-Ramp via Parity gegen echte App (Renderer #2) | `spec-demo` / `stub-demo` (realer Pfad) |
| Flow ist net-new, keine Route | **GREENFIELD** | Spec **spec-first aus Use Cases** → KD als Frühvalidierung → Spec bleibt SoR | `mock` / `stub-demo` |
| Journey teils vorhanden | **GEMISCHT** | ADR-211 I3 Phase B: **je Screen** entscheiden, in **einem** KD | je Screen |

Je Kandidat: gewählte Klasse + **1-Satz-Begründung mit Beleg** + deklariertes I2-Pattern.

## Step 3: Zuschnitt + Tooling-Gap-Check

- **Zuschnitt:** ein KD pro kohärenter User-Journey / UC-Cluster; auf `--limit` begrenzen,
  Anzahl begründen. Anker-KD = die Produkt-Spine (README/Wertkern) markieren.
- **Tooling-Gap:** hat das Repo `iil-klickdummy` + `make klickdummy-i1|i2|i3`? Fehlt es,
  ist **Onboarding Teil der Bauaufgabe** — im Report explizit als Vorbedingung ausweisen.
- **Drift-Schutz:** Verdacht auf existierendes Konzept → im Report auf `/klickdummy-search`
  verweisen (nicht selbst suchen; das ist ein eigener Skill).

## Step 3.5: KD-Referenz auflösen (Spec/Lokal/GitHub/iil.pet)

Pro Kandidat/bestehendem KD **vier feste Felder** auflösen — nie weglassen. Nicht auflösbar
⇒ `—` **mit 1-Wort-Grund**, nicht stillschweigend leer lassen (Lücken sollen auffallen, s. Retro
2026-07-06 zur KD-Pipeline-Darstellung):

| Feld | Quelle | `—` wenn |
|---|---|---|
| `Spec` | `<KLICKDUMMY_PATH>/<name>/screens-spec.yaml` | Kandidat noch nicht gebaut |
| `Lokal` | `<KLICKDUMMY_PATH>/<name>/shell.html?feedback=on` | Kandidat noch nicht gebaut |
| `GitHub` | `https://github.com/<REPO_OWNER>/<REPO_NAME>/blob/main/<KLICKDUMMY_PATH>/<name>/` | Spec nicht auf `origin/main` (`git log origin/main -- <KLICKDUMMY_PATH>/<name>/` leer) |
| `iil.pet` | `https://iil.pet/genesor/render/<repo>-<name>.html` | Repo/KD nicht Klasse A (genesor-vendored) ODER Datei fehlt in `iil-pet-portal/genesor/render/` — Live-Inhalt selbst NICHT prüfbar (Cloudflare-Access-Wand, 🌀 `agent_memory_search(query="genesor live verifizieren Cloudflare")`), nur Datei-Präsenz zählt |

## Step 4: Hand-off (dieser Skill baut nichts)

Pro Kandidat den konkreten nächsten Befehl ausgeben:
- **Brownfield/Greenfield mit klarem Screen-Set** → `/klickdummy <name> klasse=<pattern> persona=<rolle>`
- **Greenfield, Scope groß/unklar** → zuerst `/konzept` (T1/T2), dann `/klickdummy`
- **Existiert evtl. schon** → `/klickdummy-search "<topic>"`

## Output-Format

```
== /kd-scout <repo> ==
  Stack: <type> · HTMX: <detection> · bestehende KDs: <n>
  Kandidaten: <N> (limit=<L>)

Flow-Landkarte
  [A] <Journey>  Routen: <namen>  Persona: <rolle>  UC: <ref|—>
  [B] ...

Entscheidung
  [A] BROWNFIELD · spec-demo · „Route <x> existiert in <file:L> → App läuft"
  [B] GREENFIELD · mock     · „kein Route-Treffer für <flow> → net-new"

Zuschnitt
  Anker-KD: [A] (<Grund: Produkt-Wertkern>)
  Weitere:  [B], [C]  (optional, nach Freigabe)
  ⚠ Tooling-Gap: <iil-klickdummy fehlt → Onboarding Teil der Aufgabe | vorhanden>

KD-Referenz-Übersicht
| # | Name   | Status            | Spec | Lokal | GitHub | iil.pet |
|---|--------|-------------------|------|-------|--------|---------|
| A | <name> | bestehend|Kandidat | ✓/—  | ✓/—   | ✓/—    | ✓/—     |
| B | ...

Links (nur wo ✓ — volle Pfade/URLs NICHT in die Tabelle, sonst Zeilenumbruch-Chaos)
  [A] <Spec-Pfad>
      <GitHub-Blob-URL | — + Grund>
      <iil.pet-URL | — + Grund>

Hand-off
  [A] → /klickdummy <name> klasse=spec-demo persona=<rolle>
  [B] → /konzept  (Scope unklar) → dann /klickdummy
  Drift-Check vor Bau: /klickdummy-search "<topic>"
```

## Anti-Patterns

- ❌ **Selbst scaffolden/schreiben** — `mode: read-only`. Bau ist `/klickdummy` (write). Der Scout
  endet an der Entscheidung + Hand-off.
- ❌ **brownfield/greenfield raten** statt den billigsten Check (Route existiert?) zu fahren —
  das Route-Signal ist die Entscheidung, nicht ein Bauchgefühl.
- ❌ **Flow-Aussage ohne Beleg** — jede Zeile der Landkarte trägt Datei/Route (Evidenz-Disziplin).
- ❌ **Nur `urls.py` scannen** — Fragment-/Router-/Decorator-Routen übersehen ⇒ unvollständige Coverage
  (🌀 `agent_memory_search(query="from-django alle URL-Module parsen nicht nur urls.py")`).
- ❌ **Spec-loses `.html` als KD vorschlagen**, wenn ein spec-getragenes KD existiert — erweitern
  (🌀 `agent_memory_search(query="klickdummy aktualisieren statt neu generieren")`).
- ❌ **Tooling-Gap verschweigen** — fehlt `iil-klickdummy`, muss der Report das als Vorbedingung nennen,
  sonst scheitert `/klickdummy` überraschend.
- ❌ **Kandidaten ohne Cap** — Default 4, damit der Report entscheidbar bleibt.
- ❌ **KD-Referenz-Feld stillschweigend weglassen** statt `—` + Grund — eine fehlende Zeile sieht aus
  wie „vergessen zu prüfen", ein `—` mit Grund ist eine geprüfte Aussage.
- ❌ **Volle URLs in die Übersichtstabelle** — Presence-Marker (✓/—) in der Tabelle, volle Pfade/Links
  in der separaten Liste darunter (sonst Terminal-Zeilenumbruch macht die Tabelle unlesbar).
- ❌ **iil.pet-Link ungeprüft behaupten** — nur setzen, wenn die Datei tatsächlich in
  `iil-pet-portal/genesor/render/` liegt; den Live-Inhalt kann dieser Skill nicht verifizieren
  (Cloudflare-Wand) — das ist kein Grund, den Link auch bei fehlender Datei zu raten.

## 🌀-Memory-Discovery-Pfad

Drift-Lehren zuerst in lokaler CC-Memory (`~/.claude/projects/.../memory/MEMORY.md`), dann Orchestrator.
Relevante reale Einträge (iil-klickdummy):
- `klickdummy-update-not-regenerate` — bestehendes KD erweitern statt neu droppen
- `klickdummy-ux-test` — drei KD-Artefakt-Klassen (A genesor-Render / B in-Repo-Shell / C conversational)
- `spec-as-sor-keystone` — Spec ist Source-of-Record, KD ist Renderer

## Bezug

- `platform:ADR-211` — Klickdummy-Konvention (I1–I4, 4 I2-Patterns)
- `KONZ-iil-klickdummy-008` — KD-Co-Creation-Loop (greenfield + brownfield)
- `~/.claude/policies/klickdummy.md` — Invarianten-SSoT
- Hand-off-Ziele: `/klickdummy` (Bau), `/konzept` (Greenfield-Scoping), `/klickdummy-search` (Drift-Check)

## Dogfood-Tests (Pflicht-Review-Gate per `claude-skills.md`)

### Test 1 — travel-beat (brownfield, Tooling-Gap)

```
/kd-scout travel-beat
```
**Erwartung:** 4 Kandidaten (Reise planen / Story generieren+lesen / Welt pflegen / Paywall+Quota),
alle **BROWNFIELD** (Routen belegt in `apps/*/urls.py`), Anker-KD = Reise→Story (Produkt-Spine),
⚠ Tooling-Gap (kein `iil-klickdummy` im Repo), Hand-off `→ /klickdummy`.
Belegt am Repo-Ist-Stand 2026-07-05 (Django 5.x, Port 8089, keine bestehenden KD-Artefakte).

### Test 2 — Repo mit bestehendem KD (erweitern statt neu)

```
/kd-scout ausschreibungs-hub
```
**Erwartung:** bestehende genesor-KDs erkannt (Klasse A), Kandidaten als **erweitern** markiert,
kein Vorschlag eines spec-losen Duplikats.

### Test 3 — Fokus-Flag

```
/kd-scout risk-hub --flow "ex-schutz freigabe"
```
**Erwartung:** nur die ex-schutz-Freigabe-Journey in der Landkarte, GEMISCHT-Entscheidung je Screen.

### Test 4 — KD-Referenz-Übersicht bei mehreren bestehenden KDs (echter Gap-Beleg)

```
/kd-scout risk-hub
```
**Erwartung (verifiziert am Ist-Stand 2026-07-06):** die KD-Referenz-Übersicht zeigt für
`sds-verwalten` alle vier Felder ✓ (`git log origin/main -- klickdummy/sds-verwalten/` nicht leer,
`iil-pet-portal/genesor/render/risk-hub-sds-verwalten.html` vorhanden) — für `avv-pflege` dagegen
`Spec ✓ / Lokal ✓ / GitHub ✓ / iil.pet —` (auf `origin/main`, aber keine Datei
`iil-pet-portal/genesor/render/risk-hub-avv-pflege.html`). Der Skill markiert diese Lücke sichtbar
statt sie zu verschweigen — genau das Verhalten, das die neue Referenz-Tabelle erzwingen soll.

## Changelog

- 2026-07-05: Initial. Read-only Discovery/Entscheidungs-Vorstufe zu `/klickdummy` (write).
  Operationalisiert `KONZ-iil-klickdummy-008` (KD-Co-Creation-Loop) + `platform:ADR-211`.
  Konform zu `claude-skills.md` (Frontmatter, Step-0-project-facts, Anti-Patterns, 3 Dogfood-Tests,
  keine MCP-Calls → keine Signatur-Verifikation nötig). Dogfood-Beleg: travel-beat-Scout.
- 2026-07-06: **KD-Referenz-Übersicht** (Step 3.5 + Output-Format) — Konsistenz-Review der
  gesamten Pipeline (`kd-scout`→`klickdummy`→`kd-review`, iil-klickdummy-Session): vier feste
  Felder (Spec/Lokal/GitHub/iil.pet) je Kandidat/bestehendem KD, `—` + Grund statt stillem
  Weglassen. Bei mehreren KDs als Übersichtstabelle (Presence-Marker) + separate Link-Liste
  darunter (volle URLs sprengen die Tabellenbreite sonst). 3 neue Anti-Patterns. Dogfood Test 4
  (risk-hub, echter iil.pet-Deploy-Gap zwischen `sds-verwalten` und `avv-pflege`, verifiziert
  2026-07-06). Analoge Änderung in `/klickdummy` + `/kd-review` (Einzel-KD-Form).
