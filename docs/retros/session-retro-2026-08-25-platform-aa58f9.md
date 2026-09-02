---
retro_schema: 1
date: 2026-08-25
repo_scope: [platform]
session_id: aa58f9
footprint: full
footprint_reduction_reason: "Rule-B-Level deep (Prod-Host-Eingriffe: Dummy-Volume, Restore-Container auf prod) um eine Stufe reduziert: (a) beide Eingriffe im akzeptierten Zielzustand #2284 benannt und freigegeben (Owner 'go', Issue-Body), (b) voll reversibel, per trap/rm rückstandsfrei, keine DB-Migration, (c) findings_total 9 <= 10"
findings_total: 9
findings_survived: 6
refuted_rate: 0.33
phase3_refuted: 3
pre_refuted: 0
over_ask: 0
over_act: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [scope-gap-not-in-exit-signal, oversized-pr-guardian-warning-ignored, workflow-dispatch-needs-default-branch]
recurring_findings: [claim-before-cheapest-check, deferred-item-no-tracking-issue, tracking-doc-stale-after-new-occurrence, partial-fix-not-generalized-to-sibling-artifacts, ci-gate-maskiert-failure]
gates_caught: [ci-gate-maskiert-failure]
---

# Session-Retro 2026-08-25 — platform (aa58f9): Melder-Schweigen, Backup-Wahrheit, PyPI-Sunset

