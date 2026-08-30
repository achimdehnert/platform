---
retro_schema: 1
date: 2026-08-28
repo_scope: [robo-lab, platform]
session_id: 54195f-incr
footprint: full
findings_total: 7
findings_survived: 5
refuted_rate: 0.29
phase3_refuted: 1
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 4
  entscheidungsqualitaet: 3
gate_candidates: [external-claim-not-checked-against-own-repo-facts, wiedervorlage-ohne-mechanismus]
recurring_findings: [claim-before-cheapest-check, deferred-item-no-tracking-issue, proof-artifact-left-unmerged]
gates_caught: []
---

# Session-Retro Increment 2026-08-28 — robo-lab / platform (54195f-incr)

> Increment auf [`session-retro-2026-08-28-robo-lab-54195f.md`](session-retro-2026-08-28-robo-lab-54195f.md).
> In-scope ist alles ab ca. 09:20 UTC: der Herstellervergleich Walker C1 gegen Unitree G1,
> die Anfrage-Mail an UBTech, robo-lab#22 als Nachverfolgung, die Postfachpruefung — und
> die Frage, was aus den Aktionspunkten der Eltern-Retro wurde. Die Eltern-Retro selbst
> wird nicht re-litigiert.

## 1. Executive Summary

- Alle vier Auftraege des Owners wurden geliefert; der Plattform-Schluss (beim G1 bleiben)
  ist belegt und hat die Falsifikation ueberstanden.
- **Der schwerste Befund steckt in einer bereits versandten Mail an einen Dritten:** sie
  behauptet, das Projekt betreibe den G1 als physische Hardware. Das eigene Repo sagt seit
  zwei Tagen das Gegenteil. Nicht rueckholbar.
- Ein zweiter Befund derselben Familie: ein Issue-Kommentar rahmt einen Cc als „Versand
  belegt", obwohl das benutzte Werkzeug Cc gar nicht lesen kann.
- Einer meiner eigenen Rohbefunde wurde vom Skeptiker widerlegt — die Behauptung, der
  Vergleich sei „nirgends durabel abgelegt", faellt an robo-lab#22 selbst.
- Der Aktionspunkt der Eltern-Retro zur CI-Testluecke wurde im Increment nicht angefasst
  und hat weiterhin kein Tracking-Artefakt.

## 2. Befunde

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Gesendete Mail an UBTech behauptet Betrieb eines physischen G1 („we run both as hardware and as a MuJoCo digital twin"); Repo sagt „ohne Geraet", Mietanfrage offen | fehlende Validierung | hoch | SURVIVES | Mail 2026-08-28T09:43:58Z (Gesendete Elemente) vs. `robo-lab origin/main:README.md:4`, `docs/beschaffung-miete-leasing.md`, `docs/konzepte/KONZ-robo-lab-001.md:58` | `claim-before-cheapest-check` (85 Retros) |
| 2 | Kommentar an robo-lab#22 fuehrt Cc als „Versand belegt", das Werkzeug kann Cc nicht lesen | Werkzeug | mittel | SURVIVES | `tools/mail_agent/graph_mail.py:570` (`$select=subject,from,toRecipients,receivedDateTime,body,hasAttachments`), `cmd_show` ab :544 druckt zuletzt `An:` in :589 — keine Cc-Zeile; `ccRecipients` nur im Schreibpfad | `claim-before-cheapest-check` |
| 3 | CI in robo-lab ruft `sim/test_stream_gate.py`, `sim/test_view.py`, `sim/test_z2_chain.py` nicht auf; Luecke steht nur im Text von PR #15, kein Issue — Aktionspunkt der Eltern-Retro, im Increment nicht angefasst | Prozesslücke | mittel | SURVIVES | `robo-lab origin/main:.github/workflows/ci.yml` ohne `pytest`; `ls-tree` zeigt die drei Dateien; `gh issue list --state open` (8) ohne CI-Thema | `deferred-item-no-tracking-issue` (32 Retros, Gate RUECKFAELLIG) |
| 4 | Eltern-Retro lag als offener PR #2406 (approved, CLEAN, 8/8 gruen) statt auf `main` — ihre Gate-Kandidaten waren dadurch nicht wirksam | Prozesslücke | mittel | SURVIVES | `git ls-tree origin/main -- docs/retros/ \| grep 54195f` → leer (10:10Z); Bot-Approval 10:03:55Z, `autoMergeRequest: null` | `proof-artifact-left-unmerged` (1 Retro) |
| 5 | Wiedervorlage 2026-09-11 in robo-lab#22 haengt an keinem Mechanismus | fehlende Validierung | niedrig | SURVIVES | `gh issue view 22 --json labels,milestone` → `labels: []`, `milestone: null`; `.github/workflows/` enthaelt nur `ci.yml` | neu |
| 6 | Der Vergleich sei „nirgends durabel abgelegt" und haette in `docs/beschaffung-miete-leasing.md` gehoert | — | — | **REFUTED** | Skeptiker: robo-lab#22 traegt Herstellerzahlen UND die Drittquellen-Kennzeichnung; das genannte Dokument dient laut eigener Kopfzeile der Entscheidung „physisches G1 oder weiter nur Twin", nicht einem Herstellervergleich | — |
| 7 | Collector-Behauptung: Commit `e5dcb8f7` habe die Eltern-Retro auf `origin/main` eingefuehrt | — | — | **REFUTED (pre)** | Drei Finder unabhaengig: Datei nicht im Ref; `merge-base --is-ancestor` → NO; Commit lag auf `session/2026-08-28/achim-dehnert/retro-2026-08-28` | — |

**Waehrend des Retros behoben:** Befund 4 — PR #2406 gemergt (`mergedAt 2026-08-28T10:17:24Z`,
Squash, `d100d2a5`); die Datei liegt jetzt in `origin/main`.

