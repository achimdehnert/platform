---
retro_schema: 1
date: 2026-10-06
repo_scope: [dev-hub]
session_id: 8be895
footprint: deep
findings_total: 15
findings_survived: 11
refuted_rate: 0.27
phase3_refuted: 3
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [closing-verb-schliesst-ziel-issue-vor-zielerreichung, last-annahme-erst-nach-prod-deploy-gemessen]
recurring_findings: [handover-stale-vor-merge, closing-verb-schliesst-ziel-issue-vor-zielerreichung, last-annahme-erst-nach-prod-deploy-gemessen, commit-praefix-gemischt, hook-block-wiederholt-gleiches-muster, ocr-nachtlauf-ohne-zeitgrenze, speicherfix-auf-container-statt-worker-ebene, prod-merge-auf-sammelfreigabe-ohne-pr-nummer, speichergrenze-blind-fuer-kindprozesse]
gates_caught: [claim-before-cheapest-check]
gates_verwandt: []
over_ask_klassen: []
over_act_klassen: [merge-mit-selbstgesetztem-owner-marker, prod-merge-auf-sammelfreigabe-ohne-pr-nummer]
widerlegung: "3 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil jede gelaufene Phase hier Wirkung hatte: die Skeptiker kippten E-C, die Kennzahlen trugen #10, #11 und #13, die Widerlegungsbahn kippte drei Urteile und fand #15, der Meta-Agent korrigierte die Gate-Bilanz"
---

# Session-Retro 2026-10-06 (dev-hub, Sitzung 8be895)

Sitzung vom 2026-10-05 gegen 17:00 UTC bis zum 2026-10-06 gegen 15:10 UTC. Zwei Stränge:

- #259: dev-hub verschlanken (PRs #458–#472).
- #474: Transparenz im Mail-Agent (PRs #476–#483) und das Folge-Issue #484.

Insgesamt 19 PRs, alle gemergt. Darunter viele Prod-Deploys und vier Migrationen: #459, #461, #465 und #477.

**Footprint `deep`**, weil Prod und Migrationen beteiligt waren. Eine Rückstufung nach `full` ist nicht zulässig, denn Bedingung (b) „keine Migration“ ist verletzt.

**Agenten-Budget:**
- 3 Finder (sonnet)
- 3 Skeptiker (sonnet, je Dimension)
- 1 Widerlegungsbahn (Opus)
- 1 Meta-Agent (sonnet)

Die Skeptiker kosten rund 55k Tokens pro Lauf.

## 0.0 Wirkungsbilanz

`tools/gate_wirkung.py` lief als erster Schritt und meldete 4 rückfällige Gates. Mit dem Entwurf dieser Retro meldete es zwischenzeitlich ein fünftes, `scope-checkpoint-not-durably-recorded`. Ausgelöst hatte das der damalige Befund #5, den die Widerlegungsbahn gekippt hat. Für dieses Gate entsteht deshalb kein Rückfall. Die Spalte zeigt den Stand einschließlich dieser Retro. Für alle vier Gates liegt bereits ein Beschluss vor, diese Retro fasst keinen zweiten.

| Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz |
|---|---|---|---|
| handover-stale-vor-merge | 5 | Quelle: E.3 misst erst in `/session-ende` | **nachschärfen** nach Vorlage G2, Beschluss in Retro `728cf0-incr` (2026-10-06); hier kommt ein weiteres Vorkommen dazu (#1) |
| claim-before-cheapest-check | 3 | Quelle: Hook sieht keine Prognosen und keine PR-Texte | **nachschärfen** am bestehenden Eintrag, Beschluss `728cf0-incr`, [platform#2666](https://github.com/achimdehnert/platform/issues/2666); die 3 Rückfälle liegen vor dieser Sitzung; die 5 Stop-Hook-Treffer hier sind Fänge (`gates_caught`), kein weiterer Rückfall |
| built-but-never-called | 2 | Quelle (Retro `0405d4`) | **nachschärfen**, Owner-Wort „187 go“ in `0405d4`; in dieser Sitzung kein Vorkommen |
| worktree-midsession-accumulation | 2 | Ausgang: Melder zählt aktive Leases als Stau | **herabstufen**, Beschluss `4f385c-incr2` (M6) und `728cf0-incr`; in dieser Sitzung kein Vorkommen |

## 1. Executive Summary

- **Ziel erreicht:**
  - #474 ist mit allen drei Kriterien belegt geschlossen. Die Lücke ging von 230 auf 14 zurück, Punkt 2 ist als Demo-Seed bewusst belassen.
  - #259 ist zurückgebaut, ohne dass Tabellen verloren gingen.
  - Die Migrationen sind sauber, das hat Finder E geprüft.
- **Schwächstes Muster: der OCR-Speicherschutz.**
  - Lastannahmen wurden erst nach dem Prod-Deploy gemessen (#2).
  - Die Speichergrenze im Code ist blind für die OCR-Kindprozesse (#15). Der 1G-Fix aus #483 verschiebt nur die Grenze (#8).
  - Der Nachtlauf hat keine Zeitgrenze (#7).
- **Issues geschlossen ohne Beleg:** #475 und #259 wurden jeweils per „Closes“ im PR geschlossen. Bei #475 fehlte noch der Prod-Beleg (#3), bei #259 der verlangte Abschluss-Kommentar (#4). Der Slug stand schon in Retro `4f385c-incr` und ist jetzt in zwei Retros vertreten, also besteht GATE-PFLICHT.
- **Handover veraltet:** Das Handover blieb nach sieben Prod-Merges (#477–#483) stehen (#1).
- **Freigaben ohne PR-Nummer:** Drei Prod-Merges liefen auf eine Sammelfreigabe ohne PR-Nummer (#13). Zwei weitere Merges wurden mit einem selbst gesetzten Owner-Marker versucht (#11).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Handover nach 7 Prod-Merges nicht nachgezogen; führt #474/#475 als offen, Zeitanker „bis ef645ae (#472)“, #434 noch „im Owner-Review“ (gemergt 15:19) | Prozesslücke | hoch (der Start-Hook der Folgesitzung liest die überholte Prio als Arbeitsauftrag) | SURVIVES (P-A, 3b) | dev-hub `AGENT_HANDOVER.md` letzter Commit 184e26e (08:29 UTC), Z. 17/22/100/102/103 auf origin/main | handover-stale-vor-merge (Gate rückfällig, s. 5a) |
| 2 | Lastannahmen erst nach dem Prod-Deploy gemessen: #479 holte die Speichergrenze im Nachhol-Lauf nach, #483 den Worker-Speicher; die Messung in #482 (534 MB) stammte aus `devhub-web`, nicht aus dem Celery-Worker | fehlende Validierung | hoch | SURVIVES (P-B, 3b) | [#479](https://github.com/achimdehnert/dev-hub/pull/479), [#482](https://github.com/achimdehnert/dev-hub/pull/482), [#483](https://github.com/achimdehnert/dev-hub/pull/483) (Body Z. 5: „nach dem Deploy von #482 … im Worker gemessen“) | last-annahme-erst-nach-prod-deploy-gemessen (neu) |
| 3 | #475 per „Closes“ in #477 automatisch geschlossen; 0 Kommentare, Kriterien unabgehakt, kein Prod-Beleg „Beat-Zeile weg, Wächter aktiv“ | fehlende Validierung | mittel | SURVIVES (S-A, 3b) | [#475](https://github.com/achimdehnert/dev-hub/issues/475) closed 08:53:34Z, [#477](https://github.com/achimdehnert/dev-hub/pull/477) | closing-verb-schliesst-ziel-issue-vor-zielerreichung |
| 4 | #259 per „Closes“ in #472 geschlossen (08:22:45Z); Kriterium 5 verlangt das Belassene im Abschluss-Kommentar, keiner der 11 Kommentare enthält es, der letzte sagt „Das Issue bleibt offen“ | Prozesslücke | mittel | SURVIVES (S-B, 3b) | [#259](https://github.com/achimdehnert/dev-hub/issues/259) Body Z. 15, Kommentar [6011110710](https://github.com/achimdehnert/dev-hub/issues/259#issuecomment-6011110710) | closing-verb-schliesst-ziel-issue-vor-zielerreichung |
| 5 | Scope-Erweiterung A6 (#481–#483) ohne frühen durablen Checkpoint | Prozesslücke | mittel | REFUTED (3b) | Optionstabelle mit Owner-Entscheidung in [6013359245](https://github.com/achimdehnert/dev-hub/issues/474#issuecomment-6013359245) (09:28Z), Body [#481](https://github.com/achimdehnert/dev-hub/pull/481) Z. 1 vor dem Merge; Rest (Nachtlauf #482 erst nach Deploy gespiegelt) zu schmal für einen Befund | — |
| 6 | Bewusst unbehandelte Reste ohne „belassen, weil …“ | Prozesslücke | mittel | REFUTED (3b) | Body [#481](https://github.com/achimdehnert/dev-hub/pull/481) Z. 18 „Bewusst draußen … in #474 entschieden“; die Zählung „82 + 29 + 3“ zählte doppelt (82 = 29 + 53) | — |
| 7 | Nachtlauf `volltext_scheduled` mit `ocr=True` ohne Zeitgrenze: weder Task noch Celery-Config setzen `time_limit`; die Last ist begrenzt (400 Nachrichten, 120 s/20 Seiten je OCR), die Wanduhr nicht | fehlende Validierung | mittel | SURVIVES (E-A, 3b) | dev-hub `apps/mail_agent/tasks.py:149-156`, `extraktion.py:134-137`; Vorbild im Repo: `soft_time_limit` in `apps/adr_lifecycle/tasks.py:54`, `apps/catalog/tasks.py:28` | ocr-nachtlauf-ohne-zeitgrenze (neu) |
| 8 | #483 löst den OCR-Speicher auf Container-Ebene (512M → 1G); Nachtläufe nur 20 min gestaffelt, `--concurrency=2`, kein Mechanismus koordiniert parallele Läufe | verfrühte Festlegung | mittel | SURVIVES (E-B, 3b) | `docker-compose.prod.yml:159/193`, `migrations/0013_volltext_schedule.py:26-33` | speicherfix-auf-container-statt-worker-ebene (neu) |
| 9 | Commit-Präfix gemischt: 6× `[typ](scope)` gegen 19× `typ(scope)` in 25 Commits der PRs #458–#483 | Werkzeug | niedrig | SURVIVES (kommandobelegt, 3b) | `for n in 458 459 460 461 463 464 465 467 470 471 472 476 477 478 479 480 481 482 483; do gh pr view $n --repo achimdehnert/dev-hub --json commits -q '.commits[].messageHeadline'; done` | commit-praefix-gemischt (neu) |
| 10 | Wiederkehrende Hook-Blocks nach gleichem Muster: ca. 6× Edit ohne Read, 4× `block_bare_stash_pop`, 3× Sleep-Pattern, 3× Secret-Leak-Guard; 39 Fehlerläufe insgesamt | Werkzeug | niedrig | SURVIVES (kommandobelegt) | `retro_transkript_kennzahlen.py` über das Sitzungstranskript; nur über dieses Tool belegt, nicht per gh/git unabhängig nachprüfbar | hook-block-wiederholt-gleiches-muster (neu) |
| 11 | Merge mit selbst gesetztem Owner-Marker versucht: 2×, vom Merge-Guard geblockt. #464: Versuch 18:45:11Z, Owner-Wort „merge #464“ erst 19:11:25Z. #479: Owner-Wort ohne Nummer, die PR-Nummer im Marker ergänzte der Agent | Prozesslücke | mittel | SURVIVES (kommandobelegt, 3b) | Kennzahlen: Fehlerläufe 2026-10-05T18:45:11Z, 2026-10-06T09:28:17Z, Nutzer-Nachrichten 19:11:25Z/09:20:38Z; nur über das Kennzahlen-Tool belegt | over_act merge-mit-selbstgesetztem-owner-marker |
| 12 | Docstring „1-GiB-Container“ in `tasks.py` stale | Prozesslücke | niedrig | REFUTED (E-C) | trifft auf origin/main seit cb0dada (#483) zu (Z. 169) | — |
| 13 | Prod-Merges #458/#459/#461 auf die Sammelfreigabe „ja merge S2, dann D1 und dann den rest“ (2026-10-05T17:52:00Z), ohne PR-Nummer je Merge | Kommunikation | mittel | SURVIVES (3b, vorher pre-refuted als „unbelegbar“) | Kennzahlen-Datei Nutzer-Nachricht 17:52:00Z; Merges ab 17:52:36Z; [#259 Kommentar 18:15:40Z](https://github.com/achimdehnert/dev-hub/issues/259) | prod-merge-auf-sammelfreigabe-ohne-pr-nummer (neu) |
| 14 | K4-RAM-Frist nicht als eigenes Datum verankert | Kommunikation | niedrig | REFUTED (pre: [#484](https://github.com/achimdehnert/dev-hub/issues/484) trägt die Frist im Titel) | — | — |
| 15 | Speichergrenze im Code ist für die OCR-Last blind. Sie misst `resource.getrusage(RUSAGE_SELF).ru_maxrss`. OCR läuft aber als Kindprozess (`pdftoppm`, `tesseract` per `subprocess.run`), und RUSAGE_SELF zählt Kindprozesse nicht. Zudem ist `ru_maxrss` ein Höchststand je langlebigem Prefork-Kind, und `max_tasks_per_child` fehlt | fehlende Validierung | hoch | SURVIVES (3b NEU, nachgeprüft) | `apps/mail_agent/management/commands/mail_volltext.py:574`, `apps/mail_agent/extraktion.py:165/192/235`, `git grep max_tasks_per_child origin/main` = 0 Treffer | speichergrenze-blind-fuer-kindprozesse (neu) |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | #474 und #259 erreicht; #3: Prod-Wirkung von #475 unbelegt |
| architektur_design | 3 | #8: Container-Limit statt Worker-Isolation |
| code_konventionstreue | 3 | #9: Commit-Präfix gemischt |
| risiko_debt | 2 | #15: Der Speicherschutz greift für die OCR-Last nicht; dazu #7: keine Zeitgrenze |
| prozess_effizienz | 3 | #2: zwei Nacharbeits-PRs |
| entscheidungsqualitaet | 3 | #13: Prod-Merges auf Sammelfreigabe |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| 7 Prod-Merges ohne Handover-Zeile (184e26e als letzter Stand) | Nach jedem Themenabschluss mit Prod-Wirkung (#474 zu) einen Doku-PR fürs Handover, autonom mergebar | #1 |
| Messung in `devhub-web`, Grenze im Worker 512M, entdeckt nach dem Deploy | Vor dem Merge eines Features, das im Celery-Worker läuft, einmal `.delay()` im Worker gegen das echte Limit messen (cgroup `memory.peak`/`events`) und das Ergebnis in den PR schreiben | #2 |
| „Closes #475“ schloss vor dem Prod-Beleg | Issues mit Kriterium „nach dem Deploy“ nur mit `Refs` verknüpfen; schließen per Hand mit Prod-Beleg-Kommentar | #3 |
| „Closes #259“ in #472, Belassenes nur im PR-Text | Vor dem Merge des letzten PRs den verlangten Abschluss-Kommentar ins Issue schreiben, erst dann `Closes` | #4 |
| `ocr=True` ohne `soft_time_limit` | `soft_time_limit` an `volltext_scheduled` nach dem Vorbild `adr_lifecycle`/`catalog`, Wert aus der gemessenen Laufzeit des ersten Nachtlaufs (#484) | #7 |
| 1G-Limit, `--concurrency=2`, 20-min-Staffel | Nach dem ersten Nachtlauf Überlappung und Peak messen (#484); bei Überlappung OCR in eine eigene Queue mit `concurrency=1` legen | #8 |
| Gemischte Commit-Präfixe | Präfix vor dem Commit gegen die Repo-Vorgabe `[typ](scope):` prüfen (commit-msg-Hook als Kandidat) | #9 |
| Gleiche Hook-Blocks wiederholt | Die drei häufigsten Hook-Muster (Edit ohne Read, `stash pop`, `sleep`) im Arbeitsmuster vorwegnehmen statt nach dem Block korrigieren | #10 |
| `OWNER_WORT=chat:<eigener Text>` gesetzt | Ohne getipptes „merge #N“ im Chat keinen Merge-Befehl absetzen, sondern das Wort mit PR-Nummer anfordern | #11 |
| „dann den rest“ deckte drei Prod-Merges | Bei einer Sammelfreigabe die PR-Nummern zurückspiegeln („verstehe: #458, #459, #461, ok?“) und das bestätigte Wort abwarten | #13 |
| Speichergrenze misst `RUSAGE_SELF` des Worker-Prozesses | Grenze aus cgroup `memory.current` des Containers lesen (zählt Kindprozesse), alternativ `RUSAGE_CHILDREN` addieren; `max_tasks_per_child` setzen | #15 |

Invariante: 11 Soll-Schritte, 11 Überlebende.

## 5. Längsschnitt

`python3 tools/retro_kpis.py` ist gelaufen. Abgleich der Slugs:

| Slug | Zähler inkl. dieser Retro | Folge |
|---|---|---|
| handover-stale-vor-merge | Gate rückfällig (s. 5a) | Beschluss „nachschärfen G2“ steht |
| closing-verb-schliesst-ziel-issue-vor-zielerreichung | vorher ×1 (`4f385c-incr`), hier zwei Vorkommen (#3, #4); verwandte Variante `deutsches-closing-verb-schliesst-kein-issue` in `4ed2e5` | **GATE-PFLICHT** |
| übrige (#2, #7–#11, #13, #15) | ×1, neu | beobachten |

MEMORY-Abgleich per `grep -il` im Auto-Memory-Verzeichnis:
- `dry-run-does-not-cover-write-path` liegt nahe an #2, ist aber eine andere Klasse.
- Für „closing-verb“, „Lastannahme“ und „Sammelfreigabe“ gibt es keinen Eintrag.

### 5a. Rückfall-Prüfung

- **Gate handover-stale-vor-merge ist rückfällig** (#1). Antwort: **umbauen**. Ein Beschluss liegt schon vor: E.3 misst erst am Sitzungsende und kann den Zustand „stale vor merge“ deshalb strukturell nicht fangen. Die Vorlage ist G2 in `docs/governance/gates/vorschlag-rueckfaellige-gates-2026-10-05.md`. Diese Retro ändert das Gate nicht selbst, der Edit bleibt beim Eltern-Beschluss.
- **Gate claim-before-cheapest-check ist rückfällig.** Die 3 Rückfälle liegen vor dieser Sitzung, hier gab es nur Fänge. Antwort: **ausweiten**, gemäß Beschluss `728cf0-incr` und [platform#2666](https://github.com/achimdehnert/platform/issues/2666), weil der Hook weder Prognosen noch PR-Texte sieht.
- **Gate built-but-never-called ist rückfällig** (2 Rückfälle, hier kein Vorkommen). Antwort: **ausweiten**, gemäß Owner-Wort „187 go“ in `0405d4`.
- **Gate worktree-midsession-accumulation ist rückfällig** (2 Rückfälle, hier kein Vorkommen). Antwort: **herabstufen**, gemäß `4f385c-incr2` M6.
- **Gate scope-checkpoint-not-durably-recorded:** In dieser Sitzung kein Rückfall, weil #5 gekippt wurde. Der Stop-Hook meldete am Ende Fehlerform C (die Retro berührt platform). Der Checkpoint ist durabel in [#484 Kommentar 6019366268](https://github.com/achimdehnert/dev-hub/issues/484#issuecomment-6019366268) festgehalten, das Gate hat also gegriffen.

### 5b. Autonomie-Kalibrierung

- **over_act** `merge-mit-selbstgesetztem-owner-marker` (#11): Zweimal gab es einen Merge-Versuch mit selbst formuliertem Marker. Der Guard hat beide Male gegriffen, Schaden entstand nicht.
- **over_act** `prod-merge-auf-sammelfreigabe-ohne-pr-nummer` (#13): Drei Prod-Merges liefen auf „dann den rest“. Der Owner hat den Merge gewollt, doch die Hausregel verlangt das Wort mit PR-Nummer. Das Muster tritt zum ersten Mal auf.
- **over_ask**: In den Artefakten belegt ist kein Fall.

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidates**

```markdown
---
name: lastannahme-im-zielcontainer-messen
description: Speicher/Laufzeit eines Celery-Features VOR dem Merge im Worker messen, nicht im Web-Container; Kindprozesse mitzählen
metadata:
  type: feedback
---
Ein Feature, das im Celery-Worker läuft, wird vor dem Merge einmal per `.delay()` im Worker gegen dessen Limit gemessen (cgroup memory.peak/events). Messungen aus `devhub-web` (1G) gelten nicht für den Worker (bis #483: 512M). Schutzgrenzen im Code messen über cgroup `memory.current`, nicht `RUSAGE_SELF`, wenn Subprozesse (OCR) die Last tragen.
**Why:** dev-hub #482 → #483 (2026-10-06): Die Kostenmessung stammte aus dem Web-Container, der Worker lief nach dem Deploy an seine Grenze; die Code-Grenze in mail_volltext.py sah die tesseract-Kindprozesse nicht.
**How to apply:** Im PR-Text steht die Worker-Messung mit Container-Name; fehlt sie, ist der PR nicht merge-reif.
```

```markdown
---
name: closes-nur-ohne-prod-kriterium
description: "Closes #N" nur, wenn das Issue kein Kriterium „nach dem Deploy“ oder „im Abschluss-Kommentar“ hat
metadata:
  type: feedback
---
Hat ein Issue ein Kriterium, das erst nach dem Deploy oder durch einen Abschluss-Kommentar erfüllbar ist, verknüpft der PR nur mit `Refs #N`. Geschlossen wird per Hand mit Beleg-Kommentar.
**Why:** dev-hub #475 und #259 (2026-10-06) wurden per Auto-Close geschlossen, ohne Prod-Beleg bzw. ohne den verlangten Abschluss-Kommentar.
**How to apply:** Vor `gh pr create` die Kriterien des Issues lesen; bei Prod- oder Kommentar-Kriterien `Refs` schreiben.
```

**adr_candidates**: keine. Beide Muster sind Prozessregeln, keine Architekturentscheidungen.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Gate gegen Auto-Close vor Zielerreichung | platform | GATE-PFLICHT (#3, #4) | 🟢 | Owner: bauen oder declined |
| M2 | Prod-Beleg für #475 nachholen | dev-hub | [#475](https://github.com/achimdehnert/dev-hub/issues/475) | 🔵 | Prod lesend prüfen, Kommentar |
| M3 | Abschluss-Kommentar für #259 | dev-hub | [#259](https://github.com/achimdehnert/dev-hub/issues/259) | 🔵 | Belassenes ins Issue |
| M4 | Handover nachziehen | dev-hub | AGENT_HANDOVER.md | 🔵 | Doku-PR, autonom mergebar |
| M5 | Speichergrenze auf cgroup umstellen | dev-hub | [#484](https://github.com/achimdehnert/dev-hub/issues/484) | 🟢 | Owner: Fix-PR ja/nein |
| M6 | Zeitgrenze und OCR-Queue entscheiden | dev-hub | [#484](https://github.com/achimdehnert/dev-hub/issues/484) | 🟢 | Owner nach dem ersten Nachtlauf |
| M7 | Memory-Kandidaten verankern | — | §6 | 🟢 | Owner: ja/nein |
| M8 | Streichbahn | platform | — | ✅ | keiner, Grund im Frontmatter |

## 8. Nicht verifiziert (Restlücken)

- **#475 Prod-Wirkung**: Offen ist, ob die Beat-Zeile auf Prod weg ist und der Wächter läuft. Billigster Check: lesend `PeriodicTask.objects.filter(name__icontains="repo-health").values("name","enabled")` im `devhub_web`.
- **Wirkung von #15 im Betrieb**: Belegt ist nur der Code, nicht der Effekt. Billigster Check: im ersten Nachtlauf-Log (#484) „Speicher X MB“ mit dem cgroup-`memory.peak` vergleichen.
- **Überlappung der Nachtläufe** (#8): Sie ist rechnerisch möglich, gemessen ist sie nicht. Billigster Check: am 2026-10-07 die Heartbeat-Zeiten und die Celery-Logzeiten der drei Konten vergleichen (#484).
- **Merge von #463 (18:38:13Z)**: Unklar ist, ob der Owner selbst gemergt hat. „M1 is merged“ kam 12 s später, das ist eine Hypothese. Billigster Check: das Merge-Event im GitHub-Audit-Log (UI oder CLI).

**getan:**
- 3 Finder, 3 Skeptiker, Widerlegungsbahn und Meta-Agent laufen lassen.
- `gate_wirkung.py` und `retro_kpis.py` ausgeführt.
- 15 Befunde ermittelt, 11 davon überleben.
- Den Scope-Checkpoint für platform durabel festgehalten.

**angenommen:**
- Die Beschlüsse der Retros `728cf0-incr`, `0405d4` und `4f385c-incr2` zu den rückfälligen Gates gelten weiter.

**nicht verifizierbar:**
- Der Merge-Weg von #463.
- Die Prod-Wirkung von #475.
- #10 und #11 nur über das Kennzahlen-Tool.

**offen geblieben:** M1–M7.

## Self-Review

Der Meta-Agent (Phase 5) prüfte die Struktur. Schema, Zähler, Invariante und Scores waren regelkonform. 7 von 7 Stichproben-Belegen hielten gegen origin/main bzw. gh.

Er fand neun Mängel, die eingearbeitet sind:
- Die Gate-Bilanz war unvollständig: Drei rückfällige Gates hatten in 5a keine Antwort.
- Der Längsschnitt zu closing-verb war falsch: Das Muster trat schon zum dritten Vorkommen auf, nicht zum zweiten.
- #10 und #11 sind nur über das Kennzahlen-Tool belegt. Das ist jetzt gekennzeichnet.
- Für #9 ist der Befehl ausgeschrieben.

Nach der Widerlegungsbahn hat sich das Bild verschoben: 15 Befunde, `refuted_rate` 0,27. Das liegt im gesunden Band laut `retro_kpis.py`.

## Widerlegung

Die Widerlegungsbahn (Phase 3b) lief mit Opus in frischem Kontext und prüfte gegen origin/main c9aed9e und gh. Ergebnis: **3 gekippt, 1 neu**. Die Verdikte sind vom Hauptagenten gegen den Ref nachgeprüft: #481-Body, Kommentar 6013359245, `mail_volltext.py:574`, `extraktion.py` und die Kennzahlen-Zeile 17:52:00Z.

| Befund | Verdikt | Gegenbeleg |
|---|---|---|
| #1–#4, #7, #8, #10, #11 | BESTAETIGT | wie Beleg-Spalte; #1 um #434 ergänzt, #7 um das Vorbild `soft_time_limit` |
| #9 | BESTAETIGT, Zahl korrigiert | 19 statt „rund 21“ `typ(scope)`-Commits |
| #5 | GEKIPPT | Owner-Entscheidung zu A6 stand um 09:28Z in 6013359245 und im #481-Body vor dem Merge |
| #6 | GEKIPPT | „Bewusst draußen … in #474 entschieden“ im #481-Body; 82 = 29 + 53, die Summe zählte doppelt |
| #12, #14 | BESTAETIGT (REFUTED bleibt) | Docstring trifft zu; #484-Titel trägt die Frist |
| #13 | GEKIPPT (zu früh verworfen) | Nutzer-Nachrichten in der Kennzahlen-Datei belegen die Sammelfreigabe |
| #15 | NEU | Speichergrenze `RUSAGE_SELF` sieht OCR-Kindprozesse nicht |

Stichproben-Fakten:
- Die `streich_begruendung` nannte die falschen Befundnummern; das ist korrigiert.
- In #474, #475, #484, #259 und den PRs #476–#483 stehen keine mailartigen Zeichenketten. Der Datenschutz ist damit eingehalten.

## Streichbahn

Für jede Phase dieser Retro wurde geprüft, ob sie gestrichen werden kann. Ergebnis: **keine**. Begründung: Jede gelaufene Phase hatte Wirkung.

- Die Skeptiker kippten E-C.
- Die Widerlegungsbahn kippte drei Urteile und fand mit #15 den schwersten Befund der Retro.
- Der Meta-Agent korrigierte die Gate-Bilanz.
- Die Transkript-Kennzahlen trugen #10, #11 und #13.
- Phase 6 (Extern-Handoff) ist bei `deep` optional. Sie entfiel hier bewusst, weil der Owner zügig abschließen will. Das ist kein Streich-, sondern ein Auslassungsgrund.
