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
`make klickdummy` meldet I1–I4 PASS und die Shell lädt lokal.

## Akzeptanzkriterien

Alle Pfade relativ zum Repo; `<KLICKDUMMY_PATH>`/`<ADR_PATH>` aus `project-facts.md` (Gate G1).

| # | Kriterium (aus `platform:ADR-211`) | Prüfbefehl |
|---|---|---|
| AK1 | **I1 Spec-first:** `screens-spec.yaml` + `screens-spec.schema.json` + `shell.html` liegen im KD-Pfad; jede Spec-`screens[].id` hat eine `<section data-screen="<id>">` in der Shell und umgekehrt | `make klickdummy-i1` → PASS; Gegenprobe: `grep -o 'data-screen="[^"]*"' <KLICKDUMMY_PATH>/<name>/shell.html` vs. `grep -E '^\s+- id:' …/screens-spec.yaml` |
| AK2 | **I2 4-Pattern:** `class:` ∈ `{mock, stub-demo, story, spec-demo}` explizit in Spec und ADR; bei Nicht-`mock` steht die Prod-Guard-Mechanik in `class_evidence` (`demo_route` / `catalog_route` / `prod_guard`) | `make klickdummy-i2` → PASS; `grep -E '^class: (mock\|stub-demo\|story\|spec-demo)$' …/screens-spec.yaml` |
| AK3 | **I3 Off-Ramp:** jeder Screen trägt `off_ramp_status` (bei `mock`: `static`) und ≥1 `parity_acceptance`-Eintrag mit prüfbarem `check` | `make klickdummy-i3` → PASS; `grep -c 'parity_acceptance' …/screens-spec.yaml` ≥ Anzahl Screens |
| AK4 | **I4 Namensraum:** alle Cross-Repo-Refs als `repo:ADR-NNN`; Spec `adr.local: <REPO_SHORT>:ADR-<NNN>`, `adr.conforms_to: platform:ADR-211` | `make klickdummy-i4` → PASS |
| AK5 | **ADR-Frontmatter (Rev 11):** `<ADR_PATH>/ADR-<NNN>-klickdummy-<name>.md` mit `tags: [klickdummy]`, `class`, `sunset_after` (ISO, Default heute + 12 Monate), `conforms_to: platform:ADR-211`, `extension_review_required`; `<NNN>` = höchste vorhandene + 1 | `grep -E '^(tags|class|sunset_after|conforms_to|extension_review_required):' <ADR_PATH>/ADR-<NNN>-klickdummy-<name>.md` → 5 Treffer |
| AK6 | **Makefile + CI:** `KLICKDUMMIES` enthält `<pfad>/screens-spec.yaml:<pfad>/screens-spec.schema.json`; ein CI-Job führt `make klickdummy` aus | `grep -n '<name>/screens-spec.yaml' Makefile`; `grep -rn 'make klickdummy' .github/workflows/` → ≥1 Treffer |
| AK7 | **Shell lädt lokal** mit sichtbarem Inhalt; Feedback-Widget nur per `?feedback=on` aktiv | `python3 -m http.server 8765 -d <KLICKDUMMY_PATH>/<name>` → `curl -s localhost:8765/shell.html \| grep -c data-screen` ≥1; Render-/UX-Prüfung → `/kd-review` |

`make klickdummy` (Sammel-Target) muss alle vier Invarianten PASS melden. Rot bei I4 durch
**vorbestehende** Drift ⇒ separater Fix-PR, nicht Teil dieses Laufs.

## Harte Gates

