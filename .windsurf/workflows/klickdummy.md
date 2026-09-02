---
description: Neuen Klickdummy im Repo anlegen (Spec, Schema, Shell, ADR, Makefile) nach platform:ADR-211 Rev 13 — I1–I4 grün
mode: write
---

# /klickdummy — Klickdummy anlegen, bis I1–I4 grün sind

> **Wann:** Workshop / frühe UX-Validierung braucht einen klickbaren Stand; das Repo hat
> `iil-klickdummy` bereits adoptiert (Makefile-Target `klickdummy-install` existiert).
> **Wann NICHT:** Einmaliges Workshop-Bild, das danach weggeworfen wird (§Wann-NICHT in
> `platform:ADR-211`) · echte App-UI ohne `?demo=`-Sonderzustand → normaler Code · Erst-Adoption
> von `iil-klickdummy` (Repo-Infrastruktur, eigener PR) · **Kandidaten erst finden** → `/kd-scout`
> (read-only) · **gebauten Klickdummy prüfen** → `/kd-review` (Render, I1-Coverage, UX-Kritik) ·
> **Sitemap/Portal-Wiring** → `/kd-sitemap`.

**Aufruf:** `/klickdummy <name> [klasse=mock] [persona=<rolle>] [fachliche_grundlage=<pfad>]`
(Modus A) oder `/klickdummy` ohne Argumente (Modus B, Interview in 5 Phasen, s. Referenzpfad).
Optional als Folge-Prompts: `screens=[…]` · `extension_review_required=true|false` ·
`sister_of=[repo:ADR-NNN,…]`.

## Ziel

Im aktuellen Repo existiert unter `<KLICKDUMMY_PATH>/<name>/` ein Klickdummy mit Spec, Schema
und `shell.html`, dazu ein lokales Klickdummy-ADR und ein `KLICKDUMMIES`-Eintrag im Makefile —
`make klickdummy` meldet I1–I3 PASS, I4 bringt keinen neuen Treffer, und Shell samt Widget laden
lokal aus der Repo-Wurzel.

## Akzeptanzkriterien

Alle Pfade relativ zur Repo-Wurzel; `<KLICKDUMMY_PATH>`/`<ADR_PATH>` nach Gate G1. `<spec>`/`<schema>`
= Dateinamen wie im Repo-Bestand (AK6); `<kd>` = `<KLICKDUMMY_PATH>/<name>`. Jeder Befehl belegt
genau das, was in seiner Zeile steht — nicht mehr.

