---
description: Lege einen neuen Klickdummy im aktuellen Repo nach platform:ADR-211 Rev 13 Cookbook an (Spec + Schema + Shell + ADR + Makefile-Erweiterung)
mode: write
---

# /klickdummy — Neuen Klickdummy nach platform:ADR-211 Rev 13 anlegen

> **Wann:** Workshop / frühe UX-Validierung; Repo hat `iil-klickdummy` schon installiert (oder kann via Step 0.6 installieren).
> **Wann NICHT:** Nur einmaliges Workshop-Bild gezeigt + weggeworfen → §Wann-NICHT-Klausel `platform:ADR-211` Rev 13. Echte App-UI ohne `?demo=`-Sonderzustand → normaler Code.

## Verwendung — zwei Modi

### Modus A: Direkt-Argumente

```
/klickdummy <name> [klasse=mock] [persona=<rolle>] [fachliche_grundlage=<pfad/doc.md>]
```

| Variable | Pflicht | Beispiel | Bedeutung |
|---|---|---|---|
| `<name>` | **ja** | `schichtleitung-cockpit` | kebab-case, wird Pfad-Name + Spec-ID-Suffix |
| `klasse` | nein (default `mock`) | `mock` \| `stub-demo` \| `story` \| `spec-demo` | I2-Pattern; bei nicht-`mock` zusätzliche Prod-Guard-Pflicht |
| `persona` | nein | `schichtleitung` | Default-Persona für Screens |
| `fachliche_grundlage` | nein | `docs/Angebot_KI_Werkleiterassistent_Phase1_IIL.md` | Konzept-Doc, aus dem Screens abgeleitet werden |

Optional als Folge-Prompts: `screens=[a,b,c]` · `extension_review_required=true|false` · `sister_of=[repo:ADR-NNN,...]`.

### Modus B: Geführter Dialog (Interview-Modus)

```
/klickdummy
```

(Ohne Argumente.) Skill startet einen strukturierten Interview-Loop in 5 Phasen
(siehe **Step 0.7 Interview-Modus** unten), sammelt alle Pflicht-Variablen
und ggf. Screen-Definitionen, zeigt eine YAML-Vorschau zur Konfirmation —
dann erst beginnen Bau-Steps 1-11. Empfohlen für **Workshop-Vorbereitung**
ohne fertige Spec-Vorstellung.

## Step 0: Repo-Kontext (PFLICHT — kein Hardcoding)

Aus `.windsurf/rules/project-facts.md` (always_on) im aktuellen Repo lesen:

```
- REPO_OWNER     (z.B. "ttz-lif", "achimdehnert", "meiki-lra")
- REPO_NAME      (z.B. "ttz-hub", "writing-hub", "meiki-hub")
- REPO_SHORT     (kanonisches Cross-Repo-Prefix für `repo:ADR-NNN`, z.B. "ttz-hub")
- ADR_PATH       (z.B. "docs/adr")
- KLICKDUMMY_PATH (z.B. "klickdummy")  # Default
```

Fehlt project-facts.md ⇒ STOP, User auf `agent-session-start.md`-Workflow verweisen.

## Step 0.5: Klasse validieren (I2 4-Pattern, Rev 11/13)

Klasse muss in `{mock, stub-demo, story, spec-demo}` sein.

- **`mock`** (Default) — separater Wegwerf-Code-Pfad, keine echte Persistenz. **I2-Externprobe N/A.** Reicht für Workshop-Klickdummies.
- **`stub-demo`** — realer Code-Pfad, synth. Daten an dedizierter Demo-Route. **Pflicht:** Demo-Route muss in Prod 404 antworten.
- **`story`** — Component-Catalog (Storybook o.ä.). **Pflicht:** Catalog-Route in Prod 404.
- **`spec-demo`** — env-gegateter Zustand via `?demo=<state>`. **Pflicht:** `?demo=` in Prod 404/disabled.