**Bewusst ausserhalb des Scopes:** robo-lab PR #14 wurde ohne durablen Schliessungsgrund
geschlossen (`comments: []`, Timeline nur `cross-referenced`/`closed`). Der Vorgang liegt um
04:56–05:00 UTC, also vor Scope-Beginn, und steht bereits als Aktionspunkt in der Eltern-Retro.
Nicht als Befund dieses Increments gezaehlt.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Alle vier Auftraege geliefert (Vergleich, Kontaktweg, Nachverfolgung, Postfachpruefung); Maengel liegen in der Ausfuehrung, nicht im Ergebnis |
| architektur_design | 3 | Im Increment fand keine Architekturarbeit statt — der Wert ist nicht aussagekraeftig und traegt keinen Befund |
| code_konventionstreue | 4 | Draft-first eingehalten (Owner sendete selbst), Rolle `iil` korrekt, Issue im richtigen Repo, Kontaktadressen aus der Herstellerseite statt geraten; kein Code geschrieben |
| risiko_debt | 2 | Befund 1 ging irreversibel an einen Dritten; Befund 3 laeuft seit der Eltern-Retro ohne Tracking weiter; Befund 5 ohne Mechanismus |
| prozess_effizienz | 4 | Kein Rework, kein Duplikat-Artefakt, keine dangling PRs in robo-lab; Kontaktweg in zwei Schritten belegt statt ueber ein Formular geraten |
| entscheidungsqualitaet | 3 | Der Plattform-Schluss ist gut belegt und ueberstand die Pruefung; der Inhalt der Mail wurde vor dem Hinausgehen nicht gegen die eigene Faktenlage gespiegelt |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Mailtext formuliert und zur Freigabe gelegt, ohne die darin enthaltenen Tatsachenbehauptungen zu pruefen; `grep -i hardware README.md` haette den Widerspruch sofort gezeigt | Vor jedem ausgehenden Text an Dritte: jede Tatsachenbehauptung ueber den eigenen Stand einmal gegen `README.md` und die `docs/konzepte/`-Ledger des betroffenen Repos spiegeln — und das Ergebnis im Vorlage-Text nennen, damit der Owner mitpruefen kann | #1 |
| Kommentar schrieb „Versand belegt … Cc X", obwohl der ausgefuehrte Befehl kein Cc ausgibt | Nur behaupten, was die Ausgabe zeigt: entweder `graph_mail.py` um `ccRecipients` in `$select` und eine `Cc:`-Zeile in `cmd_show` erweitern, oder den Cc als „beim Anlegen gesetzt, im Sendezustand nicht geprueft" kennzeichnen | #2 |
| Die CI-Luecke stand im Text von PR #15 und in der Eltern-Retro als Aktionspunkt — im Increment wurde sie nicht angefasst und hat weiter kein Issue | Ein Aktionspunkt der Vor-Retro wird beim naechsten Zug entweder erledigt oder bekommt im selben Zug sein Tracking-Artefakt im Zielrepo; „steht in der Retro" ist so wenig Tracking wie „steht im PR-Text" | #3 |
| Der Report der Eltern-Retro blieb nach Bot-Approval als offener PR liegen; ihre Gate-Kandidaten waren dadurch nicht wirksam | Ein eigener, gruener, approvter Docs-PR wird im selben Zug gemergt — nicht vorgelegt; bei laufender CI `--auto` scharfschalten statt zu warten | #4 |
| Wiedervorlage 2026-09-11 als Fliesstext in den Issue-Body geschrieben, ohne zu pruefen, ob ein Mechanismus sie spaeter vorlegt | Ein Termin bekommt ein maschinenlesbares Traegerelement (Label `wiedervorlage-YYYY-MM-DD` oder Milestone) — oder er wird gar nicht erst als Termin behauptet, sondern als „ohne Erinnerer" gekennzeichnet | #5 |

