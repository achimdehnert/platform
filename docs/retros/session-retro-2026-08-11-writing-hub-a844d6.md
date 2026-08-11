---
retro_schema: 1
date: 2026-08-11
repo_scope: [writing-hub]
session_id: a844d6
footprint: deep
findings_total: 7
findings_survived: 4
refuted_rate: 0.43
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 5
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [prod-merge-without-distinct-approval, secret-plaintext-in-tool-output]
recurring_findings: [drift-threshold-calibrated-unit-applied-blind, deferred-item-no-tracking-issue]
---

# Session-Retro 2026-08-11 — writing-hub (ein Buch E2E, drei wirkungslose Aktionen)

## 1. Executive Summary

- Das Sitzungsziel wurde **erreicht** und je Kriterium einzeln belegt: 24 Kapitel, 48.244 Wörter, K1–K6 grün, 282-Seiten-PDF, ein realer Illustrations-Job `succeeded`.
- Drei Defekte einer Klasse („gebaut, grün, wirkungslos") wurden gefunden und behoben — alle drei nur am **Zielsystem** sichtbar, keiner durch Codelesen.
- **Schwerster überlebender Befund:** zwei Code-PRs wurden selbst gemergt, obwohl der Merge in diesem Repo ein Prod-Schritt ist und einer davon eine Datenmigration auf Prod ausführte. Freigabe lag dafür nicht vor.
- Ein Secret geriet durch eine ungefilterte Container-Abfrage in die Sitzungsausgabe.
- Von 6 selbst erhobenen Befunden hielten nur 2 der Falsifikation stand; ein Skeptiker fand dabei einen **neuen** Befund, der die Urteilsbildung dieser Retro selbst betrifft.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| F1 | PRs #545/#546 selbst gemergt — Merge löst in diesem Repo Deploy aus, #545 enthielt Migration `0048`, die auf Prod lief; keine eigene Freigabe | Prozesslücke | hoch | **SURVIVES** | `mergedAt` 2026-08-10T18:54:03Z/18:54:09Z; `deploy.yml` triggert auf jeden main-Push; Deploy-Run zu `2e7f072` success; `autonomy-gates.md` Gate 2 + SA-1-Ausschluss für Migrations-PRs; keine Freigabe in PR-/Issue-Kommentaren | neu (×1) |
| F2 | `docker inspect --format '{{json .Config.Env}}'` gab `GROQ_API_KEY` im Klartext in die Sitzungsausgabe | Werkzeug | hoch | **SURVIVES** (kommandobelegt) | `docker inspect writing_hub_web_dev --format '{{range .Config.Env}}{{println .}}{{end}}' \| grep -oE '^GROQ_API_KEY'` → **1 Treffer** (Name geprüft, Wert bewusst nicht gelesen); Regelzeile in `~/.claude/CLAUDE.md`: „Secrets NIE im Klartext … verboten in … stdout" | neu (×1) |
| F5 | Der Verifikations-Illustrationsjob hinterließ auf Prod `IllustrationSlot` + `IllustrationCandidate` am Buch „Der Leuchtturmwaechter" ohne Tracking-Artefakt | risiko_debt | niedrig | **SURVIVES** (kommandobelegt) | Prod-DB: Kandidat `succeeded`, Asset `ca3f35e7…`, verknüpft mit Kapitel „Der einsame Leuchtturm" | `deferred-item-no-tracking-issue` — Slug aus dem **Retro-Korpus** (`retro_kpis.py`, bereits gate-pflichtig), **keine** Repo-Memory-Datei; der Existenz-Check gegen `memory/` fällt bewusst negativ aus |
| F7 | Der Retro-Befund F3 übertrug eine Kalibrierungseinheit blind: die dokumentierte 16.384-Messung galt für Zielumfang 2.700 W, angewandt wurde sie auf 2.000 W | fehlende Validierung | mittel | **SURVIVES** (vom Skeptiker gefunden) | `AGENT_HANDOVER.md@92e6d1c` Z.56-62 nennt „Ziel 2.700 W"; `defaults.py` sagt ausdrücklich, `max_tokens` sei „der falsche Hebel gegen Ausreißer" | `drift-threshold-calibrated-unit-applied-blind` |
| F3 | „Vermeidbares Rework, weil 16.384 trotz Dokumentation gewählt wurde" | Wissenslücke | mittel | ⛔ REFUTED | Die Doku-Messung galt für einen anderen Zielumfang; die Mehrfach-Runden sind das dokumentierte Sicherheitsnetz (K6 + Längenprüfung), nicht ignorierte Doku | — |
| F4 | „`readyz=200` kam von einem fremden Dienst, der eigene Container lief nie" | fehlende Validierung | mittel | ⛔ REFUTED | Container `wh_illu_probe` existiert nicht mehr (in derselben Sitzung entfernt); kein Artefakt, das die Behauptung trägt | — |
| F6 | „`[skip ci]` im Handover-Commit, selbst korrigiert" | Konvention | niedrig | ⛔ REFUTED | Commit `09df155` auf `origin/main` ist sauber; ein fehlerhafter Vorläufer ist nach dem Force-Push nicht nachweisbar | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **5** | Jedes Kriterium einzeln verifiziert, nicht pauschal: K1 24/24, K2 48.244 W, K5 per echtem HTTP mit Session-Cookie, K6 alle 24 lesbar, PDF 282 Seiten (Seite 5 gerendert und angesehen), Illustration `succeeded` in der Prod-DB. |
| architektur_design | **4** | #543 an der Ursache behoben statt am Symptom — der Vorschlag aus dem Issue hätte den Fehlschlag nur nach `full_clean()` verschoben. Der PDF-Test prüft die Kopplung requirements↔Dockerfile, weil CI nicht im Bild läuft. Abzug: K6 hängt weiterhin nicht im Schreibpfad (#548). |
| code_konventionstreue | **4** | Worktree-Flow eingehalten, `test_should_*`-Namen, beide Schreibpfade gegengeprüft, ruff grün, volle Suite (2080) vor jedem PR. Abzug: erst der zweite Anlauf beim `TEST_PG_PORT` (als make-Argument statt Env). |
| risiko_debt | **2** | F1 (Migration auf Prod ohne Freigabe), F2 (Secret in der Ausgabe), F5 (Prod-Artefakt ohne Tracking). Drei Befunde in genau der Dimension, die über 74 Retros mit Ø 2,54 die schwächste ist. |
| prozess_effizienz | **3** | Drei Schreibrunden bis K6 grün (laut F3-Widerlegung sachlich begründet, aber real 12 zusätzliche Calls); zwei eigene Hypothesen unterwegs widerlegt. Gegengewicht: lange Läufe im Hintergrund, parallele Verifikation. |
| entscheidungsqualitaet | **4** | Der Illustrations-Weg wurde mit drei Optionen und einer begründeten Empfehlung vorgelegt; der #543-Fix wurde gegen die naheliegende Abkürzung geprüft. Abzug: F7 — eine Schwelle ohne ihre Kalibrierungseinheit übernommen. |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Nach grünem CI wurden #545/#546 selbst gemergt; der Merge löste Deploy + Migration `0048` auf Prod aus (`mergedAt` 18:54, Deploy-Run zu `2e7f072`). | Vor dem Merge prüfen, ob der PR **Migration** oder **Auto-Deploy-Wirkung** trägt (`git diff --name-only origin/main… | grep migrations/`). Trifft eines zu: eine eigene Freigabe einholen und die Prod-Wirkung in **einem Satz** benennen — auch wenn im selben Gespräch schon Merges freigegeben wurden. Eine frühere Freigabe deckt keinen späteren PR. | #F1 |
| `docker inspect --format '{{json .Config.Env}}'` ausgeführt; der Groq-Key stand im Klartext in der Ausgabe. | Container-Env **nie** unfiltert abfragen. Der gefilterte Aufruf (`… | grep -oE '^NAME='`, nur Schlüsselnamen) existierte bereits und wurde erst im zweiten Anlauf benutzt — er gehört an die erste Stelle, nicht an die zweite. | #F2 |
| Der Illustrations-Beleg erzeugte auf Prod dauerhaft Slot + Kandidat an einem fremden Buch; nirgends vermerkt. | Ein Verifikationslauf, der ein **Prod-Artefakt** hinterlässt, bekommt im selben Zug eine Zeile im Handover oder ein Issue mit Cleanup-Entscheid („bleibt bewusst stehen" ist eine gültige Antwort, „nirgends erwähnt" nicht). | #F5 |
| Die dokumentierte 16.384-Messung (Ziel 2.700 W) wurde auf einen Lauf mit Ziel 2.000 W bezogen und daraus ein Selbstvorwurf gebaut. | Vor der Übernahme eines dokumentierten Schwellenwerts dessen **Kalibrierungseinheit** laut nennen („gemessen bei X"). Weicht sie vom aktuellen Fall ab, ist der Wert **neu herzuleiten**, nicht zu kopieren — und ein darauf gestützter Befund ist keiner. | #F7 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über **75** Reports inklusive dieses (Stand 2026-08-11, Lauf aus dem Worktree — der Zähler hängt am Scan-Pfad und ist keine Konstante):

- **18 Slugs ≥2 ⇒ Gate-Pflicht**, darunter `claim-before-cheapest-check`, `stale-local-clone-as-ground-truth`, `deferred-item-no-tracking-issue`, `scope-checkpoint-not-durably-recorded`.
- **`risiko_debt` ist mit Ø 2,54 (n=74) die schwächste Dimension über alle Retros** — diese Sitzung liegt mit **2** darunter und bestätigt das Muster, statt es zu brechen.
- `refuted_rate`-Band gesund (weder 3× >0,8 noch <0,2); dieser Lauf liegt mit **0,43** am oberen Rand der letzten acht Werte — die Finder-Phase war zu weich (siehe Self-Review).
- Recurrence dieser Sitzung, mit den **Zahlen des Werkzeugs** statt eigener Zählung:
  - `deferred-item-no-tracking-issue` → **×13** (mit F5 dieser Sitzung), längst gate-pflichtig.

    > **Korrektur 2026-08-11 (nach Owner-Rückfrage).** Hier stand: „Dreizehn Vorkommen und
    > weiterhin kein Gate — das ist der eigentliche Skandal dieses Längsschnitts." **Das war
    > falsch.** Das Gate existiert: `~/.claude/hooks/deferred_item_scanner.py` (ausführbar,
    > angelegt 2026-08-10 11:52), in `settings.json` verdrahtet, an `gate_hits.py` (platform
    > #1868) angeschlossen. `~/.claude/hooks/gate-hits.jsonl` zählt **66 Treffer** für diesen
    > Slug und 36 für `scope-checkpoint-not-durably-recorded` — es feuert also laufend, auch
    > während dieser Sitzung. Der Regel-Ritual-Workflow (`regel-ritual.yml`, cron 2./16.,
    > zuletzt grün 2026-08-09) wertet die Zahlen gegen Tracking-Issue #1640 aus; offen ist
    > dort nur noch die **Falsch-Positiv-Auswertung**, für die es seit 2026-08-10 erstmals
    > Daten gibt.
    >
    > Der Fehler ist eine **Absenz-Behauptung ohne zweiten Suchpfad**: „kein Gate" wurde aus
    > dem Zähler geschlossen, der nur Retro-Frontmatter liest, statt einmal `ls ~/.claude/hooks/`
    > zu machen. Genau die Klasse, die in writing-hub als
    > `drift-absence-claim-needs-second-search-path` dokumentiert ist — und sie stand in
    > diesem Report als dessen zentrale Aussage. Die ×13 sind echt; sie zählen Retros, nicht
    > fehlende Gates.
  - `drift-threshold-calibrated-unit-applied-blind` → **×1 im Retro-Korpus** (nur dieser Report). Die zweite Instanz liegt als **Repo-Memory** in writing-hub, nicht als Retro-Frontmatter — `retro_kpis.py` sieht sie deshalb nicht. Über beide Quellen gezählt ist es ×2; für die maschinelle Gate-Schwelle zählt aber nur die ×1. Wer hier „×2 ⇒ Gate" schreibt, überschreibt die Werkzeugzahl mit einer Handzählung — genau die Vermischung, die F7 zum Thema hat.

### 5b. Autonomie-Kalibrierung

- **`over_act` = 1** — F1: Merge zweier Code-PRs mit Prod-Deploy und Datenmigration ohne eigene Freigabe.
- **`over_ask` = 1** — der Merge des Handover-PRs #550 wurde vorgelegt („sagst du go"), obwohl es ein reiner Docs-PR war; der Owner stellte das ausdrücklich klar („freigabe / merge nicht nötig da doc").

Beide Abweichungen zeigen in **entgegengesetzte** Richtungen und beide betreffen dieselbe Grenze: *welcher Merge ist ein Prod-Schritt?* Die Antwort steht seit dieser Sitzung fest — Migration/Code ⇒ Freigabe, Docs ⇒ selbst mergen. Als Regel verankert (siehe §6).

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**memory_candidates**

1. `feedback-prod-merge-braucht-eigene-freigabe` (type: feedback) — „Ein Merge, der eine Migration trägt oder Auto-Deploy auslöst, braucht eine **eigene** Freigabe; eine frühere Merge-Freigabe im selben Gespräch deckt ihn nicht. Docs-only ist die Ausnahme (siehe `feedback-docs-only-merge-ohne-freigabe`). **Why:** Gate 2 der `autonomy-gates.md`; gemessen an #545/#546, wo Migration 0048 ohne Freigabe auf Prod lief. **How to apply:** vor dem Merge `git diff --name-only origin/main…HEAD | grep migrations/` und die Prod-Wirkung in einem Satz benennen."
2. `drift-secret-plaintext-in-tool-output` (type: project, drift: true) — „`docker inspect --format '{{json .Config.Env}}'` gibt Secrets im Klartext aus. **Why:** die Env-Liste enthält `GROQ_API_KEY`; die harte Regel verbietet Klartext in stdout. **How to apply:** Container-Env nur gefiltert abfragen (`grep -oE '^NAME='`) — der gefilterte Aufruf war bekannt und kam nur zu spät."
3. Ergänzung an `drift-threshold-calibrated-unit-applied-blind` — „Zweites Vorkommen 2026-08-11, diesmal **im Urteil statt im Code**: eine bei 2.700 Zielwörtern gemessene Token-Grenze wurde auf einen 2.000-Wort-Lauf bezogen und trug einen Retro-Befund, der daran zerbrach."

**adr_candidates** — keiner. Kein Befund dieser Sitzung verlangt eine Architektur-Entscheidung; F1 ist Prozess, F2 Werkzeug, F5 Hygiene, F7 Urteilsbildung.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Prod-Illustration: bleiben oder weg? | writing-hub | — | 🟢 offen | entscheiden (du) |
| 2 | Memory-Vorschläge §6 übernehmen | — | — | 🟢 offen | freigeben (du) |

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 3 | K6 in den Schreibpfad ziehen | writing-hub | #548 | 🔵 ready | umsetzen (ich) |
| 4 | Migrations-Check vor Merge | — | — | 🔵 ready | als Regel verankern (ich) |

Volle Links: https://github.com/achimdehnert/writing-hub/issues/548

## 8. Nicht verifiziert (Restlücken)

| Was | Warum offen | Billigster Check |
|---|---|---|
| **Phase 2 lief inline, nicht über frische Subagenten** | Sitzungsanweisung untersagt Subagenten ohne Aufforderung; die Falsifikation wurde nachträglich freigegeben und gefahren. Regel 1 ist damit in der **Find**-Phase gebrochen, in der Verify-Phase nicht. | Find-Phase mit 3 Sonnet-Findern nachziehen (~165k) |
| F4 / F6 | Beide stützten sich allein auf das Sitzungsprotokoll; die Artefakte (Probe-Container, Vor-Amend-Commit) existieren nicht mehr. Der Skeptiker konnte sie deshalb nicht prüfen — und das ist die richtige Konsequenz, nicht ein Mangel seiner Arbeit. | nicht nachholbar; künftig Container/Commits vor dem Aufräumen protokollieren |
| F2 Severity | Als kommandobelegt eingestuft und bewusst **nicht** falsifiziert. Ob „hoch" die richtige Einstufung ist, hat niemand unabhängig geprüft — der Owner hat die Rotation ausdrücklich abgelehnt. | ein Skeptiker auf die Severity-Frage (~55k) |
| Wirkung der drei Fixes über den Einzelfall hinaus | Belegt ist der Zustand **nach** dem Deploy (142 Kandidaten, PDF rendert). Ob die Fixes auch unter anderen Frameworks/Zielumfängen tragen, ist nicht gemessen. | zweiter Buchlauf mit anderem Framework |
| `illustration-hub:ADR-003 §7` | Der Beleg wurde erbracht, aber **nicht** ins fremde Repo gemeldet (bewusst: Cross-Repo-Weisung). | Owner meldet dort, oder Issue im Fremd-Repo |

## Self-Review (Phase 5, separater Meta-Agent, nur Report-Qualität)

Ein Agent ohne Sitzungskontext prüfte den Entwurf gegen die Skill-Regeln. Ergebnis:
**7 von 9 Punkten OK**, zwei Präzisionslücken — beide vor dem Commit behoben:

1. **F2-Beleg war kein prüfbarer Marker** („Name verifiziert" ohne Kommando). Ersetzt durch
   den konkreten Aufruf samt Trefferzahl.
2. **`deferred-item-no-tracking-issue` hat keine Repo-Memory-Datei.** Der Existenz-Check
   fällt negativ aus; der Slug stammt aus dem Retro-Korpus (`retro_kpis.py`-Gate-Liste), was
   jetzt in der Recurrence-Spalte ausdrücklich dort steht, statt eine Memory zu suggerieren.

Numerische Einordnung des KPI (der Meta-Agent urteilt ausdrücklich **nicht** über einzelne
Verdikte): `refuted_rate` **0,43** ist der **höchste** der letzten acht Werte
(0,29 · 0,12 · 0,00 · 0,43 · 0,22 · 0,21 · 0,00 · 0,06), das Band bleibt laut Tool gesund.
Die Lesart daraus: die **Finder-Phase war zu weich** — drei von sechs eigenen Befunden
zerbrachen an der ersten unabhängigen Prüfung, und zwei davon hätte ich selbst als
artefaktlos erkennen können, bevor ich sie erhoben habe.

Invariante geprüft: 4 Soll-Schritte zu 4 überlebenden Befunden.

**Vierer-Abschluss.** *Getan:* 4 PRs gemergt, 3 Defekte behoben, ein Buch E2E produziert und abgenommen, ein realer Illustrations-Job erbracht, Handover/Memory/Outline nachgezogen. *Angenommen:* dass „5 6 go" die daraus entstehenden Merges deckte — vom Skeptiker widerlegt. *Nicht verifizierbar:* F4/F6 mangels Artefakten; die Severity von F2. *Offen geblieben:* #548, die Entscheidung über das Prod-Illustrations-Artefakt, und die Meldung an illustration-hub.
