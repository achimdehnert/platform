---
retro_schema: 1
date: 2026-09-02
repo_scope: [platform]
session_id: c36878
footprint: full
findings_total: 15
findings_survived: 12
refuted_rate: 0.20
phase3_refuted: 3
pre_refuted: 0
over_ask: 0
over_act: 0
over_ask_klassen: []
over_act_klassen: []
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 4
  entscheidungsqualitaet: 4
gate_candidates: [selbstbetreffend-mit-produktivaenderung-gebuendelt, governance-pfad-ohne-review-pflicht, version-regex-verliert-zweite-stelle, claim-gate-sieht-keine-chronologie-behauptung]
recurring_findings: [claim-before-cheapest-check, deferred-item-no-tracking-issue]
gates_caught: [claim-before-cheapest-check]
---

# Session-Retro 2026-09-02 — platform — Lotsen-Wachstum (c36878)

Reviewte Sitzung: Owner-Auftrag „Fähigkeiten so verbessern, dass eine perfekte Zusammenarbeit
bei weiter wachsenden LLM-Fähigkeiten (Fable 6, 7, 8, …) gewährleistet ist; Wachstum zu
geeigneter Zeit vorschlagen." Ergebnis: [#2617](https://github.com/achimdehnert/platform/pull/2617)
(gemergt, `da7dab8d`), Tracking [#2618](https://github.com/achimdehnert/platform/issues/2618).

**Methode:** 1 Collector (haiku) + 3 Finder (sonnet, je Dimension) + 1 gebündelter Skeptiker
(sonnet) auf die Bewertungsbefunde. Kommandobelegte Befunde gingen nicht durch die
Falsifikation (Phase-0-Klassentabelle). Erste Retro mit den in dieser Sitzung eingeführten
Feldern `over_ask_klassen` / `over_act_klassen`.

## 1. Executive Summary

- Der Auftrag ist geliefert: Sensor, Einstufungslogik und Runbook sind gebaut, gemergt,
  live verteilt und mit acht neuen Tests belegt. Der Regelkreis steht.
- Der **schwerste Befund kam nicht aus der Sitzung, sondern durch sie**: selbstbetreffende
  Governance-Texte unter `docs/governance/` sind von keiner Review-Regel gedeckt. Nur die
  mitgebündelte `.windsurf/`-Datei erzwang hier ein menschliches Auge.
- Genau dieses Bündeln verstößt gegen die Charta-Regel, Selbstbetreffendes ungebündelt
  vorzulegen. Der Verstoß hat den PR zufällig sicherer gemacht als die Regel es getan hätte.
- Die Einstufungslogik für Modellwechsel trifft bei Datums- und Zweitversions-IDs ein
  stilles Fehlurteil (MINOR statt MAJOR) — im Herzstück der Modellgenerationsfestigkeit.
- Drei von fünf Bewertungsbefunden wurden widerlegt, darunter zwei Selbstanklagen, die zu
  streng waren. Eine Aussage an den Owner über die Chronologie des Review-Bots war falsch.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `docs/governance/` ist weder in `.github/CODEOWNERS` noch in `sa_m.governance_pfade` geschützt; das `main`-Ruleset verlangt `required_approving_review_count: 0` + `require_code_owner_review: true`. Ein PR mit nur der Runbook-Datei wäre CLEAN ohne jedes Review gemergt worden — obwohl dort selbstbetreffende Vollmachten-Regeln liegen | Prozesslücke | hoch | SURVIVES | `git show origin/main:.github/CODEOWNERS`; `gh api repos/achimdehnert/platform/rulesets/17621471 --jq '.rules[]\|select(.type=="pull_request").parameters'`; `sa_m.governance_pfade` in `policies/autonomy-gates.md` | neu |
| 2 | Runbook §3a (selbstbetreffend) wurde mit drei Produktivänderungen in einem PR gebündelt. Charta Art. 1.8 verlangt „nie mit Produktivänderungen gebündelt"; der Changelog derselben Datei nennt am 2026-08-06 einen Präzedenzfall, in dem es korrekt getrennt wurde | Konventionsverstoß | mittel | SURVIVES | `git show origin/main:docs/konzepte/KONZ-platform-025-lotsen-charta.md` Art. 1.8 + Changelog-Zeile 2026-08-06; `gh pr view 2617 --json files` | neu |
| 3 | `fam_major()` im Detektor captured nur die erste Ziffernfolge nach der Familie. `claude-haiku-4-5-20251001` → `claude-haiku-4-9-20260315` ergibt beidseitig `haiku-4` und wird als **MINOR** eingestuft — das Gegenteil des Design-Ziels „im Zweifel MAJOR". Kein Test deckt diesen Fall | fehlende Validierung | hoch | SURVIVES | Skeptiker stellte die Originalfunktionen in einer Shell nach; `git show origin/main:tools/claude-hooks/model_change_detector.sh`; Testdatei kennt nur vier Fälle | neu |
| 4 | Runbook §3a Schritt 3 verlangt ein Registry-Feld `assessed_with` je Vollmacht. Das Feld existiert im Schema nicht. Träte heute ein MAJOR-Wechsel ein, gäbe es kein Feld, in das die Wiedereinsetzung geschrieben werden könnte | Prozesslücke | hoch | SURVIVES | `git show origin/main:registry/lotse-authorizations.yaml \| grep -c assessed_with` → 0 | neu (in #2618 getrackt) |
| 5 | Der Gate-Registry-Eintrag `model-change-detection` trägt kein Feld `last_drill_pass`, während der Hook-Kopf `"last_drill_pass": "2026-08-06"` behauptet. Die Diskrepanz steht weder in #2618 noch in #1640 | Prozesslücke | mittel | SURVIVES | `git show origin/main:docs/governance/gate-registry.json`; Hook-Kopf Z. 6; `gh issue view 2618` ohne Zeile dazu | `deferred-item-no-tracking-issue` ×34 |
| 6 | `pr_merge_sa.py` wertet als Mandat nur `latestReviews`/`reviewDecision` oder einen Freigabe-Vermerk im verlinkten Issue. Ein PR-Kommentar fließt nirgends in `classify()` ein und kann M0 strukturell nie anheben — der als Freigabe-Beleg gesetzte Kommentar war für das Werkzeug wirkungslos | Werkzeug | mittel | SURVIVES | `grep -n "latestReviews\|reviewDecision\|comments" tools/pr_merge_sa.py` — keine Lesestelle für `pr.comments` | neu |
| 7 | Eine Zwischenstandsmeldung nannte die PR-Nummer ohne anklickbaren Link; der Owner musste korrigieren. Kanonische Regel seit 2026-07-08 in `~/.claude/CLAUDE.md` (Action-Board Regel 4), laut `feedback_reporting_table_format.md` bereits vier frühere Rezidive | Kommunikation | mittel | SURVIVES (**Hypothese** — das konkrete Ereignis ist nur durch Session-Gedächtnis gedeckt; belegt ist nur das Muster) | `feedback_reporting_table_format.md` Z. 39-49 belegt die Wiederholungshistorie, nicht diesen Vorfall | als Retro-Slug neu; 5. Vorkommen im Memory-Log |
| 8 | Eine Statuszeile meldete „13/13 grün", real waren es 14 Checks. Der Stop-Hook `evidence_claim_scanner.py` blockte den Turn und erzwang den Beleglauf | fehlende Validierung | niedrig | SURVIVES | Hook-Feedback im Verlauf; `gh pr checks 2617` → 14 pass, 1 skipped | `claim-before-cheapest-check` ×75 — **vom Gate gefangen** |
| 9 | Dem Owner wurde gesagt, er habe den Review-Bot erst nach dem Merge angestoßen. Die Run-Historie zeigt `workflow_dispatch`-Läufe sowohl vor (06:34, 06:37, 06:58) als auch nach dem Merge (07:17, 07:22). Die Kausalkette war anders als berichtet | Kommunikation | mittel | SURVIVES | `gh run list --workflow=bot-review.yml --json event,createdAt` | `claim-before-cheapest-check` (gleiche Klasse, nicht vom Gate gefangen) |
| 10 | Erster Versuch, den Arbeitsbranch per `git switch -c` im geteilten Haupt-Tree anzulegen; ein Guard blockte und protokollierte `unauthorized_head_flip`. Erst danach wurde `repo-session.sh start` genutzt, obwohl die Regel seit 2026-06-20 in einer Drift-Memory steht | Prozesslücke | niedrig | SURVIVES | `.git/iil-guard-events.log` Zeile 2026-09-02T06:55:45Z; `feedback_shared_worktree_multisession_git_collision.md` | neu als Slug |
| 11 | Von sechs Punkten des angenommenen Zielzustands sind drei offen, zwei davon strukturell blockiert (Registry-Feld erst nach Ratifikation, Rubber-Stamp-Quote ohne Messfeld). Die Lücke ist offen deklariert, aber sie ist real | Prozesslücke | niedrig | SURVIVES | `gh issue view 2618` — 3 von 6 Checkboxen offen | neu |
| 12 | `bot-review.yml` stellt sich im eigenen Dateikopf als Ersatz für den Reflex-Klick dar; auf dem einzigen hier geprüften selbstbetreffenden PR hat er nicht gewirkt, die Kontrolle kam von einem menschlichen Zweit-Reviewer. Einzelbeleg, kein Trend | Werkzeug | niedrig | SURVIVES (als **Hypothese** geführt) | `gh api repos/achimdehnert/platform/pulls/2617/reviews` — nur `wirdigital` | neu |
| 13 | Behauptet wurde, der in dieser Sitzung erweiterte Detektor hätte den eigenen Modellwechsel fangen müssen | fehlende Validierung | — | **REFUTED** | Die Grenze („NICHT ein per `--model` gesetztes Session-Override") stand wortgleich schon in `da7dab8d^`. Ein SessionStart-Hook kann ein Mid-Session-Event bauartbedingt nicht sehen. Älterer, akzeptierter Design-Rahmen, nicht dieser Sitzung zuzurechnen | — |
| 14 | Behauptet wurde, der Sensor sei strukturell wirkungslos, und die rückwirkende Klassifikation der Altfälle hätte gemacht werden müssen | fehlende Validierung | — | **REFUTED** | `nominierung_auswertung()` liefert ohne Klassen weiterhin Summen, Quoten und Einzelbelege (35 Retros tragen die Zählfelder). Eine rückwirkende Selbstklassifikation durch denselben beurteilten Agenten wäre ein Interessenkonflikt, den die Charta nirgends als Weg nennt | — |
| 15 | Behauptet wurde, der geblockte Bot-Dispatch sei eine Fehlkalibrierung, die den Lauf wirkungslos machte | Werkzeug | — | **REFUTED** | Der Bot hat auf diesem PR nie reviewt; die Schutzwirkung stand nie auf ihm. Ob der lokale Block eine Fehlkalibrierung war, ist aus GitHub-Artefakten nicht belegbar | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Alle drei Bausteine gebaut, gemergt, verteilt, getestet; die zwei offenen Glieder sind bewusst gestuft und in #2618 getrackt (Befund 11), nicht vergessen |
| architektur_design | 3 | Sensor-Design tragfähig (Klassen statt Summen, `over_act` sperrt), aber die Einstufungslogik — das Herzstück der Modellgenerationsfestigkeit — hat einen stillen Fehlurteil-Pfad (Befund 3) |
| code_konventionstreue | 3 | Acht neue Tests, Lint grün, K1-Pin protokollkonform nachgezogen und reproduziert; dagegen der Bündelungs-Verstoß gegen Art. 1.8 (Befund 2) |
| risiko_debt | 3 | Eine neu aufgedeckte strukturelle Lücke (Befund 1) und eine Werkzeug-Diskrepanz (Befund 5) blieben am Sitzungsende ohne Tracking-Artefakt |
| prozess_effizienz | 4 | Gerader Weg Bau → PR → Merge → Verteilung → Retro; Abzug für den Worktree-Umweg (Befund 10) und den wirkungslosen Bot-Umweg |
| entscheidungsqualitaet | 4 | Zielzustand vorab vorgelegt, kein Self-Merge bei selbstbetreffender Regel, K1-Pin protokollkonform, rückwirkende Klassifikation richtigerweise unterlassen (Befund 14); Abzug für zwei falsche Aussagen an den Owner (Befunde 8, 9) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| `docs/governance/` fiel durch beide Schutzlisten; nur die mitgebündelte `.windsurf/`-Datei erzwang Review | `docs/governance/` in `.github/CODEOWNERS` und in `sa_m.governance_pfade` aufnehmen, dann per Testfall belegen, dass ein Nur-Runbook-PR review-pflichtig wird | #1 |
| §3a wurde mit Sensor, Detektor und Pin in einem PR eingereicht | Selbstbetreffendes zuerst allein einreichen, Produktivänderungen im Folge-PR — so wie es der Changelog vom 2026-08-06 schon einmal vormachte | #2 |
| `fam_major()` schneidet nach der ersten Ziffernfolge ab | Die vollständige Versionskette vergleichen und Datums-Suffixe als eigene Dimension behandeln; den Fall `haiku-4-5-<datum>` → `haiku-4-9-<datum>` als Testfall ergänzen, der heute rot wäre | #3 |
| §3a beschreibt ein Registry-Feld, das nicht existiert | Vor dem Ratifizieren eines Ablaufs prüfen, ob jedes darin genannte Feld ein Artefakt hat; fehlt eines, im selben Zug den Schema-PR vorlegen | #4 |
| Gate-Registry und Hook-Kopf widersprechen sich beim Drill-Datum | Beim Anfassen eines Gate-Moduls Kopf und Registry gegeneinander prüfen und die Abweichung im selben Turn als Issue anlegen | #5 |
| Ein PR-Kommentar wurde als Freigabe-Beleg gesetzt, den das Merge-Werkzeug nicht liest | Den Freigabe-Vermerk dorthin schreiben, wo `pr_merge_sa.py` ihn liest — in das verlinkte Issue — oder das Werkzeug um die Kommentar-Lesestelle erweitern | #6 |
| Zwischenstand nannte die PR-Nummer ohne Link | Vor dem Absenden jede Meldung mit möglicher Owner-Aktion auf einen anklickbaren Link prüfen, auch bei board-freien Einzeilern | #7 |
| „13/13 grün" ohne vorherigen Check-Lauf | Jede Zahl im Antworttext aus einem Kommando dieses Turns beziehen, nicht aus dem Gedächtnis eines früheren Laufs | #8 |
| Chronologie des Bot-Dispatchs behauptet, ohne die Run-Liste zu lesen | Vor jeder Aussage über die Reihenfolge fremder Läufe die Run-Historie mit Zeitstempeln ziehen | #9 |
| `git switch -c` im geteilten Haupt-Tree als erster Reflex | An einem Tag mit Parallelarbeit `repo-session.sh start` als ersten Schritt setzen, bevor irgendein Branch entsteht | #10 |
| Drei von sechs Zielzustands-Punkten blieben offen | Beim Vorlegen eines Zielzustands sofort markieren, welche Punkte in derselben Sitzung erreichbar sind und welche eine Ratifikation abwarten | #11 |
| Der Review-Bot wirkte auf dem selbstbetreffenden PR nicht | Über mehrere PRs messen, auf welchem Anteil der Bot tatsächlich approved, bevor er als Kontrollmechanismus gezählt wird | #12 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 109 Reports: `claim-before-cheapest-check` ×75,
`deferred-item-no-tracking-issue` ×34, `scope-checkpoint-not-durably-recorded` ×24.
Beide in dieser Sitzung wieder aufgetretenen Slugs stehen weit über der Gate-Schwelle.

Die drei neuen Kandidaten sind als Slug nachweislich neu (`grep -l` über `docs/retros/`
liefert 0 Treffer für `selbstbetreffend-mit-produktivaenderung-gebuendelt`,
`governance-pfad-ohne-review-pflicht`, `version-regex-verliert-zweite-stelle`).

Für Befund 7 existiert kein Retro-Slug (0 Treffer für `board-link-fehlt-in-meldung` und
`link-fehlt`) — die Rezidiv-Zählung „fünftes Vorkommen" stammt aus dem Memory-Log
`feedback_reporting_table_format.md`, nicht aus dem Retro-Zähler. Beide Zähler messen
Verschiedenes; hier wird der Retro-Zähler geführt (×1) und die Memory-Historie benannt.

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py` (Haupt-Repo, ohne diesen Report): **fünf** Gates rückfällig.
Eines davon betrifft diese Sitzung unmittelbar:

| Gate | vor Bau | nach Bau | Urteil | gefangen |
|---|---|---|---|---|
| `claim-before-cheapest-check` (blocking seit 2026-08-28) | 69 | 2 | 🚨 RUECKFAELLIG | 1× (dieser Report) |

**Befund über das Gate, nicht über den Slug.** Der Stop-Hook fing in dieser Sitzung die
Zahl-Behauptung „13/13 grün" (Befund 8) und erzwang den Beleglauf — das ist der
Wirksamkeits-Beleg, den `gates_caught` festhält. Dieselbe Klasse schlüpfte im selben Lauf
aber durch: die Behauptung, der Owner habe den Review-Bot erst nach dem Merge angestoßen
(Befund 9), trägt keinen Zahl-Marker, sondern eine **Reihenfolge-Aussage über fremde Läufe**.
Mit diesem Report steigt der Rückfall-Zähler von 2 auf 3.

**Gewählte Antwort: ausweiten.** Das Gate sieht die Familie nicht. Sein Scanner erkennt
Zahl-, Status- und Artefakt-Marker; eine Chronologie-Behauptung („erst nach", „vorher",
„zuerst") über Läufe, die der Agent nicht selbst gestartet hat, fällt durch. Neuer
Gate-Kandidat: `claim-gate-sieht-keine-chronologie-behauptung`. Die beiden anderen zulässigen
Antworten scheiden aus: *umbauen* nicht, weil der Hook am richtigen Punkt feuert (vor dem
Absenden); *herabstufen* nicht, weil das Gate im selben Lauf nachweislich gefangen hat.

**Ehrlichkeits-Sperre.** Das in dieser Sitzung erweiterte Gate `model-change-detection`
(gebaut 2026-08-02, advisory) steht auf **unerprobt**: 0 Vorkommen vor und 0 nach dem Bau.
Es hat nie gefeuert, und der Modellwechsel dieser Sitzung konnte das bauartbedingt nicht
ändern (Befund 13, REFUTED). Der Ausbau ist damit **kein** Wirksamkeitsnachweis. Ein erster
echter Beweislauf steht aus.

Die vier übrigen rückfälligen Gates (u.a. `untested-command-handed-to-user`,
`untested-tool-module-green-gate`, letzter Rückfall jeweils 2026-09-01) stammen nicht aus
dieser Sitzung.

## 5b. Autonomie-Kalibrierung

`over_ask`: **0** belegt. Vier Punkte gingen an den Owner: der Zielzustand vor Arbeitsbeginn
(Policy `zielzustand.md`), der Merge von #2617 (selbstbetreffend, Art. 1.8), das
Registry-Feld `assessed_with` (`registry/` ist CODEOWNERS- und `sa_m`-geschützt) und das
Retro-Schema-Feld. Die ersten drei waren zu Recht vorgelegt. Das Schema-Feld wäre autonom
möglich gewesen, wurde aber nur als offene Checkbox geparkt, nicht aktiv zur Entscheidung
vorgelegt — kein echter Fall.

`over_act`: **0** belegt. Zwei Kandidaten wurden geprüft und beide verworfen: Der Nachzug des
eingefrorenen K1-Instrument-Pins folgt einer in der Baseline-Datei selbst vorregistrierten
Anweisung („bei Tool-Änderung: Baseline mit neuer Version NEU berechnen") und hat drei
identisch autonome Präzedenzfälle. Die Live-Verteilung nach `~/.claude` lag unter dem
Owner-Wort „11 go", nutzte die Lane-Verzeichnisse (nicht das Elternverzeichnis der
Drift-Episode 2026-07-30) und legte Backups an.

**Beide Klassenlisten bleiben leer.** Das ist der erste Lauf mit den neuen Feldern: der
Sensor bekommt aus dieser Sitzung kein Futter, und das ist ein ehrliches Ergebnis, kein
Versäumnis. Eine Nominierung braucht zwei Retros mit derselben Klasse.

## 6. Verankerung

**memory_candidates** (kopierfertig, nicht von mir geschrieben):

```markdown
---
name: feedback_docs_governance_hat_keine_review_pflicht
description: "docs/governance/ faellt durch CODEOWNERS UND sa_m.governance_pfade — ein PR mit nur einer Governance-Datei mergt ohne menschliches Auge, obwohl dort selbstbetreffende Regeln liegen"
metadata: { type: feedback, rule_class: B, drift: true, drift_episode: 2026-09-02-governance-pfad-review-frei }
---

`.github/CODEOWNERS` schuetzt `/governance/` (Repo-Wurzel) und `/.windsurf/`, aber **nicht**
`docs/governance/`. `sa_m.governance_pfade` in `policies/autonomy-gates.md` listet
`.github/`, `docs/adr/`, `policies/`, `registry/`, `packages/`, `CODEOWNERS`,
`tools/pr_merge_sa.py` — ebenfalls ohne `docs/governance/`. Das `main`-Ruleset trägt
`required_approving_review_count: 0` mit `require_code_owner_review: true`: ohne
CODEOWNERS-Treffer verlangt GitHub gar kein Approval.

**Warum das zaehlt:** In `docs/governance/` liegen das Modellwechsel-Runbook und der
Sunset-Ledger — Texte, die die Vollmachten des Agenten betreffen. PR #2617 bekam sein
Review nur, weil zufaellig eine `.windsurf/`-Datei mitgebuendelt war. Waere §3a wie von der
Charta verlangt ungebuendelt eingereicht worden, waere er ohne jedes menschliche Auge
durchgelaufen — die Regel „ungebuendelt" haette den PR unsicherer gemacht als ihr Bruch.

**How to apply:** Vor jeder Aenderung unter `docs/governance/` pruefen, ob der Pfad
inzwischen in beiden Listen steht. Bis dahin gilt: selbstbetreffende Governance-Texte
niemals allein einreichen, ohne einen Reviewer ausdruecklich anzufordern.
Siehe [[feedback_ratified_class_needs_harness_entry]], [[project_sa_m_merge_autonomy]].
```

```markdown
---
name: feedback_version_regex_verliert_die_zweite_stelle
description: "Eine Modell-ID-Regex, die nach der ersten Ziffernfolge abschneidet, stuft haiku-4-5-<datum> -> haiku-4-9-<datum> als MINOR ein — stilles Fehlurteil statt fail-loud"
metadata: { type: feedback, rule_class: B, drift: true, drift_episode: 2026-09-02-fam-major-zweite-stelle }
---

`fam_major()` im Modellwechsel-Detektor captured `^claude-([a-z]+)-([0-9]+).*$` und verwirft
alles nach der ersten Ziffernfolge. Zwei verschiedene Snapshots derselben Hauptversion
(`claude-haiku-4-5-20251001` vs. `claude-haiku-4-9-20260315`) ergeben beidseitig `haiku-4`
und werden als **MINOR** eingestuft — obwohl das Design-Ziel ausdruecklich „im Zweifel
MAJOR" lautet. Provider-Praefixe und Schreibfehler fallen dagegen korrekt auf MAJOR zurueck,
weil der Match leer bleibt.

**Warum das zaehlt:** MINOR bedeutet im Runbook: Vollmachten bleiben aktiv, keine
Re-Qualifikation. Ein Fehlurteil in dieser Richtung ist genau der Fall, den fail-loud
verhindern sollte.

**How to apply:** Bei Versions-Vergleichen die vollstaendige Kette vergleichen, nicht das
erste Segment; Datums-Suffixe als eigene Dimension behandeln. Testfall-Pflicht: mindestens
ein Paar, das sich erst in der ZWEITEN Stelle unterscheidet.
Siehe [[feedback_condition_matches_spelling_not_substance]].
```

```markdown
---
name: feedback_freigabe_vermerk_muss_dort_stehen_wo_das_werkzeug_liest
description: "Ein Owner-Wort als PR-Kommentar hebt das SA-M-Mandat nicht — pr_merge_sa.py liest nur Reviews und den Issue-Body, nie pr.comments"
metadata: { type: feedback, rule_class: B }
---

`pr_merge_sa.py` bestimmt das Mandat aus `latestReviews`/`reviewDecision` (M2) oder aus einem
`Freigabe: akzeptiert durch Owner`-Vermerk im **verlinkten Issue** (M1). Es gibt keine
Lesestelle fuer `pr.comments`. Ein Owner-Wort, das als PR-Kommentar festgehalten wird, ist
fuer das Werkzeug unsichtbar und laesst es bei M0 — der Kommentar dokumentiert, deckt aber
nicht.

**How to apply:** Den Freigabe-Vermerk in das verlinkte Issue schreiben, nicht (nur) an den
PR. Der PR-Kommentar bleibt als menschenlesbare Spur sinnvoll, ersetzt aber kein Mandat.
Siehe [[project_sa_m_merge_autonomy]], [[feedback_gate_approval_needs_pr_comment]].
```

**adr_candidates:** keine. Alle drei Befunde sind Vollzug bestehender Entscheide
(KONZ-032 CODEOWNERS-Scope, KONZ-038 D7 Detektor, SA-M) — nach `adr-threshold.md` genügen
PR und Tracking-Issue.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Governance-Pfad review-pflichtig | platform | #2618 | 🟢 offen | CODEOWNERS + sa_m ergänzen (du/ich) |
| M2 | Regex-Fehlurteil MINOR | platform | #2618 | 🔵 ready | Testfall + Fix (ich) |
| M3 | Drill-Datum-Diskrepanz | platform | #2618 | 🔵 ready | Issue anlegen (ich) |
| M4 | Freigabe-Vermerk ins Issue | platform | #2618 | 🔵 ready | Gewohnheit umstellen (ich) |

## 8. Nicht verifiziert (Restlücken)

- **Ob die Link-Regel nach der Owner-Korrektur erneut verletzt wurde.** Die Finder hatten
  keinen Transkript-Zugriff; PR- und Issue-Text enthalten selbst keine nackten Nummern.
  Billigster Check: die Chat-Turns nach der Korrektur durchsehen.
- **Ob der lokale Classifier-Block des Bot-Dispatchs eine Fehlkalibrierung war.** Aus
  GitHub-Artefakten nicht belegbar (Befund 15, REFUTED aus genau diesem Grund).
  Billigster Check: Classifier-Entscheidungslog, falls eines existiert.
- **Ob `gate_drill_check.py` das fehlende `last_drill_pass`-Feld als Drift wertet oder still
  ignoriert** (Befund 5). Billigster Check: `python3 tools/gate_drill_check.py` und die
  Ausgabe für `model-change-detection` lesen.
- **Ob der Review-Bot systematisch auf selbstbetreffenden PRs ausfällt** (Befund 12, als
  Hypothese geführt). Billigster Check: die letzten zehn PRs mit `docs/governance/`-Dateien
  auf Bot-Reviews prüfen.
- **Ob ein MAJOR-Wechsel den Detektor real auslöst.** Das Gate steht auf `unerprobt`; der
  Wechsel dieser Sitzung war bauartbedingt unsichtbar. Billigster Check: beim nächsten
  echten Sitzungsstart nach einem Modellwechsel die Datei `~/.claude/hooks/state/model-changes.log`
  auf ihre erste Zeile prüfen.

- **Warum ein früherer Lauf von `gate_wirkung.py` in derselben Sitzung `claim-before-cheapest-check`
  als „wirksam" mit 63/0 auswies, während zwei spätere Läufe übereinstimmend 69/2 und
  RUECKFAELLIG zeigen.** Die Differenz ist unerklärt; am Haupt-Repo wurde zwischen den Läufen
  nichts committet. Billigster Check: `git log --since='2026-09-02 00:00' -- docs/retros/`
  gegen die Laufzeitpunkte halten. Bis dahin gilt der zweifach reproduzierte spätere Stand.

**Der Vierer:** *Getan* — Sensor, Einstufung, Runbook gebaut, gemergt, verteilt, acht Tests.
*Angenommen* — dass die Live-Verteilung wirkt (Doctor meldete Drift 0, aber kein Hook ist
seither bei einem Sitzungsstart gelaufen). *Nicht verifizierbar* — die fünf Punkte oben.
*Offen geblieben* — drei Zielzustands-Punkte in #2618 und die zwei ungetrackten Befunde 1 und 5.

## Self-Review (Phase 5, Meta-Agent)

Der Meta-Reviewer prüfte den Entwurf gegen die Skill-Regeln und fand zwei Mängel, beide
eingearbeitet: Befund 7 stand als plattes SURVIVES, obwohl nur Session-Gedächtnis ihn
deckt — jetzt als Hypothese gekennzeichnet. Und §5a etikettierte `claim-before-cheapest-check`
als „wirksam", während der reproduzierte Werkzeug-Lauf RUECKFAELLIG zeigt — die härtere
Verletzung, weil ein rückfälliges Gate als Erfolg dargestellt wurde. §5a ist ersetzt und
führt jetzt die Klasse „Gate rückfällig" mit der Antwort *ausweiten*.

Bestätigt ohne Befund: Frontmatter schema-valide, Arithmetik stimmt (15 = 12 + 3,
`refuted_rate` 0.20 exakt), Invariante `|Soll| == |Survivors|` = 12 erfüllt und lückenlos
referenziert, Längsschnitt-Zahlen decken sich mit dem Werkzeug-Output, Report-Pfad
kollisionsfrei.

**`refuted_rate` numerisch:** 0.20 liegt knapp über der Theater-Schwelle. Die letzten acht
Reports zeigen 0.36 · 0.29 · 0.21 · 0.17 · 0.11 · 0.00 · 0.10 · 0.00 — das Werkzeug warnt
bereits „letzte 3 <0.2". Dieser Report durchbricht die Tief-Serie nicht, sondern setzt sie
auf demselben Niveau fort. Das ist auffällig im Sinne des Band-KPIs und verdient bei der
nächsten Retro Aufmerksamkeit: entweder finden die Finder zu wenig Widerlegbares, oder die
Falsifikation greift zu selten durch. Für diesen Lauf spricht gegen „Theater", dass drei von
fünf vorgelegten Bewertungsbefunden gekippt sind (60 % auf der tatsächlich falsifizierten
Teilmenge) — die niedrige Gesamtquote entsteht durch die neun kommandobelegten Befunde, die
per Skill-Regel gar nicht erst durch die Falsifikation gehen.
