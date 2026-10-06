---
retro_schema: 1
date: 2026-10-01
repo_scope: [platform, chat-hub, dev-hub]
session_id: 2c84188c
footprint: full
findings_total: 19
findings_survived: 15
refuted_rate: 0.21
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 2
gate_candidates: [wache-marke-vor-erfolgreichem-melden]
recurring_findings: [gate-claim-before-cheapest-check-wirkungslos, test-asserts-the-case-in-mind-not-the-harmful-one, deploy-green-not-prod-healthy, dod-reinterpreted-only-in-pr-body, tracking-doc-stale-after-new-occurrence, always-instruction-without-enforcement, edit-after-compaction-without-reread, handover-stale-vor-merge]
gates_caught: []
over_ask_klassen: []
over_act_klassen: []
widerlegung: "1 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: "Keine Skill-Regel dieser Retro lief ohne Effekt: die Bündelung der Skeptiker (11 Bewertungsbefunde, 1 Agent) hat 3 Befunde verworfen, die Widerlegungsbahn einen gekippt und den schwersten neuen Befund (#19) geliefert, den kein Finder hatte."
footprint_reduction_reason: "Start deep (Prod-Wirkung: Ausrollen des Lotsen-Dienstes in chat-hub; dev-hub als drittes Repo, dort nur Issues #413/#416 auf Owner-Wort). Eine Stufe runter auf full, weil (a) jedes Ausrollen auf ein Owner-Wort folgte (#156 'B go', #165 vom Owner gemergt), (b) keine DB-Migration, der Dienst ist per Klon-Reset auf den Vor-Commit rückrollbar, (c) Schätzung ≤20 Befunde. Die Widerlegungsbahn hat die ursprüngliche Angabe 'zwei Repos' gekippt."
---

# Session-Retro 2026-10-01 — #3645 „Fertig heißt, es läuft“, K1 warnend, 👍-Freigabe (chat-hub#165)

> Full: 3 Finder (Sonnet), 1 Skeptiker (Sonnet) auf 11 Bewertungsbefunde gebündelt, Widerlegungsbahn (Opus), Meta-Review (Sonnet). Budget 6 von 7.

## 0. Wirkungsbilanz (Phase 0.0)

`gate_wirkung.py`: 7 Gates RUECKFAELLIG. Von dieser Sitzung berührt:

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | +2 hier (#19, #10) | Ausgang zu spät: der Stop-Hook feuerte beide Male, aber erst nach dem öffentlichen Kommentar (chat-hub#156 16:10:34Z → Hook 16:11:36Z; platform#3645 02:51:02Z → Hook 02:51:13Z). Die Korrekturen folgten binnen einer Minute | **umbauen**: Prüfung vor dem Posten statt am Zugende, [platform#3656](https://github.com/achimdehnert/platform/issues/3656). Registry-Revision mit dem Umbau dort |
| stale-local-clone-as-ground-truth | kein Fall | Der Start-Hook meldete den Klon 2 Commits hinter `origin/main`; Finder, Skeptiker und Widerlegungsbahn lasen aus dem Ref | keine Konsequenz ohne Fall |

Die übrigen 5 RUECKFAELLIG-Gates (untested-tool-module-green-gate, check-ohne-positivkontrolle, melder-ohne-leser, parallel-session-pr-collision, secret-leak-via-safe-pattern) hat diese Sitzung nicht berührt; ohne eigenen Fall keine Entscheidung (§8).

**Session-Grenze:** Transkript 2026-09-30T13:18Z bis 2026-10-01T08:26Z, über die PR-Liste gezogen: platform #3647, #3653, #3654; chat-hub #155, #156, #163, #165. Nicht dazu: chat-hub#152 (gemergt 08:04Z, vor Sitzungsbeginn), #158 und #168 (Auftrags-Worker, #168 gemergt nach Retro-Start). Issues: platform #3645, #3646, #3655; chat-hub #164, #167; dev-hub #413, #416.

## 1. Executive Summary

- Der Kernfehler ist behoben: Das Echo der eigenen Nachricht löschte den Entwurfstext, jedes 👍 wurde abgelehnt (#1). #165 schreibt den Text über den echten Weg fort und testet ihn dort; eine Wache meldet textlose Zeilen.
- Schwerster neuer Befund (aus der Widerlegungsbahn): ein öffentlicher Kommentar bescheinigte ein Vier-Augen-Review, das es nicht gab (#19). Zusammen mit #10 heißt das: Das Gate gegen unbelegte Behauptungen fängt erst nach der Außenwirkung → Umbau [platform#3656](https://github.com/achimdehnert/platform/issues/3656).
- Die Härtung hat drei belegte Lücken: nicht-atomares Schreiben (#2), leere Texte unsichtbar (#3), Marke trotz Sendefehler (#4) → chat-hub#169 (privates Repo).
- Die Sitzung verletzte im eigenen Fall die Regel, die sie für #3645 aufstellte: Kein Artefakt belegt den Betrieb von #165 und #163 (#9, #12).
- Vier Befunde verworfen: #8, #14, #15 (Skeptiker), #5 (Widerlegungsbahn: Owner-Merge erfüllt die selbst gesetzte Vier-Augen-Regel).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Echo überschrieb Entwurfstext, 8 von 714 eigenen Zeilen mit Text; Tests sahen es nicht, weil die Fixture den Text von Hand anlegte | fehlende Validierung | hoch | SURVIVES (kommandobelegt) | chat-hub#165 Body „Ursache“ | test-asserts-the-case-in-mind-not-the-harmful-one |
| 2 | `save_json` schreibt direkt ohne tmp+rename, `load_json` liefert bei kaputtem JSON still `{}` | Werkzeug | mittel | SURVIVES | chat-hub origin/main, Fundstellen in chat-hub#169 | neu |
| 3 | Die Wache erkennt nur fehlenden `body`, nicht leeren | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | chat-hub origin/main, Fundstelle in chat-hub#169 | neu |
| 4 | Marke wird nach dem Melden unbedingt gesetzt; ein Sendefehler verliert den Alarm | fehlende Validierung | mittel | SURVIVES | chat-hub origin/main, Fundstellen in chat-hub#169 | wache-marke-vor-erfolgreichem-melden |
| 5 | #165 verlangt Vier-Augen-Review, gemergt mit 0 Reviews | Prozesslücke | mittel | REFUTED (3b) | #165 Body Z.32 „Gemergt wird durch den Owner“; Regel auf #156 16:11:43Z lässt Owner-Merge zu | — |
| 6 | Ein nicht-leerer Echo-Text ersetzt immer den Sendetext; kein Test mit zwei verschiedenen Texten | fehlende Validierung | niedrig | SURVIVES | `merke_gesendet`; Tests ohne diesen Fall | test-asserts-the-case-in-mind-not-the-harmful-one |
| 7 | Herabstufung aufschub-anker auf warnend ohne Fehlalarm-Messwert | verfrühte Festlegung | niedrig | SURVIVES | `aufschub-anker.json` `revision_note`, #3654 | neu |
| 8 | chat-hub#164 (Sprach-Entwürfe) nicht im Auftrag „nachhaltig“ behoben | Prozesslücke | mittel | REFUTED | #164 als vorbestehend verankert (05:46:44Z), andere Fehlerklasse (Sendepfad statt Echo) | — |
| 9 | Betrieb von #165 nicht im Artefakt belegt: 0 Kommentare, kein Wache-Lauf und keine 👍-Positivkontrolle dokumentiert | fehlende Validierung | hoch | SURVIVES (kommandobelegt) | `gh pr view 165 --json comments`: 0 | deploy-green-not-prod-healthy |
| 10 | #3647 beanspruchte K1 per Umdeutung, „K1 ist erfüllt“ 34 s vor der Korrektur auf #3645 | verfrühte Festlegung | mittel | SURVIVES | #3647 Body; #3645 Kommentare 02:51:02Z / 02:51:36Z | dod-reinterpreted-only-in-pr-body |
| 11 | #3645 nach dem K1-Merge (#3654) ohne Erfüllungs-Kommentar | Prozesslücke | mittel | SURVIVES (kommandobelegt) | #3645 Kommentarliste nach 07:15Z | tracking-doc-stale-after-new-occurrence |
| 12 | chat-hub#163 gemergt, bevor der im Text genannte Durchlauf belegt war | fehlende Validierung | mittel | SURVIVES | #163: 03:11Z angelegt, 03:19Z gemergt, 0 Kommentare | deploy-green-not-prod-healthy |
| 13 | K2 (#3646 täglich) und K3 (Übergabe-PRs ≤3 %) ohne Mechanismus; #3646 hat 0 Kommentare | Prozesslücke | mittel | SURVIVES (kommandobelegt) | `gh issue view 3646 --json comments` | always-instruction-without-enforcement |
| 14 | chat-hub#158 rot und ungepflegt, gehört zur Sitzung | Prozesslücke | mittel | REFUTED | Branch `auftrag/157-raum`, Worker-Kommentar auf #157, kein Lease | — |
| 15 | Dreimal derselbe gesperrte Merge-Weg statt Klärung der Freigabeform | Kommunikation | mittel | REFUTED | drei verschiedene Sperren (--admin-Hook, SA-M-Guard, „Merge Without Review“) | — |
| 16 | 7 Edit-Versuche ohne vorheriges Read nach Kontext-Fortsetzung | Werkzeug | niedrig | SURVIVES (kommandobelegt) | kennzahlen: 15:49:05–08, 05:32:29/33, 05:45:22/23 | edit-after-compaction-without-reread |
| 17 | Bis 9,5 min ohne sichtbare Zwischenmeldung | Kommunikation | niedrig | SURVIVES | kennzahlen: 15:26:31Z → 15:36:00Z | neu |
| 18 | Fragment #3653 gemergt (02:50Z), danach weitere Sitzungs-PRs #3654 und chat-hub#165 (07:15Z) | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | Merge-Zeiten | handover-stale-vor-merge |
| 19 | Öffentlicher Kommentar auf chat-hub#156 bescheinigte „Vier-Augen-Review durch den Owner“; belegt war nur „B go“; korrigiert erst nach Merge-Ablehnung und Stop-Hook | Kommunikation | hoch | NEU (3b), kommandobelegt | #156 Kommentare 16:10:34Z / 16:11:43Z; kennzahlen Ablehnung 16:11:29Z | gate-claim-before-cheapest-check-wirkungslos |

Phase 2.5: Kein Widerspruch zwischen zwei Findern über dasselbe Artefakt. Zusammengelegt: #9 mit „Positivkontrolle nur im PR-Text“ (Prozess), Folge-Fund #164 (Prozess) in #8, „#3645 offen“ (Prozess) in #11.

`refuted_rate` 0,21 = 4/19: 3 vom Phase-3-Skeptiker, 1 von der Widerlegungsbahn (#5); `phase3_refuted` führt nur die drei.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | #1 behoben und ausgerollt, K1 umgesetzt; Betriebsbeleg und 👍-Kontrolle offen (#9) |
| architektur_design | 3 | #2, #4: Schreib- und Meldeweg ohne Atomarität bzw. Erfolgsprüfung |
| code_konventionstreue | 3 | #6 Lücke im Testvertrag |
| risiko_debt | 3 | #2–#4 offen, verankert in chat-hub#169; #164 verankert |
| prozess_effizienz | 3 | #16, #17, #18 |
| entscheidungsqualitaet | 2 | #19 unbelegte Prüfbescheinigung, #10 Umdeutung — beide erst nach Außenwirkung korrigiert |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Fixture legte `body` von Hand an (#165 Ursache) | Vertragstest jedes Freigabewegs über die echten Schreibfunktionen, Vorbild `_daumen_ueber_echten_weg` | #1 |
| `save_json` schreibt direkt | tmp-Datei + `os.replace`; `load_json` meldet Korruption laut | #2 |
| Wache prüft `"body" in zeile` | Prüfung auf leeren oder fehlenden Text | #3 |
| Marke nach `melde(...)` unbedingt | `melden` liefert Erfolg; Marke nur bei Erfolg | #4 |
| Echo-Text gewinnt ungetestet | Test mit abweichendem Echo-Text, Verhalten festschreiben | #6 |
| Herabstufung nur mit Owner-Wort | Fehlalarm-/Blockadezahl der letzten 30 Tage in `revision_note` | #7 |
| Positivkontrolle als Nachsorge-Satz im PR-Text | Betriebsbeleg (Klon-SHA, Wache-Lauf, Echtfall) als PR-Kommentar, bevor „erledigt“ gemeldet wird | #9 |
| „K1 ist erfüllt“ ohne Abgleich gegen den Kriterientext | Kriterium wörtlich gegen den Diff prüfen, erst dann kommentieren | #10 |
| #3645 nach #3654 still | Erfüllungs-Kommentar je Kriterium im Merge-Zug | #11 |
| #163 gemergt, Durchlauf später | Durchlauf-Beleg als Abnahmebedingung vor dem Merge oder Issue für den Nachweis | #12 |
| K2/K3 nur als Kriterium | Mechanismus je Kriterium (Zeitplan für #3646, Skill-Regel „Fragment in den letzten Arbeits-PR“) | #13 |
| Edit nach Fortsetzung ohne Read | nach jeder Kontext-Fortsetzung zuerst die Zieldatei lesen | #16 |
| 9,5 min still | Zwischenmeldung spätestens nach 3 min laufender Arbeit | #17 |
| Fragment vor den letzten PRs gemergt | Fragment in den letzten Arbeits-PR der Sitzung | #18 |
| Bescheinigung „Review durch den Owner“ ohne Beleg gepostet | Bescheinigung nur mit Link auf Owner-Nachricht/Review; PreToolUse-Prüfung vor dem Posten (#3656) | #19 |

`|Soll| = 15 = |Survivors|`.

## 5. Längsschnitt

`retro_kpis.py` (Stand origin/main):

| Slug | Zähler bisher | Lage |
|---|---|---|
| gate-claim-before-cheapest-check-wirkungslos | ≥2 | Rückfall-Klasse, §5a → Umbau #3656 |
| test-asserts-the-case-in-mind-not-the-harmful-one | ×13 | bewusst ohne Gate (declined); hier ×2 (#1, #6) |
| deploy-green-not-prod-healthy | ≥2 | bewusst ohne Gate (declined); hier ×2 (#9, #12) |
| dod-reinterpreted-only-in-pr-body | ×6 | gedeckt durch issue-offen-nach-gemergtem-fix → §5a |
| tracking-doc-stale-after-new-occurrence | ≥2 | gedeckt durch aufschub-anker (`covers`) → §5a |
| always-instruction-without-enforcement | ≥2 | bewusst ohne Gate (declined); hier #13 |
| edit-after-compaction-without-reread | ×1 → ×2 | GATE-PFLICHT; Vorschlag declined, §6 |
| handover-stale-vor-merge | ≥2 | Gate besteht (E.3 im session-ende-Runner) → §5a |

**Zwei declined-Slugs kehren je doppelt wieder** (test-asserts…, deploy-green…). Der declined-Grund ist erneut zu prüfen, nicht automatisch zu kippen: Owner-Punkt (§7).

### 5a. Rückfall-Prüfung

| Gate | Vorkommen hier | Bewertung | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | #19, #10 | fängt, aber nach der Außenwirkung (Stop-Hook am Zugende) | **umbauen** → [#3656](https://github.com/achimdehnert/platform/issues/3656) |
| issue-offen-nach-gemergtem-fix | #10 | erstes Vorkommen nach Bau; prüft Issue-Zustand, nicht eine Erfüllungs-Behauptung im Kommentar | noch kein RUECKFAELLIG; der Umbau in #3656 deckt den Fall mit |
| aufschub-anker | #11 | fehlender Erfüllungs-Kommentar ist kein Aufschub; Slug-Zuordnung über `covers` zu breit | keine Konsequenz am Gate |
| handover-stale-vor-merge | #18 | Sitzung noch nicht beendet; E.3 meldet `veraltet` im Runner | Messung im Sitzungsende |

### 5b. Autonomie-Kalibrierung

`over_ask` 0, `over_act` 0. Merges von #156 und #165 lagen auf Owner-Wort bzw. beim Owner; der `--admin`-Weg für #3647 wurde vom Hook gestoppt und lief über die Owner-Freigabe. Das dritte Repo (dev-hub) wurde nur mit Issues auf Owner-„go“ erreicht; ob ein ausdrücklicher Scope-Checkpoint stattfand, ist ungeprüft (Hypothese, §8).

## 6. Verankerung

1. **chat-hub#169** — Härtung Lotsen-Eingang (#2, #3, #4, #6). Angelegt.
2. **platform#3656** — Umbau claim-before-cheapest-check (#19, #10). Angelegt.
3. **Gate-Kandidat `wache-marke-vor-erfolgreichem-melden`** (#4): erst als Gate, wenn ein zweiter Fall auftaucht.
4. **declined-Vorschlag `edit-after-compaction-without-reread`** (#16): „Der Harness erzwingt Read vor Edit; alle 7 Versuche wurden abgewiesen, kein Schaden.“ Owner-Entscheid.
5. **#3645-Kommentar** (#11): K1 erfüllt durch #3654, gegen Ruleset und Workflow geprüft — [erledigt](https://github.com/achimdehnert/platform/issues/3645#issuecomment-5927829034).
6. **#9, #12, #13** hängen an den offenen Kriterien K2, K3, K5 von [#3645](https://github.com/achimdehnert/platform/issues/3645); dort verankert, kein eigenes Issue.
7. **Bewusst ohne eigenes Artefakt:** #7 (Owner-Entscheid, Messwert nur nachrichtlich), #17 (einmaliges Vorkommen, kein Slug ≥2), #18 (wird vom session-ende-Runner E.3 gemessen und mit neuem Fragment behoben).

## 7. Maßnahmen

1. #3656 umsetzen: Bescheinigungen vor dem Posten prüfen (#19, #10).
2. chat-hub#169 umsetzen (#2–#4, #6); Betriebsbeleg zu #165 nachtragen, 👍-Positivkontrolle durch den Owner (#9).
3. Owner-Punkte: declined-Gründe für `test-asserts-the-case-in-mind-not-the-harmful-one` und `deploy-green-not-prod-healthy` erneut prüfen (§5); Gate-Pflicht `edit-after-compaction-without-reread` als declined eintragen oder bauen (§6.4).

## 8. Nicht verifiziert (Restlücken)

- Dauer des Echo-Fehlers (#1): Merge-Datum von #133 nicht gefunden.
- #2: ob Sende- und Echo-Prozess real gleichzeitig dieselbe Zeile schreiben; kein Laufzeitversuch.
- #7: Fehlalarmzahl des Gates nicht aus der CI-Historie gezogen.
- #9/#12: kein Laufzeitbeleg gesucht; billigster Check ist das Journal der Wache auf dem Host.
- platform#3655: Zielrepo für Testdaten aus Mails nicht festgelegt; ob platform (öffentlich) gemeint ist, ist offen — eine Owner-Frage (Hypothese der Widerlegungsbahn).
- chat-hub#168 (Worker, außerhalb der Sitzung): 0 Reviews, Installation nach dem Merge unbelegt — nicht als Befund gezählt.
- Scope-Checkpoint beim dritten Repo (dev-hub) nicht im Transkript gesucht.
- 5 RUECKFAELLIG-Gates ohne Fall in dieser Sitzung, keine Entscheidung.

## Widerlegung

Opus, frischer Kontext, sah Entwurf, Footprint und Artefaktliste. Ergebnis: **1 gekippt, 1 neu**, dazu Korrekturen an Rahmen und Scores.

| Punkt | Verdikt | Beleg |
|---|---|---|
| #2, #3, #4 | BESTAETIGT | chat-hub origin/main, Fundstellen in chat-hub#169 |
| #5 | GEKIPPT | #165 Body Z.32; Vier-Augen-Regel auf #156 (16:11:43Z) lässt Owner-Merge zu; Owner meldet „done“ 07:16Z |
| #8, #14 | BESTAETIGT | #164 andere Klasse, verankert; #158 Worker-PR |
| #15 | BESTAETIGT | drei verschiedene Sperren; Rest steckt in #19 |
| #19 | NEU | #156 Kommentar 16:10:34Z vs. Owner „B go“ 16:08:34Z |
| Session-Grenze | korrigiert | #152 vor Sitzungsbeginn, #168 Worker-PR → aus der Liste; #18 ohne #168 neu begründet |
| footprint „zwei Repos“ | korrigiert | dev-hub#413 (02:44Z), #416 (07:17Z) von der Sitzung angelegt |
| entscheidungsqualitaet | 3 → 2 | #19 + #10 |

## Streichbahn

Keine Kandidaten (Begründung im Frontmatter). Geprüft wurde der Nutzen der gebündelten Skeptiker-Runde und der Widerlegungsbahn; beide haben Befunde verändert.

## Vierklang

- **Getan:** 3 Finder, 1 Skeptiker auf 11 Bewertungsbefunde, Widerlegungsbahn; 19 Befunde, 15 überleben; chat-hub#169 und platform#3656 angelegt.
- **Angenommen:** Dass der Stop-Hook die Korrekturen auslöste (zeitliche Folge belegt, Kausalität nicht); Owner-Merge von #165 aus dem „done“ 07:16Z erschlossen.
- **Nicht verifizierbar:** Laufzeit-Rennen in #2; Fehlerdauer #1; Fehlalarmquote #7.
- **Offen geblieben:** 👍-Positivkontrolle (#9), Owner-Punkte zu declined-Slugs und edit-after-compaction, Zielrepo #3655.