Bei nicht-`mock`-Klasse: **frage nach Prod-Guard-Mechanik** (welcher ENV-Flag, welche Route), bevor Spec geschrieben wird. „Pattern deklariert ohne Guard" wäre Vacuous-Pass.

## Step 0.6: iil-klickdummy-Installation prüfen

```bash
ls .venv-klickdummy/bin/klickdummy-i1 2>/dev/null && echo "✓ installed" || echo "✗ run: make klickdummy-install"
```

Wenn fehlt: `make klickdummy-install` ausführen, falls Makefile-Target existiert. Sonst zuerst `iil-klickdummy` adoptieren (siehe §Migrations-Cookbook in `platform:ADR-211` Rev 13). Bei Erst-Adoption: `/klickdummy` selbst nicht der richtige Workflow — Erst-Adoption ist Eingriff in Repo-Infrastruktur.

## Step 0.7: Interview-Modus (nur wenn Modus B: keine Argumente)

**Auslöser:** `/klickdummy` ohne Argumente. Wenn Modus A (mit `<name>` etc.) verwendet wird, wird **Step 0.7 übersprungen** und es geht direkt zu Step 1.

**Mechanik:** Coding-Agent (CC / Windsurf) führt den Dialog mit dem User. **Eine Frage pro Turn**, mit Smart-Default-Vorschlag und Erklärung. User antwortet → nächste Frage. Antworten werden in einer lokalen `<spec_draft>`-Struktur gesammelt. Phase 5 ist Konfirmations-Stop bevor Bau-Steps anfangen.

### Phase 1 — Pflicht-Variablen (4 Fragen, sequenziell)

**Frage 1.1 — Name:**

> „Wie soll der Klickdummy heißen? Kebab-case, wird Pfad-Name + Spec-ID-Suffix.
> Beispiel: `schichtleitung-cockpit`, `werkleiter-tag-uebersicht`."

Validierung: regex `^[a-z][a-z0-9-]*$`. Bei Drift: re-prompt mit Hinweis.

**Frage 1.2 — Klasse (I2-Pattern):**

> „Welches Pattern (platform:ADR-211 Rev 11 §I2)?
>
> 1. `mock` (Default) — Wegwerf-Pfad, keine echte Persistenz, keine Prod-Deploy-Pflicht. Für Workshop / frühe Validierung.
> 2. `stub-demo` — realer Code-Pfad mit synth. Daten an dedizierter Demo-Route (Route muss in Prod 404 antworten).
> 3. `story` — Component-Catalog (Storybook etc.); Catalog-Route in Prod 404.
> 4. `spec-demo` — env-gegated via `?demo=<state>`; `?demo=` in Prod 404/disabled.
>
> Welches Pattern? [Default: mock]"

Bei `stub-demo`/`story`/`spec-demo`: **adaptive Folgefragen** (siehe Phase 2).

**Frage 1.3 — Personas:**

> „Welche Personas / Rollen sehen den Klickdummy? Komma-Liste.
> [Smart-Default aus `project-facts.md` Repo-Kontext, falls Personas-Hinweise]"

Beispiele je Repo-Typ:
- ttz-hub (Werkstatt): `werkleitung, schichtleitung`
- meiki-hub (LRA): `sachbearbeiter, teamleitung`
- writing-hub (Lecture): `autor`

**Frage 1.4 — Fachliche Grundlage:**

> „Aus welchem Dokument kommen die Screens? Drei Optionen:
>
> A. **Pfad zu Konzept-Doc** (z. B. `docs/Angebot_KI_Werkleiterassistent_Phase1_IIL.md`) — Agent liest + leitet ab
> B. **Freie Beschreibung** in einem nachfolgenden Prompt
> C. **Stub** — nur 1 Skelett-Screen mit „Inhalte folgen aus Workshop"-Hinweis
>
> Welche Option (A/B/C)?"

Bei A: Datei lesen, in Phase 3 verarbeiten.
Bei B: Free-Text-Eingabe abwarten.
Bei C: Phase 3 wird sehr kurz (1 Screen).

