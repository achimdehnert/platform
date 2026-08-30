---
retro_schema: 1
date: 2026-08-28
repo_scope: [writing-hub, platform]
session_id: 73073b-incr
footprint: deep
findings_total: 14
findings_survived: 10
refuted_rate: 0.29
phase3_refuted: 2
pre_refuted: 2
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates:
  - eltern-retro-aktionspunkt-nicht-ausgefuehrt
  - belegdatei-abgeschnitten-skeptiker-blind
  - roter-deploy-nur-ueberholt-nie-adressiert
recurring_findings:
  - deferred-item-no-tracking-issue
  - partial-fix-not-generalized-to-sibling-artifacts
  - eltern-retro-aktionspunkt-nicht-ausgefuehrt
gates_caught: []
---

# Increment-Retro writing-hub — zweite Sitzungshaelfte (#839 … #846)

Anschluss an `session-retro-2026-08-28-writing-hub-73073b.md`. Dessen Befunde werden
**nicht** neu verhandelt; sie zaehlen als Vorkommen 1. In-scope sind nur die danach
entstandenen Artefakte: PR #839, #840, #842, #846, die Prod-Loeschung, und die beiden
letzten Owner-Meldungen.

## 1. Executive Summary

- Zwei Aktionspunkte des Eltern-Retros (`outline_detail.html`, Dialog-Fokusfalle) blieben
  liegen, waehrend **vier** weitere PRs an ihnen vorbei gemergt wurden. Das ist der
  eigentliche Befund dieses Increments — nicht die Defekte selbst, die schon bekannt waren.