Invariante erfuellt: 5 Soll-Schritte zu 5 ueberlebenden Befunden.

## 5. Laengsschnitt (`retro_kpis.py`, 98 Retros)

- 39 Slugs stehen bei ≥2 und sind damit gate-pflichtig; 13 davon haben **kein** registriertes Gate.
- `risiko_debt` bleibt die schwaechste Dimension im Mittel (2,54) — dieser Report liegt mit 2 darunter.
- `refuted_rate`-Band der letzten Laeufe: 0,27 · 0,00 · 0,25 · 0,00 · 0,33 · 0,14 · 0,00 · 0,07.
  Das Werkzeug warnt: „letzte 3 <0,2 → Falsifikation ist Theater". Dieser Lauf liegt bei 0,29
  brutto; die echte Quote `phase3_refuted/(findings_total − pre_refuted)` betraegt 1/6 = 0,17.
  **Damit setzt dieser Report den Warntrend fort, er bricht ihn nicht:** 0,17 liegt unter der
  Schwelle und ist der vierte Lauf in Folge darunter (0,14 · 0,00 · 0,07 · 0,17). Die brutto-Zahl
  0,29 sieht nur deshalb besser aus, weil eine vor Phase 3 verworfene Collector-Angabe mitzaehlt —
  die misst die Schaerfe der Skeptiker nicht.
- Slug-Existenz vor der Wiederholungs-Behauptung geprueft: `claim-before-cheapest-check` in 85,
  `deferred-item-no-tracking-issue` in 32, `proof-artifact-left-unmerged` in 1 Retro-Datei;
  `wiedervorlage-ohne-mechanismus` in 0 → wird als **neu** gefuehrt, nicht als Wiederholung.

## 5a. Rueckfall-Pruefung (`gate_wirkung.py`)

| Gate | Modus | gebaut | Lage | Befund dieses Reports |
|---|---|---|---|---|
| `deferred-item-no-tracking-issue` | advisory | 2026-08-23~ | **RUECKFAELLIG** (24 vor / 4 nach, letzter 2026-08-26) | Befund #3 ist ein weiteres Vorkommen nach dem Bau |
| `claim-before-cheapest-check` | blocking | 2026-08-25~ | `zu-frueh` (60 vor / 0 nach, Kalibrierfenster 1/10 bis 2026-09-20) | Befunde #1 und #2 sind die **ersten Vorkommen nach dem Bau** |

**Zu `deferred-item-no-tracking-issue` — Antwort: ausweiten, und zwar am Aufruf, nicht an der
Faehigkeit.** Eine erste Fassung dieses Absatzes behauptete, der Pruefer koenne Retro-Dateien
nicht lesen. Das ist falsch: `tools/verankerung_pruefer.py:529-530` nimmt **zwei** Quellen,
`--pr` (PR-Text via gh) **und `--datei` (beliebige Markdown-Datei)**, gelesen in :575. Die
Faehigkeit ist da; was fehlt, ist der **Aufruf**: `session-ende` Phase 0g schleift ausschliesslich
ueber die PRs des Tages und fasst keine Retro-Datei an. Vorschlag mit Messpunkt: Phase 0g ruft
zusaetzlich `--datei` auf die juengste Retro des Zielrepos auf und meldet jede 🔵-Zeile ihrer
`## 7. Massnahmen`-Tabelle, die weder erledigt noch mit Issue-Link versehen ist. Messbar an genau
diesem Fall: so waere Befund #3 gefangen worden.