Methode: Collector (haiku, nur gh/git gegen origin) → 3 Finder (sonnet, frischer Kontext, je Dimension) → Konflikt-Scan in-context (keine Faktenwidersprüche) → 1 gebündelter Skeptiker (sonnet) auf die 4 Bewertungsbefunde, 5 kommandobelegte Befunde ungeprüft übernommen → Synthese (Haupt-Session, keine neuen Kommandos). Agenten: 5 + Meta. Scope: Branch-Slugs `melder-checkc-2264`, `gate-melder-schweigen`, `backup-wahrheit-2284`, `pypi-org-sunset-adr255`; Parallel-Sitzungen desselben Tages (#2282, #2287, drei PR-lose Branches) ausdrücklich ausgeklammert.

## 1. Executive Summary

- **Geliefert:** vier PRs (#2277 ✔, #2279 ✔, #2285 offen, #2292 offen), vier Issues, ein ADR-Amendment; Zielzustand #2278 vollständig erfüllt und geschlossen, Zielzustand #2284 zu vier von sechs Kriterien mit Artefakt belegt (K1-Positivkontrolle und K4-Restore auf dem echten Prod-Pfad).
- **Schwerster Befund:** zweimal „grün" behauptet, ohne den billigsten Check zu ziehen — der K5-Workflow-Dispatch (404, Warteschleife auf leerer Run-ID) und „CI grün" für #2285 nach einem Push, der die CI rot machte. Beides ist **Gate `claim-before-cheapest-check` rückfällig** (gebaut 2026-08-20), nicht „Slug zum 65. Mal".
- **Ein Gate hat gearbeitet:** das Silent-Failure-Lint (`ci-gate-maskiert-failure`) fing das unbegründete `continue-on-error` im neuen Workflow — der Fehler lag danach im Nichthinsehen, nicht im Gate.
- **Architektur-Lücke im eigenen Werkzeug:** `backup_deckung.py` kennt „nicht im Scope", der Exit-Code nicht — prod-b hat damit keinen automatischen Leser, und ein täglich grüner Workflow sähe genauso aus wie ein seit Wochen roter prod-b. Dieselbe Klasse wie #2280, vom selben Autor, am selben Tag.
- **Drei Widerlegungen** halten die Selbstanklage ehrlich: die Hetzner-Volume-ID war seit 30.07. öffentlich, der Restore-Drill erfüllt den README-Mindestinhalt exakt, und die offenen Checkboxen in #2284 sind keine kanonische Wahrheit.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | K5-Beweislauf als „läuft im Hintergrund" gemeldet, obwohl `workflow_dispatch` auf dem PR-Branch 404 liefert; Warteschleife lief auf leerer Run-ID; Post-Merge-Beweis nur als PR-Kommentar getrackt | fehlende Validierung / Prozesslücke | hoch | SURVIVES (kommandobelegt) | `gh api …/actions/workflows` ohne `backup-deckung.yml`; PR #2285 Kommentar 10:34:59Z „Das war eine Behauptung ohne Lauf; hiermit zurückgenommen"; kein Issue/Checkbox für den Post-Merge-Lauf | claim-before-cheapest-check ×64 → **Gate rückfällig**; deferred-item-no-tracking-issue ×24 |
| 2 | #2285 seit Push a9e9d758 (07:03Z) CI-rot (Silent-Failure-Gate: `continue-on-error` unbegründet; `test_silent_failures`, `test_gate_drill_check`), danach im Kapitäns-Kanal und in #2284-Kommentar „CI grün" geführt, nie neu geprüft | fehlende Validierung | hoch | SURVIVES (kommandobelegt) | `gh pr checks 2285` → 2× fail (Jobs 97715122154, 97715108512, 07:03–07:04Z); Kommentar #2284 06:53Z unverändert | claim-before-cheapest-check → **Gate rückfällig, 2. Instanz**; tracking-doc-stale-after-new-occurrence ×6; **Gate ci-gate-maskiert-failure hat gefangen** |
| 3 | `backup_deckung.py`: Exit-Code wertet `blind`/`klassen`, nie `ausserhalb`; Workflow läuft dauerhaft `--nur prod` → prod-b ohne automatischen Leser, im Signal nicht unterscheidbar | Werkzeug / verfrühte Festlegung | hoch | SURVIVES (kommandobelegt) | PR-Head #2285 `tools/backup_deckung.py:496-498`; `.github/workflows/backup-deckung.yml:10-14,42`; `test_backup_deckung.py:236-241` prüft nur Berichtstext | neu: scope-gap-not-in-exit-signal (Klasse von #2280, selbst reproduziert) |
| 4 | #2114 „überholt" geschlossen (06:32Z), `AGENT_HANDOVER.md` Punkt 13 auf origin/main nennt es weiter als offenen Ausfall; kein PR dieser Sitzung berührt die Datei | Prozesslücke | mittel | SURVIVES (kommandobelegt) | `git log -1 -- AGENT_HANDOVER.md` = 1ca36355 (24.08. 20:09) vs. Issue-Closed 06:32:07Z | tracking-doc-stale-after-new-occurrence ×6 |
| 5 | ADR-255 Rev 5 (PyPI-Org sunset) in #2292, aber ADR-266 §Handover Z. 151-152 verlangt weiter „PyPI-Org iil: zweiten Owner eintragen (blockt ADR-255 Phase-0, REC-1)" | Prozesslücke (Geschwister-Artefakt) | mittel | SURVIVES (kommandobelegt) | `git show origin/main:docs/adr/ADR-266-*.md` Z. 151-152; PR #2292 Dateiliste (3 Dateien, ADR-266 nicht darunter) | partial-fix-not-generalized-to-sibling-artifacts ×5 (retro_kpis), ungegated |
| 6 | PR #2285: 15 Dateien, +2136 Zeilen, 4 CODEOWNERS-Pfade; Guardian G-004 („Limit 600") folgenlos; größter gemergter PR der letzten 300 war +822; Split nach K1/K3/K4/K6 ohne Duplikation möglich (Blöcke 0.7.17/0.7.18 disjunkt) | Prozesslücke | niedrig | SURVIVES (Bewertung, Skeptiker) | #2285 Kommentar 5406592359 (G-004, Auto-Warning Gate 1); Skeptiker-Diff-Prüfung | neu: oversized-pr-guardian-warning-ignored |
| 7 | Reale Hetzner-Volume-ID `/mnt/HC_Volume_105908261` in Fixtures/Skript/Protokoll eines PUBLIC-Repos | Infra-Exposure | mittel | **REFUTED** | `git grep HC_Volume origin/main`: `infra/hosts.yaml:49`, `tools/backup_meter.py:72` seit 36264176 (2026-07-30) — keine neue Offenlegung | — |
| 8 | Restore-Drill zu dünn als ADR-241-§5-Nachweis (eine Tabelle, RTO endet beim Einspielen) | Prüftiefe | niedrig | **REFUTED** | `docs/runbooks/restore-drills/README.md` verlangt wörtlich nur Smoke-Query + RTO-Ist; Protokoll liefert alle sieben Felder | — |
| 9 | #2284: sechs offene Checkboxen bei „vier erfüllt" sei Befund, nicht Formsache | Kommunikation | mittel | **REFUTED** | SA-4-Klausel verlangt nur PR-Verlinkung; kein Werkzeug parst Issue-Checkboxen (`git grep` über tools/, .github/); #2285 sagt nicht „Closes #2284" | — |

**Nullbefunde mit Abdeckungsauskunft:** Scope-Drift (Finder 1: `git diff --stat` gegen origin/main zeigte nur Branch-Staleness fremder Commits, Session-Commits im deklarierten Scope) · same-file-serial-prs auf `session_start_checks.sh` (Finder 3: `merge-base --is-ancestor` — #2285 basiert auf dem Merge von #2279, Blöcke disjunkt → widerlegt, **kein** Vorkommen) · Prognose-Mathematik `speicher_melder.py`, Fail-open-Umbau #2279, `antwort_holen`/Cache #2277, ASCII-Konvention (Finder 2: Code aus dem Ref gelesen, keine Fehler) · Owner-Freigabe der Prod-Host-Eingriffe (Finder 3: #2284-Body trägt „akzeptiert durch Owner … SA-4-fähig", Eingriffe darin benannt) · Schließung #2278/#2114 (Finder 1: Belege im Kommentar reproduziert).

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | #2278 4/4 mit Artefakt; #2284 K1/K3/K4/K6 belegt, K5 unbewiesen (#1), K2 offen; #2292 fertig, blockiert nur durch Review |
| architektur_design | 3 | #3: eigenes Werkzeug reproduziert die Zwei-Zustände-Lücke aus #2280; sonst Melder-Design (vier Klassen, Fail-open laut) tragfähig |
| code_konventionstreue | 4 | Finder 2 ohne Konventionsbefund; #2 zeigt ein Lint, das ein Repo-Gate absichtlich rot macht — die Konvention war verletzt, das Gate hat sie durchgesetzt |
| risiko_debt | 3 | #1 Post-Merge-Beweis ungetrackt, #4 Handover stale, #5 ADR-266-Zeile, #3 prod-b ungelesen — alles offen, nichts irreversibel |
| prozess_effizienz | 3 | #6 Riesen-PR mit ignorierter Warnung, #2 CI-rot unbemerkt, zwei PRs blockiert; positiv: keine Rework-Kaskade, kein Duplikat-PR |
| entscheidungsqualitaet | 4 | PyPI-Sunset gegen nachgelesene PyPI-Regeln entschieden; K4 als ein Kommando; Fixtures aus Echtdaten mit Geheimnis-Kontrolle; Abzug für #3 |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| `gh workflow run` auf PR-Branch → 404, Schleife auf leerer Run-ID, „läuft" gemeldet (#2285 Kommentar 10:34Z) | Vor jedem Dispatch: `gh workflow list` prüfen; existiert der Workflow nicht auf main, ist der Beweis **post-merge** und bekommt sofort eine Checkbox in #2284 K5 — nie nur PR-Prosa | #1 |
| Push a9e9d758 07:03Z, danach Board „CI grün" ohne `gh pr checks` (Jobs rot 07:03–07:04Z) | Jede „grün"-Aussage nach einem Push ist erst nach einem **neuen** `gh pr checks` zulässig; der Stop-Hook des Gates muss „CI grün/Checks pass" nach dem letzten Push als Marker sehen (Gate **ausweiten**) | #2 |
| `main()` gibt 0 zurück, obwohl `ausserhalb=[prod-b]` (backup_deckung.py:496-498) | Dritter Exit-Zustand: `ausserhalb` ≠ [] ⇒ Exit 2-Klasse „unvollständig gemessen", Workflow-Issue nennt prod-b als ungelesen; Test mit Exit-Erwartung | #3 |
| #2114 per Kommentar geschlossen, AGENT_HANDOVER Punkt 13 unverändert (1ca36355) | Issue-Schließung, die eine Handover-Prio betrifft, ändert die Prio **im selben Zug** (Handover-Edit im Schließ-PR oder direkt) | #4 |
| ADR-255 Rev 5 geschrieben, `grep -l "PyPI-Org iil\|REC-1" docs/` nicht gelaufen — ADR-266 Z. 151 bleibt | Vor jedem Amendment: ein `git grep` über docs/ und registry/ nach dem geänderten Sachverhalt; jede Fundstelle wird im selben PR nachgezogen oder als Zeile begründet stehen gelassen | #5 |
| 15 Dateien, 4 CODEOWNERS-Pfade, G-004 „Limit 600" ohne Reaktion | Ein PR je Akzeptanzkriterium, sobald der Guardian G-004 wirft; die Warnung bekommt im PR eine Antwort (Split oder begründete Ausnahme), nie Schweigen | #6 |

## 5. Längsschnitt (`tools/retro_kpis.py`, 92 Reports vor diesem)

| Slug | Zähler vorher | mit dieser Retro | Status |
|---|---|---|---|
| claim-before-cheapest-check | 64 | 65 | Gate seit 2026-08-20 — **rückfällig** (siehe 5a) |
| deferred-item-no-tracking-issue | 24 | 25 | Gate seit 2026-08-23 (`zu-frueh`) — Vorkommen nach Bau, noch nicht wertbar |
| tracking-doc-stale-after-new-occurrence | 6 | 7 | GATE-PFLICHT, ungegated |
| partial-fix-not-generalized-to-sibling-artifacts | 4 | 5 | GATE-PFLICHT, ungegated — `gate_deckung.py` meldete morgens 3, `retro_kpis.py` zählt 4 vorher; Differenz nicht geklärt (billigster Check: beide Slug-Listen diffen) — in #2234 widerrufener Verzicht, Nachfolge-Vorschlag offen |
| ci-gate-maskiert-failure | 9 | 10 (als `gates_caught`) | Gate 2026-08-20 — **hat gefangen**, kein Rückfall |

Neue Slugs (1. Vorkommen): `scope-gap-not-in-exit-signal`, `oversized-pr-guardian-warning-ignored`, `workflow-dispatch-needs-default-branch`.

### 5a. Rückfall-Prüfung (`tools/gate_wirkung.py`)

`claim-before-cheapest-check`: gebaut 2026-08-20~ (blocking), 55 Vorkommen vor Bau, 3 nach Bau bis 2026-08-23 — Urteil **RUECKFAELLIG**, mit dieser Retro **5 nach Bau** (#1 und #2). Beide Instanzen haben dieselbe Form: eine Statusaussage über einen *Hintergrund*-Vorgang (Dispatch, CI nach Push), deren Marker der Stop-Hook offenbar nicht als Claim erkennt. Antwort: **ausweiten** — Marker „läuft im Hintergrund", „CI grün", „Checks bestanden" nach einem `git push`/`gh workflow run` im selben Turn ohne nachfolgendes `gh run`/`gh pr checks` (Vorschlag in §6). Nicht „umbauen" (der Hook feuert am richtigen Ort) und nicht „herabstufen" (5 Rückfälle in 5 Tagen).

`ci-gate-maskiert-failure`: Gate wirksam — das Lint fing das `continue-on-error`; als `gates_caught` geführt, nicht als Rückfall.

`deferred-item-no-tracking-issue`, `untested-command-handed-to-user`: `zu-frueh` — kein Wirksamkeits-Beleg, ausdrücklich.

### 5b. Autonomie-Kalibrierung

`over_ask: 0` — die einzige Freigabe-Frage (Zielzustand #2284 „go") war policy-pflichtig. `over_act: 0` — Prod-Host-Eingriffe im akzeptierten Zielzustand benannt; #2114-Schließung und #2273-Merge (fremder Retro-Report, docs-only, kein CODEOWNERS-Pfad) unterhalb der Gates.

## 6. Verankerung (Vorschläge — schreibt der Mensch)

**memory_candidates**

```markdown
---
name: feedback_workflow_dispatch_needs_default_branch
description: "`gh workflow run <wf> --ref <branch>` liefert 404, solange die Workflow-Datei nicht auf dem Default-Branch liegt — ein Beweislauf für einen NEUEN Workflow ist vor dem Merge unmöglich; eine Warteschleife auf der leeren Run-ID meldet 'läuft'"
metadata: { type: feedback, rule_class: B, drift: true, drift_episode: 2026-08-25-k5-dispatch-404 }
---
Vor jedem Dispatch `gh workflow list` (Datei auf main?). Fehlt sie: Beweis ist post-merge, sofort als Checkbox tracken, und das Gate `autonomous-no-human-review` ist über das Code-Owner-Review erfüllt, nicht über den Dry-Run. Realfall #2285 K5.
```

```markdown
---
name: feedback_scope_gap_must_be_an_exit_state
description: "Ein Melder, der einen Teil seiner Grundgesamtheit bewusst nicht misst (--nur HOST), darf dafür nicht Exit 0 liefern — 'nicht im Scope' im Fließtext ist für den Leser unsichtbar, der nur den Exit sieht"
metadata: { type: feedback, rule_class: B, drift: true, drift_episode: 2026-08-25-backup-deckung-prod-b }
---
Dritter Zustand (unvollständig gemessen) = eigener Exit/eigene Zeile, die der Runner/Workflow als WARN rendert. Gleiche Klasse wie #2280 (Sitzungsstart) — dort erkannt, im eigenen Werkzeug am selben Tag wiederholt.
```

**Gate-Erweiterung (claim-before-cheapest-check, ausweiten):** Marker-Familie „läuft im Hintergrund / CI grün / Checks bestanden / dispatcht" im Assistant-Text, wenn im selben Turn ein `git push` oder `gh workflow run` stattfand und danach kein `gh pr checks`/`gh run view` — Hook blockiert bis der Check gezogen ist. Drill: Transkript-Fixture aus #2285 (Push 07:03Z → Board „CI grün").

**adr_candidates:** keine — #3 ist ein Werkzeug-Fix, #2280 trägt die Architekturfrage bereits.

## 7. Maßnahmen

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | CI #2285 grün: `continue-on-error` begründen | platform | #2285 | 🔵 ready | Lint-Format nachlesen, fixen (ich) |
| 2 | Exit-Zustand für `ausserhalb` + Test | platform | #2285 | 🔵 ready | in #2285 nachziehen (ich) |
| 3 | K5-Post-Merge-Beweis als Checkbox | platform | #2284 | 🔵 ready | Body ergänzen (ich) |
| 4 | ADR-266 §Handover Z. 151 nachziehen | platform | #2292 | 🔵 ready | in #2292 ergänzen (ich) |
| 5 | AGENT_HANDOVER Punkt 13 (#2114) korrigieren | platform | — | 🔵 ready | Handover-PR (ich) |
| 6 | #2284-Checkboxen K1/K3/K4/K6 abhaken | platform | #2284 | 🔵 ready | Body-Edit (ich) |

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 7 | Gate ausweiten (Marker-Familie) | platform | Registry | 🟢 offen | Freigabe für Hook-Edit (du) |
| 8 | Zwei Memory-Kandidaten übernehmen | ~/.claude | — | 🟢 offen | §6 kopieren (du) |
| 9 | Code-Owner-Approve #2285, #2292 | platform | #2285, #2292 | 🟢 offen | nach 1/2/4 (wirdigital) |

## 8. Nicht verifiziert (Restlücken)

- **Skeptiker D** las die Kommentare von #2285 statt #2284 („kein ‚vier von sechs' gefunden"); die Widerlegung stützt sich auf die Kanonizitätsfrage, die unabhängig davon trägt. Billigster Check: `gh issue view 2284 --json comments`. Die Existenz des Kommentars ist vom Collector belegt (06:53:05Z).
- **Mail-Aktionen** (16 Verschiebungen, Support-Mail-Entwurf) und **Host-Aktionen** sind nur über Session-Log bzw. PR-Text belegt — nicht per gh/git; hier als Hypothese geführt, nicht bewertet. Billigster Check: `ablage_erledigt.py --ruecknahme`-Protokoll, `docker volume ls` auf prod.
- **Wer den Token-Upload iil-aifw 0.13.0 um 10:57Z ausgelöst hat** (lokal, Dev-Maschine) — nicht ermittelt; Shell-History des Tages nicht geschrieben. Getrackt in #1904.
- **K3-Positivkontrolle** (Speicher-Prognose kippt) ist konstruktionsbedingt erst ab 26.08. möglich; offen in #2284.
- Finder-Nullbefund „Scope sauber" beruht auf Branch-Basis-Analyse, nicht auf Lesen des Zielzustands gegen jede Datei — Restrisiko klein.

**Vierer:** getan — 4 PRs, 4 Issues, ADR-Amendment, 2 Zielzustände (einer geschlossen), Prod-Positivkontrolle + Restore-Drill · angenommen — Owner-„go" für #2284 und „lassen" für PyPI-Org (Kapitäns-Kanal) · nicht verifizierbar — s. o. · offen geblieben — sechs 🔵-Punkte, K2/K3/K5 in #2284, Token-Widerruf #1904.
