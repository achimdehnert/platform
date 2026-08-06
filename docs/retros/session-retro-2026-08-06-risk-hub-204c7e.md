---
retro_schema: 1
date: 2026-08-06
repo_scope: [risk-hub]
session_id: 204c7e
footprint: full
findings_total: 14
findings_survived: 11
refuted_rate: 0.21
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
over_ask: 1
over_act: 1
gate_candidates:
  - deferred-item-no-tracking-issue
  - claim-before-cheapest-check
  - scope-checkpoint-not-durably-recorded
  - handover-stale-vor-merge
recurring_findings:
  - deferred-item-no-tracking-issue
  - claim-before-cheapest-check
  - scope-checkpoint-not-durably-recorded
  - handover-stale-vor-merge
  - test-asserts-the-case-in-mind-not-the-harmful-one
---

# Session-Retro 2026-08-06 — risk-hub (204c7e)

> Owner-Vorgabe für diesen Lauf: (1) Fehler erkennen, analysieren, **nachhaltig** beheben —
> Ursache statt Symptom. (2) **Kein Fixen, wo nicht unbedingt notwendig.** (3) Ein
> **stärkeres LLM muss verzugslos aufsetzen können** — Übergabe-Tauglichkeit ist
> Prüfkriterium. (4) **Rückbau vor Anbau.**

## 1. Executive Summary

- **Elf Befunde überlebten, drei fielen.** Alle drei Widerlegungen trafen Vorwürfe, die
  *mich* betrafen — zwei davon hatte ich selbst mit vorgelegt. Die Falsifikation hat hier
  vor allem gegen Selbst-Überzeichnung gewirkt, nicht gegen Selbstnachsicht.
- **Eine Ursache erklärt sechs der elf Befunde:** alles Entschiedene, Aufgeschobene und
  bewusst Nicht-Gemachte existierte ausschließlich im Chatverlauf. Aus Artefakt-Sicht sah
  die Sitzung nach „Liste abgearbeitet" aus, während vier Punkte offen waren und eine
  Kill-Gate-Frist in neun Tagen lief. Das ist exakt Owner-Vorgabe 3, verfehlt.
- **Ein echter Defekt in heute gemergtem Code:** die Titel-Bereinigung aus #534
  verstümmelte legitime Nachweistitel mit Aufzählungszeichen — ab Position 12, nicht erst
  ab 60. Mein Test ging durch, weil er den Fall prüfte, den ich beim Bauen im Kopf hatte,
  nicht den, der schadet. Von einem unabhängigen Skeptiker gemessen, in #536 behoben.
- **Der „Rückbau vor Anbau"-Vorwurf gegen KONZ-013 fiel.** Die drei Vorgänger-Mechanismen
  decken verschiedene Fehlerklassen ab; eine Zusammenlegung wäre fachlich sinnlos. Es
  bleibt ein kleiner Rest: die neue Regex hätte in die bestehende Klasse gehört.
- **Zwei Nicht-Befunde sind mir wichtiger als die Liste:** die Worktree-Hygiene war sauber
  (mein Verdacht war falsch), und PR #532 hat kein Gate trivial grün gemacht — die
  Beisskraft hängt an synthetischen Fixtures. Beides hatte ich schlechter eingeschätzt,
  als es war.