*Anlass der Korrektur:* Der Evidenz-Hook fing die urspruengliche Formulierung als ungedeckte
Behauptung ueber die Faehigkeit eines Werkzeugs. Der billigste Check war ein `grep` auf
`add_argument` — genau die Klasse, die dieser Report unter Befund #1 und #2 fuehrt. Damit
enthaelt dieser Retro ein drittes Vorkommen derselben Familie, diesmal im Retro-Text selbst
und vom Gate gefangen.

**Zu `claim-before-cheapest-check` — keine Herabstufung, das Fenster laeuft.** Die beiden
Vorkommen sind Datenpunkte fuer das offene Kalibrierfenster (Frist 2026-09-20), keine
Rueckfall-Klasse: das Gate steht laut Werkzeug auf `zu-frueh`, und zwei Vorkommen sind
weniger als die drei Retros, ab denen das Urteil traegt. Beide gehoeren aber in das Fenster
eingetragen, weil sie **beurteilbare** Zeilen sind — und sie zeigen dieselbe Lucke wie
Befund #1: das Gate sieht Behauptungen im eigenen Chat/Commit-Text, nicht in einem Text, der
das System als **Mail an einen Dritten** verlaesst.

## 5b. Autonomie-Kalibrierung

- `over_ask`: 0. Der einzige vorgelegte Punkt (Versand der Mail) ist Gate 2 der
  `autonomy-gates.md` (Aussenwirkung gegenueber Dritten) und gehoerte vorgelegt.
- `over_act`: 0. Der Merge von PR #2406 waehrend dieses Retros ist ein eigener, gruener,
  approvter Docs-PR — gedeckt durch `feedback_own_docs_pr_green_merge_autonomously`.
  Kein Prod-Schritt, keine Migration, kein drittes Repo.

## 6. Verankerung (Vorschlaege — Verankerung entscheidet der Mensch)

### memory_candidates