| # | Kriterium (aus `platform:ADR-211`) | Prüfbefehl |
|---|---|---|
| AK1 | **I1 Spec-first:** (a) `<kd>/<spec>.yaml` validiert gegen `<kd>/<schema>.json` (Schema fordert `spec_id`, `spec_version`, `class`-Enum, `screens` ≥1); (b) Spec↔Shell-Deckung: die Menge der `screens[].id` ist identisch mit der Menge der `<section data-screen>` in `<kd>/shell.html` | (a) `make klickdummy-i1` → PASS (prüft **nur** Spec gegen Schema); (b) `diff <(python3 -c 'import sys,yaml;print("\n".join(sorted(s["id"] for s in yaml.safe_load(open(sys.argv[1]))["screens"])))' <kd>/<spec>.yaml) <(grep -oP 'data-screen="\K[^"]+' <kd>/shell.html \| sort -u)` → leer |
| AK2 | **I2 4-Pattern:** `class:` ∈ `{mock, stub-demo, story, spec-demo}` explizit in Spec und ADR; bei Nicht-`mock` steht die Prod-Guard-Mechanik in `class_evidence` (`demo_route` / `catalog_route` / `prod_guard`) | `make klickdummy-i2` → PASS (Klassen-Deklaration); Guard: `grep -E 'demo_route\|catalog_route\|prod_guard' <kd>/<spec>.yaml` ≥1 bei Nicht-`mock` |
| AK3 | **I3 Off-Ramp:** (a) `off_ramp`-Block + `off_ramp_status` je Screen (bei `mock`: `static`); (b) ≥1 `parity_acceptance`-Eintrag mit `check` je Screen | (a) `make klickdummy-i3` → PASS (prüft **nicht** `parity_acceptance`); (b) `python3 -c 'import sys,yaml;s=yaml.safe_load(open(sys.argv[1]))["screens"];print(all(x.get("parity_acceptance") for x in s), len(s))' <kd>/<spec>.yaml` → `True <n>` |
| AK4 | **I4 Namensraum:** alle Cross-Repo-Refs als `repo:ADR-NNN`; Spec `adr.local: <REPO_SHORT>:ADR-<NNN>`, `adr.conforms_to: platform:ADR-211`. `klickdummy-i4` scannt `docs/` gesamt — **vor dem Bau** Baseline nehmen | Baseline vor dem Bau: `make klickdummy-i4 \| tail -1` notieren. Nachher: PASS **oder** Trefferzahl = Baseline und `make klickdummy-i4 \| grep -c '<name>\|ADR-<NNN>'` = 0 (vorbestehende Drift ⇒ separater Fix-PR) |
| AK5 | **ADR-Frontmatter (Rev 11):** `<ADR_PATH>/ADR-<NNN>-klickdummy-<name>.md` mit `tags: [klickdummy]`, `class`, `sunset_after` (ISO, Default heute + 12 Monate), `conforms_to: platform:ADR-211`, `extension_review_required`; `<NNN>` = höchste vorhandene + 1; übrige Felder nach Repo-Konvention (bestehendes ADR als Vorbild) | `grep -cE '^(tags\|class\|sunset_after\|conforms_to\|extension_review_required):' <ADR_PATH>/ADR-<NNN>-klickdummy-<name>.md` → 5; Repo-Validator, falls vorhanden (z. B. `iil-adrfw validate <ADR_PATH>/`) grün |
| AK6 | **Makefile + CI:** `KLICKDUMMIES` enthält `<kd>/<spec>.yaml:<kd>/<schema>.json` mit denselben Dateinamen wie die bestehenden Einträge (häufig `spec.yaml`/`spec.schema.json`; Cookbook-Vorlage `screens-spec.yaml`); ein CI-Job führt `make klickdummy` aus und hängt nicht hinter einem Skip-Gate mit `klickdummy/**` | `grep -A20 '^KLICKDUMMIES' Makefile \| grep -c '<name>/'` ≥1; `grep -rn 'make klickdummy' .github/workflows/` ≥1; Skip-Listen: `grep -rn 'klickdummy/\*\*' .github/workflows/` darf den KD-Job nicht betreffen |
| AK7 | **Shell + Widget laden lokal**, Serverstamm = **Repo-Wurzel** (nur dort lösen Shell und Widget-Pfad gemeinsam auf); Feedback-Widget nur per `?feedback=on` aktiv | `python3 -m http.server 8765` (aus der Repo-Wurzel) → `curl -s -o /dev/null -w '%{http_code}' localhost:8765/<kd>/shell.html` = 200 **und** `curl -s localhost:8765/<kd>/shell.html \| grep -c data-screen` ≥1 **und** `curl -s -o /dev/null -w '%{http_code}' localhost:8765/platform-snippets/klickdummy/feedback-widget/widget.js` = 200; Render-/UX-Prüfung → `/kd-review` |

`make klickdummy` (Sammel-Target) muss I1–I3 PASS melden; I4 nach AK4 (PASS oder Baseline
unverändert). Rot bei I4 durch **vorbestehende** Drift ⇒ separater Fix-PR, nicht Teil dieses Laufs.

## Harte Gates

