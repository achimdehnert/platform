# CONCEPT-003 · Klickdummy-Playbook (Repo-Adoption)

**Stand:** 2026-05-20 · **Audience:** Repo-Owner, Klickdummy-Autor:innen, Reviewer
**Status:** living document, basiert auf konkreten Session-Erfahrungen 2026-05-19/20
**ADR-Grundlage:** `platform:ADR-211` (Rev 11, accepted — Cross-Repo-Rahmen), `platform:ADR-213` (Namensraum)
**Operative Regel:** `platform/policies/klickdummy.md` (auto-injiziert)

> **Verhältnis ADR ↔ Playbook:** `platform:ADR-211` ist die **Entscheidung** (Invarianten I1–I4, Klassen, Lebenszyklus, Off-Ramp). Dieses Dokument ist das **Begleit-Playbook** — wie man eine ADR-211-konforme Implementierung praktisch aufsetzt. Beides zusammen ist die vollständige Antwort: ADR-211 erklärt *warum/was*, CONCEPT-003 zeigt *wie konkret*.

---

## Zweck

Wiederverwendbares Playbook, um in einem **neuen Repo** einen ADR-211-konformen Klickdummy aufzusetzen — von der Klassen-Wahl über die Implementierung bis zur Off-Ramp. Codifies die Lehren aus den vier Erst-Implementierungen (meiki-hub, risk-hub, writing-hub, meiki-fristenmanagement).

> **Wann überhaupt ein Klickdummy?** Wenn nicht-triviale UX **vor der Implementierung** mit Fachseite validiert werden soll (Workshop-Tool, Vergabe-Abnahme-Artefakt). Nicht für Style-Tweaks, einzelne Felder, oder reine Backend-Refactors.

---

## 1 · Klassen-Auswahl (entscheidet alles Weitere)

| | **Mock-Prototyp** | **Demo-Render** |
|---|---|---|
| **Backend** | nein, separates Wegwerf-Artefakt | echte App mit `?demo=<state>` |
| **Off-Ramp** | endet bei Fachabteilungs-Review (Phase A) oder Übergang zu Echt-Templates (B/C) | Parity-grün ⇒ statische Quelle weg |
| **Prod-Risiko** | gering — kein realer Code-Pfad | **hoch** — env-gating + Prod-Smoke pflicht |
| **Best für** | Konzept-/Vergabephase ohne Zielsystem; Multi-Modul-Übersicht | App-Repo mit Zielsystem, Live-Drift-Schutz nötig |
| **Beispiel** | meiki-hub:ADR-020 (Manifest); meiki-hub:ADR-021 (App-Deep-Dive Fristen) | writing-hub:ADR-180 (Lecture-Outline-Wizard) |
| **Alternative** | risk-hub:ADR-046 (Spec-Driven mit verify_dummy.py) | — |

**Entscheidungsregel:** Existiert das Zielsystem schon (Templates/Routes), und ist die UX-Drift dort ein Live-Risiko? → Demo-Render. Sonst → Mock-Prototyp.

## 2 · Die vier Invarianten — was sie praktisch heißen

| Invariante | Was du *konkret* tust | Erzwingung |
|---|---|---|
| **I1 Spec-first** | Maschinenlesbare Spec (YAML/JSON) + JSON-Schema dazu. Markdown-Bullets zählen nicht. | `make klickdummy-i1` → schema-validate |
| **I2 Prod-Sicherheit** | `class: mock-prototyp` **oder** `class: demo-render` explizit im Spec-Root. „Keine Klasse" = Verstoß. Demo-Render zusätzlich: `?demo=` in PROD per Middleware-Test + Prod-Smoke widerlegt. | `make klickdummy-i2` |
| **I3 Off-Ramp** | Pro Screen `off_ramp_status ∈ {static, parity-staging, parity-green, removed}`. `off_ramp.doppelquell_grenze: prod-release`. | `make klickdummy-i3` |
| **I4 Namensraum** | Cross-Repo-Refs **immer** `repo:ADR-NNN`. Same-Repo bare `ADR-NNN` ok. | `platform/scripts/checks/adr_cross_repo_refs.sh` |

## 3 · Stack-Patterns (vier echte Vorbilder)

### A. Manifest-Driven Single-File-Mock
Beispiel: **meiki-hub `docs/01-architektur/mockups/klickdummy/`** (`meiki:ADR-020`)