| # | Gate | Verhalten |
|---|---|---|
| G1 | **Repo-Kontext nur aus `.windsurf/rules/project-facts.md`** (`REPO_OWNER`, `REPO_NAME`, `REPO_SHORT`, `ADR_PATH`, `KLICKDUMMY_PATH`) — kein Hardcoding von Pfaden/Orgs | Datei fehlt ⇒ **STOP**, auf `/session-start` verweisen |
| G2 | **Nie überschreiben:** `<KLICKDUMMY_PATH>/<name>/` existiert bereits | **STOP**, User fragen: Update oder neuer Name. Skill ist **non-idempotent** — Re-Run nur nach Bestätigung |
| G3 | **Interview-Modus schreibt nichts vor der Konfirmation:** Phase 5 zeigt die YAML-Vorschau; Dateien entstehen erst nach explizitem „Ja, los" | Ohne „Ja, los" ⇒ keine Datei, kein `mkdir` |
| G4 | **Klasse explizit und guard-belegt:** `class` ∈ 4-Pattern (`mock-prototyp`/`demo-render` sind seit Strict-Mode abgelehnt); bei `stub-demo`/`story`/`spec-demo` **muss** vor dem Spec-Schreiben die Prod-Guard-Mechanik erfragt sein (welche Route/welcher ENV-Flag, Prod ⇒ 404/disabled) | „Pattern deklariert ohne Guard" = Vacuous-Pass ⇒ nicht schreiben, nachfragen |
| G5 | **ADR-Pflicht-Frontmatter** (AK5) — ohne `sunset_after` bricht die Auto-Deprecate-Mechanik (`adr_sunset.sh`, S7) | Fehlendes Feld ⇒ ADR gilt als nicht angelegt |
| G6 | **Erst-Adoption ist nicht dieser Skill:** fehlt `iil-klickdummy` (kein `klickdummy-install`-Target), ist das ein Infrastruktur-Eingriff | ⇒ **STOP**, auf §Migrations-Cookbook in `platform:ADR-211` verweisen |
| G7 | **Datenschutz Gov-Repos:** `KLICKDUMMY_FEEDBACK_REPO` = `<REPO_OWNER>/<REPO_NAME>` aus project-facts — nie eine fremde Org; keine Vendor-Namen in `systemgrenzen`/`target_mocks` (generische Adapter-Familien) | Verstoß ⇒ Spec/Shell nicht committen |
| G8 | **KD-Referenz nie raten:** `GitHub`-Feld erst nach Commit auf `origin/main`, `iil.pet` erst nach separatem Portal-Regen — bis dahin `—` mit Grund | Erwartetes Verhalten direkt nach dem Bau, kein Fehler |
| G9 | **Widget opt-in:** `?feedback=on` bleibt opt-in (Class-Erhalt bei `mock`) | Default-aktiv ⇒ I2-Verstoß |
| G10 | **Dogfood = Pflicht-Review-Gate** für Änderungen an diesem Skill (`claude-skills.md`) | Skill-PR ohne echten Lauf ⇒ nicht mergen |

## Referenzpfad (nicht bindend)

Ein fähigeres Modell darf einen anderen Weg nehmen, solange Akzeptanzkriterien und Harte
Gates erfüllt sind. Vorlagen liegen im installierten Paket (`.venv-klickdummy/lib/python3.*/
site-packages/iil_klickdummy/snippets/`).

**0 Kontext + Vorbedingungen** — `project-facts.md` lesen (G1); Klasse validieren (G4);
`ls .venv-klickdummy/bin/klickdummy-i1` (fehlt ⇒ `make klickdummy-install`, Target fehlt ⇒ G6).

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
`<KLICKDUMMY_PATH>/<name>/screens-spec.yaml` kopieren; setzen: `spec_id:
<REPO_SHORT>:klickdummy-spec-<name>`, `spec_date`, `title`, `adr.local`, `adr.sister_of`, `class`,
`class_evidence` (für `mock`: `no_backend: true`, `no_demo_param: true`, `target_mocks_visible:
true`; `systemgrenzen` generisch), `off_ramp`, `screens`.

**4 Screens** — aus `fachliche_grundlage` 2–5 User-Journeys ableiten; je Screen `id`, `title`,
`personas`, `purpose`, `datafields`, `target_mocks`, `parity_acceptance` (2–5 Checks),
`off_ramp_status`. Ohne Grundlage: **ein** Stub-Screen mit Hinweis „Inhalte folgen aus Workshop".

**5 Schema** — `screens-spec.schema.json`: bestehenden Klickdummy als Vorbild oder Minimalschema
(draft-07; `required: [spec_id, spec_version, class, screens]`; `class` als `enum` der 4 Pattern;
`screens` `minItems: 1`).

**6 Shell** — `snippets/shell-bootstrap/inject-widget.html` als `widget-include.html` kopieren;
`shell.html` mit einer `<section data-screen="<id>">` je Spec-Screen und vor `</body>`:

```html
<script>
  window.KLICKDUMMY_SPEC = { id: "<REPO_SHORT>:klickdummy-spec-<name>", version: "0.1", klickdummy_class: "<klasse>" };
  window.KLICKDUMMY_FEEDBACK_REPO = "<REPO_OWNER>/<REPO_NAME>";
</script>
<script src="../../platform-snippets/klickdummy/feedback-widget/widget.js" defer></script>
```

