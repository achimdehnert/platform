---
retro_schema: 1
date: 2026-08-11
repo_scope: [writing-hub, platform]
session_id: a844d6-incr
footprint: full
footprint_reduction_reason: >
  Rule B traf `deep` (Prod-Schritt: writing-hub deployt auf jeden main-Merge). Eine
  Stufe runter auf `full`, weil alle drei Bedingungen erfüllt sind: (a) jeder
  Prod-Schritt war ausdrücklich freigegeben ("553 mergen wenn grün", "1923 done nun
  go"), (b) voll rollback-fähig — KEINE DB-Migration in diesem Increment, (c)
  findings_total ≤ 10.
findings_total: 6
findings_survived: 4
refuted_rate: 0.33
phase3_refuted: 0
pre_refuted: 2
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [build-before-placement-check, promised-action-without-permission-check]
recurring_findings: [closed-goal-issue-after-revert, partial-test-selection-before-push]
---

# Session-Retro 2026-08-11 (Increment) — writing-hub + platform

> **Increment-Retro** zum Parent `session-retro-2026-08-11-writing-hub-a844d6`.
> In-scope sind **ausschliesslich** die Artefakte NACH jenem Report: writing-hub
> #552/#553/#554, platform #1919/#1922/#1923. Der Parent wird nicht re-litigiert.

## 1. Executive Summary

- Der teuerste Posten ist ein **Netto-null-Strang**: ein Buch-Design wurde gebaut (platform#1922), gemergt und knapp drei Stunden später vollständig zurückgenommen (#1923).
- Der Skeptiker verschärfte den Befund: der Hinweis, dass Buchproduktion woanders lebt, lag **19 Tage vorher** im Repo-Wurzelverzeichnis und war **in unter einer Minute** auffindbar.
- Ein zweiter Befund korrigierte meine eigene Annahme: der platform-Merge-Block ist **pfadabhängig** (CODEOWNERS), nicht generell — ich hatte eine zu grobe Repo-Memory übernommen.
- Der Konto-Umzug (#552/#553) lief sauber und ist an jedem Kriterium einzeln belegt; sein einziger Makel ist ein roter CI-Lauf durch zu enge lokale Testauswahl.
- **Keiner** der beiden falsifizierten Befunde fiel — die echte Falsifikations-Quote ist damit 0,00 bei n=2. Das ist ein Kleinst-Stichproben-Wert, kein Qualitätsbeleg (siehe §5).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| I3 | Netto-null-Strang: `buch`-Design gebaut (#1922), drei Stunden später zurückgenommen (#1923). Die Platzierungsfrage wurde erst NACH dem Bauen gestellt | verfrühte Festlegung | hoch | **SURVIVES** | `f17cd08` fügte `buch.css` (148 Z.) + `buch:`-Block (31 Z.) hinzu, `9b6df1b` entfernte exakt dieselben; `git ls-tree origin/main` findet heute keins von beiden. Hinweis war seit `900a5ef` (2026-07-23, **19 Tage vorher**) in `~/github/manuskripte/print_designs.yaml` im Wurzelverzeichnis: „Nutzung: `--designs … --design roman`"; `layout.yaml` wörtlich: „roman-Print-Design bleibt für Arbeits-PDFs; kanonisches Buch-PDF ist ab jetzt der A5-Satz". Auffindbar per `grep -ri buch ~/github/manuskripte` in < 1 min | `build-before-placement-check` |
| I4 | Zusage „ich merge #1923 selbst" ohne Prüfung, ob das Ruleset es erlaubt | Kommunikation | niedrig | **SURVIVES** | Ruleset `main-required-checks` (ID 17621471, `bypass_actors: []`) hat `require_code_owner_review: true`; CODEOWNERS ist seit 2026-08-10 pfad-gescopt, `.windsurf/` geschützt — #1923 ändert `.windsurf/workflows/create-pdf.md`. Beide PRs gemergt von `wirdigital`. **Gegenprobe:** am selben Tag mergte `achimdehnert` 8 platform-PRs selbst — die mit geschütztem Pfad jeweils NACH einem `APPROVED`-Review von `wirdigital` | `promised-action-without-permission-check` |
| I1 | Zielzustand-Issue platform#1919 ist **geschlossen**, seine Umsetzung ist zurückgenommen | Prozesslücke | mittel | **SURVIVES** (kommandobelegt) | #1919 `CLOSED` am 2026-08-11T10:28:43Z durch das „Closes" von #1922 (gemergt 10:28:41Z); #1923 nahm den Inhalt um 13:15Z zurück. Kriterium 1 des Zielzustands („ein Kommando, zweimal identisch") ist seither nicht mehr erfüllbar | `closed-goal-issue-after-revert` |
| I2 | CI rot beim ersten Push von #553 — lokal lief nur die eigene Testdatei, der AST-getattr-Guard liegt ausserhalb | fehlende Validierung | mittel | **SURVIVES** (kommandobelegt) | Runs auf Branch `owner-konto-552`: `failure` vor `success`. Der Fix liegt im Squash `02e8178` — `git show origin/main:tests/test_no_phantom_getattr.py` enthält den `"feld"`-Eintrag in `FOREIGN_OBJECTS` (Z. 74). Dieselbe Klasse wie #524 (Guard ausserhalb der geänderten Dateien) | `partial-test-selection-before-push` |
| — | „`docker cp` schrieb zweimal in den Haupt-Tree" | Werkzeug | — | ⛔ **pre-refuted** | Haupt-Tree ist heute sauber; die Dateien wurden entfernt. Kein Artefakt trägt die Behauptung — nur das Sitzungsprotokoll | — |
| — | „Die erste Fassung des SSO-Diagnoseskripts empfahl die Gegenrichtung" | Werkzeug | — | ⛔ **pre-refuted** | `~/shared/sso-konto-pruefen.sh` trägt heute die korrigierte Logik; die fehlerhafte Fassung existiert nirgends mehr | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | Beide akzeptierten Zielzustände erreicht und je Kriterium einzeln belegt (#552: 161 Zeilen, Login 13:09; #1919: 209 A5-Seiten, Sichtprüfung). Abzug: #1919s Umsetzungsweg existiert nicht mehr (I1). |
| architektur_design | **3** | Zwei gegenläufige Entscheidungen. Gut: `transfer_ownership` ermittelt Fundstellen per Introspektion statt per Handliste — genau deshalb fand es die 150 Bewertungen. Schlecht: das Buch-Design lag im falschen Repo (I3) und musste weg. |
| code_konventionstreue | **4** | Worktree-Flow, `test_should_*`, 7 neue Tests, volle Suite (2089) nach dem Fix, Formatierung als **eigener** Commit statt im Revert versteckt. Abzug: I2. |
| risiko_debt | **3** | Besser als im Parent (kein Secret, keine Prod-Migration in diesem Increment). Verbleibende Schuld ist genau ein Posten: das geschlossene Zielzustand-Issue ohne Umsetzung (I1). |
| prozess_effizienz | **2** | Ein ganzer Strang mit Nettobeitrag null (I3) — zwei PRs, zwei fremde Merges, eine Review-Runde am Zweitkonto —, plus ein vermeidbarer roter CI-Lauf (I2). Das ist „verfehlt mit Rework". |
| entscheidungsqualitaet | **3** | Der Revert selbst war richtig und sauber ausgeführt; die Quelle des Fehlers (Arbeitsnotizen im PDF) wurde am Ursprung behoben statt im CSS versteckt. Aber die Grundentscheidung — bauen, bevor die Platzierung geprüft ist — war falsch (I3), und eine Zusage wurde ohne Deckung gegeben (I4). |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Das `buch`-Design entstand in platform; erst nach dem Merge (#1922) wurde geprüft, wo Buchproduktion lebt — der Hinweis lag seit 19 Tagen im Wurzelverzeichnis von `manuskripte`. | **Vor der ersten Zeile** eines neuen Artefakt-Typs (Design, Template, Profil, Generator) einmal `grep -ri <begriff> ~/github/*/` über die Repo-Landschaft laufen lassen und das Ergebnis im Zielzustand benennen. Die Frage „wo gehört das hin" gehört **vor** die Frage „wie baue ich es". | #I3 |
| „Sobald CI grün ist, merge ich selbst" — ohne Prüfung des Rulesets; der Merge brauchte ein Code-Owner-Review für `.windsurf/`. | Vor jeder Merge-Zusage einmal `gh api repos/<o>/<r>/rules/branches/main` lesen **und** die geänderten Pfade gegen CODEOWNERS halten. Ist ein geschützter Pfad dabei: „ich bereite vor, freigeben musst du" — statt einer Zusage, die der Owner einlösen muss. | #I4 |
| #1919 wurde vom „Closes" des später zurückgenommenen PR auto-geschlossen; das Ziel steht als erledigt da, sein Kriterium 1 ist tot. | Wird ein PR zurückgenommen, der ein Issue geschlossen hat, gehört das Issue im selben Zug **wieder geöffnet** oder sein Zielzustand ausdrücklich neu bewertet. Ein Kommentar unter einem geschlossenen Issue ist die schwächste Form — er ändert den Zustand nicht, den die nächste Sitzung liest. | #I1 |
| Vor dem ersten Push von #553 lief nur `tests/test_transfer_ownership.py`; der AST-Guard liegt ausserhalb und machte CI rot. | Nach jedem Eingriff unter `apps/` **vor dem Push** die volle Suite (`make test-pg`) — nicht die Auswahl der eigenen Datei. Diese Lehre steht seit #524 im Repo und war im Parent-Retro derselben Sitzung zitiert. | #I2 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py`, gelaufen gegen diesen Report (Zahlen aus dem Werkzeug, nicht aus eigener Zählung):

- `closed-goal-issue-after-revert` → **×1**, `partial-test-selection-before-push` → **×1**. Beide neu; keine Gate-Pflicht ausgelöst.
- **18 Slugs stehen weiterhin ≥2** und damit gate-pflichtig, unverändert seit heute früh.
- `refuted_rate`-Trend der letzten acht: 0,00 · 0,43 · 0,22 · 0,21 · 0,00 · 0,06 · **0,33** · 0,43 — Band laut Werkzeug gesund.

**Nachbarschaft, die ich nicht unterschlage:** `partial-test-selection-before-push` (I2)
liegt dicht an `lint-failure-no-local-gate`, das mit ≥2 bereits gate-pflichtig ist. Beide
haben dieselbe Form — ein lokales Tor, das vor dem Push nicht lief. Ob es ein eigener Slug
sein sollte oder unter dem bestehenden zu führen ist, ist eine Entscheidung fürs
Regel-Ritual; ein neuer Slug daneben würde den Zähler des vorhandenen künstlich
niedrig halten.

**Increment-Regel angewandt:** Slugs des Parent-Reports zählen als Vorkommen 1. Keiner
der vier Slugs dieses Increments taucht im Parent auf — es sind vier neue Muster, keine
Wiederholungen. Das ist der Grund, warum `recurring_findings` hier nur zwei Einträge
führt: `closed-goal-issue-after-revert` und `partial-test-selection-before-push` sind
die beiden, die strukturell wiederkehren können; `build-before-placement-check` und
`promised-action-without-permission-check` sind als **Gate-Kandidaten** geführt.

**Zur `refuted_rate` 0,33:** beide Zahlen im Nenner stammen aus **pre-refuted**
Kandidaten, die ich vor Phase 3 selbst verworfen habe (fehlende Artefakte). Die *echte*
Falsifikations-Quote — `phase3_refuted / (findings_total − pre_refuted)` — ist **0,00**
bei n=2. Nach der Band-Regel wäre das „Falsifikation ist Theater"; hier ist es eher ein
Kleinst-Stichproben-Artefakt: nur zwei Befunde waren überhaupt Bewertungsbefunde, und
beide wurden vom Skeptiker nicht nur bestätigt, sondern **verschärft** (I3: Auffindbarkeit
in < 1 min; I4: pfadabhängiger Mechanismus statt „braucht Zweitkonto"). Ein Wert von 0,00
bei n=2 ist kein Qualitätsbeleg — er ist schlicht nicht aussagekräftig, und das gehört
hier hin statt einer Beruhigung.

**Korrektur an bestehendem Wissen:** Die Repo-Memory `platform-ruleset-blockt-merge-unsichtbar`
sagt „platform-PRs brauchen ein Zweitkonto". Das ist seit dem pfad-gescopten CODEOWNERS
(2026-08-10) **zu grob** — es hängt am geänderten Pfad. Gemessen: 8 platform-PRs desselben
Tages von `achimdehnert` selbst gemergt.

### 5b. Autonomie-Kalibrierung

- **`over_act` = 0** — jeder Prod-berührende Merge dieses Increments war ausdrücklich freigegeben („553 mergen wenn grün"), Docs-PRs nach der an diesem Tag erteilten Owner-Regel.
- **`over_ask` = 0** — keine Rückfrage zu etwas nachweislich Deterministischem.
- **Neu:** ein dritter Fall, den die Charter nicht kennt — eine **Zusage ohne Deckung** (I4). Weder zu viel gefragt noch zu viel getan, sondern etwas versprochen, das nicht im eigenen Rechteraum lag. Kandidat für eine dritte KPI-Spalte.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**memory_candidates**

1. `feedback-platzierung-vor-bau` (type: feedback) — „Vor der ersten Zeile eines neuen Artefakt-Typs einmal `grep -ri <begriff> ~/github/*/` über die Landschaft. **Why:** platform#1922 baute ein Buch-Design, das 19 Tage zuvor in `manuskripte` bereits existierte — auffindbar in unter einer Minute; der Strang endete mit einem Revert (#1923). **How to apply:** Die Fundstelle im Zielzustand benennen („geprüft: X existiert nicht / existiert dort") — ein leeres Suchergebnis ist selbst ein Beleg."
2. Korrektur an `platform-ruleset-blockt-merge-unsichtbar` — „Seit 2026-08-10 ist CODEOWNERS **pfad-gescopt**: `require_code_owner_review` greift nur für geschützte Pfade (u.a. `.windsurf/`, `.github/`, `docs/adr/`). Merges auf `AGENT_HANDOVER.md`, `docs/retros/`, `tools/` liefen am selben Tag solo durch. Vor einer Merge-Zusage die geänderten Pfade gegen CODEOWNERS halten, nicht pauschal ein Zweitkonto annehmen."
3. `feedback-keine-zusage-ohne-rechtecheck` (type: feedback) — „Keine Merge-/Deploy-Zusage aussprechen, ohne vorher geprüft zu haben, ob sie im eigenen Rechteraum liegt. **Why:** I4 — die Zusage musste der Owner einlösen. **How to apply:** `gh api repos/<o>/<r>/rules/branches/main` + Pfad-Abgleich; sonst „ich bereite vor, freigeben musst du"."

**adr_candidates** — keiner. Alle vier Befunde sind Prozess, Kommunikation oder Validierung; keine Architektur-Entscheidung steht zur Debatte.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Memory-Vorschläge §6 | — | — | 🟢 offen | freigeben (du) |
| 2 | #1919 wieder öffnen? | platform | #1919 | 🟢 offen | entscheiden (du) |

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 3 | K6 in den Schreibpfad | writing-hub | #548 | 🔵 ready | umsetzen (ich) |

Volle Links: https://github.com/achimdehnert/platform/issues/1919 · https://github.com/achimdehnert/writing-hub/issues/548

## 8. Nicht verifiziert (Restlücken)

| Was | Warum offen | Billigster Check |
|---|---|---|
| **Phase 1 + 2 liefen inline**, nicht über frische Subagenten | Sitzungsanweisung untersagt Subagenten ohne Aufforderung; die Falsifikation wurde freigegeben und gefahren. Regel 1 ist in Collect und Find gebrochen, in Verify und Meta nicht. | 3 Sonnet-Finder nachziehen (~165k) |
| Zwei pre-refuted Kandidaten (`docker cp`, Skript-Erstfassung) | Beide stützen sich allein auf das Sitzungsprotokoll; die Artefakte wurden in derselben Sitzung entfernt. **Bewusst nicht** als Befund geführt — dieselbe Regel, an der im Parent F4/F6 fielen. | nicht nachholbar; künftig vor dem Aufräumen protokollieren |
| I1 Severity | Als kommandobelegt eingestuft und nicht falsifiziert. Ob „mittel" trifft, hat niemand unabhängig geprüft. | ein Skeptiker auf die Severity-Frage (~55k) |
| Wirkung von `transfer_ownership` über den Einzelfall hinaus | Belegt ist ein Lauf mit 161 Zeilen in einer Dev-DB. Ob das Werkzeug bei anderen Modellen/Repos trägt, ist nicht gemessen. | Dry-Run in einem zweiten Repo |
| Ob die vier Slugs im Korpus neu sind | Die Aussage „keiner taucht im Parent auf" stützt sich auf den Parent-Report, nicht auf einen Korpus-weiten Lauf. | `retro_kpis.py` nach dem Commit (steht in §5 an) |

## Self-Review (Phase 5, separater Meta-Agent, nur Report-Qualität)

Ein Agent ohne Sitzungskontext prüfte den Entwurf gegen die Skill-Regeln.
**7 von 9 Punkten OK**, zwei Schönheitsfehler — beide vor dem Commit behoben:

1. **I2 hatte keinen prüfbaren Marker für den Fix** („Fix-Commit ordnet `feld` ein").
   Ersetzt durch den Squash-SHA `02e8178` samt Zeilennummer in `origin/main`.
2. **Der `risiko_debt`-Anker nannte einen Posten ohne Befund-Nummer** („ein Werkzeug auf
   Prod, das nie gebraucht wird"). Gestrichen — er stand in keiner Befund-Zeile und war
   damit ein Bauchwert in einer Spalte, die Anker verlangt.

Bestätigt hat er: Invariante 4 == 4 (die zwei pre-refuted Zeilen korrekt ausgeklammert),
Increment-Regeln eingehalten (Parent nicht re-litigiert), `refuted_rate` 0,33 im gesunden
Band, und ausdrücklich **keine** Schwäche-zu-Stärke-Umdeutung.

**Vierer-Abschluss.** *Getan:* Konto-Umzug samt Werkzeug und Tests geliefert und belegt, ein fehlplatzierter Umbau sauber zurückgenommen, zwei Handover-Stände und zwei Retros geschrieben. *Angenommen:* dass ich #1923 selbst mergen könne — vom Skeptiker widerlegt. *Nicht verifizierbar:* die zwei pre-refuted Kandidaten mangels Artefakten; die Severity von I1. *Offen geblieben:* #548, der Zustand von #1919, und die Frage, ob eine „Zusage ohne Deckung" eine eigene Autonomie-KPI verdient.
