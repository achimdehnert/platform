---
retro_schema: 1
date: 2026-07-22
repo_scope: [writing-hub, platform]
session_id: 20ef83
footprint: full
footprint_reduction_reason: "Rule-B-Trigger (Prod-Schritt) → deep; eine Stufe auf full reduziert, weil alle drei Bedingungen belegt zutreffen: (a) Prod-Merge explizit vom Menschen freigegeben ('ja, #320 mergen und /readyz/ in Prod prüfen'), (b) voll rollback-fähig, KEINE DB-Migration (PR #320 löscht nur eine Fixture-Datei), (c) findings_total-Schätzung ≤10 (real 9)."
findings_total: 9
findings_survived: 8
refuted_rate: 0.11
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [claim-before-cheapest-check, handover-stale-vor-merge, tracking-doc-stale-after-new-occurrence, deferred-item-no-tracking-issue]
recurring_findings: [claim-before-cheapest-check, handover-stale-vor-merge, tracking-doc-stale-after-new-occurrence, worktree-midsession-accumulation, issue-not-reconciled-after-cross-repo-fix, dod-reinterpreted-only-in-pr-body, alert-template-reused-for-different-failure-class]
---

# Session-Retro 2026-07-22 — writing-hub (+ platform): Seed-Sichtbarkeitskette abgeschlossen, Monitoring-Fehlschluss

## 1. Executive Summary