### Phase 2 — Adaptive Folgefragen (nur bei nicht-`mock`-Klasse)

**Bei `stub-demo`:**
> „Demo-Route-Pfad? (z. B. `/demo/<klickdummy-name>/`). Wird in `class_evidence.demo_route` festgehalten. **Pflicht:** Diese Route MUSS in Prod 404 antworten (I2-Externprobe)."

**Bei `story`:**
> „Catalog-Route? (z. B. `/storybook/`, `/styleguide/`). Wird in `class_evidence.catalog_route` festgehalten. **Pflicht:** Route in Prod 404."

**Bei `spec-demo`:**
> „Welcher Query-Parameter aktiviert den Demo-Render? Default: `?demo=on`. Welcher ENV-Flag schaltet das auf Server-Seite ab? (z. B. `KLICKDUMMY_TOUR_ENABLED + DEBUG + TESTING`). Wird in `class_evidence.prod_guard` festgehalten."

### Phase 3 — Screens definieren (Loop)

**Frage 3.0 — Anzahl:**

> „Wie viele Screens? (2-5 typisch; mehr nur wenn Workshop-Plan es vorgibt.)"

**Wenn fachliche_grundlage=A:** Agent **liest die Datei**, schlägt 2-5 Screens mit Vorschlag-Titel + Zweck vor. User bestätigt oder ändert pro Screen.

**Wenn fachliche_grundlage=B/C:** Agent fragt **pro Screen** sequenziell:

Für Screen #N:

> „**Screen #N — id** (kebab-case)? Beispiel: `frist-uebersicht`."
> „**title** (Klartext)? Beispiel: `Fristen-Übersicht`."
> „**purpose** (1 Satz, was zeigt der Screen)?"
> „**personas** für diesen Screen? [Default: alle aus Phase 1.3]"
> „**datafields** (Komma-Liste oder leer)? Format: `name (typ, quelle)`. Beispiel: `fall_id (string, FV-Adapter), frist (date, BRMS)`."
> „**target_mocks** (welche Systemgrenzen werden angeklickt aber nicht aufgelöst)? Komma-Liste generischer Adapter-Familien. Beispiel: `DMS-Adapter, BRMS Frist-Engine`. **Keine Vendor-Namen** (Anti-Pattern)."
> „**parity_acceptance** — mindestens 1 prüfbare Behauptung pro Screen. Format: `id: kurzbezeichnung | check: konkrete Aussage`. Beispiel: `id: frist-uebersicht.ampel-vollstaendig | check: Ampel-Zähler summieren zu count(alle_fristen)`."

Loop bis Anzahl erreicht.

### Phase 4 — Optionale Felder (Smart-Defaults, 1-2 Fragen)

**Frage 4.1 — Schwester-Implementierungen (Cross-Repo):**

> „Gibt es Klickdummies in anderen Repos, mit denen dieser eine **Schwester-Beziehung** hat? Format: `repo:ADR-NNN`, Komma-Liste. [Default: leer]
>
> Bekannte Klickdummy-ADRs (zur Inspiration):
> - meiki-hub:ADR-021 (Fristenmanagement, mock)
> - writing-hub:ADR-180 (Lecture-Outline-Wizard, spec-demo)
> - risk-hub:ADR-046 (Spec-Driven UI, mock)
> - ttz-hub:ADR-100 (Werkleiter-Skizze-Stub, mock)"

**Frage 4.2 — Co-Creation-Loop?**

> „Soll der Klickdummy von Anfang an mit Feedback-Widget (Pfad A-User-Direct, platform:ADR-211 Rev 13 §Co-Creation) ausgeliefert werden? [Default: nein, kann jederzeit nachgerüstet werden]"

Falls **ja**: Spec bekommt `feedback_loop.path: A-User-Direct` und `shell.html` enthält den Bootstrap-Block mit `KLICKDUMMY_FEEDBACK_REPO=<REPO_OWNER>/<REPO_NAME>`.

**Smart-Defaults (NICHT gefragt, automatisch gesetzt):**

