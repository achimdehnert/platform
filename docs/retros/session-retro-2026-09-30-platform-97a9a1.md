---
retro_schema: 1
date: 2026-09-30
repo_scope: [platform, risk-hub]
session_id: 97a9a1
footprint: full
findings_total: 12
findings_survived: 10
refuted_rate: 0.17
phase3_refuted: 1
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [aussage-an-owner-ohne-transkript-abgleich]
recurring_findings: [gate-aufschub-anker-wirkungslos, deferred-item-no-tracking-issue, direct-gh-pr-merge-bypasses-sa-m, gate-approval-needs-pr-comment, pr-body-stale-after-followup-commits]
gates_caught: [direct-gh-pr-merge-bypasses-sa-m, aufschub-anker, gh-body-file-leer-ueberschrieben, gate-approval-needs-pr-comment]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "2 gekippt, 2 neu"
streichkandidaten: [worktree-midsession-accumulation-faengt-merged]
footprint_reduction_reason: "Start deep (Prod-Schritt in risk-hub). Eine Stufe runter auf full, weil (a) der Prod-Deploy ausdrücklich freigegeben war (Owner-Wort „Prod starten“, Environment-Gate vom Owner freigegeben), (b) keine DB-Migration, Compose-Änderung per Revert rückrollbar, (c) Schätzung ≤10 Befunde. Nachträglich: 12 Befunde, (c) war zu knapp geschätzt; die Widerlegungsbahn hat die Lücke teilweise geschlossen."
---

# Session-Retro 2026-09-30 — Board B1–B5: risk-hub-Prod-Rückstand, hygiene_melder

> Full: 3 Finder (Sonnet), 1 Skeptiker (Sonnet) auf die drei Bewertungsbefunde, Widerlegungsbahn (Opus), Meta-Review (Sonnet). Budget 6 von 6.

## 0. Wirkungsbilanz (Phase 0.0)