- **Das Kernziel wurde erreicht und in Prod belegt.** PR #320 gemergt, Deploy `4349fd3` success, `/readyz/` von 503 auf 200 gemessen — die mit #318 gebaute Seed-Sichtbarkeitskette ist damit end-to-end real bewiesen, nicht nur konstruiert.
- **Der teuerste Fehler war ein Absenz-Schluss:** „kein Betterstack-Monitor" wurde mit „kein Monitoring" gleichgesetzt und in **zwei** Issues publiziert, bevor der billigste Gegencheck lief. Real überwacht `prod-uptime-canary.yml` den Hub seit 2026-06-17. Selbst korrigiert — aber erst nach Propagation ins zweite Repo, und die Korrektur erreichte die bereits gemergte Doku nie.
- **Ein zweiter, unabhängiger Fehler derselben Klasse:** Die Vollständigkeits-Aussage zur gelöschten Fixture verglich **Anzahlen** (6/14/5 vs. 9/15/8) statt **Namen** und steht falsch in drei gemergten Artefakten. Ein realer Datenverlust wurde vom Skeptiker widerlegt (`loaddata` ist pro Datei atomar, das Fixture landete nie in der DB) — die Behauptung bleibt trotzdem sachlich falsch.
- **Drei Artefakte blieben in inkonsistentem Zustand zurück:** `docs/seed-konzept.md` trägt die widerrufene Aussage auf `main`, `AGENT_HANDOVER.md` widerspricht sich nach dem eigenen Korrektur-PR im Kopfabschnitt selbst, und #322 beschreibt ein Problem, das der gemergte platform#1329 bereits löst.
- **Sauber:** ADR-233-Worktree-Disziplin (beide Haupt-Trees auf `main`, keine Reste), keine dangling/duplizierten PRs, und der `#312`-Close hielt der unabhängigen Nachmessung exakt stand (Laufzeiten und Branch-Protection-Zitat stimmen).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | „writing.iil.pet hat keinen Uptime-Monitor" in writing-hub#322 (05:43Z) publiziert und wortgleich nach platform#1328 (07:31Z) propagiert; real läuft `prod-uptime-canary.yml` seit 2026-06-17 | fehlende Validierung | hoch | SURVIVES | `git log -- .github/workflows/prod-uptime-canary.yml` → `c341ca9` 2026-06-17; Korrekturen 07:32:49Z / 07:33:06Z | `claim-before-cheapest-check` (#26) |
| 2 | Die Vollständigkeits-Aussage zu PR #320 („deckt alle drei vollständig ab, einziger Rest ist Hörbuch") ist namensbezogen falsch: 9/14 Genre- und 5/5 Audience-Namen matchen die Code-Defaults nicht | fehlende Validierung | mittel | SURVIVES | String-Diff `4349fd3^:fixtures/initial_lookups.json` vs. `origin/main:apps/projects/constants.py`; `seed_project_lookups` matcht per `get_or_create(name=…)`, rein exakt | `claim-before-cheapest-check` (#27) |
| 3 | Realer Datenverlust durch die Fixture-Löschung | fehlende Validierung | — | **REFUTED** | `loaddata` ist pro Datei atomar; Constraint-Fehler rollte die gesamte Datei zurück. Prod-`pk=6` für „Novelle" entspricht der `DEFAULT_CONTENT_TYPES`-Reihenfolge, nicht der Fixture-pk (4) → Fixture-Zeilen waren nie persistiert | — |
| 4 | `docs/seed-konzept.md` trägt die um 07:32Z widerrufene Behauptung unverändert auf `origin/main` — dauerhafte Konzept-Doku, kein Snapshot | Prozesslücke | mittel-hoch | SURVIVES | `git show origin/main:docs/seed-konzept.md` Z. 49; kein Commit nach `3a4bedc` | `tracking-doc-stale-after-new-occurrence` (#2) |
| 5 | `AGENT_HANDOVER.md` widerspricht sich nach PR #324 selbst: Kopf (Z. 8, 20) führt #320 als „offen ohne Merge-Freigabe" und „#317 (Rest) Monitor", die von #324 korrigierte Prio-Liste sagt das Gegenteil | Prozesslücke | mittel | SURVIVES | `git show origin/main:AGENT_HANDOVER.md` Kopf vs. Prio 0/17; `gh pr diff 324` berührt nur Z. 71/192/205/210 | `handover-stale-vor-merge` (#11) |
| 6 | writing-hub#322 nach Merge von platform#1329 (07:53Z) nicht nachgezogen: offen, Titel „…fehlt", DoD nennt weiter Betterstack-spezifische Konfiguration | Prozesslücke | mittel | SURVIVES | `gh issue view 322` → OPEN, letzter Kommentar 07:33Z, also **vor** dem Merge; DoD nennt `check_frequency 180`, `regions eu/us/as/au` | `issue-not-reconciled-after-cross-repo-fix` (neu) |
| 7 | #317/#319 per `Closes` geschlossen, alle DoD-Kästchen unangehakt, **null** Issue-Kommentare; die Umdeutung von #317s „**absichtlich** fehlschlagender Seed" lebt nur im PR-#323-Body | Kommunikation | mittel | SURVIVES | `gh issue view 317 --json comments` → `[]`, `state: CLOSED`, DoD 3× `- [ ]` | `dod-reinterpreted-only-in-pr-body` (neu) |
| 8 | platform#1329 routet `/readyz/`-503 (Hub erreichbar, Stammdaten unvollständig) durch Issue-Titel „Hub(s) nicht erreichbar" und eine Kommentar-Logik ohne Throttle — bei stundenlangem Seed-Fehler alle 15 min ein neuer Kommentar | verfrühte Festlegung | mittel | SURVIVES | `origin/main:.github/workflows/prod-uptime-canary.yml`: Titel-String; `gh issue comment` unbedingt bei jedem `has_down==true`-Tick, kein Zeitstempel-Check | `alert-template-reused-for-different-failure-class` (neu) |
| 9 | Zwei Tage alter DIRTY-Worktree (`294-m6-framework-beat-prompt`) mit 4 geänderten + 1 gelöschten + 1 untracked Datei, Issue #294 geschlossen, Branch nie gepusht | Prozesslücke | mittel | SURVIVES | `git status` im Worktree; `gh issue view 294` → CLOSED; `git ls-remote` leer. **Mildernd:** `KONZ-writing-hub-004` trägt eine offene M6-Zeile zum selben File — das *Feature* ist getrackt, dieser *Diff* nicht | `worktree-midsession-accumulation` (#2) |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | Kernziel erreicht und in Prod gemessen (#320 → `/readyz/` 200); #317 geschlossen, Canary-Lösung gemergt. Abzug für #322, das als offener Rest in irreführendem Zustand zurückblieb (Befund 6). |
| architektur_design | **3** | Die Entscheidung Canary statt Betterstack-Upgrade ist tragfähig und spart Kosten. Abzug: `/readyz/` wurde ohne Anpassung von Titel-Semantik und Kommentar-Throttle in eine für Erreichbarkeits-Ausfälle gebaute Meldevorlage geroutet (Befund 8), obwohl die Diskrepanz selbst erkannt und dokumentiert war. |
| code_konventionstreue | **4** | ADR-233 sauber eingehalten (beide Haupt-Trees auf `main`, alle Edits in Worktrees), Commit-Format konform, PR-Bodies mit Verifiziert/Nicht-verifiziert-Sektion. Abzug für die unangehakten DoD-Kästchen (Befund 7). |
| risiko_debt | **2** | Vier Artefakte blieben in inkonsistentem oder falschem Zustand zurück: falsche Aussage live auf `main` (4), selbstwidersprüchlicher Handover (5), veraltetes Issue (6), ungetrackter WIP-Diff (9). Genau die Dimension, die über 46 Retros mit Ø 2,70 die schwächste ist. |
| prozess_effizienz | **3** | Reihenfolge überwiegend richtig (Prod-Fix zuerst, dann Doku, dann Handover). Abzug: Befund 1 erzeugte echten Rework — Issue geschrieben, in zweites Repo kopiert, beide korrigiert; und der Canary wurde erst durch eine Nutzer-Rückfrage gefunden, nicht durch eigene Recherche. |
| entscheidungsqualitaet | **3** | Stark: der `#312`-Close hielt der unabhängigen Nachmessung exakt stand; die Weigerung, einen Betterstack-Monitor eines noch laufenden Dienstes zu löschen, war gegen die eigene Vorlage richtig. Schwach: zwei Behauptungen (1, 2) wurden ohne den billigsten Check in dauerhafte Artefakte geschrieben. |

## 4. Soll-Ablauf

Invariante: 8 überlebende Befunde → 8 Soll-Schritte.

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Aus „Betterstack-API listet keinen Monitor" wurde „es gibt kein Monitoring" und direkt in ein Issue geschrieben (#322, 05:43Z) | Vor **jeder** Absenz-Behauptung („X existiert nirgends") einen zweiten, andersartigen Suchpfad fahren — hier: `grep -rl "<domain>" ~/github/platform/.github/workflows/`. Ein Tool-Ergebnis belegt nur die Absenz *in diesem Tool* | #1 |
| Vollständigkeit über Anzahl-Vergleich behauptet (6/14/5 vs. 9/15/8), Namen nie gediffed | Bei „Quelle A deckt Quelle B vollständig ab": die beiden Wertelisten **elementweise** diffen und das Diff-Ergebnis in den PR-Body schreiben. Zählvergleich ist kein Deckungsbeweis, wenn per `name` gematcht wird | #2 |
| Korrektur einer Falschaussage erfolgte im Issue-Kommentar; die identische Aussage in der eine Stunde zuvor gemergten `docs/seed-konzept.md` blieb stehen | Beim Widerruf einer Behauptung im selben Zug `grep -rn "<kernaussage>"` über die heute gemergten Artefakte fahren und jede Fundstelle nachziehen — Korrektur gilt erst als vollständig, wenn kein gemergtes Artefakt sie noch trägt | #4 |
| PR #324 korrigierte vier Prio-Zeilen und ließ den Kopfabschnitt bewusst aus; genau dort standen dieselben Falschaussagen | Wer in einem Dokument eine Aussage korrigiert, greppt vorher nach derselben Aussage im **gesamten** Dokument. Eine bewusste Auslassung ist nur zulässig, wenn belegt ist, dass der ausgelassene Teil die korrigierte Aussage nicht enthält | #5 |
| platform#1329 löste das in #322 beklagte Problem und verlinkte #322 nur als „Refs" | Nach dem Merge eines PRs jedes im Body referenzierte fremde Issue einmal öffnen und entscheiden: schließen, umqualifizieren oder Kommentar. „Refs" ohne Rückschritt lässt Tracker veralten | #6 |
| #317 wurde per `Closes` geschlossen; die Begründung, warum ein unabsichtlicher Vorfall den geforderten absichtlichen Test ersetzt, stand nur im PR | Weicht die Erfüllung vom wörtlichen DoD ab, gehört die Begründung **als Kommentar an das Issue** — vor oder mit dem Merge. Der PR-Body ist für einen Auditor, der das Issue öffnet, unsichtbar | #7 |
| `/readyz/` wurde in einen Alarm-Katalog aufgenommen, dessen Titel und Kommentar-Kadenz für Erreichbarkeits-Ausfälle gebaut sind | Wird ein Monitor um eine **neue Fehlerklasse** erweitert, im selben PR prüfen, ob Meldungstext und Wiederholungsrhythmus zu deren typischer Dauer passen — bei stundenlangen Zuständen ein Throttle oder ein eigener Titel | #8 |
| Ein Worktree mit uncommittetem WIP liegt seit zwei Tagen, sein Issue ist geschlossen, der Branch nie gepusht | Beim Pausieren einer Arbeit im selben Zug entweder pushen (Draft-PR) oder eine Zeile im zuständigen KONZ/Issue anlegen, die auf den konkreten Worktree-Pfad zeigt. Der Reaper meldet nur Reap-Kandidaten, nicht „dirty ohne Anker" | #9 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 46 Retros, Stand 2026-07-22:

| Slug | Zähler nach dieser Session | Status |
|---|---|---|
| `claim-before-cheapest-check` | **×27** (2 neue Instanzen: Befund 1, 2) | 🚨 längst GATE-PFLICHT |
| `handover-stale-vor-merge` | **×11** (Befund 5) | 🚨 längst GATE-PFLICHT |
| `tracking-doc-stale-after-new-occurrence` | **×2** (Befund 4) | 🚨 **neu gate-pflichtig** |
| `worktree-midsession-accumulation` | **×2** (Befund 9) | 🚨 **neu gate-pflichtig** |
| `issue-not-reconciled-after-cross-repo-fix` | ×1 (Befund 6) | neu, beobachten |
| `dod-reinterpreted-only-in-pr-body` | ×1 (Befund 7) | neu, beobachten |
| `alert-template-reused-for-different-failure-class` | ×1 (Befund 8) | neu, beobachten |

**Der eigentliche Befund des Längsschnitts:** `claim-before-cheapest-check` steht bei ×27 und ist seit vielen Retros formal gate-pflichtig. Diese Session produzierte **zwei weitere Instanzen** — beide in Repos mit aktivem `evidence_claim_scanner.py`-Hook. Der bestehende Hook scannt Verifikations-/Deploy-Marker; **Absenz-Behauptungen** („X existiert nicht", „hat keinen Y") und **Deckungs-Behauptungen** („A deckt B vollständig ab") fängt er nicht. Das ist keine Disziplinlücke mehr, sondern eine belegte Werkzeuglücke — dieselbe Diagnose, die die Policy schon zweimal für andere Varianten gestellt hat (Punkt 5 Verifikations-Query, Punkt 6 PR-Close).

Abgleich gegen `<auto-memory>/MEMORY.md`: `gate-claim-before-cheapest-check.md` existiert (per `grep` geprüft), ebenso `german-schliesst-keyword-no-autoclose.md`, das die DoD-Kästchen-Klasse aus Befund 7 bereits beschreibt.

## 5b. Autonomie-Kalibrierung

| KPI | Wert | Beleg |
|---|---|---|
| `over_ask` | **1** | PR #324 (docs-only, Cosmetic-Gate übersprang den Deploy nachweislich — `deploy: skipped` in run 29899898288) wurde dem Menschen zur Merge-Freigabe vorgelegt, obwohl er keinen der fünf Gates berührt: kein Prod-Schritt, reversibel, kein drittes Repo. |
| `over_act` | **0** | Der Prod-Merge (#320) hatte explizite Freigabe. Die Cross-Repo-Schritte (platform#1328, PR #1329) waren beide ausdrücklich beauftragt. Der Betterstack-`POST` lag innerhalb des erteilten Auftrags „Monitor einrichten". |

Bewertung: kein Muster ≥2, also keine Charter-Schärfung fällig. Der eine `over_ask` ist inhaltlich der Gegenpol zum korrekten Verhalten bei #320 — die Grenze „Merge löst Deploy aus?" wurde bei #320 richtig als Gate erkannt, bei #324 aber nicht als *nicht*-Gate. Beobachten, nicht kodifizieren.

## 6. Verankerung (kopierfertig — Mensch entscheidet)

> Die folgenden Blöcke sind **Vorschläge**, nicht vollzogene Übernahmen. Keine
> der Memory-Dateien und keine Hook-Änderung wurde von dieser Retro geschrieben.

### memory_candidates

```markdown
---
name: drift-absence-claim-needs-second-search-path
description: "Kein Treffer im Tool X" ist kein Beleg für "existiert nirgends" — zweiter, andersartiger Suchpfad ist Pflicht vor jeder Absenz-Behauptung
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-22-betterstack-vs-canary
---

Aus der Betterstack-API („keine Monitore für writing-hub") wurde die Aussage
„writing.iil.pet hat überhaupt kein Uptime-Monitoring" — publiziert in
writing-hub#322 und wortgleich weiterpropagiert nach platform#1328, bevor
irgendein Gegencheck lief. Real überwacht
`platform/.github/workflows/prod-uptime-canary.yml` den Hub seit 2026-06-17,
mit **mehr** Endpoints (17) als das Betterstack-Kontingent (10) hergibt.

**Why:** Ein Tool-Ergebnis belegt Absenz nur *innerhalb dieses Tools*. Der
Schluss „nicht in meinem Werkzeug" → „nicht vorhanden" ist derselbe
Fehlschluss wie 2026-07-21 bei #316 („grep fand den Seed-Aufruf nicht" →
„Deploy führt keine Seeds aus"), nur mit SaaS statt grep.

**How to apply:** Vor jeder Aussage der Form „es gibt kein X" einen zweiten,
strukturell andersartigen Suchpfad fahren — bei Monitoring/Automatismen
konkret `grep -rl "<domain>" ~/github/platform/.github/workflows/`. Erst
wenn zwei unabhängige Pfade leer sind, ist die Absenz behauptbar; sonst als
Hypothese kennzeichnen. Siehe [[gate-claim-before-cheapest-check]] und
[[drift-prompt-var-only-reaches-file-fallback]].
```

```markdown
---
name: coverage-claim-needs-element-diff-not-count
description: "A deckt B vollständig ab" braucht einen elementweisen Werte-Diff — ein Anzahl-Vergleich beweist keine Deckung, wenn per name/slug gematcht wird
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-22-fixture-completeness
---

PR writing-hub#320 löschte `fixtures/initial_lookups.json` und behauptete in
PR-Body, `docs/seed-konzept.md` und `AGENT_HANDOVER.md`, `seed_project_lookups`
decke die Daten „vollständig ab", einziger fixture-exklusiver Eintrag sei
„Hörbuch". Belegt wurde das über einen **Anzahl**-Vergleich (6/14/5 vs.
9/15/8). Ein Namens-Diff zeigt: bei GenreLookup matchen 5 von 14, bei
AudienceLookup **0 von 5** exakt. `seed_project_lookups` matcht per
`get_or_create(name=…)`, also rein stringgleich.

Ein realer Datenverlust entstand NICHT — `loaddata` ist pro Datei atomar, der
Constraint-Fehler rollte die gesamte Fixture zurück, ihre Zeilen waren nie in
der DB. Die Behauptung bleibt trotzdem in drei gemergten Artefakten falsch.

**Why:** Zwei Listen können gleich lang und trotzdem disjunkt sein. Der
Zählvergleich fühlt sich wie ein Beweis an, ist aber blind für genau den Fall,
den ein `name`-Match erzeugt: zwei Datensätze statt einem.

**How to apply:** Bei „Quelle A ersetzt Quelle B vollständig" die beiden
Wertelisten elementweise diffen und das Diff-Ergebnis in den PR-Body
schreiben. Testet ein begleitender Test nur `.count()`, ist er für diese
Frage strukturell blind — er zählt, was der Bau-Query auch zählte
(zirkuläre Selbst-Verifikation, evidence-discipline §5).
```

```markdown
---
name: correction-must-sweep-already-merged-artifacts
description: Eine widerrufene Behauptung ist erst zurückgezogen, wenn kein gemergtes Artefakt sie mehr trägt — Issue-Kommentar allein reicht nicht
metadata:
  type: feedback
---

Die Falschaussage „writing.iil.pet hat gar keinen Uptime-Monitor" wurde am
2026-07-22 um 07:32/07:33Z in writing-hub#322 und platform#1328 per Kommentar
widerrufen. Dieselbe Aussage stand da bereits seit 06:16Z in
`docs/seed-konzept.md` auf `origin/main` — gemergt via PR #323, nie
nachgezogen. Parallel ließ PR #324 im `AGENT_HANDOVER.md`-Kopf genau die
Aussagen stehen, die er weiter unten korrigierte.

**Why:** Korrekturen entstehen dort, wo der Fehler auffällt (Issue-Kommentar),
nicht dort, wo er dauerhaft wirkt (gemergte Doku). `docs/`-Dateien haben eine
lange Halbwertszeit — ein Handover-Snapshot wird ohnehin neu geschrieben, ein
Konzept-Dokument nicht.

**How to apply:** Beim Widerruf einer Behauptung im selben Zug
`grep -rn "<kernaussage>"` über die zuletzt gemergten Artefakte fahren und
jede Fundstelle nachziehen. Beim Korrigieren *innerhalb* einer Datei zusätzlich
im gesamten Dokument nach derselben Aussage greppen — eine bewusste Auslassung
ist nur zulässig, wenn belegt ist, dass der ausgelassene Teil sie nicht enthält.
Vgl. [[german-schliesst-keyword-no-autoclose]].
```

### adr_candidates

Keine. Alle acht Befunde sind Prozess-/Werkzeuglücken innerhalb bestehender
Muster — nach `adr-threshold.md` ausdrücklich **kein** ADR-Anlass. Der einzige
Grenzfall wäre Befund 8 (Alarm-Semantik im Canary), aber auch das ist eine
Erweiterung eines bestehenden Musters, keine Architekturentscheidung; er gehört
als Issue in `platform`, nicht als ADR.

### Gate-Vorschlag (aus dem Längsschnitt, ×27 bzw. ×2)

`~/.claude/hooks/evidence_claim_scanner.py` um zwei Marker-Klassen erweitern,
die er heute nachweislich nicht fängt:

1. **Absenz-Marker** — Regex auf „gibt es kein(e|n)? …", „hat (aktuell )?kein(en)? …",
   „existiert nicht", „nirgends", „überhaupt kein" → verlangt im selben Turn
   einen zweiten Such-Toolcall mit anderem Werkzeug als dem ersten.
2. **Deckungs-Marker** — „deckt … vollständig ab", „ersetzt … vollständig",
   „einziger Rest/Eintrag ist" → verlangt im selben Turn einen Diff-artigen
   Toolcall (`diff`, `comm`, elementweiser Vergleich), nicht nur `wc -l`/`count`.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 Gate-Erweiterung `evidence_claim_scanner.py` (Absenz- + Deckungs-Marker) freigeben — file:///home/devuser/.claude/hooks/evidence_claim_scanner.py
2. 🟢 Entscheiden, ob Befund 2 eine Korrektur der drei Artefakte wert ist (kein Datenverlust, aber falscher Text) — https://github.com/achimdehnert/writing-hub/pull/320
3. 🟢 DIRTY-Worktree `294-m6-framework-beat-prompt`: pushen, verwerfen oder an KONZ-004-M6 ankern — file:///home/devuser/.repo-session/worktrees/writing-hub/

### 🔵 Offen — ich kann sofort

4. 🔵 `docs/seed-konzept.md` Monitor-Satz auf den Canary-Stand korrigieren — https://github.com/achimdehnert/writing-hub/blob/main/docs/seed-konzept.md
5. 🔵 `AGENT_HANDOVER.md`-Kopf mit der korrigierten Prio-Liste in Einklang bringen — https://github.com/achimdehnert/writing-hub/blob/main/AGENT_HANDOVER.md
6. 🔵 writing-hub#322 auf den Canary-Stand nachziehen oder schließen — https://github.com/achimdehnert/writing-hub/issues/322
7. 🔵 Begründungs-Kommentar an #317 nachtragen (DoD-Umdeutung) — https://github.com/achimdehnert/writing-hub/issues/317
8. 🔵 Issue für Canary-Alarm-Semantik + Kommentar-Throttle anlegen (existiert noch nicht) — file:///home/devuser/github/platform/.github/workflows/prod-uptime-canary.yml

### ✅ Erledigt

9. ✅ #320 gemergt, Prod-Deploy `4349fd3`, `/readyz/` 503→200 gemessen — https://github.com/achimdehnert/writing-hub/pull/320
10. ✅ #317 geschlossen mit Realfall-Beleg in der Doku — https://github.com/achimdehnert/writing-hub/pull/323
11. ✅ #312 geschlossen, Begründung hielt der Nachmessung stand — https://github.com/achimdehnert/writing-hub/issues/312
12. ✅ Canary auf `/readyz/` erweitert — https://github.com/achimdehnert/platform/pull/1329

## 8. Nicht verifiziert (Restlücken)

| Offen | Billigster Check |
|---|---|
| Ob „Hörbuch" oder eine der abweichenden Genre-/Audience-Zeilen **vor** dem Squash-Commit `6cfc8c4` (2026-04-01) je erfolgreich in Prod geladen wurde — die git-Historie beginnt dort faktisch bei einem Full-Reimport | `SELECT name FROM wh_content_type_lookup WHERE name='Hörbuch'` gegen die Prod-DB, plus Zeilenabgleich `wh_genre_lookup`/`wh_audience_lookup` (nicht ausgeführt: Prod-Zugriff ohne Freigabe) |
| Ob der Canary nach dem #1329-Merge tatsächlich grün über 18 URLs läuft | `gh run list --repo achimdehnert/platform --workflow prod-uptime-canary.yml -L 1` nach dem nächsten `schedule`-Tick |
| Ob ein realer `/readyz/`-503 im Canary wirklich ein Issue erzeugt (der Pfad ist nur aus dem Workflow-Code abgeleitet, nie ausgelöst) | `workflow_dispatch` gegen einen absichtlich falschen Endpunkt in einem Fork — in Prod bewusst nicht provozieren |
| Welche Betterstack-Plan-Stufe das 10er-Limit setzt | Betterstack-Dashboard → Settings → Billing (nur die API-Fehlermeldung ist belegt) |
| Wer platform#1329 gemergt hat und ob dabei ein Review stattfand — der Merge (07:53Z) erfolgte außerhalb dieser Session | `gh pr view 1329 --repo achimdehnert/platform --json mergedBy,reviews` |

## Self-Review

Der Meta-Reviewer (separater Agent, sah nur diesen Report + die Skill) prüfte 11
Punkte und fand zwei Formfehler, beide korrigiert: Maßnahme 8 verlinkte
platform#1328 (Betterstack-Quota) für ein Canary-Throttle-Issue, das es noch
nicht gibt → auf `file://` umgestellt; Abschnitt 6 trug den Zusatz
„(kopierfertig — Mensch entscheidet)" nicht, wodurch die Memory-Vorschläge wie
vollzogene Übernahmen wirkten → ergänzt.

**Numerische Auffälligkeit (Band-KPI, ohne inhaltliches Urteil):** `refuted_rate`
liegt bei **0,11** und ist damit der dritte Report unter 0,20 im aktuellen
Trendfenster (`590926: 0,10`, `8d663b-incr: 0,00`). Das „Band gesund"-Signal von
`retro_kpis.py` wurde vor Einrechnung dieser Session berechnet. Die Skill-Regel
liest <0,2 als möglichen Hinweis, dass Falsifikation zur Formsache wird. Gegen
diese Lesart spricht hier, dass der eine REFUTED-Entscheid genau den
folgenschwersten Befund traf (behaupteter Prod-Datenverlust) und ihn per
unabhängiger pk-Analyse zerlegt hat, statt nur Stroh zu widerlegen. Für die
Lesart spricht, dass sieben von acht Behauptungen unverändert durchgingen. Beim
nächsten Retro mitbeobachten — bei einem vierten Wert <0,2 ist die Finder- oder
Skeptiker-Schärfe ein eigener Befund wert.
