---
retro_schema: 1
date: 2026-10-05
repo_scope: [platform, decks-hub, iilsandbox]
session_id: eb9de7
footprint: deep
findings_total: 17
findings_survived: 10
refuted_rate: 0.41
phase3_refuted: 5
pre_refuted: 2
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [sicherheitscode-ausserhalb-governance-pfad, merge-ohne-head-pin, tracking-doc-stale-after-new-occurrence, budget-grenze-ohne-review-aenderbar]
recurring_findings: [gate-untested-tool-module-green-gate-wirkungslos, gate-check-ohne-positivkontrolle-wirkungslos, deferred-item-no-tracking-issue, tracking-doc-stale-after-new-occurrence, worktree-midsession-accumulation]
gates_caught: [claim-before-cheapest-check, main-tree-guard]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "1 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: keiner, weil jede Phase dieser Retro ein eigenes Ergebnis lieferte (Skeptiker kippten 5 Befunde, 3b kippte #2 und fand #17, Meta fand fehlende Belege) und keine der vier Belegarten fuer eine Phase vorliegt
---

# Session-Retro 2026-10-02 bis 2026-10-05 (Sitzung eb9de752…eb9de7)

Scope über die PR-Links im Transkript gezogen, nicht über das Datum. Zur Sitzung gehören:

- **decks-hub:** #123, #125, #127 und #128, dazu die Issues #122 und #126.
- **platform, Sandbox-Strang zu #3685 und ADR-308:** #3686, #3690, #3691, #3692, #3693, #3695, #3702, #3707, #3708, #3710, #3712, #3715, #3718 und #3721.
- **iilsandbox:** die fünf Spiegel.

Am selben Tag liefen in platform auch fremde Sitzungen (mail_agent, coach-hub, robo-lab). Die sind nicht im Scope.