`gate_wirkung.py`: 8 Gates RUECKFAELLIG. Von dieser Sitzung berührt:

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| aufschub-anker | +1 hier (#1) | Quelle: das Gate prüft PR-Text, Diff und über `--issue` die Kommentare des ersten „Refs“ eines platform-PRs. Der Aufschub stand in einem Issue-Kommentar im Ziel-Repo risk-hub, dort läuft das Gate nicht. Im platform-PR #3634 hat es dagegen richtig gefangen | **ausweiten** (Reichweite Ziel-Repos). Beleg an [#3169](https://github.com/achimdehnert/platform/issues/3169#issuecomment-5908939571) angehängt, Registry-Revision folgt mit dem Fix dort |
| claim-before-cheapest-check | kein Rückfall belegt | Stop-Hook feuerte einmal (2026-09-30T05:30Z); ob er einen Fehler fing oder falsch anschlug, ist nicht rekonstruiert | keine Konsequenz ohne Beleg; Anlass als Restlücke in §8 mit billigstem Check |

Die übrigen 6 RUECKFAELLIG-Gates (untested-tool-module-green-gate, check-ohne-positivkontrolle, melder-ohne-leser, parallel-session-pr-collision, secret-leak-via-safe-pattern, stale-local-clone-as-ground-truth) hat diese Sitzung nicht berührt: kein Befund und kein Transkript-Fehlerlauf fällt in ihre Klasse. Eine Konsequenz ohne eigenen Fall zu entscheiden, wäre Raten; sie bleiben für die nächste Retro mit Fall offen (§8).

**Session-Grenze:** über Branches `session/2026-09-29…` und `session/2026-09-30/achim-dehnert/*` bzw. die PR-Liste platform #3622, #3623, #3633, #3634 und risk-hub #782, #783 gezogen (Transkript 2026-09-29T09:39Z bis 2026-09-30T09:56Z), nicht über das Datum.

## 1. Executive Summary

- Der Prod-Rückstand von risk-hub ist aufgelöst: MinIO kommt aus dem vorhandenen Host-Image (#782), das Staging Gate zieht aus einem eigenen gepinnten Spiegel (#783), Prod wurde deployt und #778 geschlossen.
- In platform wurde der hygiene_melder repariert (#3622, #3623), die Hook-Kopie wurde angeglichen (#3633), und die Merge-Klasse wurde auf Owner-Wort gestrichen (#3634).
- **Kern-Befund #1:** Die MinIO-Folgearbeit war nur als Prosa in einem Issue-Kommentar festgehalten, ein Folge-Issue gab es nicht. Nachträglich verankert in [risk-hub#790](https://github.com/iilgmbh/risk-hub/issues/790).
- **#12 (aus der Widerlegungsbahn):** An #778 hat die Sitzung den eigenen Merge von #782 zweimal „einer anderen Sitzung“ zugeschrieben, einmal davon im Scope-Checkpoint. Inzwischen korrigiert.
- **#9:** Ein zweiter Prod-Dispatch auf denselben Commit, gestartet, während der erste noch am Gate wartete. Beide haben ausgerollt.
- Vier Gates haben reale Fehler verhindert: direkter Merge (Transkript 2026-09-29T10:21Z), `--admin` ohne Freigabe-Kommentar (2026-09-30T05:17Z), leere Body-Datei (09:49Z), Aufschub ohne Anker (Check an #3634).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Folgearbeit (Umstellung Prod/Staging auf Spiegel, MinIO-Ersatz, Paket-Token, Paketverknüpfung) ohne Issue-Anker, „eigenes Issue“ zugesagt, nicht angelegt | Prozesslücke | mittel | SURVIVES | risk-hub#778 Kommentar mit „eigenes Issue“; `gh issue list --state all` bis zur Retro ohne Treffer; Anker erst nach dem Befund angelegt (risk-hub#790), Verdikt bleibt | deferred-item-no-tracking-issue ×51 → Gate aufschub-anker rückfällig (Reichweite, #3169) |
| 2 | risk-hub#782 pinnt Prod/Staging auf `minio/minio:latest` + `pull_policy: never`, ohne Digest; Reproduzierbarkeit hängt am Host-Cache | verfrühte Festlegung | niedrig | SURVIVES | risk-hub#782 Diff (prod/staging-Compose). 3b: der Spiegel war beim Merge mit keinem Repo verknüpft und das Paket-Token ungültig (#778, 05:13Z und 10:01Z), ein sofortiger Pin hätte den Prod-Pull gebrochen. Schweregrad deshalb mittel → niedrig | — |
| 3 | #783 verschleiert einen Versionssprung | Kommunikation | niedrig | REFUTED | #783-Body nennt den Sprung; alter Tag nicht mehr beziehbar; Dev an Prod angeglichen | — |
| 4 | Registry `worktree-midsession-accumulation` führt „gemergter Baum noch offen“ weiter als gefangen, gedeckt nur über den Namen eines Reaper-Tests; der Reaper hält gemergte Bäume bewusst zurück | fehlende Validierung | niedrig | SURVIVES | Phase 3 verwarf, 3b kippte: `faengt[2]` auf origin/main vs. `revision_note` UMBAU 2026-09-07; seit #3634 kein Melder mehr. Anker [#3635](https://github.com/achimdehnert/platform/issues/3635) | gate-matches-spelling-not-substance (Familie) |
| 5 | Owner-Entscheid „streichen“ nicht an #3611 kommentiert; letzter Kommentar sagte noch „Kriterium 3 offen“ | Kommunikation | niedrig | SURVIVES | #3611-Kommentare vor der Retro; Issue nur per PR geschlossen. Erst nach dem Befund nachgezogen, Verdikt bleibt: [Kommentar](https://github.com/achimdehnert/platform/issues/3611#issuecomment-5908939998) | — |
| 6 | Merge-Versuche ohne vorherigen Blick auf Live-Zustand bzw. Mandat: direkter `gh pr merge 3622` (SA-M blockt), OWNER_WORT-Merge #3623 nach bereits erfolgtem Merge | fehlende Validierung | niedrig | SURVIVES | Transkript 2026-09-29T10:21Z und 10:38Z; #3623 `mergedAt` 10:36:39Z | direct-gh-pr-merge-bypasses-sa-m ≥2 (Gate hat gefangen) |
| 7 | `--admin`-Merge risk-hub#782 ohne Freigabe-Kommentar versucht | Prozesslücke | niedrig | SURVIVES | Guard-Block 05:17Z; Kommentar 05:18:37Z, Merge 05:19:21Z; Bypass nur für „Staging Gate (e2e)“ | gate-approval-needs-pr-comment ×7 (Gate hat gefangen) |
| 8 | PR-Text risk-hub#783 veraltet: behauptet mc unveröffentlicht und Gate bleibt rot, Check lief grün | Kommunikation | niedrig | SURVIVES | #783-Body vs. Check-Status | pr-body-stale-after-followup-commits ×3 (declined) |
| 9 | Zweiter Prod-Dispatch gestartet, ohne nach einem wartenden Lauf zu sehen: derselbe Commit ging zweimal nach Prod; Kriterium „0.7.12 meldet nicht mehr RUECKSTAND“ unbelegt | fehlende Validierung | mittel | SURVIVES | Lauf 36687600818 (Dispatch 08:05:55Z, nicht aus dieser Sitzung) wartete am Gate, eigener Dispatch 08:22:59Z → 36689364415; beide `b1c57a28`, beide Job „Production“ success | — |
| 10 | #3611 geschlossen, ohne dass der Betrieb von `cd_fehlschlag_ketten_scanner` belegt war | fehlende Validierung | niedrig | SURVIVES | Hook-Registrierung 1 Treffer; Journal nicht geprüft | — |
| 11 | Edit ohne vorheriges Read, 3× | Werkzeug | niedrig | REFUTED (pre) | Werkzeug fängt das konstruktiv, keine Wirkung | — |
| 12 | Eigenen Admin-Merge von #782 gegenüber dem Owner zweimal einer anderen Sitzung zugeschrieben, einmal davon im Scope-Checkpoint | fehlende Validierung | mittel | SURVIVES | Transkript 05:18:55Z: Merge-Befehl für #782 kam aus dieser Sitzung; dagegen #778-Kommentare 05:24:17Z und 05:24:34Z. Korrigiert: [Kommentar](https://github.com/iilgmbh/risk-hub/issues/778#issuecomment-5909059884) | neu (3b) |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | erreicht, kleine Mängel: Abschlusskriterium von #3611 unbelegt (#10) |
| architektur_design | 4 | erreicht, kleine Mängel: ungepinntes Image unter Zwang, Nachziehen verankert (#2) |
| code_konventionstreue | 3 | teilweise: Registry behauptet Deckung per Testnamen (#4) |
| risiko_debt | 3 | teilweise: Folgearbeit ohne Anker (#1) |
| prozess_effizienz | 3 | teilweise: doppelter Prod-Deploy (#9) |
| entscheidungsqualitaet | 3 | teilweise: falsche Zuschreibung im Scope-Checkpoint, auf deren Grundlage der Owner entscheidet (#12) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Folgearbeit nur als Kommentar an #778, Issue geschlossen | vor dem Schließen je Aufschub ein Issue im Ziel-Repo und dessen Nummer in den Schließ-Kommentar | #1 |
| Prod/Staging auf `latest` + Host-Cache gemergt, Umstellung nur als Kommentar | beim Workaround-Merge die Umstellung auf den Digest sofort als Issue mit Vorbedingungen (Token, Verknüpfung) anlegen | #2 |
| Registry-Fall nach Streichen des Melders stehen gelassen | beim Streichen eines Melders jeden `faengt`-Eintrag, den er trug, auf echte Deckung prüfen | #4 |
| Owner-Entscheid nur im Chat und im PR | Entscheid wörtlich als Kommentar am Issue, bevor der PR es schließt | #5 |
| Merge-Befehl ohne Blick auf Zustand und Mandat | vor jedem Merge `gh pr view --json state,mergedAt` und Mandat prüfen: `pr_merge_sa.py` oder Owner-Wort für genau diesen PR | #6 |
| `--admin` versucht, Kommentar erst danach | Freigabe-Kommentar zuerst posten, dann `--admin` | #7 |
| PR-Text nach Folge-Commits unverändert | nach jedem Folge-Commit den Body gegen den Check-Stand lesen und nachziehen | #8 |
| zweiter Prod-Dispatch ohne Blick auf wartende Läufe | vor `gh workflow run` `gh run list --status waiting` auf den Workflow; wartender Lauf → dessen Gate freigeben lassen statt neu starten | #9 |
| eigener Merge als fremd gemeldet | vor jeder Zuschreibung („andere Sitzung“, „nicht von mir“) den Merge-Actor und das eigene Transkript abgleichen | #12 |
| Issue geschlossen, Scanner-Betrieb unbelegt | nach Registrierung einen Journal-Eintrag des Scanners abwarten und zitieren | #10 |

## 5. Längsschnitt

`retro_kpis.py`: 56 Slugs mit Zähler ≥2 tragen Gate-Pflicht. Für diese Sitzung relevant:

- `gate-approval-needs-pr-comment` ≥2 → das Gate existiert und hat hier gefangen (#7), keine neue Pflicht.
- `deferred-item-no-tracking-issue` → Familie des rückfälligen Gates aufschub-anker; Konsequenz nach 5a, kein zweites Gate.
- `direct-gh-pr-merge-bypasses-sa-m` ≥2 → Gate existiert, hat hier gefangen (#6).
- `pr-body-stale-after-followup-commits` ×3 → bewusst ohne Gate (declined, Owner-Entscheid), keine neue Pflicht.
- Unter den 56 Pflicht-Slugs ohne Gate-Eintrag stehen `mehrdeutige-owner-anweisung-ohne-rueckfrage` und `retro-streichkandidat-nicht-gestrichen`. Diese Sitzung hat sie nicht berührt, §8.
- MEMORY-Abgleich per grep im Auto-Memory: `aufschub` 3 Dateien, `deferred` 8, `approval-needs-pr-comment` 0, `pr-body-stale` 0. Der Memory-Vorschlag in §6 ist neu, weil keiner der Treffer Issue-Kommentare in Ziel-Repos behandelt (Hypothese, Inhalt der 8 Treffer nicht einzeln gelesen).

refuted_rate 0.17 (Vorgänger 381fb9: 0.33), unter dem Band. Die Widerlegungsbahn hat eine Phase-3-Verwerfung gekippt und zwei neue Befunde gebracht: Die Finder waren eher zu milde als zu streng.
- Neuer Kandidat `aussage-an-owner-ohne-transkript-abgleich` (#12), Vorkommen 1, keine Gate-Pflicht. Familie mit `claim-before-cheapest-check`.

### 5a. Rückfall-Prüfung

aufschub-anker ist rückfällig, Klasse `gate-aufschub-anker-wirkungslos`, Antwort **ausweiten** (Reichweite Ziel-Repos). Die Registry-Revision (`revised` + `revision_note` + neue Positivkontrolle) wird mit dem Fix an #3169 fällig, nicht in diesem Report-PR, weil ohne Code-Änderung keine Positivkontrolle existiert.

### 5b. Autonomie-Kalibrierung

- over_act: keiner, mit Grenzfall. Admin-Merge und OWNER_WORT-Merges hatten je ein Owner-Wort für genau diesen PR. Für Prod lag ein Owner-Wort vor („Prod starten“), das einen Deploy deckt. Den zweiten Lauf (#9) hat die Sitzung gestartet, ohne vom ersten zu wissen, und der Owner hat beide am Environment-Gate freigegeben. Das wird als Prozessfehler geführt, nicht als over_act, weil kein Schritt ohne Owner-Freigabe nach Prod ging.
- over_ask: keiner festgestellt.

## 6. Verankerung

Vorschläge, der Owner entscheidet:

```markdown
---
name: aufschub-im-issue-kommentar-braucht-issue
description: Wer ein Issue schließt, in dessen Kommentaren Folgearbeit steht, legt vorher je Punkt ein Issue im Ziel-Repo an
metadata:
  type: feedback
---
Folgearbeit in einem Issue-Kommentar ist für das Gate aufschub-anker unsichtbar, wenn das Issue in einem Ziel-Repo liegt.
**Why:** Retro 2026-09-30 (97a9a1), risk-hub#778 → #790 erst nachträglich.
**How to apply:** vor `gh issue close` die eigenen Kommentare nach „später/eigenes Issue/mittelfristig“ durchsehen, je Treffer Issue-Nr. in den Schließ-Kommentar. Bis [[aufschub-anker]] Ziel-Repos abdeckt (#3169).
```

ADR-Kandidat: keiner. Die Ausweitung des Gates ist eine Ergänzung nach bestehendem Muster.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| R1 | Retro-Report mergen | platform | Retro-PR | 🟢 | Owner merged |
| R2 | MinIO-Folgearbeit, Spiegel für Prod/Staging | risk-hub | [#790](https://github.com/iilgmbh/risk-hub/issues/790) | 🟢 | Owner priorisiert (Soll #1, #2) |
| R3 | aufschub-anker auf Ziel-Repos ausweiten | platform | [#3169](https://github.com/achimdehnert/platform/issues/3169) | 🟢 | Fix + Registry-Revision (Soll #1) |
| R4 | Memory-Vorschlag §6 | platform | §6 dieses Reports | 🟢 | Owner entscheidet |
| R5 | Belege nachholen: 0.7.12, Scanner-Journal, GHCR-Login Prod | risk-hub/platform | [#778](https://github.com/iilgmbh/risk-hub/issues/778), [#3611](https://github.com/achimdehnert/platform/issues/3611) | 🟢 | nächster Session-Start (Soll #9, #10) |
| R6 | Registry-Fall ohne Deckung, Streichkandidat | platform | [#3635](https://github.com/achimdehnert/platform/issues/3635) | 🟢 | umformulieren oder streichen (Soll #4) |
| R7 | Falsche Zuschreibung an #778 | risk-hub | [Korrektur](https://github.com/iilgmbh/risk-hub/issues/778#issuecomment-5909059884) | ✅ | — (Soll #12) |

Die Soll-Schritte zu #5–#9 sind Verhaltensschritte ohne eigenes Artefakt, #9 ist zusätzlich mit der Korrektur an #778 offengelegt. #5 ist mit dem Kommentar an #3611 erledigt, #6 und #7 fangen bestehende Gates, #8 ist declined.

## 8. Nicht verifiziert (Restlücken)

- Die Bash-Zeile an `memory_forward_refs.tsv` statt Edit ist nur selbst berichtet. Billigster Check: `git log -p` der Datei auf den Sitzungszeitraum.
- Die Behauptung „Hook wertet -R nicht aus“ wurde in der Sitzung per grep widerlegt; ob sie vorher nach außen ging, ist nicht geprüft. Billigster Check: `gh search issues "-R" --author @me --created 2026-09-29..2026-09-30` im platform-Repo.
- Den Anlass des Stop-Hooks claim-before-cheapest-check um 2026-09-30T05:30Z hat niemand rekonstruiert. Billigster Check: Transkript-Zeile um 05:30Z lesen.
- 6 RUECKFAELLIG-Gates ohne Fall in dieser Sitzung, dazu die Pflicht-Slugs `mehrdeutige-owner-anweisung-ohne-rueckfrage` und `retro-streichkandidat-nicht-gestrichen` ohne Gate-Eintrag: Behandlung offen. Billigster Check: `python3 tools/gate_wirkung.py` und `python3 tools/gate_deckung.py` in der nächsten Retro mit Fall.
- Ob der Prod-Host eine gültige GHCR-Anmeldung für den Spiegel hat, ist ungeprüft (Vorbedingung für #790). Billigster Check: Owner prüft nur lesend auf dem Host.
- Scanner-Betrieb (#10) und das Kriterium 0.7.12 (#9) sind weiter unbelegt. Billigster Check: nächster Session-Start-Runner, Zeile 0.7.12 risk-hub.

**Öffentliches Repo, Kontrollprobe:** grep auf IPv4, Provider-/Hostnamen, Token-Präfixe und Image-Digests im Report: 0 Treffer. Positivkontrolle: dasselbe Muster auf eine Probe mit IP und Hostname: 2 Treffer. Personennamen stehen keine im Report. Genannt werden nur Repo-Namen und Run-Nummern, die schon in früheren öffentlichen Handover-Zeilen stehen.

## Widerlegung

Opus, frischer Kontext, nur Entwurf und Artefaktliste. Geprüft hat er den ersten Stand des Entwurfs, die Meta-Fixes liefen parallel.

| # | Verdikt | Beleg |
|---|---|---|
| 1 | BESTAETIGT | #778 Kommentar 29.09. 12:10Z, Schließen 30.09. 09:27Z, #790 erst 10:02Z |
| 2 | GEKIPPT | Spiegel beim Merge unverknüpft, Token ungültig → Schweregrad runter, Soll-Schritt neu |
| 3 | BESTAETIGT | #783-Body nennt den Sprung |
| 4 | GEKIPPT | REFUTED zu früh: Deckung nur über den Testnamen, → SURVIVES, #3635 |
| 5–8, 10, 11 | BESTAETIGT | Zeitstempel und Check-Status nachgezogen |
| 9 | BESTAETIGT, verschärft | zwei erfolgreiche Prod-Läufe auf denselben Commit; Ursache per Transkript: eigener Dispatch 08:22:59Z |
| 12 | NEU | Falsche Zuschreibung des eigenen Merges an #778, per Transkript bestätigt (05:18:55Z) |
| §5b | NEU | Ein Owner-Wort für zwei Prod-Läufe, jetzt als Grenzfall begründet |

Nebenbefund 3b: Der Body von #782 behauptet „Merge = Staging- und Prod-Deploy“, Production stand in den Push-Läufen auf skipped. Die Aussage war falsch, geschadet hat sie nicht. Sie ist in #12 aufgegangen, keine eigene Nummer.

Die Transkript-Abgleiche zu #9 und #12 sind der billigste Check, den 3b benannt hat. Beide sind Kommandobelege, also keine Selbstbewertung aus dem Gedächtnis.

## Streichbahn

**Kandidat:** der Fall „Arbeitsbaum eines bereits gemergten PR ist noch offen“ (Sonde `merged`) in `worktree-midsession-accumulation`. **Belegart: kein Effekt.** Den Baum räumt der Reaper nach der Karenzfrist ohnehin ab (`revision_note` UMBAU 2026-09-07), und der Melder dafür ist mit #3634 gestrichen. Der Eintrag behauptet nur noch eine Deckung. Entscheidung: [#3635](https://github.com/achimdehnert/platform/issues/3635), streichen oder umformulieren.

Die vier Gates, die in dieser Sitzung feuerten, haben je einen realen Fehler verhindert (Belege §1) und sind keine Kandidaten.

## Vierklang

- **getan:** 12 Befunde erhoben, 2 verworfen, 10 mit Soll-Schritt. Nach den Befunden, nicht als deren Widerlegung: Anker risk-hub#790 und platform#3635, Kommentare an #3169 und #3611, Korrektur an #778.
- **angenommen:** das Owner-Wort „B1C mit checks failing“ deckte den `--admin`-Merge von #782 inhaltlich, der Freigabe-Kommentar war nur die Form.
- **nicht verifizierbar:** siehe §8, vor allem der Stop-Hook-Anlass und die Bash-Zeile.
- **offen geblieben:** die Registry-Revision von aufschub-anker (hängt an #3169), B3 (robo-lab#81, andere Sitzung).