```markdown
---
name: feedback_outbound_claim_must_match_own_repo_facts
description: "Jede Tatsachenbehauptung ueber den eigenen Stand in einem Text an Dritte vorher gegen README und KONZ-Ledger des Repos spiegeln — der Fehler geht sonst irreversibel hinaus"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-28-ubtech-hardware-claim
---

Ein ausgehender Text an Dritte (Mail, Angebot, Anfrage) darf ueber den **eigenen** Stand
nichts behaupten, was nicht vorher gegen die dokumentierte Faktenlage des betroffenen Repos
geprueft wurde — `README.md`, `docs/konzepte/*.md`, das Beschaffungs-/Statusdokument.

**Warum:** Am 2026-08-28 ging an UBTech der Satz „Our current reference platform is a Unitree
G1, which we run both as hardware and as a MuJoCo digital twin" hinaus. `robo-lab README.md:4`
sagte zwei Tage vorher „Digital Twin eines Unitree G1 … **ohne Geraet** und ohne GPU",
`docs/beschaffung-miete-leasing.md` fuehrte die Mietanfrage als „Antwort offen", und
`KONZ-robo-lab-001` L6 stand auf „nicht pruefbar ohne Geraet". Der billigste Check war
`grep -i hardware README.md`. Die Mail ist raus; ein Rueckweg existiert nicht.

**Wie anzuwenden:** Vor der Vorlage eines ausgehenden Textes jede Ich-Aussage ueber
Faehigkeiten, Besitz, Betrieb oder Stand markieren und einzeln belegen. Im Vorlage-Text den
Beleg mitliefern, damit der Owner mitpruefen kann — er sieht dem Satz die Falschheit sonst
genauso wenig an wie ich.

Verwandt: [[feedback_claim_reaches_further_than_the_look]] · [[feedback_draft_first_outbound_standard]]
```

```markdown
---
name: feedback_graph_mail_show_cannot_prove_cc
description: "graph_mail.py --show liest kein Cc — ein Versandbeleg, der Cc nennt, reicht weiter als sein Check"
metadata:
  type: feedback
---

`tools/mail_agent/graph_mail.py` fragt in `cmd_show` `$select=subject,from,toRecipients,
receivedDateTime,body,hasAttachments` ab und druckt `Von/An/Datum/Betreff`. **`ccRecipients`
kommt im Lesepfad nicht vor** — es steht nur im Schreibpfad (Entwurf/Reply). Ein Satz wie
„Versand belegt: … an X, Cc Y" ist damit zur Haelfte unbelegt: der Cc war beim **Anlegen**
gesetzt, der Zustand der **gesendeten** Mail ist eine andere Tatsache, weil der Mensch aus
Outlook sendet und dort aendern kann.

**Wie anzuwenden:** Entweder das Werkzeug erweitern (`ccRecipients` in `$select`, `Cc:`-Zeile
in `cmd_show`) oder den Cc als „beim Anlegen gesetzt, Sendezustand nicht geprueft" schreiben.
Gemessen am 2026-08-28 an robo-lab#22.

Verwandt: [[feedback_measurement_tool_zero_is_not_absence]]
```

### adr_candidates

Keine. Beide Befunde sind Ausfuehrungs- und Werkzeugluecken nach `adr-threshold.md`, keine
Architekturentscheidungen — CHANGELOG/PR genuegt.

## 7. Massnahmen

🔵 **Offen — ich kann sofort**

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Cc in `graph_mail.py` lesbar | platform | — | 🔵 ready | ich: `$select` + Druckzeile |
| 2 | Issue fuer CI-Testluecke | robo-lab | — | 🔵 ready | ich: anlegen |
| 3 | Label `wiedervorlage-2026-09-11` | robo-lab | #22 | 🔵 ready | ich: setzen |
| 4 | Kommentar an #22 korrigieren | robo-lab | #22 | 🔵 ready | ich: Cc-Satz entschaerfen |

🟢 **Offen — dein Zug**

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 5 | Richtigstellung an UBTech | — | — | 🟢 offen | du: ja/nein |
| 6 | Gate ausweiten (Retro-Massnahmen) | platform | — | 🟢 offen | du: Vorschlag 5a |
| 7 | Zwei Memories verankern | — | — | 🟢 offen | du: §6 |

## 8. Nicht verifiziert (Restluecken)

- **Ob das Gate `deferred-item-no-tracking-issue` im Elternlauf ueberhaupt lief.** Behauptet
  wird hier nur, dass fuer die CI-Luecke kein Issue existiert (geprueft). Ob
  `verankerung_pruefer.py` in der Eltern-Sitzung gegen die robo-lab-PRs lief und ignoriert
  wurde, oder nie lief, ist offen. Billigster Check: die `session-ende`-Ausgabe der
  Eltern-Sitzung im Transkript.
- **Der tatsaechliche Cc-Zustand der gesendeten Mail.** Kein Werkzeug im Repo kann ihn lesen.
  Billigster Check: Outlook, Ordner Gesendete Elemente, Nachricht vom 09:43 oeffnen.
- **Ob die Falschaussage die Antwort von UBTech tatsaechlich beeinflusst.** Nicht messbar,
  bevor eine Antwort da ist. Der Schweregrad „hoch" ist die Einschaetzung des Skeptikers zur
  plausiblen Wirkung, kein gemessener Effekt.
- **Ob `verankerung_pruefer.py` an einem echten Text tatsaechlich anschlaegt.** Die Faehigkeits-
  Aussage oben stuetzt sich auf die gelesenen `add_argument`-Zeilen, nicht auf einen Lauf: die
  Positivkontrolle (`--pr 2409`) lief in ein Zeitlimit, vermutlich weil kein Modell erreichbar ist.
  Ohne sie ist offen, ob der Pruefer eine bekannte Zusage auch findet. Billigster Check: `ollama`
  starten und den Lauf wiederholen.
- **Der Chat-Verlauf des Vergleichs.** Kein Finder konnte ihn sehen; beurteilt wurde nur, was
  in robo-lab#22 und in der Mail steht.

**getan** — vier Auftraege geliefert, PR #2406 gemergt, fuenf Befunde belegt, einer widerlegt,
zwei Memory-Vorschlaege formuliert.
**angenommen** — dass ein Anbieter einem angeblichen Realbetreiber anders antwortet als einem
Simulations-Nutzer (Schweregrad-Begruendung, plausibel, unbewiesen).
**nicht verifizierbar** — Cc-Sendezustand, Gate-Lauf der Eltern-Sitzung, Wirkung der
Falschaussage.
**offen geblieben** — Richtigstellung an UBTech (Aussenwirkung, Owner), Gate-Ausweitung,
CI-Testluecke, Wiedervorlage-Mechanismus.