```
klickdummy/
  shell.html              # Router + Login + Layout
  module-manifest.json    # SSoT: Module/LRA/Rollen/Eingangsquellen
  module-manifest.schema.json
  modules/<mod>/screens.html   # screen-pack pro Modul
  cases.json              # demo-Vorgänge
  dist/klickdummy.html    # gebauter Single-File (per build-script)
```

Stärken: viele Module übersichtlich, Buchung/RBAC-Schichten testbar.
Wann nutzen: Vergabe/Konzept, viele Module, Multi-LRA.

### B. YAML-Spec + JS-Shell (App-Deep-Dive)
Beispiel: **meiki-hub `docs/01-architektur/mockups/fristenmanagement-klickdummy/`** (`meiki:ADR-021`)

```
fristenmanagement-klickdummy/
  shell.html              # self-contained, alle Screens in <section data-screen>
  screens-spec.yaml       # I1-Artefakt
  screens-spec.schema.json
  assets/design-system.css
  README.md
```

Stärken: eine App tief, klare ADR-Verankerung in der Spec, persona-Switch, Target-Mock-Modal.
Wann nutzen: Eine App im Detail, multiple Personas, BRMS-Logik o.ä.

### C. Echt-Template-Render mit Parity-Test
Beispiel: **writing-hub `klickdummy/lecture-outline-wizard/`** (`writing-hub:ADR-180`)

```
klickdummy/<feature>/
  01-overview.html .. NN-export.html
  index.html
tests/ux/test_<feature>_parity.py   # DB-frei, Statik-Datei-Abgleich
docs/uxspec/<feature>/v1/flow.md
```

Stärken: Parity-Test schützt vor Drift zwischen Klickdummy und echter App.
Wann nutzen: App existiert, Klickdummy ist Abnahme-Artefakt mit Bestand.

### D. Spec-Driven UI Convention
Beispiel: **risk-hub `klickdummy/`** + `klickdummy/verify_dummy.py` (`risk-hub:ADR-046 Rev 2`)

```
klickdummy/
  <feature>.html
  verify_dummy.py         # Render-Gate (Walkthrough)
docs/uxspec/<feature>/v1/flow.md
tests/ux/test_<feature>.py
```

Stärken: Spec ist primäres Artefakt; Tests sind eine Validierungsschicht.
Wann nutzen: UX-Spec-First-Kultur, Visual-Regression optional.

## 4 · Adoption für ein neues Repo (Step-by-Step)

### 4.1 Repo-lokales ADR anlegen
`docs/adr/ADR-NNN-klickdummy-<feature>.md` mit Frontmatter:

```yaml
---
status: proposed | accepted
date: YYYY-MM-DD
deciders: [...]
conforms_to: platform:ADR-211   # ← Pflicht, I4-qualifiziert
...
---
```

### 4.2 Klickdummy-Verzeichnis nach Stack-Pattern (3 oben)

Mindest-Files je nach Klasse:

**Mock-Prototyp (A/B):**
```
klickdummy/<feature>/
  screens-spec.yaml       # mit class: mock-prototyp + ADR-Verankerung
  screens-spec.schema.json
  shell.html              # self-contained (oder dist/ mit build-script)
```

**Demo-Render (C):**
```
klickdummy/<feature>/   # Mock-Pendant (auch hier YAML-Spec)
tests/ux/test_<feature>_parity.py
config/settings/*.py    # `?demo=`-Middleware mit DEBUG/TESTING-Guard
```

### 4.3 Makefile-Targets

```makefile
.PHONY: klickdummy klickdummy-i1 klickdummy-i2 klickdummy-i3 klickdummy-i4

# Format: <spec_path>:<schema_path> (mehrere Klickdummies → Liste)
KLICKDUMMIES := \
  klickdummy/<feature>/screens-spec.yaml:klickdummy/<feature>/screens-spec.schema.json

klickdummy: klickdummy-i1 klickdummy-i2 klickdummy-i3 klickdummy-i4 ## Alle 4 Invarianten

klickdummy-i1:  ## I1 Spec ↔ Schema
	@python3 scripts/klickdummy/check_i1.py $(KLICKDUMMIES)
klickdummy-i2:  ## I2 Klassen-Deklaration
	@python3 scripts/klickdummy/check_i2.py $(KLICKDUMMIES)
klickdummy-i3:  ## I3 Off-Ramp / Lebenszyklus
	@python3 scripts/klickdummy/check_i3.py $(KLICKDUMMIES)
klickdummy-i4:  ## I4 Namensraum (Cross-Repo-Refs)
	@python3 scripts/klickdummy/check_i4.py docs/
```

