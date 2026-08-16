---
retro_schema: 1
date: 2026-08-16
repo_scope: [platform, apo-hub, trading-hub, travel-beat, cad-hub, tax-hub]
session_id: 9d861a
footprint: deep
footprint_reduction_reason: "keine Reduktion — Rule-B-Trigger (≥3 Repos + Prod-Konfigurationsschritt: GitHub App + Secret in einem oeffentlichen Repo). Downscale auf full scheitert an Bedingung (c): findings_total 19 > 10."
findings_total: 19
findings_survived: 18
refuted_rate: 0.05
phase3_refuted: 0
pre_refuted: 1
scores:
  zielerreichung: 5
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [gate-log-covers-only-some-scanners, deferral-pattern-enumeration-gap, skill-copy-not-redistributed]
recurring_findings: [hand-distributed-copy-not-redistributed, skill-copy-not-redistributed, untested-tool-module-green-gate, ci-gate-maskiert-failure, claim-before-cheapest-check, deferred-item-no-tracking-issue, gate-approval-needs-pr-comment, gate-log-covers-only-some-scanners, deferral-pattern-enumeration-gap, agent-gh-output-mistaken-for-owner]
over_ask: 0
over_act: 1
---

# Session-Retro 2026-08-16 — platform (Session 9d861a)

## 1. Executive Summary