| Feld | Default-Wert | Quelle |
|---|---|---|
| `sunset_after` | heute + 12 Monate | Rev-11-Default |
| `extension_review_required` | `true` für `mock`, `false` sonst | Rev-11-Default |
| `adr.conforms_to` | `platform:ADR-211` | Konstante |
| `off_ramp.policy` | `platform:ADR-211 Static→Echt-Migrationspfad` | Konstante |
| `off_ramp.doppelquell_grenze` | `prod-release` | Konstante |
| `off_ramp_status` (je Screen) | `static` (bei Klasse `mock`) | Phase-A-Default |
| ADR-Nummer | `letzte+1` aus `ls <ADR_PATH>/ADR-*.md` | auto-detect |
| `KLICKDUMMY_FEEDBACK_REPO` | `<REPO_OWNER>/<REPO_NAME>` aus project-facts | Gov-Datenschutz-konform |

### Phase 5 — YAML-Vorschau + Konfirmation

Agent zeigt **gesamte gesammelte Spec als YAML-Block**:

```yaml
# Vorschau — schreibe ich gleich nach <KLICKDUMMY_PATH>/<name>/screens-spec.yaml
spec_id: <REPO_SHORT>:klickdummy-spec-<name>
spec_version: "0.1"
spec_date: "<heute>"
title: <Klartext>
adr:
  local: <REPO_SHORT>:ADR-<NNN>
  conforms_to: platform:ADR-211
  sister_of: [...]
class: <klasse>
class_evidence: { ... }
off_ramp: { ... }
screens:
  - id: <id>
    title: <title>
    ...
```

Dann Frage:

> „Sieht das richtig aus?
>
> - **Ja, los** → starte Bau-Steps 1-11
> - **Ändere X** → nimm Änderung am YAML auf, zeige neue Vorschau
> - **Abbrechen** → schreibe nichts, beende Skill"

**Erst nach `Ja, los` werden Files angelegt.** Bis dahin ist die Spec nur in der Konversation.

### Phase-5-Output-Beispiel (Dogfood, ttz-hub Werkleiter-Skizze)