Gov-Repos optional: eigene `KLICKDUMMY_CATEGORIES` / `KLICKDUMMY_PERSONA_HOOK`.

**7 ADR** — `<ADR_PATH>/ADR-<NNN>-klickdummy-<name>.md`, Frontmatter:

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
sunset_after: <heute + 12 Monate>
extension_review_required: true   # bei mock; false sonst
related: []
---
```

Body: Kontext · Entscheidung (Klasse + warum) · Konsequenzen · Bezug.

**8 Makefile + CI** — `KLICKDUMMIES` um `<pfad>/screens-spec.yaml:<pfad>/screens-spec.schema.json`
ergänzen. Beim **ersten** Eintrag im Repo: `grep -rn "make klickdummy" .github/workflows/`; fehlt
der Job, im selben PR anlegen (Checkout → Python 3.12 → `make klickdummy-install` →
`make klickdummy`). Ohne CI-Gate bleibt Spec-Drift bis zum nächsten manuellen Lauf unentdeckt.

**9 Prüfen** — `make klickdummy` ⇒ I1–I4 PASS (AK1–AK4); Frontmatter-Grep (AK5); Makefile/CI-Grep (AK6).

**10 Lokal laden** — `python3 -m http.server 8765 -d <KLICKDUMMY_PATH>/<name>` →
`http://localhost:8765/shell.html?feedback=on` (AK7). Widget-Token nur lokal in DevTools
(`localStorage.setItem('klickdummy_github_token', …)`), nie in Dateien.

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

[1] Pfad:      <KLICKDUMMY_PATH>/<name>/
[2] Spec:      …/screens-spec.yaml
[3] Schema:    …/screens-spec.schema.json
[4] Shell:     …/shell.html
[5] ADR:       <ADR_PATH>/ADR-<NNN>-klickdummy-<name>.md
[6] Makefile:  KLICKDUMMIES += <eintrag>   CI-Job: <wired|already present>

== Akzeptanzkriterien ==
  AK1 I1 → <PASS|FAIL>   AK2 I2 → <PASS|FAIL>   AK3 I3 → <PASS|FAIL>   AK4 I4 → <PASS|FAIL>
  AK5 ADR-Frontmatter → <5/5>   AK6 Makefile+CI → <ok>   AK7 Shell lädt → <ok>

== KD-Referenz ==   (gleiches Schema wie /kd-scout und /kd-review)
  Name: <name>   Spec: <KLICKDUMMY_PATH>/<name>/screens-spec.yaml
  Lokal: …/shell.html?feedback=on   GitHub: — (kein Commit auf main)   iil.pet: — (kein Portal-Regen)

== Nächste Schritte ==
  - Commit + PR: feat/klickdummy-<name>   - Verifikation: /kd-review <name>
```

## Anti-Patterns

- ❌ Pfade/Orgs hart kodiert statt aus `project-facts.md` (`REPO_OWNER`/`REPO_NAME`/`KLICKDUMMY_PATH`)
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

- ☐ G1: Kontext aus `project-facts.md`, keine hart kodierten Pfade/Orgs im Ergebnis
- ☐ G2/G3: nichts überschrieben; bei Modus B erst nach „Ja, los" geschrieben
- ☐ AK1–AK4: `make klickdummy` ⇒ I1–I4 PASS (Output im Bericht, nicht behauptet)
- ☐ AK5: ADR-Frontmatter 5/5 Pflichtfelder, `<NNN>` = höchste + 1
- ☐ AK6: `KLICKDUMMIES`-Eintrag + CI-Job (`grep -rn "make klickdummy" .github/workflows/`)
- ☐ AK7: Shell lokal geladen, `data-screen` ≥1; `/kd-review` als nächster Schritt genannt
- ☐ G7: Gov-Repo ⇒ Feedback-Repo = eigene Org, keine Vendor-Namen
- ☐ G8: KD-Referenz mit `—` + Grund für GitHub/iil.pet
- ☐ Output-Format vollständig; bei vorbestehender I4-Drift separater Fix-PR benannt
- ☐ Optional: `/kd-sitemap`, wenn das Repo `klickdummy/sitemap/` führt (S14)

## Changelog

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