| # | Gate | Verhalten |
|---|---|---|
| G1 | **Repo-Kontext aus dem Repo selbst, nie hart kodiert:** `REPO_OWNER`/`REPO_NAME` aus `git remote get-url origin`; `REPO_SHORT` = `REPO_NAME` (Konvention `repo:ADR-NNN`); `ADR_PATH`/`KLICKDUMMY_PATH` aus dem Bestand (`ls -d docs/adr klickdummy` bzw. `grep -A3 '^KLICKDUMMIES' Makefile`). `.windsurf/rules/project-facts.md` nur **falls vorhanden** als Zusatzquelle (Personas, Deciders) — die Datei ist oft gitignored und fehlt in Worktrees | Remote fehlt oder ADR-/KD-Pfad nicht ableitbar ⇒ Werte beim User erfragen, nicht raten |
| G2 | **Nie überschreiben:** `<KLICKDUMMY_PATH>/<name>/` existiert bereits | **STOP**, User fragen: Update oder neuer Name. Skill ist **non-idempotent** — Re-Run nur nach Bestätigung |
| G3 | **Interview-Modus schreibt nichts vor der Konfirmation:** Phase 5 zeigt die YAML-Vorschau; Dateien entstehen erst nach explizitem „Ja, los" | Ohne „Ja, los" ⇒ keine Datei, kein `mkdir` |
| G4 | **Klasse explizit und guard-belegt:** `class` ∈ 4-Pattern (`mock-prototyp`/`demo-render` sind seit Strict-Mode abgelehnt); bei `stub-demo`/`story`/`spec-demo` **muss** vor dem Spec-Schreiben die Prod-Guard-Mechanik erfragt sein (welche Route/welcher ENV-Flag, Prod ⇒ 404/disabled) | „Pattern deklariert ohne Guard" = Vacuous-Pass ⇒ nicht schreiben, nachfragen |
| G5 | **ADR-Pflicht-Frontmatter** (AK5) — ohne `sunset_after` bricht die Auto-Deprecate-Mechanik (`adr_sunset.sh`, S7) | Fehlendes Feld ⇒ ADR gilt als nicht angelegt |
| G6 | **Erst-Adoption ist nicht dieser Skill:** fehlt `iil-klickdummy` (kein `klickdummy-install`-Target), ist das ein Infrastruktur-Eingriff | ⇒ **STOP**, auf §Migrations-Cookbook in `platform:ADR-211` verweisen |
| G7 | **Datenschutz Gov-Repos:** `KLICKDUMMY_FEEDBACK_REPO` = `<REPO_OWNER>/<REPO_NAME>` aus G1 — nie eine fremde Org; keine Vendor-Namen in `systemgrenzen`/`target_mocks` (generische Adapter-Familien) | Verstoß ⇒ Spec/Shell nicht committen |
| G8 | **KD-Referenz nie raten:** `GitHub`-Feld erst nach Commit auf `origin/main`, `iil.pet` erst nach separatem Portal-Regen — bis dahin `—` mit Grund | Erwartetes Verhalten direkt nach dem Bau, kein Fehler |
| G9 | **Widget opt-in:** `?feedback=on` bleibt opt-in (Class-Erhalt bei `mock`) | Default-aktiv ⇒ I2-Verstoß |
| G10 | **Dogfood = Pflicht-Review-Gate** für Änderungen an diesem Skill (`claude-skills.md`) | Skill-PR ohne echten Lauf ⇒ nicht mergen |

## Referenzpfad (nicht bindend)

Ein fähigeres Modell darf einen anderen Weg nehmen, solange Akzeptanzkriterien und Harte
Gates erfüllt sind. Vorlagen liegen im installierten Paket (`.venv-klickdummy/lib/python3.*/
site-packages/iil_klickdummy/snippets/`).

**0 Kontext + Vorbedingungen** — `git remote get-url origin`, `ls -d docs/adr klickdummy`,
`grep -A3 '^KLICKDUMMIES' Makefile` (G1; Dateinamen `<spec>`/`<schema>` aus dem Bestand übernehmen);
Klasse validieren (G4); `ls .venv-klickdummy/bin/klickdummy-i1` (fehlt ⇒ `make klickdummy-install`,
Target fehlt ⇒ G6); I4-Baseline: `make klickdummy-i4 | tail -1` notieren (AK4).

**0.7 Interview-Modus (nur Modus B)** — eine Frage pro Turn, Smart-Default vorschlagen:

| Phase | Inhalt | Validierung / Default |
|---|---|---|
| 1 | `name` · `klasse` · `personas` · `fachliche_grundlage` (A Konzept-Doc-Pfad / B Freitext / C Stub) | `^[a-z][a-z0-9-]*$`; Klasse Default `mock` |
| 2 | nur Nicht-`mock`: `demo_route` / `catalog_route` / `prod_guard` (ENV-Flag + Query-Param) | Pflicht vor Phase 3 (G4) |
| 3 | Screens (2–5): je `id`, `title`, `purpose`, `personas`, `datafields`, `target_mocks`, `parity_acceptance` | Bei A: Datei lesen, Screens vorschlagen; ≥1 `parity_acceptance` je Screen |
| 4 | `sister_of` (repo:ADR-NNN) · Co-Creation-Loop (Pfad A-User-Direct) | Defaults: leer / nein |
| 5 | YAML-Vorschau der gesamten Spec → „Ja, los" / „Ändere X" / „Abbrechen" | G3 |