**Footprint `deep`:** drei Repos und ein Prod-Deploy (decks-hub #123). Eine Stufe herunter ging nicht, weil Bedingung (c) verfehlt ist: 16 Befunde statt höchstens 10. Agenten-Budget: 3 Finder, 2 Skeptiker, 1 Widerlegung und 1 Meta, zusammen 7, jeweils etwa 55k Tokens.

## 0.0 Wirkungsbilanz

`gate_wirkung.py` meldet 7 Gates als RUECKFAELLIG, dazu eine abgelaufene Frist: `gate-anchored-without-drill-or-control` vom 2026-10-02 steht noch auf advisory. Für alle sieben liegt seit heute die Entscheidungsvorlage platform#3722 (G1–G8) vor. Als Konsequenz geht der Fall deshalb in die bestehende Zeile der Vorlage und bekommt keinen eigenen Vorschlag.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| untested-tool-module-green-gate | 4 (+1 hier, #11) | Quelle: der grüne Test prüft die Annahme, nicht die echte API | nachschärfen (#3722 G1 „scharf stellen") |
| check-ohne-positivkontrolle | 2 (+1 hier, #7) | Quelle: Probe ohne Gegenprobe mit Recht | nachschärfen (#3722 G3) |
| handover-stale-vor-merge, melder-ohne-leser, parallel-session-pr-collision, secret-leak-via-safe-pattern, stale-local-clone-as-ground-truth | 2–3 | keine Vorkommen in dieser Sitzung (#13 widerlegt) | wie #3722 G2/G4–G7, hier nichts Neues |

## 1. Executive Summary

- Der Sandbox-Strang hat Phase 1b samt Org-Profil geliefert:
  - fünf private Spiegel, Actions aus, gemessen;
  - eng gesetzter Token, Selbstprüfung grün;
  - `pr_merge_sa.py` mit fail-closed Profilprüfung;
  - alle Fälle aus §8.2 durch Tests belegt.
- 3 von 14 Strang-PRs reparieren einen Fehler aus einem PR derselben Sitzung (#3692, #3702, #3721). Jeder dieser Fehler war vor dem Merge billig prüfbar (#11). Das ist ein Rückfall auf ein Gate, das schon gebaut ist.
- Drei Sicherheitslücken sind offen:
  - `tools/sandbox/` ist kein Governance-Pfad. #3718 hat die Selbstprüfung deshalb ohne jedes Review geändert, entgegen ADR-308 Z.151 (#5).
  - Der Budget-Wächter liegt im selben Pfad und ist die einzige Kostengrenze je Lauf (#17, aus der Widerlegung).
  - Der Merge pinnt den Head-Commit nicht, und `actions_aus` wird vor dem Merge nicht neu gemessen. Die Spiegel haben keine Rulesets, also ist der Pin die einzige mögliche Sperre (#6).
- Der Live-Merge-Test S9 steht nirgends (#2). F4 und S10 sind dagegen im ADR geführt. ADR-308 widerspricht dem Stand auf main (#1).
- decks-hub: #122 und #126 sind sauber geschlossen und deployt. Nur eine Kleinigkeit: das Issue wurde 3 s vor dem Start des Deploys geschlossen (#3).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | ADR-308 nennt Profil-Negativtests „noch offen", obwohl #3721 sie geliefert hat; #3710–#3721 fehlen im ADR | Kommunikation | mittel | SURVIVES | ADR-308 Z.195 („Noch offen vor Phase 3: Profil-Negativtests"), Z.263 Status-Zeile `tools/sandbox/` nennt nur #3695/#3702/#3707; vs. #3721-Body | tracking-doc-stale-after-new-occurrence |
| 2 | Der Live-Merge-Test S9 ist weder Issue noch Ledger- oder ADR-Zeile, nur Sitzungsnotiz (F4 und S10 sind geführt, s. Widerlegung) | Prozesslücke | mittel | SURVIVES | alle Kommentare von platform#3685 ohne S9; ADR-308 ohne „Live"/„S9"; `gh issue list -R achimdehnert/platform --search "S9 sandbox"` leer | deferred-item-no-tracking-issue |
| 3 | decks-hub #126 vor dem Deploy-Beleg geschlossen (Auto-Close 19:18:58Z, Deploy-Start 19:19:01Z) | fehlende Validierung | niedrig | SURVIVES | decks-hub Deploy-Run 37053312009 (19:19:01Z, success), Commit 6209e46 | — |
| 4 | Offene Punkte aus Phase 1b stehen nur als Checkboxen in einem Kommentar von #3685, ohne Owner | Prozesslücke | mittel | SURVIVES | https://github.com/achimdehnert/platform/issues/3685#issuecomment-5984404025 | deferred-item-no-tracking-issue |
| 5 | `tools/sandbox/` (Selbstprüfung, Wächter, Spiegeln) fehlt in `sa_m.governance_pfade` und in CODEOWNERS; #3718 änderte `selbstpruefung.py` ohne Review (`reviews: []`), gegen ADR-308 Z.151 „Klasse nach Wirkung … im Zweifel gilt Schutzregel". Der Aufschub von F4 ist Owner-Entscheid (ADR-308 Z.399) | Prozesslücke | hoch | SURVIVES | `policies/autonomy-gates.md:315`; `.github/CODEOWNERS` nur `/tools/pr_merge_sa.py`; #3718 | sicherheitscode-ausserhalb-governance-pfad (neu) |
| 6 | Vor dem Merge wird nur die Repo-ID neu geprüft: kein `--match-head-commit`, `actions_aus` nicht neu gemessen; mit `actions_aus` fallen die Checks weg, und die Spiegel haben weder Rulesets noch Branch Protection (Plan ohne Pro: 403) | fehlende Validierung | mittel | SURVIVES | `tools/pr_merge_sa.py:624-651`, `tools/pr_merge_sa.py:193`, `:649` (`--auto`); `gh api repos/iilsandbox/platform/rulesets` → 403 | merge-ohne-head-pin (neu) |
| 7 | Selbstprüfung wertet 403/404 ohne Prüfung der Header als „Recht fehlt"; #3718 behauptet „ändert nie etwas" als Tatsache, obwohl 422 unbelegt ist | fehlende Validierung | mittel | SURVIVES | `tools/sandbox/selbstpruefung.py:196`, Z.298-313; #3718-Body | gate-check-ohne-positivkontrolle-wirkungslos |
| 8 | Netzfehler in der Selbstprüfung führen zum Durchlass (fail-open) | fehlende Validierung | niedrig | REFUTED | `selbstpruefung.py:374-384`: OSError wird zum Befund, `return 1` | — |
| 9 | #3689 versteckt die Lockerung der Sperrliste hinter „nachziehen" | Kommunikation | niedrig | REFUTED | #3689-Body nennt „Stamm `token` entfällt" ausdrücklich | — |
| 10 | decks-hub #123 behauptet Backup-Deckung ohne Beleg | fehlende Validierung | niedrig | REFUTED | #123 „Nicht in diesem PR": Nachweis in #122 offen geführt | — |
| 11 | 3 von 14 Strang-PRs reparieren einen vermeidbaren Fehler eines PR derselben Sitzung (#3692←#3691, #3702←#3695, #3721←#3712) | fehlende Validierung | hoch | SURVIVES | PR-Bodies und Merge-Zeiten: 50 min bis 8 h. Abschlag aus der Widerlegung: billig prüfbar sicher bei #3721 (wörtlicher §4.4-Satz) und #3692 (echtes Journal); #3702 zeigte sich erst im ersten echten Spiegellauf | gate-untested-tool-module-green-gate-wirkungslos |
| 12 | Die Classifier-Ablehnungen waren vermeidbar, weil der Zielzustand nicht als Freigabe hinterlegt war | Prozesslücke | mittel | REFUTED | Ablehnungen zur Hälfte nicht aus der Sandbox; der Rest ist gewolltes Sperrverhalten, Charta 3 | — |
| 13 | decks-hub-Handover #125/#128 waren binnen 24 h veraltet | Prozesslücke | niedrig | REFUTED | #125 beim Merge korrekt, Ablösung nach 28 h als reguläre Fortschreibung | — |
| 14 | decks-hub #123 lag 8 Tage offen | Kommunikation | niedrig | REFUTED (pre) | Erstellt 2026-09-24, vor Beginn der Sitzung, außerhalb der Grenze | — |
| 15 | Race oder Kollision beim Merge-Anteil Owner/Agent | Kommunikation | niedrig | REFUTED (pre) | Der Finder selbst: „kein Race belegt" | — |
| 16 | 9 Worktrees vom 2026-10-05 zu bereits gemergten PRs liegen noch | Prozesslücke | niedrig | SURVIVES | `ls ~/.repo-session/worktrees/platform`: 9 Einträge 2026-10-05, Branches zu gemergten #3702 #3707 #3710 #3712 #3718 | worktree-midsession-accumulation |
| 17 | Der Budget-Wächter `tools/sandbox/waechter.py` ist laut ADR-308 Z.176 die einzige Kostengrenze je Lauf („kein Gesamtdeckel am Abo (F2)"), liegt aber im ungeschützten Pfad aus #5; eine Lockerung der Grenzen bräuchte nur ein Code-Mandat (Gate 5 Spend) | Prozesslücke | hoch | SURVIVES (NEU aus 3b) | ADR-308 Z.176; `policies/autonomy-gates.md:315`; `tools/sandbox/selbstpruefung.py:37` erlaubt API-Schlüssel im Container | budget-grenze-ohne-review-aenderbar (neu) |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | Phase 1b und Profil geliefert; ADR und Folgepunkte nicht nachgezogen (#1, #2) |
| architektur_design | 3 | Profil fail-closed und Repo-ID-Recheck, aber Selbstprüfung ohne Review gemergt, gegen die eigene ADR-Regel Z.151 (#5) |
| code_konventionstreue | 4 | Commit-Format und `test_should_*` durchgehend; Hypothese als Tatsache formuliert (#7) |
| risiko_debt | 2 | drei offene Sicherheitslücken vor Phase 3, eine davon an der Kostengrenze (#5, #6, #17) |
| prozess_effizienz | 3 | 3 Reparatur-PRs auf 14, davon 2 billig vermeidbar (#11) |
| entscheidungsqualitaet | 4 | F4 bewusst und vom Owner ratifiziert aufgeschoben (ADR-308 Z.399); Lücke beim Merge-Mandat (#6) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| ADR-308 blieb nach #3712–#3721 auf dem Stand von Phase 1b | Jeder PR, der eine „noch offen"-Zeile des ADR schließt, enthält die ADR-Zeile oder legt im selben Zug den ADR-PR an | #1 |
| S9 (Live-Merge-Test) nur als „nächste Sitzung" | Beim Verschieben im selben Zug eine Zeile in die Phase-3-Checkliste des ADR (§4.7) oder ein Issue mit Link | #2 |
| #126 per „Closes" geschlossen, bevor der Deploy gelaufen war | Bei deployten Repos „Refs" statt „Closes"; Issue erst nach grünem Deploy-Lauf schließen | #3 |
| „Bewusst offen"-Checkboxen in einem Kommentar ohne Owner | Bewusst Offenes als eigene Issue-Checkliste im Kopf von #3685, mit Owner je Zeile | #4 |
| Sicherheitscode in `tools/sandbox/` außerhalb der Governance-Pfade | Ein neues Verzeichnis mit Sicherheitsprüfungen kommt im selben PR in `governance_pfade`, als Vorschlag an den Owner | #5 |
| Merge nach einmaliger Messung, ohne Pin des Head-Commits | `gh pr merge --match-head-commit <geprüfte SHA>` und `actions_an` direkt vor dem Merge neu messen | #6 |
| 403/404 gilt ungeprüft als Beleg; Hypothese als Tatsache im PR | Header für Rate-Limit prüfen (403 mit `x-ratelimit-remaining: 0` ⇒ Befund); im PR-Text Gemessenes und Hypothese trennen | #7 |
| Tests gegen die eigene Annahme, Fehler erst im Echtlauf gefunden | Vor dem Merge ein Gegenbeispiel-Test je Spezifikationssatz (§4.4) und ein Trockenlauf gegen einen echten Spiegel | #11 |
| Worktrees gemergter PRs bleiben liegen | `repo-session.sh reap` beim Sitzungsende als Pflichtschritt | #16 |
| Budget-Wächter als einzige Kostengrenze im ungeschützten Pfad | Budgetgrenzen in eine Datei unter einem Governance-Pfad legen, die der Wächter nur liest; Änderung der Grenzen = Schutzregel-Änderung mit Owner-Approval | #17 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Lauf 2026-10-05, origin/main): 57 Slugs mit Zähler ≥2. Davon betrifft diese Sitzung:

- `deferred-item-no-tracking-issue`: 54. Vorkommen. Dafür liegt eine Owner-Entscheidung „ohne Gate" in `declined` vor. #2 und #4 sind also kein Gate-Kandidat, sondern ein Hinweis, dass die Entscheidung im declined-Eintrag überprüft werden sollte. Kein eigenes Item; der Einzelfall S9 wird mit M4 geschlossen.
- `tracking-doc-stale-after-new-occurrence`: 13. Vorkommen. Es ist kein Gate registriert und auch nichts in `declined`, also gilt GATE-PFLICHT (#1). Als Kandidat geführt.
- `worktree-midsession-accumulation`: 11. Vorkommen. Ein Gate ist registriert, aber nicht als rückfällig gemeldet. Notiert, keine Konsequenz.

Abgleich mit MEMORY.md (decks-hub): keine passende Drift-Memory.

### 5a. Rückfall-Prüfung

- `gate-untested-tool-module-green-gate-wirkungslos` (#11): **umbauen**, wie in #3722 G1 vorgeschlagen („scharf stellen"). Kein zweites Gate.
- `gate-check-ohne-positivkontrolle-wirkungslos` (#7): **ausweiten**, wie in #3722 G3.
- Beide Einträge bekommen `revised` und `revision_note` erst mit dem Owner-Wort auf #3722. Bis dahin sind sie nur Kandidaten.

### 5b. Autonomie-Kalibrierung

- `over_ask`: 0. Gemessen wurde nicht. Das Owner-Wort „all done go" zeigt aber, dass die Vorlagen angenommen wurden.
- `over_act`: 0:
  - Merges auf Governance-Pfaden (#3712, #3715, #3721) liefen über `pr_merge_sa.py` mit Approval, gemergt meist vom Owner.
  - iilsandbox-Writes waren vom Classifier gesperrt und wurden nicht umgangen.
  - Der Prod-Deploy von decks-hub #123 war vom Owner freigegeben.

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidate** (platform, `feedback`):
```
---
name: feedback_spezifikationssatz_gegenbeispiel_vor_merge
description: Jeder Satz der Form "X fuehrt zur Verweigerung" im ADR bekommt vor dem Merge einen Gegenbeispiel-Test; Echtlauf gegen Spiegel vor Merge
metadata:
  type: feedback
---
Bevor ein Werkzeug-PR gemergt wird, das eine ADR-Regel umsetzt, je Regel-Satz mindestens ein Gegenbeispiel testen und einen Trockenlauf gegen die echte Umgebung fahren.
**Why:** Retro eb9de7: 3 von 14 PRs reparierten binnen Stunden vermeidbare Fehler (#3692, #3702, #3721).
**How to apply:** Vor `pr_merge_sa.py` die Frage stellen, welcher Satz der Spezifikation noch keinen Negativtest hat.
```

**adr_candidate** (ADR-308, S10-Nachtrag):
- §5: Profil-Negativtests „belegt (#3721)".
- §4.4 ergänzen: „vor dem Merge Head-Commit pinnen und `actions_aus` neu messen".
- §8.2: `tools/sandbox/` als Governance-Pfad (F4).

## 7. Maßnahmen

- **[M1]** 🟢 F4 vorziehen: `tools/sandbox/` schützen · platform · Owner-Wort, dann Policy-PR — https://github.com/achimdehnert/platform/blob/main/policies/autonomy-gates.md
- **[M2]** 🔵 Head-Pin und Neumessung vor Merge · platform · Werkzeug-PR mit Approval — https://github.com/achimdehnert/platform/blob/main/tools/pr_merge_sa.py
- **[M3]** 🔵 S10: ADR-308 nachziehen · platform · ADR-PR mit Approval — https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-308-sandbox-werkstatt-als-weiterentwicklungs-template.md
- **[M4]** 🔵 S9 in Phase-3-Checkliste · platform · mit M3 — https://github.com/achimdehnert/platform/issues/3685
- **[M5]** 🔵 Rate-Limit-Erkennung Selbstprüfung · platform · Code-PR — https://github.com/achimdehnert/platform/blob/main/tools/sandbox/selbstpruefung.py
- **[M6]** 🟢 G1/G3 entscheiden · platform · Owner-Wort — https://github.com/achimdehnert/platform/pull/3722
- **[M7]** 🔵 Gemergte Worktrees aufräumen · platform · reap — https://github.com/achimdehnert/platform/issues/3685
- **[M8]** 🟢 Budgetgrenzen unter Schutz · platform · Owner-Wort, mit M1 — https://github.com/achimdehnert/platform/blob/main/tools/sandbox/waechter.py

## 8. Nicht verifiziert (Restlücken)

- Ob die Actions-Probe mit einem Token, das das Recht hat, 422 liefert und nichts ändert. Billigster Check: einmal mit einem Owner-Token gegen einen Wegwerf-Spiegel, als Owner-Zug.
- Ob ein Rate-Limit-403 in der Schleife über fünf Spiegel real auftritt. Billigster Check: Header `x-ratelimit-remaining` beim nächsten Lauf mitloggen.
- Prod-Wirkung von decks-hub #127 nach dem Deploy: nur der Lauf ist grün, nichts geklickt.
- Die Transkript-Kennzahlen decken die ganze Konversation ab, auch decks-hub. Wie die 34 Fehlerläufe auf die Stränge verteilt sind, wurde nicht ausgezählt.

**Getan:**
- 3 Finder, 2 Skeptiker, Widerlegung, Meta, Längsschnitt und 5a, Report.
- 17 Befunde, davon 10 überlebend (einer neu aus der Widerlegung).
- Regelbruch beim Schreiben: ein Teil der Beleg-Nachträge aus Phase 5 lief per Python-Skript statt per Edit. Der Inhalt wurde danach gelesen und ist korrekt.

**Angenommen:** Die Session-Grenze aus den Transkript-Links ist vollständig. PRs ohne Link im Transkript fehlen, zum Beispiel #3689, das nur über einen Skeptiker in den Blick kam.

**Nicht verifizierbar:** das 422-Verhalten mit Recht. Das Owner-Token ist für diese Sitzung tabu.

**Offen geblieben:** M1–M8.

## Widerlegung

Opus-Subagent mit frischem Kontext. Er sah Entwurf und Artefaktliste, keine Erzählung. Belege von ihm wurden für #5, #6 und #17 im Haupt-Kontext nachgezogen: CODEOWNERS Z.113, Rulesets 403, `reviews: []` bei #3718, `selbstpruefung.py:37`.

| # | Verdikt | Beleg |
|---|---|---|
| 2 | GEKIPPT (Teil) | F4 steht als Owner-Entscheid in ADR-308 Z.399 und in der Phase-3-Checkliste Z.248; S10 betrifft den ADR selbst. Nur S9 ist ungeführt. Befund auf S9 verengt, Severity hoch → mittel |
| 5 | BESTAETIGT, verschärft | #3718 änderte die Selbstprüfung ohne Review, gegen ADR-308 Z.151; Gegengewicht: Aufschub F4 vom Owner ratifiziert (Z.399) |
| 6 | BESTAETIGT, verschärft | iilsandbox ohne Rulesets/Branch Protection (403 „Upgrade to GitHub Pro"); `--auto` ohne Required Checks mergt sofort |
| 11 | BESTAETIGT mit Abschlag | billig vermeidbar sicher 2 von 3 |
| 1 | BESTAETIGT | ADR zuletzt 08:03 geändert, #3721 um 10:08 gemergt |
| 3 | BESTAETIGT | Hinweis „trivial, systemisches Auto-Close" — bleibt als niedrig stehen, der Soll-Schritt („Refs" statt „Closes") ist billig |
| 14 | BESTAETIGT REFUTED | #123 angelegt 2026-09-24 |
| 8–10, 12, 13, 15 | ohne Gegenindiz | nicht einzeln gegengeprüft |
| 17 | NEU | Budget-Wächter als einzige Kostengrenze im ungeschützten Pfad (Gate 5) |

Scores nach der Widerlegung: architektur_design 4 → 3, risiko_debt 3 → 2, entscheidungsqualitaet neu verankert (F4-Aufschub statt widerlegter Befunde).

Hinweis zur Phase-5-Meta: sie rechnete refuted_rate als 5/14. Das Skill-Frontmatter definiert (phase3_refuted + pre_refuted)/findings_total = 7/17 = 0.41. Der Wert folgt dem Skill.

## Streichbahn

Keine Streichung. Jede Phase lieferte ein eigenes Ergebnis:
- Die Skeptiker kippten 5 Befunde.
- Die Widerlegung verengte #2 und fand #17.
- Die Meta fand fünf fehlende harte Belege (Run-ID, Kommentar-URL, Zeilenangaben).

Damit liegt für keine Phase die Belegart „kein Effekt" vor.