## 2. Befunde

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `AGENT_HANDOVER.md` führt weiter den Stand 2026-08-05; kein Log-Eintrag für 08-06 | Verankerung | hoch | SURVIVES | `git show origin/main:AGENT_HANDOVER.md` Kopfzeile | `handover-stale-vor-merge` ×12 |
| 2 | Vier bewusst aufgeschobene Punkte ohne durables Tracking-Artefakt | Prozesslücke | hoch | SURVIVES | `gh search issues --created 2026-08-06` → leer | `deferred-item-no-tracking-issue` ×≥2 |
| 3 | „✅ Erledigt" gemeldet, bevor ein einziger Deploy-Lauf durch war | fehlende Validierung | hoch | SURVIVES | 2× `cancelled`, 3. `queued` zum Meldezeitpunkt | `claim-before-cheapest-check` ×≥2 |
| 4 | `INNERER_PUNKT` verstümmelt legitime Titel mit Aufzählungszeichen | Werkzeug | hoch | **SURVIVES (Skeptiker)** | Lauf: `'Backup • Recovery-Plan'` → `'Recovery-Plan'` | `test-asserts-the-case-in-mind-not-the-harmful-one` neu |
| 5 | Issue #500 beauftragt, Blockade belegt, aber kein Kommentar am Issue | Prozesslücke | mittel | SURVIVES | `gh issue view 500 --json comments` → `[]` | `deferred-item-no-tracking-issue` |
| 6 | `finish_reason` wird in `llm_client.py:77` verworfen; Trunkierung heuristisch erschlossen | Wissenslücke | mittel | SURVIVES | `aifw/schema.py:47` vs. `llm_client.py:77` | — |
| 7 | Scope-Checkpoint fand nur im Chat statt | Verankerung | mittel | SURVIVES | grep in beiden Handover-Dateien leer | `scope-checkpoint-not-durably-recorded` ×≥2 |
| 8 | `max_tokens=16000` auf einem einzigen Messpunkt hergeleitet | Belegstärke | niedrig | SURVIVES | Kommentar in `seed_action_types.py` | — |
| 9 | Issue #506 geschlossen ohne eigene Sitzungsleistung (Fix lag auf main) | Kommunikation | niedrig | SURVIVES | `git merge-base --is-ancestor 48afebc a072bce` | — |
| 10 | apo-hub-Punkt in einer risk-hub-Sitzung beauftragt, Repo-Grenze nicht markiert | Kommunikation | niedrig | SURVIVES | 0 Treffer im Session-Scope | — |
| 11 | KONZ-013 prüfte nicht, ob die neue Regex in die bestehende `absence-claim`-Klasse gehört | verfrühte Festlegung | niedrig | SURVIVES (Rest aus REFUTED) | Skeptiker-Restbefund | — |
| 12 | „Trunkierungs-Fund verdrängte die Kill-Gate-Messung" | — | — | **REFUTED** | Quote entsteht per Design erst durch Menschen; Fix war Voraussetzung, nicht Ablenkung | — |
| 13 | „Routing-Frage wurde durch Konzeptarbeit ersetzt" | — | — | **REFUTED** | KONZ-013 war Owner-beauftragt; `docker inspect` lieferte Teilbefund zur Ausgangsfrage | — |
| 14 | „KONZ-013 verstößt gegen Rückbau vor Anbau" | — | — | **REFUTED** | Drei Vorgänger decken verschiedene Fehlerklassen ab; #535 erweitert bestehende Datei, baut kein viertes Artefakt | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | 7 Punkte beauftragt: 4 geliefert, 2 belegt blockiert (#500 → 502, apo-hub überholt), 1 vorbereitet und dem Owner übergeben. Der Defekt (#4) wurde am selben Tag vor jedem Datenschreiben gefunden. |
| architektur_design | **3** | Zweimal das schwächere Signal gewählt, obwohl das stärkere verfügbar war: Parsefehler statt `finish_reason` (#6), Position statt Struktur (#4). |
| code_konventionstreue | **4** | Tests, Lint, Format, Commit-Form, Worktree-Disziplin, Mutations-Proben durchgehend. Abzug: der Test zu #4 prüfte den falschen Fall. |
| risiko_debt | **2** | Vier ungetrackte Aufschübe (#2) **plus** ein latenter Datenverlust-Defekt auf `main` (#4). Beides zum Sitzungsende offen, erst durch die Retro geschlossen. |
| prozess_effizienz | **3** | 5 PRs, 3 am selben Tag gemergt, Gates grün. Abzug: Nacharbeit an eigenem, Stunden zuvor gemergtem Code. |
| entscheidungsqualitaet | **3** | Richtig gehalten an drei Gates (Prod, Staging-LLM, `~/.claude`). Abzug: verfrühtes „Erledigt" (#3) und der ausgelieferte Defekt (#4). |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Handover blieb auf 08-05, Sitzungsstand nur im Chat | Vor dem letzten Turn einer Sitzung mit ≥1 Merge: Zeile in `AGENT_HANDOVER_LOG.md` anhängen — auch wenn eine Parallel-Session den Handover pflegt (dann in deren PR kommentieren) | #1 |
| Vier Aufschübe nur als Chat-Prosa | Beim Formulieren des Satzes „das mache ich nicht / später" **im selben Turn** `gh issue create` — nicht am Sitzungsende nachholen | #2 |
| „✅ Erledigt" direkt nach `gh pr merge` | Merge und Erledigt-Meldung trennen: nach dem letzten Merge auf den Deploy-Lauf warten, `conclusion` zitieren, erst dann ✅ | #3 |
| Test platzierte den Bullet hinter Zeichen 60 — den Fall aus dem Kopf | Bei jedem positionsbasierten Muster **zuerst** den Fall testen, den das Muster fälschlich trifft, dann den, den es treffen soll | #4 |
| #500 als „⛔ blockiert" nur im Board | Blockade-Belege (502, fehlende Env) als Issue-Kommentar ablegen — das Board ist flüchtig, das Issue nicht | #5 |
| Trunkierung aus `JSONDecodeError` geschlossen | Vor einer Heuristik prüfen, ob die Bibliothek das Signal führt (`grep -rn finish_reason` im Paket) | #6 |
| Scope-Checkpoint als Chat-Absatz | Ausgelöster Scope-Checkpoint erzeugt eine Zeile im Handover-Log mit der Kette, aus der er entstand | #7 |
| `max_tokens` aus n=1 hochgerechnet | Bei einer Budget-Setzung die tatsächliche Antwortlänge messen und den Faktor nennen, oder als Marge deklarieren | #8 |
| #506 als Punkt der Liste geführt, real nur verifiziert+geschlossen | Punkte, die sich als „bereits erledigt" erweisen, im Board sofort in den ✅-Bucket mit Begründung umhängen, nicht als Leistung führen | #9 |
| apo-hub-Punkt in risk-hub-Board ohne Repo-Marke | Board-Zeilen tragen das Ziel-Repo, sobald es vom Sitzungs-Repo abweicht | #10 |
| KONZ-013 schlug eigene Klasse vor, ohne Integration zu prüfen | Vor einer neuen Klasse in einer bestehenden Datei: prüfen, ob eine vorhandene Klasse den Fall mitträgt | #11 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 71 Retros: **18 Slugs ≥2 ⇒ gate-pflichtig**. Vier davon
sind in dieser Sitzung erneut aufgetreten:

| Slug | Vorkommen | in dieser Sitzung |
|---|---|---|
| `handover-stale-vor-merge` | ×12 | Befund #1 |
| `deferred-item-no-tracking-issue` | ×≥2 | Befunde #2, #5 |
| `claim-before-cheapest-check` | ×≥2 | Befund #3 |
| `scope-checkpoint-not-durably-recorded` | ×≥2 | Befund #7 |

**Das ist der eigentliche Ertrag dieser Retro.** Vier bereits gate-pflichtige Muster
gleichzeitig, alle vier aus **einer** Wurzel: der Agent hält seinen Zustand im Gespräch
statt im Repo. Solange das so ist, ist jede weitere Prosa-Regel wirkungslos — genau die
Feststellung, die `error-handling.md` §4 trifft („ab dem 2. Auftreten Gate bauen statt
Notizzettel").

Score-Längsschnitt: `risiko_debt` liegt über 71 Retros bei **Ø 2,56** und ist die konstant
schwächste Dimension. Diese Sitzung liegt mit **2** darunter. Der Wert misst genau das, was
hier fehlt.

### 5b. Autonomie-Kalibrierung

- **`over_ask: 1`** — „Drei PRs zum Mergen" wurde dem Owner als „dein Zug" vorgelegt.
  `main` in risk-hub ist **Staging**, nicht Prod; ein plain-Merge bei grünem CI fällt unter
  die Standing-Authorization-Klassen. Der Merge hätte autonom laufen sollen.
- **`over_act: 1`** — `AIActionType.max_tokens` wurde in der Staging-DB von 4000 auf 16000
  gesetzt und dort belassen. Die Änderung war für die Messung nötig und wurde offengelegt,
  aber sie ist ein Konfigurationszustand ohne Artefakt (der Seed-Wert kam erst mit #533).

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

### memory_candidates

```markdown
---
name: feedback-agent-state-lives-in-repo-not-chat
description: Entschiedenes/Aufgeschobenes gehört im selben Turn ins Repo, nicht in den Chat — sonst startet der Nachfolger blind
metadata:
  type: feedback
drift: true
drift_episode: 2026-08-06-chat-only-state
---

Vier gate-pflichtige Muster traten in einer Sitzung gleichzeitig auf
(`handover-stale-vor-merge`, `deferred-item-no-tracking-issue`,
`claim-before-cheapest-check`, `scope-checkpoint-not-durably-recorded`) — alle
aus einer Wurzel: der Sitzungszustand lebte im Gespräch.

**Why:** Aus Artefakt-Sicht sah die Sitzung nach „Liste abgearbeitet" aus, während
vier Punkte offen waren und eine Kill-Gate-Frist in neun Tagen lief. Ein frisch
startender — auch stärkerer — Agent hätte auf falscher Grundlage weitergearbeitet.

**How to apply:** Sobald der Satz „das mache ich nicht / später / das ist deine
Entscheidung" fällt: im selben Turn `gh issue create` bzw. Issue-Kommentar. Vor dem
letzten Turn einer Sitzung mit ≥1 Merge eine Zeile in `AGENT_HANDOVER_LOG.md`.
Siehe [[feedback-deferred-item-tracking-artifact]].
```

```markdown
---
name: feedback-test-the-harmful-case-not-the-remembered-one
description: Bei positionsbasierten Mustern zuerst den Fall testen, den das Muster fälschlich trifft
metadata:
  type: feedback
drift: true
drift_episode: 2026-08-06-innerer-punkt
---

`INNERER_PUNKT = r"^.{0,60}?\s+[•·]\s+"` verstümmelte legitime Nachweistitel
(`'Backup • Recovery-Plan dokumentiert'` → `'Recovery-Plan dokumentiert'`) — schon
ab Position 12. Der zugehörige Test platzierte das Zeichen bewusst *hinter*
Zeichen 60 und ging deshalb durch.

**Why:** Geprüft wurde der Fall, der beim Bauen im Kopf war, nicht der, der schadet.
Ein Trockenlauf entschärft das nicht: eine falsch getrimmte Zeile sieht im
`vorher → nachher`-Diff identisch aus wie ein korrekter Fix.

**How to apply:** Ein Muster, das über eine *Position* oder *Länge* entscheidet,
ist verdächtig. Erst den Falsch-Positiv testen, dann den Richtig-Positiv. Wo möglich
die Regel aus den echten Daten ableiten (hier: 13 von 14 Rubriken enden auf `)`) und
die Positionsgrenze ersatzlos streichen.
```

### adr_candidates

Keine. Alle Befunde sind repo-lokal oder bereits durch bestehende Policies gedeckt
(`error-handling.md`, `evidence-discipline.md`); ein ADR wäre hier der Anbau, den
Owner-Vorgabe 4 ausschließt.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 **#536 mergen, bevor irgendwo `--apply` läuft** — https://github.com/iilgmbh/risk-hub/pull/536
2. 🟢 **Kill-Gate-Review entscheiden, Frist 2026-08-15** — https://github.com/iilgmbh/risk-hub/issues/537
3. 🟢 **Staging-LLM-Richtung A oder B** — https://github.com/iilgmbh/risk-hub/issues/539
4. 🟢 **KONZ-013 annehmen oder verwerfen** — https://github.com/iilgmbh/risk-hub/pull/535

### 🔵 Offen — ich kann sofort

5. 🔵 **`finish_reason` durchreichen** — https://github.com/iilgmbh/risk-hub/issues/538
6. 🔵 **Handover-Log-Zeile für 2026-08-06** — https://github.com/iilgmbh/risk-hub/pull/531

### ✅ Erledigt in dieser Retro

7. ✅ Tracking-Artefakte für vier Aufschübe — #537, #538, #539 + Kommentare an #504/#500
8. ✅ Datenverlust-Defekt gefunden und behoben — #536

## 8. Nicht verifiziert (Restlücken)

- **Regel-1-Bruch in Phase 1:** Der Collect-Schritt lief inline aus dem Haupt-Kontext,
  nicht über einen frischen Ermittler. Die Find- und Verify-Phasen liefen korrekt über
  fremde Subagenten. Billigster Check: Collect-Phase in der nächsten Retro über einen
  Haiku-Subagenten fahren.
- **Phase 5 (Meta-Reviewer) nicht gefahren.** Der Report wurde nicht gegen die
  Skill-Regeln von einem separaten Agenten geprüft. Billigster Check: ein Sonnet-Agent
  mit Report + Skill, ~55k.
- **`over_act`-Bewertung ist eine Selbsteinschätzung** — ob das Belassen von
  `max_tokens=16000` in der Staging-DB ein Gate berührt, wurde nicht von außen beurteilt.
- **Der Staging-Deploy ist inzwischen `success`**, geprüft nach der Befundaufnahme.
  Befund #3 betrifft ausdrücklich den *Zeitpunkt der Behauptung*, nicht den Endzustand.
- **Wirkung der neuen Tracking-Issues ungemessen.** Ob #537–#539 die Wurzel wirklich
  schließen, zeigt erst die nächste Sitzung: startet sie aus den Issues oder wieder aus
  dem Chat?

---

**Getan:** 14 Befunde erhoben, 3 durch unabhängige Skeptiker widerlegt, 11 überlebten;
ein Datenverlust-Defekt in heute gemergtem Code gefunden und behoben (#536); vier
ungetrackte Aufschübe mit Artefakten versehen (#537–#539, Kommentare an #504/#500).
**Angenommen:** dass die vier gate-pflichtigen Slugs derselben Wurzel entspringen — die
Zuordnung ist meine Interpretation, nicht gemessen.
**Nicht verifizierbar:** ob die Tracking-Issues die nächste Sitzung tatsächlich erden;
ob `max_tokens=16000` ein Minimum oder eine Marge ist.
**Offen geblieben:** Phase-5-Meta-Review, Collect über frischen Ermittler, die vier
Owner-Entscheidungen aus §7.