Smart-Defaults ohne Rückfrage: `sunset_after` = heute + 12 Monate · `extension_review_required`
= `true` bei `mock`, sonst `false` · `adr.conforms_to: platform:ADR-211` · `off_ramp.policy:
platform:ADR-211 Static→Echt-Migrationspfad` · `off_ramp.doppelquell_grenze: prod-release` ·
`off_ramp_status: static` je Screen bei `mock`.

**1 Pfad** — `mkdir -p <KLICKDUMMY_PATH>/<name>/` (existiert ⇒ G2).

**2 ADR-Nummer** — `ls <ADR_PATH>/ADR-*.md | grep -oE 'ADR-[0-9]+' | sort -u | tail -1` ⇒
höchste + 1; Lücken nicht füllen. Führt das Repo `scripts/adr_next_number.py`, dessen Ausgabe
nehmen.

**3 Spec** — `snippets/spec-templates/screens-spec-template.yaml` nach
`<kd>/<spec>.yaml` kopieren (Name wie Bestand, AK6); setzen: `spec_id:
<REPO_SHORT>:klickdummy-spec-<name>`, `spec_date`, `title`, `adr.local`, `adr.sister_of`, `class`,
`class_evidence` (für `mock`: `no_backend: true`, `no_demo_param: true`, `target_mocks_visible:
true`; `systemgrenzen` generisch), `off_ramp`, `screens`.

**4 Screens** — aus `fachliche_grundlage` 2–5 User-Journeys ableiten; je Screen `id`, `title`,
`personas`, `purpose`, `datafields`, `target_mocks`, `parity_acceptance` (2–5 Checks),
`off_ramp_status`. Ohne Grundlage: **ein** Stub-Screen mit Hinweis „Inhalte folgen aus Workshop".

**5 Schema** — `<kd>/<schema>.json`: bestehenden Klickdummy als Vorbild oder Minimalschema
(draft-07; `required: [spec_id, spec_version, class, screens]`; `class` als `enum` der 4 Pattern;
`screens` `minItems: 1`).

**6 Shell** — `snippets/shell-bootstrap/inject-widget.html` als `widget-include.html` kopieren;
`shell.html` mit einer `<section data-screen="<id>">` je Spec-Screen und vor `</body>`:

```html
<script>
  window.KLICKDUMMY_SPEC = { id: "<REPO_SHORT>:klickdummy-spec-<name>", version: "0.1", klickdummy_class: "<klasse>" };
  window.KLICKDUMMY_FEEDBACK_REPO = "<REPO_OWNER>/<REPO_NAME>";
</script>
<script src="<rel-root>/platform-snippets/klickdummy/feedback-widget/widget.js" defer></script>
```

`<rel-root>` = relativer Weg von `<kd>/` zur Repo-Wurzel (bei `klickdummy/<name>/` also `../..`);
der Pfad löst nur mit Serverstamm Repo-Wurzel auf (AK7) — die Paket-Vorlage `inject-widget.html`
schreibt `platform-snippets/…` ohne Präfix und muss entsprechend angepasst werden.
Gov-Repos optional: eigene `KLICKDUMMY_CATEGORIES` / `KLICKDUMMY_PERSONA_HOOK`.

**7 ADR** — `<ADR_PATH>/ADR-<NNN>-klickdummy-<name>.md`. **Vorbild ist ein bestehendes
Klickdummy-ADR des Repos** (Feldnamen für Status/Datum/Deciders folgen der Repo-Konvention, die
der Repo-Validator durchsetzt — z. B. `status: accepted`, `decision_date:`); darüber hinaus die
Rev-11-Pflichtfelder:

```yaml
conforms_to: platform:ADR-211
tags: [klickdummy]
class: <klasse>
sunset_after: <heute + 12 Monate>
extension_review_required: true   # bei mock; false sonst
```

Body: Kontext · Entscheidung (Klasse + warum) · Konsequenzen · Bezug.