Nachträglich rekonstruiert, was der Interview-Modus bei ttz-hub:ADR-100 erzeugt hätte (vor PR #5):

```
P1.1 name?                    → werkleiter-skizze
P1.2 klasse?                  → mock
P1.3 personas?                → werkleitung, schichtleitung
P1.4 fachliche grundlage?     → A · docs/Angebot_KI_Werkleiterassistent_Phase1_IIL.md
P2   (mock — übersprungen)
P3.0 anzahl screens?          → 1 (Stub)
P3.1 screen #1 id?            → werkleiter-uebersicht-stub
     title?                   → Werkleiter-Übersicht (Stub)
     purpose?                 → Skelett — fachliche Inhalte folgen aus Workshop Iter. 1
     target_mocks?            → LLM-Gateway
     parity_acceptance?       → id: werkleiter-uebersicht-stub.exists | check: rendert + zeigt Stub-Hinweis
P4.1 sister_of?               → meiki-hub:ADR-021, writing-hub:ADR-180, risk-hub:ADR-046
P4.2 co-creation?             → nein (Stub-Phase)
P5   Vorschau + bestätigt     → Bau-Steps 1-11
```

Empirie: dieselbe Spec entstand am 2026-05-20 durch manuelle Eingabe (PR #5).

```bash
mkdir -p <KLICKDUMMY_PATH>/<name>/
```

Wenn `<KLICKDUMMY_PATH>/<name>/` schon existiert ⇒ STOP, User fragen ob Update oder neuer Name.

## Step 2: ADR-Nummer ermitteln

```bash
ls <ADR_PATH>/ADR-*.md | grep -oE 'ADR-[0-9]+' | sort -u | tail -1
# z.B. ADR-100 → nächste freie Nummer = ADR-101
```

ADR-Nummer ist `letzte+1`. Bei Lücken (ADR-001..ADR-100 ohne ADR-050) trotzdem `letzte+1` nehmen, keine Lücken füllen.

## Step 3: Spec aus Template

```bash
cp .venv-klickdummy/lib/python3.12/site-packages/iil_klickdummy/snippets/spec-templates/screens-spec-template.yaml \
   <KLICKDUMMY_PATH>/<name>/screens-spec.yaml
```

**Anpassungen** (in der Spec):

- `spec_id: <REPO_SHORT>:klickdummy-spec-<name>`
- `spec_date: <heute, ISO>`
- `title: <Name in Klartext>`
- `adr.local: <REPO_SHORT>:ADR-<NNN>`  (Nummer aus Step 2)
- `adr.sister_of: [...]`  (falls Schwester-Klickdummies in anderen Repos existieren)
- `class: <klasse>`
- `class_evidence:` je Klasse anpassen (für `mock`: `no_backend: true`, `no_demo_param: true`, `target_mocks_visible: true`)
- `class_evidence.systemgrenzen: [...]`  (generische Adapter-Familien, NICHT Vendor-Namen)
- `off_ramp.policy: platform:ADR-211 Static→Echt-Migrationspfad`
- `screens:` mit fachlich abgeleiteten Screens (siehe Step 4)

## Step 4: Screens ableiten aus fachlicher Grundlage

Wenn `<fachliche_grundlage>` gegeben:

1. Datei lesen
2. **Hauptabläufe / User-Journeys identifizieren** (2-5, mehr nur in Ausnahmefällen)
3. Pro Screen: `id` (kebab-case), `title`, `personas` (mind. `<persona>`), `purpose` (1 Satz), `datafields` (welche Felder zeigt der Screen), `target_mocks` (welche Systemgrenzen werden angeklickt aber nicht aufgelöst), `parity_acceptance` (2-5 prüfbare Checks)
4. Bei `mock`-Klasse: alle `off_ramp_status: static`

Wenn `<fachliche_grundlage>` fehlt: einen **Stub-Screen** mit Warnung anlegen (siehe ttz-hub:ADR-100 als Vorbild) — Inhalte folgen aus Workshop.

## Step 5: Schema-Datei

```bash
# generisches Schema kopieren (bestehender Klickdummy als Vorbild) ODER
# minimales Schema:
```

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["spec_id", "spec_version", "class", "screens"],
  "additionalProperties": true,
  "properties": {
    "spec_id":      { "type": "string" },
    "spec_version": { "type": "string" },
    "class":        { "type": "string", "enum": ["mock", "stub-demo", "story", "spec-demo"] },
    "screens":      { "type": "array", "minItems": 1 }
  }
}
```

## Step 6: shell.html mit Widget-Bootstrap

```bash
cp .venv-klickdummy/lib/python3.12/site-packages/iil_klickdummy/snippets/shell-bootstrap/inject-widget.html \
   <KLICKDUMMY_PATH>/<name>/widget-include.html
```

**shell.html** anlegen mit:

- mind. 1 `<section data-screen="<id>">` pro Spec-Screen
- am Ende vor `</body>`:
  ```html
  <script>
    window.KLICKDUMMY_SPEC = { id: "<REPO_SHORT>:klickdummy-spec-<name>", version: "0.1", klickdummy_class: "<klasse>" };
    window.KLICKDUMMY_FEEDBACK_REPO = "<REPO_OWNER>/<REPO_NAME>";
  </script>
  <script src="../../platform-snippets/klickdummy/feedback-widget/widget.js" defer></script>
  ```
- Wegen Plugin-Hooks (Gov-Repos): optional eigene `KLICKDUMMY_CATEGORIES` / `KLICKDUMMY_PERSONA_HOOK`

## Step 7: Lokales Klickdummy-ADR anlegen

`<ADR_PATH>/ADR-<NNN>-klickdummy-<name>.md` mit **Pflicht-Frontmatter** (Rev 11):

```yaml
---
title: "ADR-<NNN>: Klickdummy <Name>"
status: Accepted
date: <heute>
deciders: <aus project-facts.md>
scope: <REPO_NAME>
conforms_to: platform:ADR-211
tags: [klickdummy]
class: <klasse>
sunset_after: <heute + 12 Monate>      # ISO; Auto-deprecate ohne Extension
extension_review_required: true        # bei mock; false sonst
related: []
---
```

Body: Kontext, Entscheidung (welche Klasse + warum), Konsequenzen, Bezug. Vorlage: `meiki-hub:ADR-021` (für Deep-Dive) oder `ttz-hub:ADR-100` (für Stub).

## Step 8: Makefile-Variable erweitern

In `Makefile` die `KLICKDUMMIES`-Liste um den neuen Eintrag ergänzen:

```makefile
KLICKDUMMIES := \
  <existierende> \
  <KLICKDUMMY_PATH>/<name>/screens-spec.yaml:<KLICKDUMMY_PATH>/<name>/screens-spec.schema.json
```

## Step 9: I1-I4 grün stellen

```bash
make klickdummy
```

**Erwartung:**
- I1 PASS (schema-konform)
- I2 PASS (class deklariert)
- I3 PASS (off_ramp_status je Screen)
- I4 PASS (Cross-Repo-Refs als `repo:ADR-NNN`)

Wenn I4 wegen pre-existing Drift rot ist: separater Fix-PR, nicht Teil dieser Skill.

## Step 10: Live-Test (optional)

```bash
cd <KLICKDUMMY_PATH>/<name>
python3 -m http.server 8765
# Browser: http://localhost:8765/shell.html?feedback=on
```

Widget-Token einmalig setzen (DevTools-Console):

```js
localStorage.setItem('klickdummy_github_token', '<dein-PAT>');
```

## Step 11: Commit + PR

Branch: `feat/klickdummy-<name>` von `main`.

Commit-Message:

```
feat(klickdummy): <Name> (platform:ADR-211 Rev 13)

- <Klasse>-Pattern, <N> Screens
- ADR-<NNN> mit sunset_after <Datum>
- Spec + Schema + shell.html + Widget v0.5
- I1-I4 grün

Bezug: platform:ADR-211 Rev 13
```

PR-Body sollte enthalten: Screen-Liste, Klassen-Begründung, Datenschutz-Hinweis bei Gov-Repos (KLICKDUMMY_FEEDBACK_REPO setzt eigene Org).

## Output-Format

```
== /klickdummy <name> ==
  REPO_SHORT: <wert>
  KLICKDUMMY_PATH: <wert>
  ADR_NUMBER: ADR-<NNN>
  CLASS: <wert>
  SCREENS: <liste>

[1] Pfad angelegt:        <KLICKDUMMY_PATH>/<name>/
[2] Spec geschrieben:     <pfad>
[3] Schema geschrieben:   <pfad>
[4] shell.html:           <pfad>
[5] ADR:                  <ADR_PATH>/ADR-<NNN>-klickdummy-<name>.md
[6] Makefile erweitert:   KLICKDUMMIES += <eintrag>

== Tests ==
  I1 → <PASS|FAIL>
  I2 → <PASS|FAIL>
  I3 → <PASS|FAIL>
  I4 → <PASS|FAIL>

== Nächste Schritte ==
  - Live-Test: python3 -m http.server 8765 → ?feedback=on
  - Commit + PR: feat/klickdummy-<name>
```

## Anti-Patterns

- ❌ **Hardcoded Pfad** (`~/github/ttz-hub/...`) statt `project-facts.md` lesen
- ❌ **Hardcoded Owner/Org** statt `REPO_OWNER` / `REPO_NAME` Variablen
- ❌ **Klasse `mock-prototyp` oder `demo-render`** (Rev-≤10) — Strict-Mode aktiv seit 2026-05-20, `iil-klickdummy` v1.0.0 lehnt diese ab
- ❌ **`sunset_after` fehlt** im ADR-Frontmatter — Auto-deprecate-Mechanik bricht
- ❌ **Cross-Repo-Refs ohne `repo:`-Prefix** — verstößt gegen I4, vgl. Drift-Memory `klickdummy-adr180-collision`
- ❌ **Vendor-Namen in `systemgrenzen`** (z.B. `enaio`, `d.velop`) statt generischer Adapter-Familien (`DMS-Adapter`)
- ❌ **`KLICKDUMMY_FEEDBACK_REPO` auf fremde Org** (Gov-Workloads müssen eigene Org behalten — Datenschutz)
- ❌ **`?feedback=on` als Default-aktiv** — muss opt-in bleiben (class-Erhalt bei `mock`)
- ❌ **`screens: []`** — keine leere Spec; Stub-Screen muss vorhanden sein, mindestens
- ❌ **CI ohne Klickdummy-Targets** — `make klickdummy` muss laufen, sonst `klickdummy_registry.sh` rot
- ❌ **Interview-Modus überspringt Phase 5 (Konfirmation)** — schreibt nie ohne explizites „Ja, los". Sonst entstehen unintentionierte Klickdummies bei Interview-Tippfehlern.
- ❌ **Phase-3-Screens ohne `parity_acceptance`** — leerer Screen ist I1-Verstoß bei späterem Drift-Check; mindestens 1 prüfbare Behauptung pro Screen erzwingen.

## Idempotenz-Note

**Non-idempotent — confirm before re-run.** Skill legt Files an. Bei Re-Run mit gleichem `<name>`:
- Existierende Spec wird NICHT überschrieben (STOP in Step 1)
- ADR-Nummer wird neu vergeben (Step 2) — kann zu Lücken führen, wenn vorheriger Run abgebrochen
- Makefile-Eintrag muss manuell deduppliziert werden

Bei Re-Run anderen `<name>` wählen oder vorherigen Klickdummy entsorgen.

## Bezug

- `platform:ADR-211` (Rev 13, accepted) — Klickdummy-Cross-Repo-Rahmen
- `platform:ADR-213` — Cross-Repo-Ref-Format `repo:ADR-NNN`
- `iil-klickdummy` v1.0.0 — pip-Paket via Git-URL
- Drift-Memory `klickdummy-adr180-collision` (meiki-hub-lokal) — ADR-Namensraum-Kollision
- Drift-Memory `klickdummy-rev12-pivot-adr214-rejected` (meiki-hub-lokal) — warum kein zentraler Service

## Dogfood-Test (Pflicht-Review-Gate per `claude-skills.md`)

Bewährt in:

- **ttz-hub PR #5** (2026-05-20) — Erst-Adoption + Stub-Screen `werkleiter-skizze`. ADR-100, Class `mock`, sunset 2027-05-20. I1/I2/I3 PASS, I4 PASS nach 2 ADR-189-Qualifizierungen. **~10 Min Adoption-Zeit** — entspricht Cookbook-Erwartung.
- **meiki-hub PR #23** (2026-05-20) — Re-Adoption mit Plattform-Heimat (Pilot). ADR-021/026, Class `mock`. Console-Scripts statt lokaler Kopien.

## Changelog

- 2026-05-21: Initial. Aus `platform:ADR-211` Rev 13 §Migrations-Cookbook + ttz-hub-Erst-Adoption-Empirie abgeleitet. 11 Steps + 9 Anti-Patterns + 2 Dogfood-Empirie-Punkte.
- 2026-05-21: Rev 2 — Interview-Modus (Step 0.7) ergänzt. Bei `/klickdummy` ohne Args läuft strukturierter 5-Phasen-Dialog (Pflicht-Variablen / adaptive Klassen-Folgen / Screens-Loop / Optionals mit Smart-Defaults / YAML-Konfirmation), bevor Bau-Steps 1-11 starten. 2 neue Anti-Patterns (Phase-5-Bypass, leere parity_acceptance). Cross-Tool kompatibel (CC + Windsurf), kein separater Sub-Agent nötig.
