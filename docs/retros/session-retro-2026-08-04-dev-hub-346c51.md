---
retro_schema: 1
date: 2026-08-04
repo_scope: [dev-hub, platform]
session_id: 346c51
footprint: deep
findings_total: 8
findings_survived: 7
refuted_rate: 0.125
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [claim-before-cheapest-check, merged-doc-references-unmerged-doc, live-url-labelled-before-merge]
recurring_findings: [claim-before-cheapest-check, deferred-item-no-tracking-issue]
---

# Session-Retro 2026-08-04 — dev-hub Mail-Strang (346c51)

**Footprint `deep`.** Zwei harte Trigger: Prod-Schritte (12 Deploys, ~2.400 Schreibvorgänge
auf die Prod-Datenbank) und **zwei Migrationen** (`0015` schreibt `mail_agent_textunit` um,
`0016` tauscht einen GIN-Index). Die Abwärts-Regel greift nicht — sie verlangt ausdrücklich
„keine DB-Migration".

**Session-Grenze:** PR #234–#247 in `achimdehnert/dev-hub`. Die PRs #227–#233 tragen dasselbe
Datumspräfix, gehören aber anderen Sitzungen desselben Tages (Löschung, Speichergrenze,
Schlüsselwechsel) und sind **nicht** in-scope.

**Umfang:** 14 PRs (12 gemergt, 2 offen), 19 Commits, 18 Dateien, +3.127/−72 Zeilen.

---

## 1 Executive Summary

* Aus „Mail-Skripte auf DB umstellen" wurde etwas anderes — und das war richtig: der Owner
  steuerte über den Tag von der Suche zum **Vorgangsbuch**. Zwei Konzepte entstanden, eines
  davon liegt noch als offener PR.
* Der wertvollste Fund war kein Code, sondern ein Muster: **vier Mechanismen waren gebaut und
  liefen nie** (`reconcile`, `ingest_delta`, `zustand_offener_punkt`, `REPLIED`). Alle sahen von
  außen wie „funktioniert" aus, weil nichts rot wurde.
* Die Suche ist von 27,5 s auf **7,9–11,1 s** gekommen — über **zwei Fehlversuche**, die sie
  zwischenzeitlich auf 50,8 s verschlechterten.
* `claim-before-cheapest-check` ist über 68 Retros **gate-pflichtig** und trat hier erneut
  dreimal auf, zuletzt in der Abschlussmeldung an den Owner.
* Zwei Reste auf Prod: der IMAP-Pfad hat weder Stundenlauf noch Löscherkennung, während der
  Graph-Pfad beides hat.

---