**8 Makefile + CI** — `KLICKDUMMIES` um `<kd>/<spec>.yaml:<kd>/<schema>.json` ergänzen. Fehlt
ein Job mit `make klickdummy` (`grep -rn "make klickdummy" .github/workflows/`), im selben PR
anlegen (Checkout → Python 3.12 → `make klickdummy-install` → `make klickdummy`) — als
**eigenständigen** Job, nicht hinter einem Cosmetic-/Skip-Gate, das `klickdummy/**` ausnimmt
(sonst ist der Job bei seinem eigenen Anlass blind). Ohne CI-Gate bleibt Spec-Drift bis zum
nächsten manuellen Lauf unentdeckt.

**9 Prüfen** — `make klickdummy` ⇒ I1–I3 PASS, I4 gegen Baseline (AK1–AK4 inkl. Deckungs- und
`parity_acceptance`-Befehl); Frontmatter-Grep (AK5); Makefile/CI-Grep (AK6).

**10 Lokal laden** — aus der **Repo-Wurzel** `python3 -m http.server 8765` →
`http://localhost:8765/<kd>/shell.html?feedback=on`; Shell **und** `widget.js` müssen 200 liefern
(AK7). Widget-Token nur lokal in DevTools (`localStorage.setItem('klickdummy_github_token', …)`),
nie in Dateien.

**11 Commit + PR** — Branch `feat/klickdummy-<name>`; Message
`feat(klickdummy): <Name> (platform:ADR-211 Rev 13)` mit Klasse, Screen-Anzahl, ADR-Nummer +
`sunset_after`, „I1–I4 grün". PR-Body: Screen-Liste, Klassen-Begründung, bei Gov-Repos
Datenschutz-Hinweis (G7).

**Bezug:** `platform:ADR-211` (Rev 13, accepted) · `platform:ADR-213` (Ref-Format `repo:ADR-NNN`)
· `iil-klickdummy` ≥ v1.0.0 · Drift-Memories `klickdummy-adr180-collision`,
`klickdummy-rev12-pivot-adr214-rejected`.

## Output-Format

```
== /klickdummy <name> ==
  REPO_SHORT: <wert>   KLICKDUMMY_PATH: <wert>   ADR: ADR-<NNN>   CLASS: <wert>
  SCREENS: <liste>

[1] Pfad:      <kd>/
[2] Spec:      <kd>/<spec>.yaml
[3] Schema:    <kd>/<schema>.json
[4] Shell:     <kd>/shell.html
[5] ADR:       <ADR_PATH>/ADR-<NNN>-klickdummy-<name>.md
[6] Makefile:  KLICKDUMMIES += <eintrag>   CI-Job: <wired|already present>

== Akzeptanzkriterien ==
  AK1 I1 → <PASS|FAIL> · Deckung <leer|diff>   AK2 I2 → <PASS|FAIL>   AK3 I3 → <PASS|FAIL> · parity <True n>
  AK4 I4 → <PASS|Baseline <n> = <n>, 0 neu>   AK5 ADR-Frontmatter → <5/5>   AK6 Makefile+CI → <ok>
  AK7 Shell 200 / data-screen <n> / widget.js 200

== KD-Referenz ==   (gleiches Schema wie /kd-scout und /kd-review)
  Name: <name>   Spec: <kd>/<spec>.yaml
  Lokal: http://localhost:8765/<kd>/shell.html?feedback=on (Serverstamm Repo-Wurzel)
  GitHub: — (kein Commit auf main)   iil.pet: — (kein Portal-Regen)

== Nächste Schritte ==
  - Commit + PR: feat/klickdummy-<name>   - Verifikation: /kd-review <name>
```

## Anti-Patterns