Die vier `check_iN.py` sind generisch (in meiki-hub erstmals gebaut; portabel kopierbar).

### 4.4 CI-Integration

GitHub Actions Snippet:

```yaml
- name: Klickdummy-Invarianten
  run: make klickdummy
```

### 4.5 Platform-Registry (falls applicable)
Wenn das Repo zur achimdehnert-Org gehört, in `platform/registry/repos.yaml` eintragen — dann erscheint es im Plattform-SF1-Check (`klickdummy_registry.sh`). Fremd-Org-Repos (z. B. meiki-lra) tragen sich nicht ein und verantworten Konformität per eigenem CI.

## 5 · Patterns aus der Praxis (Lift-and-shift)

### 5.1 `shell.html` — self-contained Klickdummy-Shell

```html
<!DOCTYPE html>
<html lang='de'><head>
<meta charset='UTF-8'>
<meta name='klickdummy_class' content='mock-prototyp'>   <!-- I2 fallback -->
<title>... Klick-Dummy</title>
<link rel='stylesheet' href='assets/design-system.css'>
</head><body>
<aside><ul id='nav'></ul></aside>
<select onchange="setPersona(this.value)" id='personaSwitch'>
  <option value='sachbearbeiter'>Sachbearbeiter:in</option>
  <option value='teamleitung'>Teamleitung</option>
</select>
<main>
  <section data-screen='cockpit' class='active'>...</section>
  <section data-screen='worklist'>...</section>
  <!-- weitere screens -->
</main>
<!-- Target-Mock Modal -->
<div id='modal'>...</div>
<script>
const NAV = [{id:'cockpit', label:'…', icon:'⏱'}, ...];
function go(id){ location.hash = '#/' + id; }
function router(){ /* show/hide sections */ }
function ext(title, sub){ /* öffne Modal mit Systemgrenze */ }
window.addEventListener('hashchange', router);
router();
</script>
</body></html>
```

### 5.2 `screens-spec.yaml` — I1-Artefakt mit ADR-Anker

```yaml
$schema: ./screens-spec.schema.json
spec_id: <repo>:klickdummy-spec-<feature>
spec_version: "0.1"

adr:
  local: <repo>:ADR-NNN
  conforms_to: platform:ADR-211      # I4-qualifiziert
  sister_of:                          # andere Implementierungen unter ADR-211
    - meiki-hub:ADR-020
    - writing-hub:ADR-180

class: mock-prototyp                  # I2
class_evidence:
  no_backend: true
  no_demo_param: true
  target_mocks_visible: true
  systemgrenzen: [DMS-Adapter, FV-Adapter, ...]

off_ramp:
  doppelquell_grenze: prod-release    # I3 Default

screens:
  - id: cockpit
    title: …
    personas: [sachbearbeiter, teamleitung]
    parity_acceptance:
      - id: cockpit.kpi-vollstaendig
        check: "Alle 4 KPI-Tiles zeigen Live-Werte (Ampel-Klassen)"
    off_ramp_status: static            # static | parity-staging | parity-green | removed
```

### 5.3 Sortierbare + filterbare Tabellen