## 2 Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | KONZ-004 ist gemergt und verweist in §9 auf KONZ-003, das **nicht** in `main` liegt (PR #238 offen) | Prozesslücke | hoch | SURVIVES (kommandobelegt) | `git show origin/main:docs/konzepte/KONZ-dev-hub-003-*` → nicht vorhanden; `gh pr view 238` → OPEN | neu |
| 2 | Suchzeit „21 s" im gemergten Konzept und in der Abschlussmeldung — **vor** PR #240 gemessen, nie nachgemessen | fehlende Validierung | hoch | SURVIVES (kommandobelegt) | KONZ-004 §9 vs. Messung 2026-08-05: 11,06 / 7,91 s | `claim-before-cheapest-check` |
| 3 | dev-hub#211 in drei PR-Texten referenziert, nie kommentiert oder fortgeschrieben | Prozesslücke | mittel | SURVIVES (kommandobelegt) | Issue #211 OPEN, ohne Kommentar; PRs #244/#245/#246 | `deferred-item-no-tracking-issue` |
| 4 | Transport-Asymmetrie auf Prod: Graph hat Delta + Abgangserkennung, IMAP (hnu, mittwald) hat beides nicht | Risiko/Debt | hoch | SURVIVES (kommandobelegt) | PR #236 OPEN seit 11:42 | neu |
| 5 | Die zwei Fehlversuche an der Suche waren vermeidbar — beide Ursachen ohne Deploy prüfbar | fehlende Validierung | hoch | **SURVIVES** (Skeptiker) | `SHOW pg_trgm.word_similarity_threshold` = lesender Einzeiler; Doppelberechnung im `order_by` im ORM-SQL sichtbar. PR #237 „Ursache 1"/„Ursache 2" | `claim-before-cheapest-check` |
| 6 | ~~Drei Testfehler derselben Klasse~~ | — | — | **REFUTED** | `git grep "in inhalt" apps/mail_agent/tests/` → 20 Treffer, meist ungescopt und unauffällig · `config/settings/base.py:316,324` (`TIME_ZONE`/`USE_TZ`) → (b) ist Config-Unkenntnis, kein Scoping · `git grep localtime -- apps/*/tests/` → 0 Treffer ausserhalb der neuen Datei | — |
| 6′ | Zwei ungescopte Zusicherungen über die **gesamte** Antwort kollidierten mit legitimem Seitentext | Wissenslücke | niedrig | SURVIVES (Skeptiker-Fund) | `git grep "in inhalt" apps/mail_agent/tests/` → 20 Treffer, meist ungescopt; Kollision bei Überschrift + Zusammenfassung | neu |
| 7 | „✅ Schon live" mit URL neben Funktionen, die nur im ungemergten PR #245 existierten | Kommunikation | hoch | **SURVIVES** (Skeptiker) | #244 gemergt 16:39:13Z ohne Sortier-/Link-Marker; #245 erstellt 16:57:10Z, gemergt 17:02:57Z; beide Hostnamen = ein vhost seit PR #226 | neu |

**Nicht als Befund gewertet:** der abgebrochene Deploy `eed17e4` (Concurrency-Gruppe). Harmlos —
`git merge-base --is-ancestor eed17e4 c2acc48` bestätigt, dass der Code mit dem nächsten Lauf
auf Prod kam. Zum Zeitpunkt des Merges wurde das allerdings nicht geprüft.

---

## 3 Scorecard