- ❌ Pfade/Orgs hart kodiert statt aus Remote und Repo-Bestand abgeleitet (G1)
- ❌ Serverstamm = KD-Verzeichnis — `widget.js` lädt dann nie, obwohl `shell.html` 200 liefert
- ❌ Klasse `mock-prototyp` / `demo-render` (Rev ≤10) — Strict-Mode lehnt ab
- ❌ `sunset_after` fehlt im ADR-Frontmatter — Auto-Deprecate bricht
- ❌ Cross-Repo-Refs ohne `repo:`-Prefix — I4-Verstoß (Drift-Memory `klickdummy-adr180-collision`)
- ❌ Vendor-Namen in `systemgrenzen` statt generischer Adapter-Familien (`DMS-Adapter`)
- ❌ `KLICKDUMMY_FEEDBACK_REPO` auf fremde Org — Gov-Datenschutz
- ❌ `?feedback=on` default-aktiv — muss opt-in bleiben
- ❌ `screens: []` — mindestens ein Stub-Screen
- ❌ Screen ohne `parity_acceptance` — späterer I1-Drift-Check rot
- ❌ Interview-Modus überspringt Phase 5 — schreibt nie ohne „Ja, los"
- ❌ CI ohne `make klickdummy` — Drift bleibt unentdeckt
- ❌ Nicht-`mock`-Klasse ohne benannte Prod-Guard-Route — Vacuous-Pass
- ❌ Zahlen/Aggregate als Literal statt aus den KD-Daten berechnet (Rev 17 Daten-Treue)

## Abschluss-Checkliste

- ☐ G1: Owner/Name aus `git remote`, Pfade aus dem Bestand; keine hart kodierten Pfade/Orgs im Ergebnis
- ☐ G2/G3: nichts überschrieben; bei Modus B erst nach „Ja, los" geschrieben
- ☐ AK1–AK3: `make klickdummy` ⇒ I1–I3 PASS **plus** Deckungs-Diff leer und `parity_acceptance`
  `True <n>` (Output im Bericht, nicht behauptet)
- ☐ AK4: I4 PASS **oder** Trefferzahl = Baseline vor dem Bau und 0 Treffer auf `<name>`/`ADR-<NNN>`
  (vorbestehende Drift ⇒ separater Fix-PR benannt)
- ☐ AK5: ADR-Frontmatter 5/5 Pflichtfelder, `<NNN>` = höchste + 1, Repo-Validator grün
- ☐ AK6: `KLICKDUMMIES`-Eintrag mit Bestands-Dateinamen + eigenständiger CI-Job
- ☐ AK7: Serverstamm Repo-Wurzel — Shell 200, `data-screen` ≥1, `widget.js` 200; `/kd-review` genannt
- ☐ G7: Gov-Repo ⇒ Feedback-Repo = eigene Org, keine Vendor-Namen
- ☐ G8: KD-Referenz mit `—` + Grund für GitHub/iil.pet
- ☐ Output-Format vollständig
- ☐ Optional: `/kd-sitemap`, wenn das Repo `klickdummy/sitemap/` führt (S14)

## Changelog

- 2026-09-02: **Revision nach Dogfood** (PR #2614, Lauf gegen ein KD-tragendes Repo): G1 auf
  ableitbare Quellen (Remote + Bestand) umgestellt statt STOP auf eine meist fehlende Datei;
  Serverstamm Repo-Wurzel in Schritt 6/10 und AK7 (Widget 200 geprüft); Dateinamen
  `<spec>`/`<schema>` aus dem Bestand; AK1/AK3 auf das beschränkt, was `i1`/`i3` belegen, Deckung
  und `parity_acceptance` mit eigenem Befehl; I4-Baseline in AK4 und Checkliste; ADR-Vorbild
  statt eigener Frontmatter-Vorlage.
- 2026-09-02: **v2 zielorientiert, platform#2606 Stufe 3** — Ziel, Akzeptanzkriterien (AK1–AK7
  aus ADR-211 I1–I4 + Frontmatter-Konvention), Harte Gates (G1–G10, alle bisherigen
  PFLICHT/STOP/nie-Marker zugeordnet), Referenzpfad nicht bindend, Abschluss-Checkliste;
  hart kodierte Beispiel-Pfade/Orgs entfernt.
- 2026-07-06: KD-Referenz im Output-Format (Spec/Lokal/GitHub/iil.pet, gleiches Schema wie
  `/kd-scout`/`/kd-review`).
- 2026-05-21: Rev 2 — Interview-Modus (5 Phasen) ergänzt; 2 Anti-Patterns (Phase-5-Bypass,
  leere `parity_acceptance`).
- 2026-05-21: Initial aus `platform:ADR-211` Rev 13 §Migrations-Cookbook; Dogfood: zwei
  Erst-/Re-Adoptionen (Stub-Screen bzw. Plattform-Heimat, je ~10 Min, I1–I4 PASS).