Häufiger Klickdummy-Wunsch („Worklist"). Pattern aus dieser Session:

```html
<div class='filterbar' id='wl-filter'>
  <button class='chip active' data-filter='all'>Alle</button>
  <button class='chip' data-filter='hot'>Nur 🔴/🟠</button>
</div>
<table id='wl-table'>
  <thead><tr>
    <th class='sortable' data-sort='id'>Fall</th>
    <th class='sortable' data-sort='due'>Fristende</th>
  </tr></thead>
  <tbody>
    <tr data-amp='rot' onclick='go("detail")'>
      <td>WG-2026-000812</td>
      <td data-sortkey='2026-05-15'>15.05.2026</td>  <!-- semantischer Sort -->
    </tr>
  </tbody>
</table>
```

```js
// Filter
document.querySelectorAll('#wl-filter .chip').forEach(b => b.onclick = () => {
  document.querySelectorAll('#wl-filter .chip').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  document.querySelectorAll('#wl-table tbody tr').forEach(tr => {
    const show = b.dataset.filter === 'all' ||
                 (b.dataset.filter === 'hot' && ['rot','orange'].includes(tr.dataset.amp));
    tr.classList.toggle('row-hidden', !show);
  });
});
// Sort mit data-sortkey-Override
let st = {col:null, asc:true};
document.querySelectorAll('#wl-table th.sortable').forEach((th, i) => th.onclick = () => {
  const asc = (st.col === i) ? !st.asc : true; st = {col:i, asc};
  const tbody = th.closest('table').querySelector('tbody');
  const rows = [...tbody.querySelectorAll('tr')];
  rows.sort((a,b) => {
    const key = tr => tr.cells[i].dataset.sortkey || tr.cells[i].textContent.trim();
    return (asc ? 1 : -1) * key(a).localeCompare(key(b), 'de', {numeric:true});
  });
  rows.forEach(r => tbody.appendChild(r));
  th.closest('tr').querySelectorAll('th').forEach(h => h.removeAttribute('data-sort-dir'));
  th.setAttribute('data-sort-dir', asc ? 'asc' : 'desc');
});
```

CSS:
```css
.kv-table th.sortable{cursor:pointer; user-select:none; position:relative; padding-right:24px}
.kv-table th.sortable::after{content:"⇅"; position:absolute; right:8px; opacity:.35}
.kv-table th.sortable[data-sort-dir="asc"]::after{content:"▲"; opacity:1}
.kv-table th.sortable[data-sort-dir="desc"]::after{content:"▼"; opacity:1}
.kv-table tbody tr.row-hidden{display:none}
```

### 5.4 Target-Mock (Systemgrenzen sichtbar)

```html
<button onclick="ext('DMS-Adapter', 'GET /wiedervorlage/123')">DMS-Adapter</button>
<div id='modal'>
  <span class='x' onclick="closeModal()">×</span>
  <h2 id='mTitle'></h2><div id='mSub'></div>
  <div>Systemgrenze — im Klick-Dummy nicht ausgeführt. Real wäre dies ein Absprung/Call in das angebundene System.</div>
</div>
```

```js
function ext(title, sub){
  document.getElementById('mTitle').textContent = title;
  document.getElementById('mSub').textContent = sub || '';
  document.getElementById('modal').classList.add('open');
}
```

### 5.5 Wizard / Multi-Step

```html
<div class='wizard-steps'>
  <div class='ws active'>1. Eingabe</div>
  <div class='ws'>2. Prüfung</div>
  <div class='ws'>3. Freigabe</div>
</div>
<div id='step1'>...</div><div id='step2' style='display:none'>...</div>
```

```js
function wizard(step){
  ['step1','step2','step3'].forEach((id,i) => {
    document.getElementById(id).style.display = i+1 === step ? 'block' : 'none';
  });
  document.querySelectorAll('.ws').forEach((w,i) => {
    w.classList.toggle('done', i+1 < step);
    w.classList.toggle('active', i+1 === step);
  });
}
```

### 5.6 DMS-/Adapter-Agnostik

**Hauptscreens**: generische Adapter-Begriffe (`DMS-Adapter`, `FV-Adapter Wohngeld`, `Melderegister-Adapter`, `Signatur-Adapter`).
**Hersteller-Marken** (enaio, d.velop, OK.Wobis, BayBIS, BayernID/BundID): **nur auf separatem „Pilot-Anbindung"-Screen** — sonst macht der Klickdummy implizit eine technische Vorentscheidung.

## 6 · Fallstricke (Lessons aus dieser Session)

| # | Falle | Belegt | Fix |
|---|---|---|---|
| L1 | YAML-Quote-Falle: `repo:ADR-NNN` enthält `:` → ScannerError im Block-Style | ADR-211 Rev 8 | Quoten: `conforms_to: "platform:ADR-211"` oder inline-Form |
| L2 | iil-adrfw Schema `additionalProperties: false` | ADR-211 Rev 8 | Nur Standard-Felder im Frontmatter; Custom-Info im Body |
| L3 | Bash `cmd \| grep -q` + `pipefail` → SIGPIPE false-FAIL | SF1 `--main` Bug | `grep -E ... >/dev/null` (kein early-close) |
| L4 | `$(cmd)` strippt trailing-newline → `printf %s` vs Datei mit Newline ≠ | SF6 Bug | Direkter `<(cmd)`-Subprocess-Substitution |
| L5 | Tote Filter-Chips ohne onclick | Worklist-Präs-Feedback | Filter-Chips mit `data-filter`-Attr + JS-Listener |
| L6 | Spalten-Sort lexikographisch falsch für Daten/Ampel | Worklist | `data-sortkey`-Override (ISO-Datum, Dringlichkeits-Index) |
| L7 | Working-Tree-Scan ≠ origin/main-Scan (Dev-Branch-Drift) | SF1 Default | `--main`-Modus mit `git ls-tree` + `git grep` |
| L8 | Pinned-Worktree-Stale nach Policy-Merge | SF6 | `git -C pinned fetch + checkout origin/main` als Pflicht nach Policy-PRs |
| L9 | ADR-Nummern-Kollision über Repos (ADR-180 platform vs writing-hub) | Drift-Episode 2026-05-19 | `repo:ADR-NNN` qualifiziert (I4 / ADR-213) |
| L10 | Mixed-Scope-PR (Klickdummy + ADR-Set zusammen) erschwert Review | meiki #20 | `git cherry-pick` auf saubere Branches → 2 PRs |
| L11 | Klickdummy-Klasse implizit aus Prosa | initialer ADR-211 | `klickdummy_class`-Feld im Spec-Root explizit + class_evidence |
| L12 | Hersteller-Marken in Hauptscreens machen implizite Vorentscheidung | fristen-klickdummy v0.1 | Trennung „Pilot-Anbindung"-Screen |
| L13 | Adversarial-Review 1× reicht nicht | ADR-211 Rev 2→9 | Multi-Pass-Reviews, Befunde explizit nummeriert (F1, F2, …) |
| L14 | Same-Repo vs Cross-Repo-Ref-Inkonsistenz beim Reader | I4 Diskussion | Same-Repo bare `ADR-NNN` ok für Lesefluss; Cross-Repo immer qualifiziert |

## 7 · Lebenszyklus eines Klickdummys

```
  ┌────────────────────────────────────────────────────────────────┐
  │  Phase A — kein Zielsystem                                     │
  │  - Workshop-Tool, Vergabe-Artefakt                             │
  │  - Endet: ADR-Status accepted-frozen / superseded              │
  │  - Spec eingefroren, Pfad → klickdummy/archive/                │
  └────────────────────────────────────────────────────────────────┘
                                ↓ (sobald erste Impl-Route entsteht)
  ┌────────────────────────────────────────────────────────────────┐
  │  Phase B — Transition (je Screen)                              │
  │  - Klickdummy + echte App nebeneinander                        │
  │  - Pro Screen: off_ramp_status: static → parity-staging        │
  └────────────────────────────────────────────────────────────────┘
                                ↓ (Parity-Test grün, prod-Release)
  ┌────────────────────────────────────────────────────────────────┐
  │  Phase C — mit Zielsystem                                      │
  │  - Parity-grün/Screen ⇒ statische Quelle entfernen             │
  │  - Doppelquell-Grenze: prod-Release                            │
  │  - status: parity-green → removed                              │
  └────────────────────────────────────────────────────────────────┘
```

## 8 · Tooling-Inventar (zentral verfügbar)

- **Plattform-Skripte:**
  - `platform/scripts/checks/klickdummy_registry.sh` — Cross-Repo-Konformität (SF1)
  - `platform/scripts/checks/adr_cross_repo_refs.sh` — I4 / ADR-213-Lint (SF5)
  - `platform/scripts/checks/klickdummy_policy_sync.sh` — Pinned-Worktree-Konsistenz (SF6)
- **Repo-Skripte (in jedem Klickdummy-Repo zu spiegeln):**
  - `scripts/klickdummy/check_i1.py` — Spec ↔ Schema
  - `scripts/klickdummy/check_i2.py` — Klassen-Deklaration
  - `scripts/klickdummy/check_i3.py` — Off-Ramp
  - `scripts/klickdummy/check_i4.py` — Namensraum
- **Policy:** `platform/policies/klickdummy.md` (auto-injiziert in jede Session)

## 9 · Checkliste vor PR-Merge

- [ ] Spec hat `class: mock-prototyp` ODER `class: demo-render` mit `class_evidence`
- [ ] `conforms_to: platform:ADR-211` im Repo-ADR-Frontmatter (gequoted!)
- [ ] Alle Cross-Repo-Refs als `repo:ADR-NNN` (Same-Repo bare zulässig)
- [ ] `make klickdummy` exit 0 (alle 4 Checks grün)
- [ ] `iil-adrfw validate docs/adr/` grün (Repo-ADR + Plattform-Schema)
- [ ] shell.html oder Templates rendern lokal (Server-Smoke `curl /shell.html → 200`)
- [ ] Demo-Render-Repo: Middleware-Test + Prod-Smoke `?demo=` → 404 im PROD
- [ ] Adversarial-Review-Pass(e) dokumentiert im ADR-Body (Revisionshistorie)
- [ ] Hersteller-Marken nur in „Pilot-Anbindung"-Screen, Hauptscreens DMS-agnostisch
- [ ] Filter/Sort/Wizard funktional (keine toten Buttons)

## 10 · Repo-Adoptionsstatus (Stand 2026-05-20)

| Repo | ADR | Pattern | Stand |
|---|---|---|---|
| **meiki-hub** | `meiki:ADR-020` | A — Manifest-Driven Static Mock | ✅ accepted, gemergt (`feat/klickdummy-v04`); 7 Module + Querschnitt; CI grün |
| **meiki-hub** | `meiki:ADR-021` | B — YAML-Spec + JS-Shell (App-Deep-Dive) | ✅ accepted; 8 Screens (Fristenmanagement); PR #21 offen (Klickdummy v0.1) + PR #22 (Phase-1-ADRs) |
| **writing-hub** | `writing-hub:ADR-180` | C — Echt-Template-Render mit Parity-Test | ✅ accepted, gemergt; Lecture-Outline-Wizard, 8 Screens + Parity-Test (10 passed, DB-frei) |
| **risk-hub** | `risk-hub:ADR-046 Rev 2` | D — Spec-Driven UI Convention | ✅ accepted, gemergt; `klickdummy/verify_dummy.py` + `docs/uxspec/<feature>/v1/flow.md`-Konvention |
| **dev-hub** | (offen) | (in Adoption) | ⏸ In Adoption — Pattern und ADR-Nummer offen. Empfehlung: bei UI-Mehrkomponenten-Cockpit → Pattern A oder B |
| **pptx-hub** | (offen) | (in Adoption) | ⏸ In Adoption — Pattern und ADR-Nummer offen. Bei reinem Rendering-Service ohne UX-Wizard ist Klickdummy evtl. nicht ADR-pflichtig (siehe Threshold §1) |

**Cross-Org / nicht-registry-Repos** (z. B. `meiki-lra/meiki-hub`) verantworten Konformität über die **eigene** Repo-CI; SF1 (`klickdummy_registry.sh`) deckt nur platform-`registry/repos.yaml`-Repos ab. Die Implementierungsliste hier ist die kanonische Übersicht.

## 11 · Bezug

- `platform:ADR-211` — Klickdummy-Cross-Repo-Rahmen (Invarianten I1–I4, Phasen, Off-Ramp)
- `platform:ADR-213` — `repo:ADR-NNN`-Referenz-Format plattformweit
- `platform/policies/klickdummy.md` — operative Auto-Injektions-Regel
- `meiki-hub:ADR-020` — Manifest-Klickdummy-Konvention (Pattern A)
- `meiki-hub:ADR-021` — Fristenmanagement-App-Deep-Dive (Pattern B)
- `risk-hub:ADR-046 Rev 2` — Spec-Driven UI Convention (Pattern D)
- `writing-hub:ADR-180` — Lecture-Outline-Wizard mit Parity (Pattern C)
- Drift-Memory `2026-05-19-klickdummy-adr180-collision` (Auslöser-Episode)

## Glossar (lokal)

| Begriff | Definition |
|---|---|
| **Klickdummy** | Renderer einer Anforderungs-Spec zur frühen Validierung |
| **Mock-Prototyp** | Wegwerf-Renderer ohne Backend (Systemgrenzen als Target-Mock) |
| **Demo-Render** | Env-gegateter Zustand der echten App (`?demo=`) — Prod-Sicherheitsfläche |
| **Parity-Test** | Renderer↔Implementierung-Äquivalenztest — Gate **und** Off-Ramp |
| **Off-Ramp** | Parity-grün ⇒ statische Quelle entfernt; Grenze: prod-Release |
| **Target-Mock** | Sichtbar gemachte Systemgrenze (benannter Absprung statt totem Link) |
| **Persona-Switch** | Rollen-Umschalter im Klickdummy (z. B. Sachbearbeiter ↔ Teamleitung) |
| **Adapter-Agnostik** | Hauptscreens nutzen generische Adapter-Begriffe; Marken nur in einem dedizierten Screen |