| Dimension | Score | Anker |
|---|---|---|
| `zielerreichung` | **4** | Erhebliche Lieferung (Graph-Delta live und belegt, Antwort-Erkennung mit 2.356 Buchungen, zwei Konzepte, drei Ansichten). Abzug für #1 und #4 — zwei Stränge enden offen. |
| `architektur_design` | **3** | Gute Entscheidungen (partieller Index statt Rückbau, zwei Verkettungswege je Transport, Engstellen-Invariante im Konzept). Aber die Zwei-Stufen-Abfrage war konstruktiv falsch und musste zurückgebaut werden (#5). |
| `code_konventionstreue` | **4** | Tests zu jeder Änderung, Ruff sauber, Worktrees durchgehend, Commit-Botschaften per Datei. Abzug für einen `-m`-Versuch mit Anführungszeichen und #6′. |
| `risiko_debt` | **2** | #1 (toter Verweis im gemergten Dokument), #3 (Issue nur im PR-Text), #4 (Transport-Asymmetrie auf Prod), dazu zwei offene PRs. Die schwächste Dimension — wie im Längsschnitt-Mittel (2,57). |
| `prozess_effizienz` | **3** | #5 (zwei Optimierungsrunden ohne Vorab-Messung, davon eine mit Regression auf Prod), #7 (Fehlmeldung kostete den Owner einen vergeblichen Aufruf). 12 Deploys für 12 Merges. |
| `entscheidungsqualitaet` | **4** | Weiterleitungs-Idee begründet abgelehnt, kaputte Relevanzordnung ersatzlos gestrichen statt als Option erhalten, Recall-Frage durch Messung statt Entscheidung gelöst. Abzug für den tautologischen Befund #6. |

---

## 4 Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Schritt) | eliminiert |
|---|---|---|
| KONZ-004 wurde gemergt, während KONZ-003 als PR offen blieb — §9 verweist ins Leere | Vor dem Merge eines Dokuments, das ein anderes referenziert: `git show origin/main:<referenziertes-dokument>` — existiert es nicht, entweder zuerst das andere mergen oder den Verweis als „offener PR #N" schreiben | #1 |
| „21 s" wurde nach PR #239 gemessen, nach #240 nie wieder — und trotzdem als Ergebnis genannt | Jede Zahl, die in ein durables Artefakt oder eine Abschlussmeldung geht, wird **im selben Turn** neu gemessen. Eine Zahl aus einem früheren Turn ist eine Behauptung, kein Beleg | #2 |
| dev-hub#211 dreimal im PR-Text erwähnt, nie am Issue | Wird ein Issue in einem PR erwähnt, bekommt es im selben Zug einen Kommentar mit dem PR-Link und dem verbleibenden Rest — der PR-Text erreicht die Lesefläche des Issues nicht | #3 |
| PR #236 blieb offen, während der Graph-Zwilling gemergt und deployt wurde | Bei Transport-/Pfad-Paaren: entweder beide Seiten im selben Zug fertigstellen, oder die Asymmetrie als Issue anlegen, bevor die erste Seite auf Prod geht | #4 |
| #235 wurde gemergt mit „nicht belegt, um wieviel es schneller wird" — und war langsamer | Vor jedem Performance-PR die **billigsten** lesenden Checks fahren: Servereinstellungen (`SHOW …`) und das erzeugte SQL (`str(qs.query)`). Erst wenn die daraus folgende Erwartung steht, deployen | #5 |
| Zusicherungen prüften Substrings über die gesamte Antwort und kollidierten mit Seitentext | Textzusicherungen auf den Bereich einschränken, um den es geht (`inhalt[inhalt.index('<marker>'):]`), statt über die ganze Antwort zu suchen | #6′ |
| Ein Board nannte „✅ Schon live" mit URL neben Funktionen aus einem offenen PR | In einem Turn, in dem ein PR noch offen ist, steht die zugehörige Zeile auf 🟡 „gebaut, nicht deployt". Eine Live-URL wird erst genannt, nachdem der Deploy des betreffenden SHA verifiziert ist | #7 |

Invariante erfüllt: **7 Soll-Schritte für 7 überlebende Befunde.**

---

## 5 Längsschnitt

`python3 tools/retro_kpis.py` über 68 Berichte. **18 Slugs stehen auf Gate-Pflicht (≥2).**

Zwei davon wurden in dieser Sitzung erneut getroffen:

| Slug | Zähler | Hier |
|---|---|---|
| `claim-before-cheapest-check` | ≥2, gate-pflichtig | Befund #2 und #5 |
| `deferred-item-no-tracking-issue` | ≥2, gate-pflichtig | Befund #3 |

**Der unbequeme Teil:** `claim-before-cheapest-check` ist bereits durch einen Hook verankert
(`evidence_claim_scanner.py`), der in dieser Sitzung **zweimal gefeuert** und beide Male eine
echte Lücke gefangen hat. Er hat Befund #2 trotzdem nicht verhindert — weil er prüft, ob der
**aktuelle Turn** einen Beleg trägt, nicht, ob ein aus einem früheren Turn übernommener Beleg
noch gilt. Das ist eine benennbare Lücke im bestehenden Gate, kein fehlendes Gate.

`risiko_debt` liegt im Mittel über alle 68 Berichte bei **2,57** und ist damit dauerhaft die
schwächste Dimension. Diese Sitzung liegt mit **2** darunter.

### 5b Autonomie-Kalibrierung

* `over_ask`: **0** belegt. Der Owner gab durchgehend explizite Freigaben; keine reversible,
  deterministische Handlung wurde unnötig vorgelegt.
* `over_act`: **0** belegt. Alle Prod-Schritte (Merges, Deploys, DB-Schreibvorgänge, die
  Tabellensperre aus Migration 0015) wurden vorher benannt und einzeln freigegeben — die
  Sperre ausdrücklich („sperre ist ok").

Keine Verschiebung der Gate-Liste in `feedback_autonomy_charter` angezeigt.

---

## 6 Verankerung — Vorschläge (nicht selbst geschrieben)

### memory_candidates

```markdown
---
name: feedback_number_from_earlier_turn_is_a_claim
description: Eine Zahl aus einem früheren Turn ist eine Behauptung, kein Beleg — vor jeder Wiederverwendung neu messen.
metadata:
  type: feedback
  rule_class: A
  drift: true
  drift_episode: 2026-08-04-stale-21s-in-merged-concept
---

Der Evidenz-Hook prüft, ob der **aktuelle** Turn einen Beleg trägt. Er prüft **nicht**, ob eine
Zahl, die aus einem früheren Turn übernommen wurde, noch gilt.

Realfall 2026-08-04 (dev-hub, Mail-Suche): „27,5 s → 21 s" wurde nach PR #239 gemessen. Danach
entfernte PR #240 den gesamten Bewertungsblock (16,08 s → 3,17 s in der Einzelmessung). Die
21 s gingen trotzdem in das gemergte Konzept KONZ-dev-hub-004 §9 **und** in die
Abschlussmeldung an den Owner. Nachgemessen am Folgetag: 11,06 / 7,91 s.

**Why:** Die Zahl war zum Zeitpunkt ihrer Messung korrekt und wurde nie falsch — sie wurde
nur überholt. Genau deshalb greift kein Beleg-Check: es *gab* einen Beleg.

**How to apply:** Jede Zahl, die in ein durables Artefakt (ADR, Konzept, Issue, PR-Body) oder
in eine Abschlussmeldung geht, wird im selben Turn neu erhoben. Steht die Messung nicht zur
Verfügung, wird die Zahl mit ihrem Messzeitpunkt genannt („gemessen nach #239") statt nackt.
Verwandt: [[feedback_claim_reaches_further_than_the_look]].
```

```markdown
---
name: feedback_merged_doc_must_not_reference_unmerged_doc
description: Vor dem Merge eines verweisenden Dokuments prüfen, ob das referenzierte in main liegt.
metadata:
  type: feedback
  rule_class: B
---

Realfall 2026-08-04: KONZ-dev-hub-004 wurde gemergt und verweist in §9 auf KONZ-dev-hub-003 —
dessen PR (#238) blieb offen. Der Verweis zeigt seither ins Leere.

**Why:** Beide Dokumente entstanden in derselben Sitzung, und die Reihenfolge der Merges war
nicht die der Erstellung. Im Konzepttext liest sich der Verweis wie eine vorhandene Quelle.

**How to apply:** Vor dem Merge eines Dokuments mit Querverweis:
`git show origin/main:<referenzierter-pfad>`. Existiert er nicht — zuerst das andere mergen,
oder den Verweis als „offener PR #N" formulieren.
```

### adr_candidates

Keiner. Alle Befunde sind Prozess- oder Validierungslücken innerhalb bestehender
Entscheidungen (ADR-284 §7/§7a, ADR-288 §4.6/§4.7, ADR-293). Ein neues ADR wäre nach
`adr-threshold.md` überschießend.

---

## 7 Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 KONZ-003 mergen oder den Verweis in KONZ-004 §9 entschärfen — https://github.com/achimdehnert/dev-hub/pull/238
2. 🟢 IMAP-Delta und Wochenabgleich mergen — schließt die Transport-Asymmetrie — https://github.com/achimdehnert/dev-hub/pull/236

### 🔵 Offen — ich kann sofort

3. 🔵 Kommentar an dev-hub#211 mit den drei PRs und dem verbleibenden Rest — https://github.com/achimdehnert/dev-hub/issues/211
4. 🔵 Zahl in KONZ-004 §9 auf die nachgemessenen 7,9–11,1 s korrigieren
5. 🔵 Zwei ungescopte Zusicherungen in `test_ansicht_antworten.py` einschränken

### 🟡 Zur Entscheidung

6. 🟡 Evidenz-Hook um „Zahl aus früherem Turn" schärfen — betrifft `~/.claude/hooks/`, gehört laut Memory in einen platform-PR

---

## 8 Nicht verifiziert (Restlücken)

| Was | Warum offen | Billigster Check |
|---|---|---|
| **Phase 2 (Find) lief inline**, nicht über frische Subagenten | Regel-1-Bruch, bewusst: die Umgebung verlangt Freigabe für Agenten; die Freigabe kam für die drei Bewertungsbefunde, nicht für die Find-Phase | Nachträglicher Finder-Lauf je Dimension (~55k je Agent) |
| Ob weitere Antworten existieren, die die Erkennung **nicht** findet (neuer Betreff, Telefonat) | Im Konzept als benannte Grenze geführt, nie gemessen | Stichprobe von 20 offenen Punkten gegen das Postfach prüfen |
| Ob der IMAP-Delta-Pfad (#236) gegen ein echtes Postfach funktioniert | Nie scharf gelaufen — PR nicht gemergt | `mail_ingest --modus delta --ordner-limit 1 --account hnu` zweimal |
| Ob die Suchzeit von ~8 s stabil ist | Zwei Läufe (11,06 / 7,91 s), erster kalt | Fünf Läufe nach einer Aufwärmphase |
| Der exakte Sendezeitpunkt der Fehlmeldung aus Befund #7 | Liegt außerhalb der Git-Artefakte | Nicht aus dem Repo prüfbar; Befund stützt sich auf das 23-Minuten-Fenster |
| `over_ask`/`over_act` = 0 | Aus den Artefakten abgeleitet, nicht aus einem separaten Durchgang | Eigener Finder auf die Freigabe-Zeilen des Transkripts |

**Getan:** 12 PRs gemergt und deployt, Graph-Delta auf Prod belegt, 2.356 Antworten gebucht,
Suche von 27,5 s auf ~8 s, zwei Konzepte, drei Ansichten auf den echten Bestand.
**Angenommen:** dass die Transport-Asymmetrie bis zum Merge von #236 tragbar ist.
**Nicht verifizierbar:** der IMAP-Delta-Pfad am echten Postfach; die Dunkelziffer nicht
erkannter Antworten.
**Offen geblieben:** #236, #238, dev-hub#211, die Zahl in KONZ-004 §9.

---

## Self-Review (Meta-Agent, Phase 5)

Ein separater Meta-Reviewer prüfte **den Bericht gegen die Skill-Regeln**, nicht die Session.

**Ein harter Verstoß, korrigiert:** Befund #6 (REFUTED) trug in der Beleg-Spalte nur
Analyse-Prosa statt eines Artefakt-Belegs. Regel 5 kennt keine Ausnahme für refutierte
Befunde — die Zeile trägt jetzt die drei Kommandoergebnisse des Skeptikers.

**Ein weicher Befund, korrigiert:** die Scorecard-Anker für `risiko_debt` und
`prozess_effizienz` verwiesen als einzige nicht auf `#N`. Nachgezogen.

**Numerisch:** `refuted_rate = 0.125` folgt der Skill-Formel
`phase3_refuted/(findings_total − pre_refuted) = 1/8`. Der Trend der letzten acht Berichte
lautet 0.33 · 0.21 · 0.23 · 0.30 · 0.45 · 0.00 · 0.29 · 0.00 — 0,125 liegt unter dem jüngsten
Median, aber innerhalb der vorhandenen Streuung (zwei Berichte bei 0,00). Kein Einzelwert löst
„dauerhaft <0,2" aus.

**Einordnung, die der Meta-Reviewer nicht geben durfte und die deshalb hier steht:** die
niedrige Quote hat eine strukturelle Ursache — vier der acht Befunde waren kommandobelegt und
gingen nach Skill-Regel gar nicht erst an einen Skeptiker. Über die drei tatsächlich
falsifizierten Befunde liegt die Quote bei **1/3 = 0,33** und damit im Band der Vorberichte.