- Die neue Basisklasse `LangLauf` (#846, noch offen) wird von **keinem** der beiden
  aelteren, strukturgleichen Modelle genutzt; die Vertagung steht nur in einem Docstring.
- Die Zuordnung Art → Modell existiert an **drei** Stellen; ein Code-Kommentar verspricht
  ausdruecklich das Gegenteil.
- Der Owner musste die Autonomie-Grenze bei CI-Zustaenden **zweimal** mit Nachdruck
  korrigieren (`over_ask`).
- Dieser Retro hat sich selbst einen Fehler nachgewiesen: seine Belegdatei war
  abgeschnitten, und der Skeptiker konnte es nicht sehen, weil er dieselbe Datei las.

## 2. Befunde

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Eltern-Retro-Aktionspunkt „`outline_detail.html` sweepen" nicht ausgefuehrt; #838 blieb offen, waehrend #836/#839/#840/#842 gemergt wurden — keiner beruehrt die Datei | Prozessluecke | kritisch | SURVIVES | `gh issue view 838` state=OPEN, created 13:36:47Z; `gh pr view --json files` der vier PRs enthaelt `templates/outlines/outline_detail.html` nirgends | Vorkommen 2 (Eltern-Befund 3) |
| 2 | Eltern-Retro-Aktionspunkt „Dialog-Fokusfalle" nicht ausgefuehrt; #837 offen, `templates/base.html` seit 07:07Z unveraendert | Prozessluecke | hoch | SURVIVES | `git log origin/main --since=2026-08-27 -- templates/base.html` → nur `db40231` (#818, 07:07Z, VOR Issue-Erstellung 13:36Z); `base.html:288-294` behandelt nur Escape/Enter | Vorkommen 2 (Eltern-Befunde 4+5) |
| 3 | `LangLauf` (#846) wird von `FigurenVertiefenLauf` und `ChapterReviewLauf` nicht geerbt; die Vertagung steht nur im Docstring, kein Issue, keine Ledger-Zeile | Wissensluecke | hoch | SURVIVES | `git grep -F "LangLauf" origin/main` → 0 (PR offen); Feldvergleich `apps/worlds/models.py` / `apps/projects/models.py` → `id/status/gesamt/fertig/gescheitert/fehler/created_at/updated_at` identisch; `gh issue list --search "LangLauf"` → 0 | `deferred-item-no-tracking-issue` |
| 4 | Zuordnung Art → Modell an **drei** Stellen: `_bauplan()` in `tasks.py`, `ARTEN` in `views_html.py`, `Art`-Enum in `models.py`; Kommentar behauptet „muss nichts kopieren" | verfruehte Festlegung | hoch | SURVIVES | alle drei in PR #839; `ARTEN` loest per `getattr(welt_modelle, name)` auf — echte Zweitzuordnung, kein Label-Wegweiser; ohne `ARTEN`-Eintrag wirft `post()` vorher `Http404` | — |
| 5 | Belegdatei dieses Retros war abgeschnitten (700-Zeichen-Grenze koepfte den 13.346-Zeichen-Sammelsatz der vorverdichteten Owner-Nachrichten); der Skeptiker konnte es nicht bemerken, weil er dieselbe Datei las | Werkzeug | hoch | SURVIVES | `grep -oic verfein` roh=290, Extrakt=0; Transkript Z. 3456 ist `type=user`, Laenge 13346, beginnt mit „This session is being continued…" | neu |
| 6 | Owner musste die Autonomie-Grenze bei CI-Zustaenden zweimal mit Nachdruck korrigieren | Prozessluecke | hoch | SURVIVES | Transkript `~/.claude/projects/-home-devuser-github-writing-hub/73073bd8-7fb9-44ee-9337-57165b185b5f.jsonl` Z. 2298 („203 ist abwinken -> autonomes go !!") und Z. 2359 („204 -> checks pending -> damit ist das nicht mein Zug !!!!"), beide `type=user`, `isSidechain=false` | `over_ask` ×2 |
| 7 | Compound-Ask der Owner-Nachricht zur Review-Seite nur zur Haelfte geliefert: Mehrfach-Agentenwahl ja (#842), „Einzelfeedback transparenter / Editierfenster" weder umgesetzt noch getrackt | Prozessluecke | hoch | SURVIVES | `gh pr diff 842 --name-only` → nur `views_review.py`, `review_chapter.html`, `services/review_lauf.py`; `gh issue list --search "Einzelfeedback"/"editierfenster"` → 0 | `deferred-item-no-tracking-issue` |
| 8 | Letzte Owner-Meldung der Sitzung (identische Kapitel, fehlender Fortschritt) hat kein Tracking-Artefakt | Prozessluecke | hoch | SURVIVES | `gh issue list --search "gleiche Wortzahl"/"dieselbe Anzahl"` → 0; Handover #835 (Stand 27.08.) nennt es nicht | `deferred-item-no-tracking-issue` |
| 9 | PR #846 ist `BLOCKED` an einem roten Playwright-Test, nicht an einem haengenden Check | fehlende Validierung | mittel | SURVIVES | `gh pr view 846` mergeStateStatus=BLOCKED; Job „ci / Unit Tests" (98913471108) FAILED `tests/ux/test_gesamtdurchlauf.py::…[chromium]`, TimeoutError auf `[data-testid='alle-schritte']`. Die Zusatzbehauptung „seit ueber 24h" widerlegt sich am eigenen Zeitstempel (createdAt 16:29Z) | — |
| 10 | Deploy-Lauf `c414369` (27.08., 18:22Z) schlug fehl, wurde nie re-getriggert, diagnostiziert oder getrackt — nur vom naechsten Push ueberholt | fehlende Validierung | mittel | SURVIVES | Run 33103177940, attempt=1, Job „changes" failure, `ci/deploy` skipped; naechster Erfolg erst 28.08. 04:47Z. Vom Eltern-Retro uebersehen | `roter-deploy-nur-ueberholt-nie-adressiert` |
| 11 | Scope Creep: PR #839 setze nicht Gefordertes um | Kommunikation | niedrig | **REFUTED** | Der Owner forderte es woertlich: „ergaenzen: bei welten charkteren und gegenstaenden: Button \"ALLLE per KI verfeinern\"". Die Nullsuche des Finders — und die des Skeptikers — lief auf der abgeschnittenen Belegdatei (Befund 5) | — |
| 12 | Prod-Loeschung der Duplikat-Figuren ohne durables Artefakt | Prozessluecke | mittel | **REFUTED** | `gh pr view 840 --json body`: Projekt-ID, betroffene Namen, Auswahlregel, Backup-Pfad `/root/backups/writing-hub/2026-08-28-figuren-dubletten.json`, Gegenprobe „12 → 9, global 0 in 8 Projekten", Freigabevermerk — vollstaendig vorhanden | — |
| 13 | Owner musste **dreimal** dieselben fehlschlagenden Checks melden | Kommunikation | mittel | **REFUTED** | Transkript `~/.claude/projects/-home-devuser-github-writing-hub/73073bd8-7fb9-44ee-9337-57165b185b5f.jsonl` Z. 1279 („105 -> checks failing go") und Z. 1413 („116 failing ;") sind Positionen einer durchnummerierten Abarbeitungsliste mit eigenem „go" — Statusmeldung, keine Korrektur. Verifizierte Anzahl ist zwei (Z. 2298 / Z. 2359), nicht drei | — |
| 14 | Zwei rote Deploys aus einer Ursache; #834 behob sie nicht, erst #836 | fehlende Validierung | hoch | **REFUTED** | Sachlich zutreffend, aber bereits Eltern-Befund 1 (`session-retro-2026-08-28-writing-hub-73073b.md`). Increment-Regel 2 verbietet Re-Litigation | Vorkommen 1 beim Eltern-Retro |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | #839/#840/#842 geliefert; Befund 7 (halber Auftrag) und 8 (letzte Meldung ungetrackt) ziehen ab |
| architektur_design | 3 | `LangLauf` ist der richtige Schnitt am dritten Fall (Befund 3 lobt die Basis, tadelt die Reichweite); Befund 4 dreifache Zuordnung |
| code_konventionstreue | 4 | Tests assertieren gegen echte DB-Zustaende, Prompts in Templates, AST-Gates (Nullbefunde des Code-Finders); Abzug fuer den falschen Kommentar in Befund 4 |
| risiko_debt | 2 | Befunde 1, 2, 3, 7, 8 sind saemtlich ungetrackte oder liegengelassene Reste; #846 blockiert (Befund 9) |
| prozess_effizienz | 3 | Befund 6 (`over_ask` ×2); Befund 10 (roter Deploy ohne Nachlauf) |
| entscheidungsqualitaet | 3 | Die Prod-Loeschung ist vorbildlich belegt (Befund 12 widerlegt); dagegen vier Merges an zwei offenen Eltern-Aktionspunkten vorbei (Befunde 1, 2) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| #838 angelegt 13:36Z, danach vier Merges, keiner beruehrt die Datei | Ein Aktionspunkt aus dem eigenen Retro wird vor dem naechsten Feature-Merge abgearbeitet oder ausdruecklich mit Grund vertagt — „liegen lassen und weiterbauen" ist keine dritte Option | #1 |
| #837 offen, `base.html` seit vor der Issue-Erstellung unveraendert | Dieselbe Regel, plus: a11y-Befunde ohne Owner-Druck bekommen beim Anlegen ein Faelligkeitsdatum, sonst rutschen sie strukturell hinter Feature-Arbeit | #2 |
| Vertagung der Geschwister-Migration steht im Docstring von `langlauf.py` | Eine Vertagung im **Code** zaehlt so wenig wie eine im PR-Text: derselbe Zug erzeugt ein Issue, und der Docstring verweist darauf | #3 |
| Drei Stellen tragen die Art-Zuordnung, ein Kommentar behauptet eine | Beim Einfuehren einer Registry wird der Anspruch getestet, nicht kommentiert: ein Test ergaenzt eine vierte Art und muss mit **einer** Aenderung gruen werden | #4 |
| Belegdatei auf 700 Zeichen gekuerzt, Skeptiker las dieselbe Datei | Jede abgeleitete Belegdatei bekommt eine Positivkontrolle gegen die Quelle (ein bekannter Begriff muss in beiden vorkommen), und der Skeptiker bekommt die **Quelle**, nicht das Extrakt | #5 |
| Owner korrigierte die CI-Autonomie zweimal in einer Sitzung | Ein roter oder haengender Check ist nie ein Vorlagegrund; vorgelegt wird erst, wenn eine inhaltliche Entscheidung dranhaengt | #6 |
| Die Owner-Nachricht zur Review-Seite enthielt zwei Forderungen, geliefert wurde eine | Eine Nachricht mit mehreren Forderungen wird beim Umsetzen aufgeteilt: was nicht in den PR geht, wird im selben Zug Issue — vor dem Merge, nicht danach | #7 |
| Letzte Owner-Meldung diagnostiziert, aber nirgends abgelegt | Eine Owner-Meldung erzeugt ihr Tracking-Artefakt beim **Eingang**, nicht beim Beheben — sonst haengt es am Sitzungsende | #8 |
| #846 blockiert an rotem Test, wurde als „wartet auf CI" gefuehrt | Vor jeder Aussage ueber einen PR-Zustand `mergeStateStatus` **und** `statusCheckRollup` lesen; „pending" und „failure" sind verschiedene Lagen | #9 |
| Roter Deploy vom Vortag nur durch den naechsten Push ueberholt | Ein fehlgeschlagener Deploy wird im selben Zug re-getriggert oder mit Run-ID als offener Punkt abgelegt; Zeitablauf ist keine Behebung | #10 |

## 5. Laengsschnitt

`python3 tools/retro_kpis.py` (101 Retros): 40 Slugs stehen bei ≥2 und sind damit
gate-pflichtig. `risiko_debt` bleibt mit Ø 2,52 die schwaechste Dimension ueber alle
Retros — dieser Increment liegt mit 2 darunter, was die Befunde 1/2/3/7/8 abbilden.

Drei Slugs dieses Reports:
- `deferred-item-no-tracking-issue` — Befunde 3, 7, 8. Bereits ×24 vor Gate-Bau, ×6 danach.
- `partial-fix-not-generalized-to-sibling-artifacts` — Befund 3.
- `eltern-retro-aktionspunkt-nicht-ausgefuehrt` — Befunde 1, 2. Neu.

## 5a. Rueckfall-Pruefung

`python3 tools/gate_wirkung.py` meldet drei rueckfaellige Gates. Eines davon trifft
diesen Report unmittelbar:

**`deferred-item-no-tracking-issue` ist rueckfaellig** — 24 Vorkommen vor dem Bau
(2026-08-23, Modus `advisory`), **6 danach**, letzter Rueckfall 2026-08-28. Dieser
Increment liefert drei weitere (Befunde 3, 7, 8). Der Befund lautet damit nicht
„Slug zum 31. Mal", sondern **„Gate rueckfaellig"**.

Antwort: **ausweiten**. Das Gate ist ein Wortlisten-Scanner ueber PR-Texte. Befund 3
zeigt seine strukturelle Blindstelle: die Vertagung stand in einem **Docstring im Code**
(`apps/core/langlauf.py`, „nachziehen nur, wenn wir es ohnehin anfassen"), nicht im
PR-Text — dort kann kein PR-Text-Scanner sie sehen. Die Ausweitung ist konkret: der
Scanner liest zusaetzlich die **hinzugefuegten** Kommentar- und Docstring-Zeilen des
Diffs. Befund 8 zeigt eine zweite Blindstelle: eine Owner-Meldung ohne jeden PR erzeugt
gar keinen Scan-Anlass — dafuer braucht es einen Aufhaenger am Sitzungsende, nicht am PR.

Die beiden anderen Rueckfaelle (`untested-command-handed-to-user`,
`untested-tool-module-green-gate`) beruehren diesen Increment nicht; sie bleiben beim
zustaendigen Report.

## 5b. Autonomie-Kalibrierung

- **`over_ask`: 2** — Befund 6, beide Faelle CI-Zustaende (Transkript Z. 2298, Z. 2359). Das Muster steht
  damit ueber Retros bei ≥2 ⇒ die Gate-Liste der Autonomie-Charta gehoert geschaerft:
  „CI-Zustand (rot, pending, haengend) ist nie ein Vorlagegrund" als eigene Zeile,
  nicht als Auslegung von „deterministisch/reversibel".
- **`over_act`: 0** — breit gesucht in Nachrichtendatei und PR-Historie #816–#846; jede
  Merge- und Prod-Aktion traegt eine woertliche Freigabe. Die Prod-Loeschung ist mit
  Backup-Pfad, Umfang und Gegenprobe belegt (Befund 12 widerlegt).

## 6. Verankerung

**memory_candidates** (writing-hub):

```markdown
---
name: drift-belegdatei-abgeschnitten-skeptiker-blind
description: Ein aus dem Transkript abgeleitetes Extrakt war gekuerzt; der Skeptiker las dasselbe Extrakt und konnte den Fehler nicht sehen
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-28-belegdatei-abgeschnitten
---

Fuer einen Retro wurden die Owner-Nachrichten aus dem Transkript extrahiert und je
Nachricht auf 700 Zeichen gekuerzt. Die vorverdichteten Nachrichten der ersten
Sitzungshaelfte liegen aber in EINEM Sammelsatz von 13.346 Zeichen (Transkript Z. 3456,
`type=user`) — die Kuerzung koepfte ihn. Die Datei sah mit 39 durchnummerierten Zeilen
vollstaendig aus. Ein Finder schloss daraus auf Scope Creep, und der Skeptiker
bestaetigte ihn, weil er dieselbe Datei las.

**Why:** Ein abgeleitetes Extrakt ist ein Messgeraet. Ohne Positivkontrolle gegen die
Quelle ist seine Null nicht von der Null der Welt zu unterscheiden — und ein Skeptiker,
der dasselbe Extrakt liest, kann den Unterschied per Konstruktion nicht finden.

**How to apply:** Jede abgeleitete Belegdatei bekommt vor der Nutzung eine
Positivkontrolle: ein Begriff, der in der Quelle nachweislich vorkommt, muss auch im
Extrakt vorkommen (`grep -oic <begriff>` auf beiden). Und der Skeptiker bekommt die
**Quelle** genannt, nicht nur das Extrakt. Verwandt: [[drift-absence-claim-needs-second-search-path]],
[[drift-pruefung-erkennt-eigenen-leerlauf-nicht]].
```

```markdown
---
name: feedback-eigener-retro-aktionspunkt-vor-feature-merge
description: Aktionspunkte des eigenen Retros werden abgearbeitet oder begruendet vertagt, bevor weitere Feature-PRs daran vorbei mergen
metadata:
  type: feedback
---

Im Increment-Retro 2026-08-28 blieben zwei Aktionspunkte des Eltern-Retros derselben
Sitzung liegen (`outline_detail.html` = Issue #838, Dialog-Fokusfalle = Issue #837),
waehrend vier weitere PRs (#836, #839, #840, #842) gemergt wurden — keiner beruehrte die
betroffenen Dateien. #838 beschreibt dabei dieselbe Bauform, die kurz zuvor drei
Prod-Projekte 24 Tage lang unbedienbar gemacht hatte.

**Why:** Ein Retro, dessen Aktionspunkte dieselbe Sitzung nicht ueberleben, ist ein
Protokoll und keine Korrektur. Der Aufwand faellt an, die Wirkung nicht.

**How to apply:** Vor dem naechsten Feature-Merge die offenen Aktionspunkte des eigenen
Retros ansehen. Zwei zulaessige Abschluesse je Punkt: erledigt, oder vertagt **mit Grund
und Faelligkeit** im Issue. „Steht im Retro" ist kein dritter.
```

**adr_candidates:** keine. Alle Befunde sind Prozess- oder Repo-lokal; die
ADR-Schwelle (neue Abhaengigkeit, Umkehr einer Entscheidung, Cross-Repo-Wirkung) ist
nicht erreicht.

## 7. Massnahmen

### Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | `outline_detail.html` JSON sweepen | writing-hub | #838 | 🔵 | fixen (ich) |
| 3 | `LangLauf`-Geschwister: Issue | writing-hub | — | 🔵 | Issue anlegen (ich) |
| 5 | Editierfenster Review: Issue | writing-hub | — | 🔵 | Issue anlegen (ich) |
| 6 | Identische Kapitel: Issue | writing-hub | — | 🔵 | Issue anlegen (ich) |
| 7 | #846 roter Playwright-Test | writing-hub | #846 | 🔵 | Test fixen (ich) |
| 8 | Art-Zuordnung auf eine Stelle | writing-hub | — | 🔵 | Registry + Test (ich) |

### Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 2 | Dialog-Fokusfalle beheben | writing-hub | #837 | 🟢 | entscheiden: jetzt oder Faelligkeit |
| 4 | Gate `deferred-item…` ausweiten | platform | — | 🟢 | entscheiden: Docstring-Scan bauen |
| 9 | Autonomie-Charta: CI-Zeile | platform | — | 🟢 | entscheiden: Zeile aufnehmen |
| 10 | Deploy `c414369` nachziehen | writing-hub | — | 🟢 | entscheiden: Re-Run oder abhaken |

## 8. Nicht verifiziert (Restluecken)

- **Erste Sitzungshaelfte im Soll-Ist-Abgleich nicht abgedeckt.** Wegen Befund 5 enthielt
  die Belegdatei nur die Owner-Nachrichten nach der Kontext-Verdichtung. Wie viele
  Forderungen der ersten Haelfte ungeprueft blieben, ist unbekannt. Billigster Check:
  den 13.346-Zeichen-Satz aus Transkript Z. 3456 ungekuerzt als eigene Belegdatei
  ausgeben und den Scope-Finder erneut laufen lassen.
- **Methodische Abweichung, offengelegt:** Befund 11 wurde nicht vom Phase-3-Skeptiker
  widerlegt, sondern in Phase 4 durch eine Integritaetspruefung der Belegdatei. Der
  Skeptiker konnte es strukturell nicht — er las dieselbe Datei. Die Pruefung war ein
  `grep` auf ein selbst erzeugtes Extrakt, kein Urteil ueber die Sitzung; sie ist in
  `pre_refuted` gezaehlt.
- **Befund 10 stammt aus dem Zeitfenster des Eltern-Retros**, wurde dort aber nicht
  behandelt. Er ist hier gefuehrt, weil er sonst zwischen beiden Reports verschwaende —
  formal eine Abweichung von der Increment-Scope-Regel.
- **`gates_caught` ist leer**, und das ist eine Aussage: kein bestehendes Gate hat einen
  der zehn ueberlebenden Befunde gefangen.
- **Kein Extern-Handoff (Phase 6)** eingeholt — die Methode dieses Reports hat damit keine
  anbieter-fremde Zweitmeinung gesehen. Billigster Check: den Report zusammen mit den fuenf
  Eisernen Regeln an einen fremden Anbieter geben, mit dem Auftrag, **Methode und
  Score-Logik** zu kritisieren (keine Evidenz-Fakten — dafuer fehlt dort gh/git).

**Der Vierer.** *Getan:* Collector, drei Finder, drei gebuendelte Skeptiker,
Laengsschnitt und Rueckfall-Pruefung, Report. *Angenommen:* dass die 39 extrahierten
Nachrichten die zweite Sitzungshaelfte vollstaendig abbilden — geprueft ist nur, dass
sie die erste **nicht** abbilden. *Nicht verifizierbar:* ob in der ersten Haelfte
weitere ungetrackte Forderungen liegen (Werkzeug dafuer benannt, s. o.).
*Offen geblieben:* die zehn Massnahmen aus §7.