- **Zielzustand [#2004](https://github.com/achimdehnert/platform/issues/2004) erreicht und geschlossen**, alle vier Kriterien einzeln belegt; zusätzlich die GitHub App live (`nicht prüfbar 12 → 0`, `DISKREPANZ 8 → 18`). 8 eigene PRs, alle gemergt, 0 offen.
- **Die wertvollste Einzelleistung war eine Selbstkorrektur:** die Prämisse des eigenen Auftrags war zur Hälfte falsch — ein Routing-Mechanismus fehlte nie, vier von fünf Repos hatten den Befund längst. Der Glaube an die eigene Prämisse hätte fünf Duplikate erzeugt.
- **Der schärfste Befund entstand erst durch die Falsifikation und widerlegt meinen eigenen ersten Hauptbefund** (#1/#19): ich schloss aus „16 von 16 Protokolleinträgen stammen von einem Melder", die anderen Scanner schwiegen. **Zwei von fünf aktiven Scannern schreiben gar nicht ins Protokoll** — die Null war teilweise mein Filter.
- **Dreimal an einem Tag war „gemergt" nicht „wirksam"** — inklusive des Abschluss-Skills selbst, der eine Fassung ohne seine eigene, an diesem Tag gemergte Pflicht-Phase ausführte.
- **Ein Blindfleck der Retro-Methode wurde sichtbar:** ein Skeptiker zitierte meinen eigenen `gh`-Kommentar als „Owner-Aussage" — meine Schreibzugriffe laufen unter demselben Konto. Diskriminator gefunden (#18).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | **Das Gate-Protokoll deckt nur 3 von 5 aktiven Scannern ab.** `evidence_claim_scanner` und `untested_command_scanner` schreiben nicht hinein — ausgerechnet die beiden, die heute nachweislich feuerten. Jede FP-/Recall-Auswertung auf dieser Basis ist strukturell unvollständig | fehlende Validierung | **hoch** | SURVIVES | `grep -c gate_hits` je Hook: 4/3/3/**0**/**0**; 16 Protokollzeilen, alle `artefakt-budget-schwelle-erreicht` | `gate-log-covers-only-some-scanners` (neu) |
| 2 | **Der `deferred_item_scanner` schwieg bei einer echten Verletzung** — Ursache ist eine Lücke in einer *aufgezählten* Verb-Liste, nicht defekte Mechanik | fehlende Validierung | **hoch** | SURVIVES | Replay: mein Wortlaut „bewusst nicht mitgemacht" → kein Treffer; Positivkontrollen „bewusst aufgeschoben" / „nicht Teil dieses PRs" → Treffer. Codekommentar zeigt: dieselbe FN-Klasse wurde schon einmal nachgezogen (Retro 287b23) | `deferral-pattern-enumeration-gap` (neu) |
| 3 | Die bewusst aufgeschobene Konsolidierung der zwei Befund-Gedächtnisse hat **kein** Tracking-Artefakt — sie steht nur im PR-Text von #2007 | Prozesslücke | mittel | SURVIVES | kein offenes Issue; `grep "Restüberschneidung"` im #2007-Body = 1; #2006 CLOSED COMPLETED | `deferred-item-no-tracking-issue` ×13 |
| 4 | Drei hand-/lane-verteilte Artefakte waren nach dem Merge **nicht wirksam** | Prozesslücke | **hoch** | SURVIVES | 0.7.5 `RESULT: DRIFT` ×2; `doctor` `copy-stale=2` → nach `generate` `DRIFT-SCORE 0` | `hand-distributed-copy-not-redistributed` ×1→×2 |
| 5 | Der ausgeführte `/session-ende` kannte seine eigene, an diesem Tag gemergte Pflicht-Phase 0f nicht | Prozesslücke | mittel | SURVIVES | `grep -c "0f: Cross-Repo-Befunde"` = 0 vor, 1 nach der Verteilung | `skill-copy-not-redistributed` ×1→×2 |
| 6 | #2005 ging rot in CI: registriertes Modul nicht executable — die volle Suite lief **vor** dem Registry-Eintrag, beide gekippten Tests sind registry-parametrisiert | fehlende Validierung | mittel | SURVIVES | Commit `ad145ab7`; ein Wurzelgrund, zwei rote Tests | `untested-tool-module-green-gate` ×3 |
| 7 | `continue-on-error: true` ohne Begründung darüber verletzte das eigene blockierende Gate | Konventionsverstoß | mittel | SURVIVES | `test_silent_failures`, 4 Fundstellen (Z. 70/79/88/97) | `ci-gate-maskiert-failure` ×8 |
| 8 | gitleaks: Private-Key-Muster in einem Drill; die Nachbesserung im **Folgecommit** genügte nicht — der Scanner prüft den Commit-Bereich | Werkzeugverständnis | mittel | SURVIVES | Fingerprint an Commit `3bfebb5b`; #2010 gemergt mit 2 statt 4 Commits | — |
| 9 | Phase 0f meldete beim allerersten Lauf `OK` — **vakuum wahr**, das Journal existiert nicht | fehlende Validierung | mittel | SURVIVES | `~/.claude/befund-journal.json` fehlt, Exit 0 trotzdem | — |
| 10 | Memory-Write mit Backticks im Bash-Argument verstümmelt — bestehende Regel verletzt | Konventionsverstoß | niedrig | SURVIVES | Shell-Fehlerausgabe „command substitution: Zeile 32"; Neuschrieb per `--content-file` | — |
| 11 | Absence-Claim über die GitHub-REST-API ohne Check; die daraufhin gefahrene Probe war **wertlos**, weil die Positivkontrolle am fehlenden `admin:org`-Scope scheiterte | fehlende Validierung | mittel | SURVIVES | Evidence-Gate blockierte den Turn; erst die REST-Doku belegte die Aussage | `claim-before-cheapest-check` ×42 |
| 12 | `--help` des Setup-Skripts druckte Quelltext (`sed -n '1,30p'` bei längerem Kopf); kein Test sah hin | Werkzeugverständnis | niedrig | SURVIVES | live reproduziert, Fix + Regressions-Drill in #2010 | — |
| 13 | Erster Entwurf des Registry-Schiedsrichters hätte dem Handover die **eigene Parser-Annahme** als Fehler vorgehalten | verfrühte Festlegung | mittel | **SURVIVES** (Skeptiker) | `owner_explizit` in `handover_refs.py:64`; `schiedsrichter()` verzweigt darauf; `AGENT_HANDOVER.md:45` trägt die korrekte meiki-lra-URL; vor dem Merge gefangen | — |
| 14 | #2011 wurde **ohne Auftrag** begonnen (Scanner-Befund als Auslöser) | Kommunikation | mittel | **SURVIVES** (Skeptiker) | #2004 behandelt ausschließlich K1–K4; #2011 referenziert #1640, nicht #2004. Kein Prod/Publish/irreversibel → `over_act`, kein Gate-Bruch | `over_act: 1` |
| 15 | Der Token-Beweislauf war kaputt (Kommandozeilen-Zuweisung wirkte auf die eigene Substitution) — die naheliegende Deutung wäre „Token-Pfad greift nicht" gewesen | Werkzeugverständnis | mittel | **SURVIVES** (Skeptiker) | Skeptiker stellte den Mechanismus unabhängig nach: `FOO=a BAR="$(echo $FOO)"` propagiert den Wert; `token_fuer()` + Tests existieren | — |
| 16 | Eingriff in die Entprellungs-Zustandsdatei mit **behaupteter, ungeprüfter** Wirkung | fehlende Validierung | mittel | **SURVIVES** (Skeptiker) | Pre-Fix-Code (`5dc24607~1`) filterte `placeholders` nicht und speicherte sie nicht — `schon` wurde für diese Befundart nie gelesen | — |
| 17 | **Die Freigabe zu #2011 hat kein durables Artefakt** — auf dem PR stehen nur Bot-Kommentare, die Owner-Anweisung lebte nur im Chat | Prozesslücke | mittel | **SURVIVES** (Skeptiker-Neufund) | `gh pr view 2011 --json comments` → nur `github-actions`. Präzisierung: der Slug ist eine **Memory-Regel**, kein registriertes Gate (Registry-Abfrage nach `approval`/`veto` = leer) | `gate-approval-needs-pr-comment` |
| 18 | **Ein Skeptiker hielt meinen eigenen `gh`-Kommentar für eine Owner-Aussage** und stützte darauf seinen „stärksten Beleg" — zirkulär, und für einen Subagenten nicht erkennbar | Werkzeugverständnis | mittel | SURVIVES | Skeptiker-Ausgabe zitiert #1640-Kommentar als „der Owner-Account selbst"; der Kommentar stammt von mir. Diskriminator gefunden: `merged_by` trennt `wirdigital` (Mensch) von `achimdehnert` (Agent-Token) | `agent-gh-output-mistaken-for-owner` (neu) |
| 19 | *(pre-refuted)* Erste, scharfe Fassung von #1: „die anderen advisory-Scanner feuerten in vier Sitzungen nie" | fehlende Validierung | — | **REFUTED (vor Phase 3, durch eigenen Check)** | Zwei der fünf Scanner schreiben gar nicht ins Protokoll; die Aussage über ihr Feuern war aus dem Protokoll nicht ableitbar | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **5** | #2004 mit allen vier Kriterien einzeln belegt geschlossen; App zusätzlich live und in Prod gemessen |
| architektur_design | **4** | Gate nach *Messung* eng gehalten (`CROSS_REPO_PHASEN` = 1 Phase, nachdem der erste Lauf 3 Repos gefordert hätte, davon 1 zu Unrecht); Abdeckungslücke sauber von Befund getrennt. Abzug: zwei parallele Befund-Gedächtnisse (#3) |
| code_konventionstreue | **3** | vier Konventions-/Gate-Verstöße (#6, #7, #8, #10), alle gefangen, alle vermeidbar |
| risiko_debt | **3** | ein aufgeschobener Punkt ohne Tracking (#3) und eine Freigabe ohne Artefakt (#17); alles Übrige verankert |
| prozess_effizienz | **3** | Rework: drei Nachbesserungen an #2010 inkl. Historie-Squash, exec-bit-Nachlauf an #2005, ein wertloser API-Probelauf |
| entscheidungsqualitaet | **4** | Prämissen-Korrektur bei K4 verhinderte fünf Duplikate; App statt PAT mit Arithmetik begründet; kein gitleaks-Allowlist-Eintrag als bequemer Ausweg. Abzug: #13 und #19 waren beides verfrühte Festlegungen |

## 4. Soll-Ablauf (Ist → Soll → eliminiert)

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Aus 16/16 Protokolleinträgen auf das Schweigen der übrigen Scanner geschlossen | Vor jeder Aussage über ein Protokoll prüfen, **wer überhaupt hineinschreibt** (`grep -c gate_hits` über alle Hooks) — die Abdeckung ist die Voraussetzung der Auswertung | #1 |
| Scanner schwieg wegen eines fehlenden Verbs in einer Enumeration | Muster-basierte Scanner mit dem **realen Turn-Text replayen**, statt aus Schweigen auf Regeltreue zu schließen; jeder Fund erweitert die Enumeration | #2 |
| „bewusst nicht mitgemacht" nur im PR-Text von #2007 | Beim Schreiben eines Aufschubs in einen PR-Text **im selben Zug** ein Issue anlegen — der PR-Text ist per Hausregel kein Tracking | #3 |
| Nach drei Merges an verteilten Artefakten lief der Drift-Melder erst beim nächsten Sitzungsstart | `hook-dist-drift.sh` bzw. `cc-skill-dist/doctor.py` **unmittelbar nach jedem Merge** an einem verteilten Artefakt laufen lassen | #4 |
| Der Abschluss-Skill führte eine Fassung ohne seine eigene neue Phase aus | Identisch mit dem Schritt zu #4, angewandt auf die `commands`-Lane: nach einer Skill-Änderung `doctor` **vor** dem nächsten Skill-Aufruf | #5 |
| Volle Suite lief vor dem Registry-Eintrag; CI fand, was lokal grün war | Bei Änderung an einer **parametrisierenden** Datei (Registry, Katalog, Fixture-Quelle) die Suite **danach** erneut laufen lassen | #6 |
| `continue-on-error` als Block-Kommentar über der Gruppe begründet | Gate-relevante Direktiven **je Zeile** begründen — der Prüfer liest zeilenweise | #7 |
| Secret-Muster im Folgecommit korrigiert, gitleaks blieb rot | Bei einem Secret-Scanner-Treffer sofort die **Historie** bereinigen (Squash/Amend), nicht den Endstand | #8 |
| Phase 0f meldete beim ersten Lauf OK, ohne Datenbasis | Ein neues Gate meldet beim ersten Lauf **`UNGEPRUEFT`**, solange seine Datenquelle nicht existiert — nicht `OK` | #9 |
| Backticks in einem Bash-Argument verstümmelten den Memory-Inhalt | Mehrzeilige/markdown-haltige Inhalte **ausschließlich** über `--content-file` übergeben, nie über `--content` | #10 |
| Absence-Claim aufgestellt, dann mit einer Probe „belegt", deren Positivkontrolle durchfiel | Zu jeder Abwesenheits-Behauptung **zuerst** die Positivkontrolle fahren; fällt sie durch, bleibt die Aussage Hypothese | #11 |
| `--help` schnitt per Zeilennummer aus dem Kopfkommentar | Hilfetexte als eigener Block im Werkzeug, mit einem Test, der Quelltext-Marker ausschließt | #12 |
| Der Schiedsrichter-Entwurf klassifizierte, bevor die Herkunft des Werts geklärt war | Vor jeder Klassifikation fragen: **stammt der Wert aus der Quelle oder aus meinem Default?** — bei Default keine Anklage, sondern Korrektur | #13 |
| Ein Scanner-Befund löste direkt einen PR aus, ohne Auftrag | Ein Befund, der **nicht** aus dem akzeptierten Zielzustand folgt, wird erst gespiegelt und dann gebaut — nicht umgekehrt | #14 |
| Kommandozeilen-Zuweisung und abhängige Substitution in einer Zeile | Werte, von denen eine Substitution abhängt, **vorher** in eine Variable schreiben — nie im selben Kommando-Präfix | #15 |
| Wirkung eines Eingriffs behauptet, ohne ihn auszuführen | Nach jedem Eingriff in einen Melder-Zustand den Melder **einmal laufen lassen**, bevor die Wirkung behauptet wird — identisch mit dem Schritt zu #11, hier auf den eigenen Eingriff angewandt | #16 |
| Owner-Freigabe blieb im Chat, der PR trägt nur Bot-Kommentare | Jede Freigabe, die einen Merge trägt, im selben Zug als **PR-Kommentar** ablegen | #17 |
| Skeptiker hielt einen Agent-`gh`-Kommentar für eine Owner-Aussage | In jeden Skeptiker-Prompt den **Diskriminator** aufnehmen: `merged_by`/`author` = `wirdigital` ist der Mensch, `achimdehnert` ist der Agent-Token — sonst ist jede eigene Ausgabe scheinbar fremder Beleg | #18 |

**Invariante:** 18 überlebende Befunde ↔ 18 Soll-Schritte. Zwei Schritte (#5, #16) sind ausdrücklich als Anwendung eines anderen Schritts auf einen zweiten Kontext formuliert; die Zählung bleibt 1:1. Für #19 (pre-refuted) gibt es korrekterweise keinen Schritt.

## 5. Längsschnitt (`tools/retro_kpis.py`, Pflichtlauf)

- **`hand-distributed-copy-not-redistributed`** ×1 (d57884) → mit dieser Sitzung **×2 ⇒ gate-pflichtig**. Gate existiert (Melder 0.7.5, registriert via #1996) und hat **dreimal korrekt gefeuert**. Die Lücke ist nicht der Melder, sondern sein **Auslösezeitpunkt**.
- **`skill-copy-not-redistributed`** ×1 (c45b39) → **×2 ⇒ gate-pflichtig**, und hierfür existiert **kein** erzwingender Mechanismus: `doctor` diagnostiziert, aber nichts ruft ihn nach einer Skill-Änderung auf. **Gate-Kandidat.**
- **`claim-before-cheapest-check` ×42**, **`deferred-item-no-tracking-issue` ×13**, **`ci-gate-maskiert-failure` ×8**, **`untested-tool-module-green-gate` ×3** — alle bereits gegated, und **drei davon haben in dieser Sitzung gegriffen** (#6, #7, #11). Das ist der Gegenbeweis zu #1: die *blockierenden* Mechanismen wirken; die *protokollierenden* sind teils gar nicht angeschlossen.
- **Drei neue Slugs** (`gate-log-covers-only-some-scanners`, `deferral-pattern-enumeration-gap`, `agent-gh-output-mistaken-for-owner`) — erster Datenpunkt, kein Gate, keine Recurrence-Behauptung.
- **Score-Kontext:** `risiko_debt` ist über 77 Messungen mit **2,55** die schwächste Dimension. Diese Sitzung liegt mit 3 leicht darüber, der Abzug hat aber exakt die typische Form (aufgeschobener Punkt ohne Anker).

## 5b. Autonomie-Kalibrierung

- **`over_ask: 0`**, **`over_act: 1`** (#14, skeptiker-bestätigt).
- **Erstmals artefaktgestützt statt erzählungsgestützt:** `merged_by` trennt die Merges sauber — `wirdigital` (Mensch) hat #2003/#2005/#2007/#2008/#2009 gemergt, der Agent-Token `achimdehnert` #2010/#2011/#2012/#2013. Von meinen vier Merges waren zwei Handover-PRs (Phase 0a-merge erlaubt sie ausdrücklich) und zwei Code-PRs nach wörtlicher Owner-Anweisung.
- **Konsequenz für [#1640](https://github.com/achimdehnert/platform/issues/1640):** das Kriterium `prs_seit_owner` traf den Fall (#14), den die absolute Schwelle verfehlt — mit einer belegten Unschärfe (zählt blockierte Versuche mit).

## 6. Verankerung (kopierfertig — der Mensch entscheidet)

**memory_candidates**

```markdown
---
name: feedback_check_who_writes_before_reading_a_log
description: Vor jeder Aussage über ein Protokoll prüfen, welche Erzeuger überhaupt hineinschreiben — sonst ist die Null der Filter.
metadata:
  type: feedback
drift: true
drift_episode: 2026-08-16-gate-log-partial-coverage
---

Aus „16 von 16 Einträgen stammen von einem Melder" wurde geschlossen, die übrigen
advisory-Scanner feuerten nie. Tatsächlich schreiben **zwei von fünf** aktiven
Scannern gar nicht in `gate-hits.jsonl` — ausgerechnet die beiden, die an dem Tag
nachweislich gefeuert hatten.

**Why:** Eine Auswertung ist nur so vollständig wie die Erzeuger-Abdeckung ihres
Protokolls. Ohne diesen Check misst man die Schreiber, nicht die Welt.

**How to apply:** `grep -c gate_hits ~/.claude/hooks/*.py` (oder das Äquivalent)
BEVOR aus einem Protokoll auf Verhalten geschlossen wird. Siehe
[[feedback_absence_claim_needs_full_family_grep]].
```

```markdown
---
name: feedback_agent_gh_output_is_not_owner_evidence
description: Meine gh-Schreibzugriffe laufen unter dem Owner-Konto — Subagenten halten sie für fremde Belege.
metadata:
  type: feedback
drift: true
drift_episode: 2026-08-16-circular-evidence
---

Ein Retro-Skeptiker nannte als „stärksten Beleg" einen Issue-Kommentar, der
angeblich vom Owner stammte. Er stammte von mir — `gh` schreibt unter
`achimdehnert`. Der Skeptiker stützte meine Behauptung auf meinen eigenen Text.

**Why:** Artefakt-Erdung ist blind gegenüber der Frage, WER das Artefakt erzeugt
hat, wenn Agent und Mensch dasselbe Konto teilen.

**How to apply:** Diskriminator in jeden Skeptiker-Prompt: `merged_by`/`author`
= `wirdigital` ist der Mensch, `achimdehnert` ist der Agent-Token. Gilt auch für
Kommentare, Issues und PR-Bodies. Siehe [[feedback_repo_identity_not_from_remote_name]].
```

**adr_candidates** — keine. Kein Befund verlangt eine Architektur-Entscheidung.

## 7. Maßnahmen (Action Board)

### 🟢 Offen — dein Zug

1. 🟢 Entscheiden: sollen `evidence_claim_scanner` und `untested_command_scanner` ins Gate-Protokoll schreiben — https://github.com/achimdehnert/platform/issues/1640
2. 🟢 Freigabe-Praxis: Chat-Freigaben, die einen Merge tragen, als PR-Kommentar ablegen — https://github.com/achimdehnert/platform/pull/2011

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 3 | Tracking für Konsolidierung | platform | [#2007](https://github.com/achimdehnert/platform/pull/2007) | 🔵 ready | Issue anlegen (ich) |
| 4 | Verb-Lücke im Deferral-Muster | platform | — | 🔵 ready | Muster ergänzen (ich) |
| 5 | Gate: Skill-Verteilung nach Edit | platform | — | 🔵 ready | Konzept vorlegen (ich) |
| 6 | 0f meldet UNGEPRUEFT statt OK | platform | — | 🔵 ready | Kleiner Fix (ich) |

### ✅ Erledigt

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 7 | Zielzustand | platform | [#2004](https://github.com/achimdehnert/platform/issues/2004) | ✅ done | — |
| 8 | Leseflläche verdrahtet | platform | [#2007](https://github.com/achimdehnert/platform/pull/2007) | ✅ done | — |
| 9 | GitHub App live | platform | [#2013](https://github.com/achimdehnert/platform/pull/2013) | ✅ done | — |
| 10 | Zähler-Unschärfe verankert | platform | [#1640](https://github.com/achimdehnert/platform/issues/1640) | ✅ done | — |

## 8. Nicht verifiziert (Restlücken)

| Lücke | Billigster Check |
|---|---|
| **Regel 1 war für die Find-Phase gebrochen** — sie lief inline, weil Subagenten zu dem Zeitpunkt untersagt waren. Die Falsifikation (Phase 3) wurde nach der Freigabe vollständig nachgeholt: 2 Skeptiker + 1 Meta-Reviewer, ~215k Token. Die **Finder**-Phase bleibt inline-erzeugt. | Eine zweite Find-Runde mit frischen Subagenten über dieselben Artefakte; Delta zeigt, was der Eigen-Kontext übersah. |
| Skeptiker 1 stützte einen seiner drei Belege auf **meine eigene Commit-Message** (`d4bfbebb`) — kein voll unabhängiger Beleg, auch wenn er zwei der drei Fälle unabhängig nachstellte | Denselben Befund gegen den Code **vor** dem Commit prüfen, nicht gegen dessen Beschreibung. |
| `refuted_rate: 0.05` — der Einzelwert liegt unter 0,2, die **Bandregel** (letzte 3 Werte) schlägt damit aber **nicht** an (`0.33 · 0.43 · 0.25` bleiben im Band). Ursache ist nicht laxe Falsifikation: alle vier Bewertungsbefunde überlebten eine echte Prüfung | Beim nächsten Retro beobachten, ob 0-Refutations zur Serie werden. |
| Ob der `deferred_item_scanner` nach Ergänzung des fehlenden Verbs alle Formulierungsvarianten trifft | Die letzten N Retro-Reports nach Aufschub-Formulierungen greppen und gegen das Muster replayen. |
| Ob die 18 Diskrepanzen des ersten Flottensicht-Nightly real sind oder Rückstand aus geschlossenen Vorgängen | Morgen früh den Report lesen — Phase 0.7.6 legt ihn beim Sitzungsstart vor. |

**Vierer-Abschluss:**

- **getan:** Zielzustand #2004 erreicht und geschlossen · 8 PRs gemergt · GitHub App live und in Prod belegt · 5 Alt-Issues ins Zielrepo überführt · drei Verteil-Drifts nachgezogen · zwei Melder-Defekte gefixt · Recall-Messung und Zähler-Unschärfe in #1640 verankert · Falsifikation mit 3 Subagenten nachgeholt.
- **angenommen:** dass die vier App-Installationen vollständig sind (per App-JWT verifiziert, also belastbar) · dass die 18 Diskrepanzen Rückstand und kein Defekt sind (Plausibilität).
- **nicht verifizierbar:** ob eine frische Finder-Runde zusätzliche Befunde gefunden hätte · ob das Deferral-Muster nach der Ergänzung vollständig ist.
- **offen geblieben:** Protokoll-Abdeckung der zwei nicht schreibenden Scanner (#1) · Verb-Lücke (#2) · Konsolidierung ohne Tracking (#3) · Gate für Skill-Verteilung (#5) · Wochenlauf-Beweis morgen früh.
