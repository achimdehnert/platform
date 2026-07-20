---
id: ADR-272
title: "Adopt a machine-readable distribution contract with bounded drift-detection latency"
status: accepted
decision_date: 2026-07-11
deciders:
  - "Achim Dehnert"
consulted: []
informed: []
domains:
  - governance
  - tooling
  - distribution
tags: [skills, policies, distribution, drift, cc-skill-dist, registry]
related:
  - "ADR-229"
  - "ADR-230"
  - "ADR-234"
  - "ADR-258"
  - "ADR-263"
  - "ADR-265"
---

<!--
  ADR-TEMPLATE v2.0 (2026-02-21)
  Basis: MADR 4.0 + Platform-Governance (ADR-021, ADR-046, ADR-056, ADR-059)
  Strategie: techdocs-first, dev-hub-sync, Drift-Detector-kompatibel
-->

# ADR-272: Adopt a machine-readable distribution contract with bounded drift-detection latency

*(v1.1, REC-1: „redistribution latency" → „drift-detection latency" — der ADR begrenzt nachweislich nur die Detektion, nicht die Aktualisierung selbst; Definitionen in §3.1. Dateiname bleibt unverändert, Links stabil.)*

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Accepted (2026-07-11, Owner-Go auf Basis v1.1 — §External Sparring)  |
| **Scope**       | platform                                                             |
| **Erstellt**    | 2026-07-11                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | wirdigital (PR #1072) · intern: deep-review · extern: GPT-5.5        |
| **Supersedes**  | –                                                                    |
| **Superseded by** | –                                                                  |
| **Relates to**  | ADR-230 (cc-first-skill-distribution), ADR-234 (clean-state-invariant), ADR-258 (cc-hook-distribution), ADR-263 (windsurf-rules-distributor-hardening), ADR-265 (untrack-distributed-symlink-targets), ADR-229 (windsurf-distribution-single-source) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten              |
|----------------|------------|---------------------------------------------|
| `platform`     | Primär     | `registry/distribution.yaml` (neu), `tools/cc-skill-dist/`, `scripts/{sync-workflows.sh,gen_project_facts.py,ship-workflow.sh}`, `.windsurf/workflows/session-start.md` |
| alle Consumer-Repos | Sekundär | `.windsurf/workflows/` (Symlinks), `project-facts.md`, `.github/workflows/receive-windsurf-rules.yml` |
| Maschinen (`~/.claude`) | Sekundär | `commands/`, `skills/`, `hooks/managed/`, `policies` (Symlink) |

---

## Decision Drivers

- **Die 4 Drift-Muster sind struktureller Natur, nicht episodisch**: Der /repo-optimize-Lauf 2026-07-03 fand (1) Regel-Kopie statt Regel-Verweis, (2) Kanon-Konflikte, (3) lügende Indizes, (4) Redistribution-Latenz. Die Fix-Runde 2026-07-04 (PRs #898/#905/#906) behob Instanzen der Muster 1–3 — am 2026-07-11 lagen bereits drei **neue** Instanzen vor (siehe §1.1). Punktuelle Sweeps skalieren nicht.
- **10 Verteilmechanismen ohne gemeinsamen Vertrag**: cc-skill-dist (3 Lanes), sync-workflows.sh, claude-policy, platform-pinned-Refresh, windsurf-subset, receive-windsurf-rules, gen_project_facts, ship-workflow — jeder mit eigener Quelle, eigenem Trigger, eigenem (oder keinem) Gate. Niemand kann heute maschinell beantworten: „Was wird von wo wohin verteilt, und was sichert es?"
- **Redistribution-Latenz ist unbounded**: `~/.claude/commands` wird nur manuell regeneriert (Stand 2026-07-11: 4 Commits hinter main, ohne Detektion). Der Policy-Refresh-Hook deckt nur `~/.claude/policies` ab. Der ADR-265-Realfall (Policies froren wochenlang auf Mai-Stand ein) hat gezeigt, was still veraltende Kopien kosten.
- **Ein Mechanismus verletzt die Autonomie-Gates aktiv**: `receive-windsurf-rules.yml` pusht in 19 Repos direkt auf `main` mit `[skip ci]` und `contents:write` — genau das Muster, das das Gate `autonomous-no-human-review` verbietet. ADR-263 (Härtung) ist proposed/not-started; dieser ADR erhöht dessen Dringlichkeit, ohne ihn neu zu entscheiden.

---

## 1. Context and Problem Statement

Die Plattform verteilt Regeln, Skills, Hooks, Policies und Registry-Fakten aus dem
platform-Repo an ~44 Repos und an Maschinen-Verzeichnisse (`~/.claude/*`). Die
einzelnen Mechanismen sind solide gebaut (MANAGED-BY-Header, content_hash, atomare
Swaps, Round-Trip-CI bei cc-skill-dist; hartes Registry-Gate bei ADR-234). Was fehlt,
ist die **Systemebene**: ein Vertrag, der für *jeden* Verteilweg dieselben Invarianten
erzwingt. Ohne ihn entstehen die dokumentierten Drift-Muster immer wieder neu — jede
Korrektur repariert eine Instanz, nicht die Klasse.

### 1.1 Ist-Zustand (Evidenz 2026-07-11)

Mechanismen-Inventar (Kurzform; vollständig in `registry/distribution.yaml`):

| Mechanismus | Quelle → Ziel | Trigger | Gate |
|---|---|---|---|
| cc-skill-dist commands/skills/hooks | `.windsurf/workflows/`, `skills/`, `tools/hooks/` → `~/.claude/*` | manuell pro Maschine | Round-Trip-CI (nur HEAD, nicht Live) |
| sync-workflows.sh | `.windsurf/workflows/` → Symlinks in Repos | manuell + /session-start | keins |
| claude-policy | `policies/*.md` → Orchestrator-Memory | CI bei Merge | idempotenter Sync, kein Gate |
| platform-pinned-Refresh | `policies/` → `~/.claude/policies` (Symlink) | SessionStart-Hook | fail-soft (friert bei DIRTY ein) |
| receive-windsurf-rules | platform → 19 Repos, push auf main | `repository_dispatch` | **keins, umgeht CI per [skip ci]** |
| gen_project_facts.py | `registry/canonical.yaml` + `github_repos.yaml` → `project-facts.md` je Repo | manuell + /session-start | keins, kein generated-Header |
| ship-workflow.sh | **hartkodierte** 18-Repo-Liste | manuell | keins |

Frische Belege, dass die Muster nach der Fix-Runde 2026-07-04 zurückkehrten:

1. **Lügender Index auf ADR-Ebene**: ADR-230 §8 Rollout-Gate hat alle Checkboxen
   leer („nicht ausgerollt"), während `~/.claude/commands/` real 82/82 generierte
   Dateien mit MANAGED-BY-Footer + `manifest.json` trägt — der Rollout IST vollzogen,
   das Dokument bildet ihn nicht ab.
2. **Policy ohne Gate wird verletzt**: `~/.claude/skills/manifest.json` trägt
   `generator_version: "0.2.0-prototype"` — wörtlich das Anti-Pattern F-C aus
   `policies/claude-skills.md`, das dort seit dem Retro verankert ist. Prosa-Regeln
   ohne CI-Gate halten nicht.
3. **Kanon-Konflikt bei Repo-Listen**: `ship-workflow.sh` (hartkodiert, 18 Repos,
   inkl. veralteter Einträge), `sync-workflows.sh` (liest `github_repos.yaml`) und
   `registry/canonical.yaml` (25 prod_url-Einträge) führen drei divergierende
   Prod-Repo-Listen. Derselbe Klassenfehler kostete am selben Tag Abdeckung: der
   manuelle 9-Repo-Deploy-Scan aus session-start übersah tax-hub, das der
   Registry-Filter fand.

### 1.2 Warum jetzt

Am 2026-07-11 wurden drei geplante Cloud-Agenten aufgesetzt (deploy-health-triage,
fleet-drift-report, pr-review-prep), die täglich gegen Registry und GitHub-Zustand
prüfen. Damit steigt die Zahl der Konsumenten, die sich auf kanonische Quellen
verlassen — und der Preis jeder stillen Kopie-Drift. Gleichzeitig lieferte die
Evidenz-Exploration für diesen ADR die drei o.g. Rückfall-Belege binnen Minuten:
das Problem ist billig zu finden und wird ohne Strukturänderung weiter auftreten.

---

## 2. Considered Options

### Option A: Dünner Verteil-Vertrag + 4 Invarianten + Latenz-Detektion ✅

Ein maschinenlesbares Inventar (`registry/distribution.yaml`) beschreibt jeden
Verteilweg; vier Invarianten gelten für alle Wege; Latenz wird dort gemessen, wo
sie sichtbar ist (Session-Start auf der Maschine, CI im Repo). Kein neuer
Verteilmechanismus, kein Daemon.

**Pros:**
- Right-sized: kodifiziert und gated, was bereits Best Practice der besten Lane ist (cc-skill-dist)
- Jede Invariante adressiert genau ein dokumentiertes Drift-Muster
- Inkrementell umsetzbar (4 kleine Phasen, je 1 PR)
- Ehrliche Architektur-Grenze: CI kann Maschinen-Verzeichnisse nicht sehen → Detektion läuft im Session-Start, wie beim bewährten Policy-Refresh

**Cons:**
- Der Vertrag ist selbst eine weitere Datei, die lügen kann (Mitigation: Contract-Lint in CI, §4.1)
- Latenz wird detektiert, nicht eliminiert (bewusst: Auto-Push wäre Option B)

### Option B: Zentraler Auto-Distributor (Push-Modell verallgemeinern)

Alle Ziele (Repos + Maschinen) werden bei jedem Merge automatisch beschrieben,
nach dem Vorbild von `receive-windsurf-rules.yml`.

**Pros:**
- Latenz → ~0

**Cons:**
- Verallgemeinert genau den Mechanismus, der heute das größte Risiko ist (push auf main, `[skip ci]`, org-weites Schreibrecht) → **Abgelehnt weil:** verletzt das Gate `autonomous-no-human-review`; Maschinen-Verzeichnisse sind aus CI ohnehin nicht erreichbar; ADR-263 will das Bestandsexemplar härten/stilllegen, nicht vermehren.

### Option C: Status quo + weitere punktuelle Sweeps

Muster bei Auftreten per Sweep beheben (wie 2026-07-04).

**Pros:**
- Kein Vorab-Aufwand

**Cons:**
- Empirisch widerlegt: drei Rückfall-Instanzen binnen einer Woche nach dem letzten Sweep → **Abgelehnt weil:** wiederkehrende Instanz-Kosten ohne Klassen-Fix; genau die Drift-Historie, die dieses ADR motiviert.

### Option D: Pull-basierte, versionierte Distributions-Bundles *(ergänzt v1.1, REC-11)*

CI erzeugt aus den Quellen ein unveränderliches, gehashtes Bundle mit Versionskennung; Ziele ziehen eine explizite Version und melden ihren Ist-Stand.

**Pros:**
- Soll/Ist als eindeutige Versionsdifferenz statt heterogener Dateivergleiche; saubere Trennung Veröffentlichung/Bezug/Aktivierung

**Cons:**
- Neues Release-/Packaging-Konzept quer über alle Lanes; löst inaktive Maschinen ebenfalls nicht → **Nicht jetzt:** als spätere Zielarchitektur notiert (Konzept-Kandidat), ändert die heutige Entscheidung nicht.

### Option E: Selbstbeschreibende Verteiler (describe-Modus) *(ergänzt v1.1, REC-11)*

`distribution.yaml` wird aus maschinenlesbaren Selbstbeschreibungen der Verteiler generiert statt manuell gepflegt.

**Pros:**
- Reduziert die häufigste Driftklasse des Vertrags selbst (fehlender/veralteter Inventareintrag)

**Cons:**
- Adapter für heterogene Alt-Mechanismen nötig → **Teilübernahme:** describe-Pflicht gilt ab P2 für **neu eingeführte** Verteiler; der Alt-Bestand bleibt manuelles Inventar.

---

## 3. Decision Outcome

**Gewählte Option: Option A — Dünner Verteil-Vertrag + 4 Invarianten + Latenz-Detektion.**

Option A macht die Systemebene explizit und prüfbar, ohne einen neuen
Verteilmechanismus zu bauen. Option B skaliert das gefährlichste Bestandsmuster,
Option C ist durch die Rückfall-Evidenz widerlegt. Die Invarianten kodifizieren,
was die reifste Lane (cc-skill-dist) bereits lebt — Neues wird nur dort gebaut,
wo eine Lücke belegt ist.

### Die vier Invarianten

| # | Invariante | Adressiertes Muster |
|---|---|---|
| **I1** | Jedes verteilte Artefakt ist (a) **Symlink/Pointer** oder (b) **deterministisch generierte Kopie** mit MANAGED-BY-Marker (Quelle + content_hash) und Drift-Gate — beide Formen sind zulässig (ADR-230). Verboten ist allein die dritte Form: **manuell duplizierter Regeltext** ohne Marker. *(v1.1, REC-6)* | Regel-Kopie |
| **I2** | Je Artefakt-Typ (= Lane in `registry/distribution.yaml`) genau **eine** deklarierte kanonische Quelle bzw. Quellen-Liste (§3.1); Konsumenten (Skripte, Skills) lesen Listen aus der Registry statt sie zu hartkodieren. *(v1.1, REC-7)* | Kanon-Konflikt |
| **I3** | Behauptungen über den **aktuellen** Verteil-Zustand (Rollout-Checkboxen, Indizes, Manifeste) sind **generiert + CI-gegated** oder werden automatisiert als veraltet markiert; ein bloßes Stand-Datum genügt nur für explizit als **Snapshot** gekennzeichnete historische Aussagen. *(v1.1, REC-8)* | Lügender Index |
| **I4** | **Drift-Detektions-Latenz** ist gemessen und begrenzt — auf Maschinen nur während aktiver Sessions (WARN-Banner, laut aber nicht blockierend); Meldesemantik nach Risikoklasse, Eskalation und Mess-Felder in §3.1. Für nie gestartete Maschinen existiert **keine** Obergrenze (ehrliche Grenze). *(v1.1, REC-1/2)* | Redistribution-Latenz |

### 3.1 Begriffs- und Mess-Definitionen *(v1.1, aus externem Review)*

**Latenz-Begriffe (REC-1):** *Detektions-Latenz* = Zeit von kanonischer Änderung bis zur ersten Meldung · *Remediations-Latenz* = bis zur tatsächlichen Aktualisierung des Ziels · *Redistributions-Latenz* = Summe beider. Dieser ADR begrenzt **nur die Detektions-Latenz**, und auf Maschinen nur während aktiver Sessions; Remediation bleibt ein manueller Akt mit Eskalationsregel (unten).

**Risikoklassen (REC-2, bewusst nur zwei — YAGNI):**

| Klasse | Artefakte | Meldesemantik |
|---|---|---|
| A (kritisch) | `policies/`, `tools/hooks/`, Workflow-Quellen | jedes Content-Delta → Meldung beim nächsten Check |
| B (Komfort) | commands-/skills-Kopien, `project-facts.md` | Meldung erst bei Freshness > 7 Tage |

**Artefakttyp / kanonische Quelle (REC-7):** Ein *Artefakttyp* ist eine Lane in `registry/distribution.yaml`; seine *kanonische Quelle* ist die dort deklarierte `source`-Liste. Zusammengesetzte Artefakte (z.B. `project-facts.md`) sind deterministische Ableitungen aus **mehreren** Inputs — jeder Input ist für seine Fakten kanonisch, die Ableitung selbst ist nie Quelle. *Zwischenzustand bis ADR-273 (M28-6):* `canonical.yaml` führt für Repo-Fakten; `github_repos.yaml` ist geduldeter, in der Lane sichtbar deklarierter Zusatz-Input.

**Mess-Definition (REC-14):** Jede Detektion erzeugt eine grep-bare `DIST-DRIFT`-Zeile mit: Lane · Quell-Commit-Delta · `first_detected_at` · nach Behebung `remediated_at` + Status. Implementierung: P2 (#1073).

**Eskalationsregel (REC-10):** Ein WARN, das >14 Tage unbehoben bleibt, führt der tägliche fleet-drift-Report als Zeile im rollenden Sammel-Issue — der persistente, abfragbare Zustand existiert damit bereits, es wird kein neuer Mechanismus gebaut.

**Wirksamkeits-Zählung (REC-9, right-sized):** Für §8.3 zählen **deduplizierte** Defekt-Ereignisse (dasselbe Ereignis = 1), belegt aus zwei Quellen: Session-Retros **und** `DIST-DRIFT`-Zeilen. Eine vollwertige Event-Datenbank ist bewusst nicht Scope.

---

## 4. Implementation Details

### 4.1 P1 — Verteil-Vertrag (dieser PR)

`registry/distribution.yaml`: ein Eintrag je Verteilweg mit `source`, `targets`,
`mechanism`, `trigger`, `gate`, `header`, `owner_adr`. Initialbefüllung = das
Inventar aus §1.1 (10 Einträge). Contract-Lint (P2) prüft: jede `source` existiert,
jedes deklarierte `gate` existiert als Workflow/Skript, kein Verteilweg ohne Eintrag
(Detektion neuer Verteiler über Heuristik: Workflows mit `contents:write` auf
Fremd-Repos bzw. Skripte, die nach `~/.claude` schreiben).

### 4.2 P2 — Latenz-Detektion + Header-Nachrüstung

- `/session-start` ruft `tools/cc-skill-dist/doctor.py --live --quick` gegen
  `~/.claude/commands` (analog Policy-Refresh-Banner, WARN statt Hard-Fail —
  Alarm-Müdigkeits-Lehre aus dem Advisory-Scanner-Fall).
- `gen_project_facts.py` schreibt einen generated-Header (Quelle, Commit,
  `do_not_edit`) in jede `project-facts.md` (I1-Lücke aus §1.1).
- Contract-Lint als Job in `validate-workflows.yml` — geprüft wird nicht nur Existenz, sondern **referenzielle und operative Konsistenz**: das deklarierte Gate muss den Verteilweg nachweisbar beobachten und als blockierend/beobachtend klassifiziert sein *(v1.1, REC-4)*.
- **describe-Pflicht für neue Verteiler** *(v1.1, REC-11/Option E)*: neu eingeführte Verteilmechanismen liefern eine maschinenlesbare Selbstbeschreibung, gegen die ihr Lane-Eintrag geprüft wird.
- Erkennung **nicht deklarierter** Verteilwege wird verbindlicher Confirmation-Mechanismus *(v1.1, REC-5)*: Heuristik über typische Primitive (cross-repo `contents:write`, Schreibziele `~/.claude/*`), dokumentierte Falschpositiv-Regel + gegatete Ausnahmen.

### 4.3 P3 — Kanon-Konsolidierung der Repo-Listen

`ship-workflow.sh` liest `ALL_REPOS` aus `tools/registry_api.py` (Filter wie
`deploy_failure_monitor.load_deploy_repos()`); `sync-workflows.sh` wechselt von
`github_repos.yaml` auf `canonical.yaml`-Reader. Die hartkodierte Liste in
`.windsurf/workflows/session-start.md` §0.7 bekommt einen Verweis-Kommentar auf
die Registry als Quelle.

### 4.4 P4 — Index-Reconciliation

ADR-230 §8-Checkboxen per Amendment gegen die Live-Manifeste abgleichen
(Evidenz: `~/.claude/commands/manifest.json`); `-prototype`-Suffix aus der
skills-Lane entfernen (ein `generate.py --kind skills --allow-live`-Lauf nach
Merge des Versions-Fixes). Beides kleine, getrennte PRs.

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `platform`     | P1 Vertrag + ADR | ✅ Abgeschlossen | 2026-07-11 | PR #1072, merged `be0ec47` |
| `platform`     | P2 Latenz + Header + Lint | ⬜ Ausstehend | – | Issue folgt (model:sonnet-5) |
| `platform`     | P3 Repo-Listen-Kanon | ⬜ Ausstehend | – | Issue folgt (model:sonnet-5) |
| `platform`     | P4 Index-Reconciliation | ⬜ Ausstehend | – | ADR-230-Amendment |

---

## 6. Consequences

### 6.1 Good

- Drift-Muster werden auf Klassen-Ebene adressiert; neue Verteilwege erben die Invarianten statt sie neu zu erfinden
- „Was wird von wo wohin verteilt?" ist erstmals maschinell beantwortbar — auch für die neuen Cloud-Agenten und für /platform-audit
- Latenz-Drift wird am Ort ihrer Entstehung sichtbar (Session-Start), ohne neues Schreibrecht irgendwo

### 6.2 Bad

- Ein weiterer Registry-Bestandteil, der gepflegt werden muss (Mitigation: Contract-Lint failt bei toten Quellen)
- Session-Start wird um einen Check länger (Mitigation: `--quick`, Sekundenbereich)

### 6.3 Nicht in Scope

- Härtung/Stilllegung von `receive-windsurf-rules.yml` — bleibt ADR-263 (dieser ADR erhöht nur die Priorität)
- Konsolidierung `canonical.yaml` vs. `github_repos.yaml` als SSoT-Frage (eigene Entscheidung, Kandidat ADR-273; §4.3 migriert nur Konsumenten auf canonical)
- Auto-Push auf Maschinen oder Repos (bewusst verworfen, Option B)
- Pull-Bundle-Zielarchitektur (Option D) — als Konzept-Kandidat notiert, nicht Teil dieser Entscheidung
- Garantierte **Remediations**-Latenz (§3.1) — nur Detektion wird begrenzt; alles Weitere wäre Option B durch die Hintertür

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Contract-Datei driftet selbst (lügender Index 2. Ordnung) | Mittel | Mittel | Contract-Lint in CI (P2); Heuristik-Scan auf nicht-deklarierte Verteiler |
| Doctor-WARN im Session-Start wird ignoriert (Alarm-Müdigkeit) | Mittel | Niedrig | Nur EIN Banner, nur bei echtem Delta; Wirksamkeits-Messung §8.3 mit Abschalt-Kriterium |
| P3 bricht ship-Workflows (Registry-Filter ≠ alte Liste) | Niedrig | Hoch | Diff alte Liste vs. Registry-Filter im P3-PR ausweisen; Lehre aus dem CI-Replace-Gate (Job-Katalog-Diff) |

---

## 8. Confirmation

1. **Contract-Lint (ab P2)**: CI-Job in `validate-workflows.yml` — jede `source` in `registry/distribution.yaml` existiert, jedes deklarierte Gate existiert; rot bei Verstoß.
2. **Detektions-Banner (ab P2)**: `doctor.py --live --quick` im Session-Start; `DIST-DRIFT`-Zeile mit Mess-Feldern nach §3.1, Messung analog `measure-evidence-discipline.py`.
3. **Wirksamkeits-Test (bindend, falsifizierbar)**: Bis **2026-10-15** gilt — tauchen in Session-Retros oder `DIST-DRIFT`-Zeilen erneut **≥2 unabhängige, deduplizierte Instanzen** (§3.1) der Muster 1–4 auf, die eine Invariante hätte verhindern müssen, wird die betroffene Invariante nachgeschärft oder dieses ADR als gescheitert markiert. Meldet umgekehrt der Detektions-Check bis dahin nie ein Delta über Schwelle, wird der Check auf wöchentlich reduziert (kein Selbstzweck).
4. **Verteiler-Vollständigkeit (ab P2)**: Heuristik-Scan auf nicht deklarierte Verteilwege (§4.2) läuft als Teil des Contract-Lint; Fund ohne Lane-Eintrag = rot *(v1.1, REC-5)*.
5. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft — Staleness-Schwelle: 6 Monate.

---

## External Sparring (Audit, Step-5-Nachweis)

`external_sparring_by: openai/gpt-5.5 @ 2026-07-11` *(im Body statt Frontmatter — Schema v3 strikt; Präzedenz ADR-267)* · Transport: `/adr-handoff-extern`, manuell, 1 Runde · Externe Empfehlung: **Überarbeiten** → umgesetzt als v1.1, danach Accept (Owner-Go 2026-07-11). Intern zusätzlich: deep-review-Routine fand vor dem P1-Merge einen CONFIRMED-BLOCKER (unparsebares `distribution.yaml`) — dieser Vorfall belegt **ausschließlich** die Notwendigkeit eines Parse-/Beobachtungs-Gates, nicht die Validierung des Gesamtvertrags *(REC-13)*.

Rückfluss-Tag-Tabelle (nur `[valid]` floss ein, als eigene Formulierung):

| REC | Verdikt | Umsetzung |
|---|---|---|
| 1 Titel/I4 = Detektion | valid | Titel, I4, §3.1 |
| 2 Melde-Semantik | valid (right-sized) | §3.1: 2 Risikoklassen |
| 3 Schema versioniert | valid | → #1073 |
| 4 Lint: Gate-Wirkung | valid | §4.2 + #1073 |
| 5 Verteiler-Detektion | valid | §4.2, §8.4 + #1073 |
| 6 I1 vs. ADR-230 | valid | I1 Dreiteilung |
| 7 Artefakttyp-Definition | valid | §3.1 + Zwischenzustand |
| 8 I3 Snapshot-Regel | valid | I3 neu |
| 9 Messbasis | teil-valid | §3.1 Dedup + DIST-DRIFT; Event-DB verworfen (YAGNI) |
| 10 Eskalation/Persistenz | valid (right-sized) | §3.1: >14 Tage → fleet-drift-Issue |
| 11 Optionen D/E | valid | §2 ergänzt; describe-Pflicht → §4.2 |
| 12 P1-vor-Accept transparent | valid | Absatz unten; Befund AD-13 selbst: [missversteht-Kontext] — merged-proposed ist der gewollte Status-Lifecycle |
| 13 Vorfall nicht überdehnen | valid | Formulierung oben |
| 14 Mess-Definition | valid (minimal) | §3.1; Implementierung #1073 |

Out-of-scope getaggt: Pull-Bundle-Modell als sofortiger Ersatz (bleibt Konzept-Kandidat, §2 Option D).

**Transparenz (REC-12):** P1 (`distribution.yaml` + Parse-Gate) wurde am 2026-07-11 **vor** dem Accept gemergt (PR #1072). Der Merge ist reversibel (eine YAML-Datei, ein CI-Step, dieses Dokument); der Owner war dadurch weder fachlich noch prozessual auf Annahme festgelegt. Der Accept erfolgte erst nach internem + externem Review auf Basis dieser v1.1.

---

## Glossar

| Abkürzung / Begriff | Bedeutung |
|-----------|-----------|
| **ADR** | Architecture Decision Record — dokumentierte Architektur-Entscheidung |
| **SSoT** | Single Source of Truth — die eine verbindliche Quelle eines Fakts |
| **MANAGED-BY-Header/Footer** | Marker in generierten Dateien: Quelle, Commit, Inhalts-Hash, „nicht von Hand editieren" |
| **Lane** | Ein Verteilkanal von cc-skill-dist (commands, skills, hooks) |
| **Symlink** | Dateisystem-Verweis auf die Originaldatei statt einer Kopie |
| **Drift** | Schleichendes Auseinanderlaufen von Kopie und Quelle |
| **CI / Gate** | Continuous Integration / automatische Prüfung, die einen Merge blockieren kann |
| **Redistribution-Latenz** | Zeit zwischen Änderung der Quelle und Aktualisierung der verteilten Kopien (= Detektions- + Remediations-Latenz, §3.1) |
| **Detektions-Latenz** | Zeit zwischen Änderung der Quelle und der ersten Meldung der Abweichung — das, was dieser ADR begrenzt |
| **Context and Problem Statement / Considered Options / Decision Outcome / Confirmation** | MADR-4.0-Standardabschnitte: Problem / geprüfte Optionen / Entscheidung / Einhaltungs-Prüfung |

---

## 9. More Information

- ADR-230: cc-first-skill-distribution — Basis-Entscheidung, deren Praxis hier zum Vertrag verallgemeinert wird
- ADR-234: clean-state-invariant — Vorbild für „generiert + gegated" (Registry-Views)
- ADR-263: windsurf-rules-distributor-hardening — abhängige Härtung, Priorität durch diesen ADR erhöht
- ADR-265: untrack-distributed-symlink-targets — Realfall für stille Fail-soft-Drift (Policies auf Mai-Stand)
- Memory/Retro: /repo-optimize-Report 2026-07-03 (`~/shared/repo-optimize-platform-2026-07-03.md`), Fix-PRs #898/#905/#906

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-11 | Achim Dehnert | Initial: Status Proposed |
| 2026-07-11 | Achim Dehnert | v1.1 (externes Sparring GPT-5.5, 14 RECs getaggt, 13 valid): Titel + I4 auf **Detektions**-Latenz präzisiert, I1/I3 nachgeschärft, §3.1 Definitionen (Risikoklassen, Mess-Felder, Eskalation), Optionen D/E, §8.4 Verteiler-Vollständigkeit, Audit-Abschnitt. Status → **Accepted** (Owner-Go auf Basis v1.1) |
