---
retro_schema: 1
date: 2026-09-23
repo_scope: [platform, risk-hub, iil-assist-voice]
session_id: 4ed2e5
footprint: deep
findings_total: 19
findings_survived: 16
refuted_rate: 0.16
phase3_refuted: 2
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 2
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [push-to-merged-branch-silently-lost, new-rule-shadowed-by-earlier-rule, deutsches-closing-verb-schliesst-kein-issue, personendaten-in-oeffentlichem-issue]
recurring_findings: [claim-before-cheapest-check, issue-offen-nach-gemergtem-fix, test-asserts-the-case-in-mind-not-the-harmful-one, untested-tool-module-green-gate]
gates_caught: [claim-before-cheapest-check, scope-checkpoint-not-durably-recorded, secret-leak-via-safe-pattern]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "3 gekippt, 1 neu"
streichkandidaten: [retro-phase-2.5-finder-konflikt-erkennung]
---

# Session-Retro 2026-09-23 — platform (Sitzung 4ed2e5)

## 1. Executive Summary

- Die Sitzung lieferte weit ueber ihren Einstieg hinaus: aus „sieben Session-Start-Befunde verankern" wurden 5 gemergte PRs, 6 neue Issues und sechs Prod-Schreibungen ueber drei Repos — jeder Schritt einzeln vom Owner freigegeben.
- **Zwei Befunde mit Aussenwirkung, beide waehrend der Retro behoben:** die vom Owner verlangte Kuerzung der Aufbewahrungstabelle erreichte `main` nie (Push auf einen schon gemergten Branch, #1 → #3439), und zwei Kommentare eines **oeffentlichen** Repos trugen ab 03:27 Mandanten-, Gemeinde- und Privatnamen (#17, redigiert, Kontrollprobe 0 Treffer).
- Zwei Codefehler in gemergtem Code (#2, #4): eine neue Regel in `schleuse.py` wird von einer aelteren verschattet, ein verirrtes `$` macht aus einem Praefix einen exakten Vergleich. Beide Tests waren gruen — der Testfall traf zufaellig die Variante, die den Konflikt umgeht (#3).
- Das Gate `claim-before-cheapest-check` hat fuenfmal gefangen und jedes Mal eine Korrektur ausgeloest — und den sechsten Fall nicht gesehen, weil ein erfolgreicher `git push` wie ein Beleg aussieht. Konsequenz in §5a: ausweiten.
- Zweimal wurde Arbeit einer **Fremdsitzung** dieser zugerechnet — von einem Finder und von der Widerlegungsbahn. Befund #13 (keine Sitzungs-ID im Artefakt) hat sich im Verlauf der Retro selbst bewiesen.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Owner-Korrektur an KONZ-064 auf einen bereits gemergten Branch gepusht, erreichte `main` nie | fehlende Validierung | kritisch | SURVIVES | `git merge-base --is-ancestor 3c394370 origin/main` → exit 1; `git show origin/main:docs/konzepte/KONZ-platform-064-*.md` enthaelt 0× „Liste 1 — muss auf Verlangen vorlegbar sein" | neu (`push-to-merged-branch-silently-lost`) |
| 2 | Neue Klasse „PR-/Issue-Text" wird von der aelteren Regel „Bericht" verschattet; `review-*.md` faellt in die falsche Klasse | fehlende Validierung | hoch | SURVIVES | `tools/schleuse.py` (2ec4601b): „Bericht" an Position 6, „PR-/Issue-Text" an Position 8; `klasse_von()` nimmt den ersten Treffer | neu (`new-rule-shadowed-by-earlier-rule`) |
| 3 | Der Test zur neuen Klasse waehlt `"review 2.md"` — die einzige Variante ohne Bindestrich und damit die einzige, die den Shadowing-Fall nicht beruehrt | fehlende Validierung | hoch | SURVIVES | `tools/tests/test_schleuse.py:194` — `("review 2.md", "PR-/Issue-Text", 14)`; alle Geschwister-Beispiele derselben Parametrisierung nutzen Bindestrich | `test-asserts-the-case-in-mind-not-the-harmful-one` ×11 ⇒ GATE-PFLICHT |
| 4 | `k4w?$` in der Modell-Ausgabe-Regel: verirrtes `$` mitten in der Alternation macht aus dem Praefix einen exakten Vergleich | fehlende Validierung | mittel | SURVIVES | Repro: `.match("k4-run-2026")` → False, `.match("k4")` → True | neu |
| 5 | `paperless_zustellen` — der echte Transport — hat null Testabdeckung; alle 7 Tests injizieren ihn weg | fehlende Validierung | mittel | SURVIVES | `grep -n "paperless_zustellen" tools/tests/test_belegbeschaffung.py` → kein Treffer | `untested-tool-module-green-gate` ×21 ⇒ GATE-PFLICHT |
| 6 | Teilfehler-Pfad in `paperless_zustellen`: scheitert `rm -f` nach erfolgreichem `install`, ist das PDF zugestellt, aber nicht im Index — der naechste Lauf liefert erneut | fehlende Validierung | mittel | SURVIVES | `tools/sevdesk/belegbeschaffung.py:1107` (`install … && rm -f …`, `check=True`) gegen `:1152` (`index[schluessel] = {`) — die Buchung steht nach der Kette | neu |
| 7 | risk-hub#771 blieb OPEN trotz gemergtem #772 — „Schliesst #771" ist deutsch, GitHub kennt nur `closes/fixes/resolves` | Prozessluecke | mittel | SURVIVES | `gh api repos/iilgmbh/risk-hub/issues/771/timeline` → nur `cross-referenced`, kein `closed` mit source 772 | `issue-offen-nach-gemergtem-fix` ×9 ⇒ GATE-PFLICHT |
| 8 | Secret-Leak-Guard blockierte viermal in 90 Sekunden — vier Zugriffsvarianten gegen dieselbe Datei, statt vorher die Guard-Regel zu lesen | Werkzeug | mittel | SURVIVES | `retro_transkript_kennzahlen.py <transkript.jsonl>`, Fehllauf-Block 09:42:04–09:43:03: viermal wortgleicher `PreToolUse:Bash hook error: Secret-Leak-Guard` | neu |
| 9 | Drei Anlaeufe fuer eine Funktionssignatur (`sammeln()` in `schleuse.py`) — zwei davon durch einen vorherigen Blick in die Datei vermeidbar | Werkzeug | niedrig | SURVIVES | `retro_transkript_kennzahlen.py <transkript.jsonl>`, Fehllaeufe 03:18:50 (`TypeError: sammeln() missing 1 required positional argument`) und 03:18:57, Erfolg erst 03:19:05 | neu |
| 10 | `gh pr create` mit Freitext direkt in der Kommandozeile — Backticks und Kommas wurden von der Shell interpretiert | Werkzeug | niedrig | SURVIVES | `retro_transkript_kennzahlen.py <transkript.jsonl>`, Fehllauf 05:45:23 `gh pr create` Exit 2 „unknown arguments"; zweiter Fall beschaedigte Kommentar 5790439528 an #3405 (per PATCH repariert) | neu |
| 11 | Zwei Edit-Aufrufe scheiterten identisch mit „File has not been read yet" — die Datei war zuvor nur per Bash inspiziert | Werkzeug | niedrig | SURVIVES | `retro_transkript_kennzahlen.py <transkript.jsonl>`, Fehllaeufe 03:22:43 und 03:24:17, beide `<tool_use_error>File has not been read yet` | neu, genau 2× |
| 12 | Relative Zielgroesse („unentschieden < 10 % des Bestands") als absolute Zahl gefuehrt („< 30"), waehrend dieselbe Sitzung den Nenner halbierte — 39 von 291 sind 13 %, 39 von 158 sind 25 % | verfruehte Festlegung | mittel | SURVIVES | #3405 nennt Messung, 10-%-Ziel und die „30" im selben Text (291 × 10 % = 29,1); nach dem Sweep #3411 sind es 158 Eintraege | neu (`relative-schwelle-als-absolute-zahl`) |
| 13 | Branch-Namen tragen keine Sitzungs-ID (`session/<datum>/<owner>/<slug>`); bei parallelen Sitzungen ist die Zurechnung von Artefakten nicht maschinell moeglich | Werkzeug | mittel | SURVIVES | `gh issue list -R achimdehnert/platform --search "created:2026-09-23" --state all` → **13** Issues, davon 6 dieser Sitzung; `gh pr view <n> --json headRefName` zeigt fuer alle dasselbe Schema ohne Sitzungs-ID | neu |
| 14 | CHANGELOG-Eintrag bei #3410 vorhanden, bei #3427 nicht — gleiche Sitzung, gleicher Autor, gleiche Aenderungsart | Prozessluecke | niedrig | SURVIVES | `git show 0eafd8f5 --stat` ohne `CHANGELOG.md`; kein CHANGELOG-Gate in `CORE_CONTEXT.md` gefunden | neu |
| 15 | „21 Dokumente importiert und 6 per `manage.py shell` in der risk-hub-Prod-DB korrigiert, ohne Audit-Trail" | — | kritisch | **REFUTED** | Skeptiker: risk-hub `documents_document` = 0, kein scharfer Import; die 6 Korrekturen betrafen **Paperless** (doc-hub) und sind an #3102/#3414 dokumentiert | — |
| 16 | „Kein sichtbarer Scope-Checkpoint" — **Repo-Haelfte** | — | hoch | **REFUTED** | Skeptiker: #3405 traegt „## Scope-Checkpoint der Sitzung 2026-09-23" mit Repo-Tabelle, Freigabe-Wort je Repo und offener Frage | — |
| 17 | Mandanten-, Gemeinde- und Privatnamen standen ab 03:27 in zwei Kommentaren eines **oeffentlichen** Repos; die Regel dazu hat dieselbe Sitzung 3,5 h spaeter selbst formuliert, ohne den Altbestand zu bereinigen | Kommunikation | hoch | SURVIVES | 4 Namenstreffer in #3405-Kommentaren 5788463915/5788688135; der 06:54-Kommentar sagt „Die namentliche Liste steht **nicht hier** … dieses Repo ist oeffentlich". Am 2026-09-23 redigiert, Kontrollprobe 0 Treffer / 3 Platzhalter | neu (`personendaten-in-oeffentlichem-issue`) |
| 18 | Der Scope-Checkpoint deckt die Repo-Eskalation, **nicht** die Prod-Eskalation: er steht 03:54, danach folgten sechs Prod-Schreibungen ohne neuen Checkpoint | Prozessluecke | mittel | SURVIVES | `gh api repos/<owner>/<repo>/issues/<n>/comments` ueber 12 Vorgaenge (platform #3405 #3409 #3411 #3414 #3426 #3102 #2083 #2234 #3215 #3234, risk-hub #771 #773): genau ein Treffer auf „Scope-Checkpoint", Kommentar 5788688135 um 03:54:43 | `scope-checkpoint-not-durably-recorded` ×32 ⇒ GATE-PFLICHT |

**Vor Phase 3 verworfen (`pre_refuted` = 1):** „‚alles erledigt' um 10:05 war nicht das Ende, um 12:07 folgte ein nicht offengelegter Arbeitsblock." Die Zeitstempel stimmen, die Deutung nicht — aber die urspruengliche Begruendung („200 ist eine Board-Nummer") war selbst unbelegt und wurde von der Widerlegungsbahn zu Recht beanstandet. Belegt ist stattdessen: die um 12:07–12:44 an platform entstandenen Vorgaenge (#3435, #3437, #3441) gehoeren zu **anderen** Sitzungen, und der einzige Arbeitsblock dieser Sitzung nach 10:05 steht offen im Issue (#3102-Kommentar 5792835981). Kein verdeckter Block.

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---:|---|
| Zielerreichung | 4 | Einstiegsziel uebererfuellt (#3405, #3410 gemergt), aber Befund 1: ein Deliverable trug auf `main` die abgelehnte Fassung |
| Architektur & Design | 4 | Kein Befund der Tabelle betrifft den Zuschnitt: die Erdung gab zwei von drei Auftragsthemen an #2083 und doc-hub#18 zurueck statt sie neu aufzumachen. Abzug nur wegen Befund #12 — eine Zielgroesse wurde relativ gedacht und absolut abgenommen |
| Code- & Konventionstreue | 2 | Befunde 2, 4, 5, 14 — vier Code-/Konventionsbefunde in drei PRs, davon zwei in derselben Datei |
| Risiko & Debt | 2 | Befund 1 (abgelehnter Inhalt oeffentlich, unbemerkt) + Befund 6 (Teilfehler-Pfad ohne Test) |
| Prozess-Effizienz | 3 | 293 Bash-Aufrufe, 15 Fehllaeufe; Befunde 8, 9, 10, 11 sind zusammen rund zehn vermeidbare Aufrufe — gemessen an 293 aber kein struktureller Bruch |
| Entscheidungsqualitaet | 3 | Befund #1 (behauptet „PR aktualisiert", ohne den PR-Zustand zu pruefen) und Befund #17 (Sichtbarkeitsregel selbst formuliert, Altbestand nicht bereinigt) — beide Male wurde eine erkannte Regel nicht auf das eigene Ergebnis angewandt |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Nach `git push` auf einen Feature-Branch „PR aktualisiert" gemeldet; der PR war seit 10 Minuten gemergt | Nach jedem Push auf einen PR-Branch `gh pr view <n> --json state,mergedAt` — ein erfolgreicher Push ist kein Beleg dafuer, dass die Aenderung ankommt | #1 |
| Neue Regeln ans Ende von `REGELN` angehaengt, ohne Overlap gegen die bestehenden zu pruefen | Jede neue Regel einmal gegen ALLE frueheren laufen lassen und belegen, dass genau eine matcht — als Test, nicht als Blick | #2 |
| Testbeispiele aus dem Bestand gewaehlt; die gewaehlte Variante umging den Konfliktfall | Bei geordneten Regelmengen den Testfall so waehlen, dass er die **frueheste** konkurrierende Regel beruehrt — sonst prueft der Test die eigene Absicht | #3 |
| Regex ueber zwei String-Literale verteilt, zusammengesetztes Muster nie ausgegeben | Ein zusammengesetztes Muster einmal `print(pattern.pattern)` und gegen zwei Positiv- und zwei Negativbeispiele halten | #4 |
| Transport per `zustell_fn` injiziert, echte Funktion nie aufgerufen | Fuer die echte Transportfunktion mindestens einen Test mit gefaktem `subprocess.run`, der die drei Aufrufe und ihre Reihenfolge prueft | #5 |
| Index-Eintrag erst nach dem letzten Kettenschritt gesetzt | Den Index setzen, sobald der **wirksame** Schritt (`install`) durch ist — Aufraeumschritte danach duerfen die Buchung nicht zuruecknehmen | #6 |
| „Schliesst #771" in den PR-Text geschrieben und angenommen, das Issue schliesse sich | Closing-Keyword englisch schreiben (`Closes #771`) und nach dem Merge `gh issue view <n> --json state` gegenpruefen | #7 |
| Vier Zugriffsvarianten gegen eine geschuetzte Datei durchprobiert | Beim ersten Guard-Treffer die Guard-Regel lesen, bevor die naechste Variante laeuft | #8 |
| Funktion per Heredoc aufgerufen, Signatur dreimal geraten | Vor dem ersten Aufruf die Signatur lesen (`sed -n` auf die `def`-Zeile) — ein Blick statt drei Fehlversuche | #9 |
| Freitext mit Sonderzeichen direkt als `--body` in die Kommandozeile | Jeden mehrzeiligen oder Backtick-haltigen Text per `--body-file` uebergeben, ausnahmslos | #10 |
| Datei per Bash inspiziert, dann per Edit geaendert | Vor dem ersten Edit die Datei einmal per Read-Werkzeug oeffnen, auch wenn der Inhalt schon bekannt ist | #11 |
| Zielgroesse relativ gedacht („< 10 %"), als absolute Zahl abgenommen („< 30"), Nenner danach halbiert | Relative Kriterien relativ abnehmen („< 10 % des Bestands"), oder den Nenner beim Setzen der Zahl einfrieren und das im Kriterium sagen | #12 |
| Retro-Artefaktliste von Hand zusammengestellt | Branch-Namen um die Sitzungs-ID erweitern (`session/<datum>/<owner>/<sid>/<slug>`), damit die Zurechnung maschinell faellt | #13 |
| CHANGELOG bei einem `feat` gepflegt, beim naechsten nicht | Fuer `tools/`-Feature-Commits einen CHANGELOG-Eintrag verlangen — entweder als CI-Gate oder gar nicht als Konvention fuehren | #14 |
| Dateinamen aus `~/shared` in ein oeffentliches Issue kopiert, die Sichtbarkeitsregel erst Stunden spaeter angewandt | Vor jedem Kommentar an ein Repo, das `CLAUDE.md` als PUBLIC fuehrt, die Namensliste gegen Mandanten-/Personenbezug pruefen — und bei spaeterer Erkenntnis den **Altbestand** mitredigieren, nicht nur nach vorn anwenden | #17 |
| Ein Scope-Checkpoint fuer die Repo-Zahl geschrieben, danach sechs Prod-Schreibungen ohne neuen | Den Checkpoint an den **Auslöser** binden: je einmal beim dritten Repo UND beim ersten Prod-Schritt, danach bei jedem neuen Zielsystem | #18 |

## 5. Laengsschnitt

`python3 tools/retro_kpis.py` ueber 136 Reports, Existenz je Slug per `grep -rl docs/retros/*.md` geprueft:

| Slug | Zaehler | Konsequenz |
|---|---:|---|
| `claim-before-cheapest-check` | 117 Reports | GATE-PFLICHT eingeloest (Gate existiert, blocking) — siehe 5a |
| `untested-tool-module-green-gate` | 21 Reports | GATE-PFLICHT — Befund #5 ist das 22. Vorkommen |
| `test-asserts-the-case-in-mind-not-the-harmful-one` | 11 Reports | GATE-PFLICHT — Befund #3 ist das 12. Vorkommen |
| `issue-offen-nach-gemergtem-fix` | 9 Reports | GATE-PFLICHT — Befund #7 ist das 10. Vorkommen, erstmals mit belegter Ursache (deutsches Closing-Verb) |

Neu und ohne Vorkommen: `push-to-merged-branch-silently-lost`, `new-rule-shadowed-by-earlier-rule`, `deutsches-closing-verb-schliesst-kein-issue` (je 0 Treffer in `docs/retros/`).

## 5a. Rueckfall-Pruefung

`python3 tools/gate_wirkung.py`: **1 Gate RUECKFAELLIG** — `claim-before-cheapest-check` (gebaut 2026-08-02, blocking, Rev 9 vom 2026-09-17; 85 Vorkommen vor dem Bau, 2 danach, letzter Rueckfall 2026-09-23).

Dieselbe Ausgabe fuehrt das Gate zugleich unter „hat seinen Befund GEFANGEN (2×)". Beides trifft zu und ist kein Widerspruch: in dieser Sitzung feuerte der Hook **fuenfmal** und loeste jedes Mal eine Korrektur aus, bevor die Aussage stehen blieb — das ist der Wirksamkeits-Beleg. Befund #1 ist der Fall, den er **nicht** sah.

**Ursache: an der Quelle.** Die Aussage lautete „PR aktualisiert", im selben Zug lief ein `git push`, der fehlerfrei durchlief. Fuer die Korroboration sah das aus wie ein Beleg — der Push belegt aber nur, dass der Branch bewegt wurde, nicht dass der PR die Aenderung noch aufnimmt. Dieselbe Verwechslung wie in Rev 7 („ein Check FEUERT belegt nie, dass er SPERRT"), nur eine Ebene tiefer.

**Konsequenz: ausweiten** (eine der drei zulaessigen Antworten). Vorgeschlagene neue Trefferklasse `push-ohne-pr-zustand`: behauptet ein Zug, ein PR oder Branch sei aktualisiert/nachgezogen/ergaenzt, und lief im selben Zug ein `git push`, dann entwaffnet nur ein **danach** laufendes `gh pr view … --json state` (oder `mergedAt`/`mergeStateStatus`) die Korroboration. Ein erfolgreicher Push allein entwaffnet ausdruecklich nicht. Der Eintrag bekommt `revised: 2026-09-23` + `revision_note` — **kein zweites Gate unter neuem Namen**.

Drill-Vorschlag: Realfall als Fixture (Push 06:54:17 auf einen 06:44:52 gemergten PR) plus drei Nicht-Treffer (Push auf offenen PR mit anschliessendem `gh pr view`; Push ohne Aktualisierungs-Behauptung; Aktualisierungs-Behauptung ohne Push).

## 5b. Autonomie-Kalibrierung

`over_ask`: keine Klasse. Die einzige Vorlage war eine Dreifachfrage zu Zielorten von Mandanten- und Privatdokumenten — nicht deterministisch, nicht reversibel im Sinne der Regel, und vom Owner mit einer Praezisierung beantwortet. Kein Over-Ask.

`over_act`: keine Klasse. Jeder Prod-Schritt trug ein ausdrueckliches Owner-Wort im selben oder vorangehenden Zug: Schleuse-Sweep („40 Variante 1"), Paperless-Einlieferung („131 ja"), Prod-Read („68 go"), Secret-Datei und Host-Env („172 bis 174 go"), scharfer Belegbeschaffungs-Lauf („200 go"). Der Prod-Dispatch fuer risk-hub wurde ausdruecklich **nicht** selbst ausgeloest und liegt beim Owner.

## 6. Verankerung — kopierfertige Vorschlaege

### memory_candidates

```markdown
---
name: feedback_push_auf_gemergten_branch_geht_verloren
description: "Ein git push auf einen bereits gemergten PR-Branch laeuft fehlerfrei durch und erreicht main nie — nach jedem Push den PR-Zustand pruefen"
metadata:
  node_type: memory
  type: feedback
  rule_class: B
  drift: true
  drift_episode: 2026-09-23-konz064-korrektur-verloren
---

Ein `git push` auf einen Branch, dessen PR **schon gemergt** ist, meldet Erfolg und aendert
nichts an `main`. Realfall 2026-09-23: PR platform#3416 wurde 06:44:52 gemergt, der
Korrektur-Commit `3c394370` (Owner-Einwand zur Aufbewahrungstabelle) ging 06:54:17 auf
denselben Branch. `git merge-base --is-ancestor 3c394370 origin/main` → exit 1. Auf dem
**oeffentlichen** Repo stand danach stundenlang die vom Owner abgelehnte Fassung; gefunden
hat es erst die Retro derselben Sitzung, behoben per Cherry-pick in platform#3439.

**Why:** Der fehlerfreie Push sieht aus wie ein Beleg. Er belegt aber nur, dass der Branch
bewegt wurde — nicht, dass ihn noch jemand nach `main` bringt.

**How to apply:** Nach jedem Push auf einen PR-Branch `gh pr view <n> --json state,mergedAt`.
Ist der PR `MERGED`, braucht die Aenderung einen neuen PR (Cherry-pick), keinen weiteren Push.
Siehe [[feedback_claim_before_cheapest_check]].
```

```markdown
---
name: feedback_deutsches_closing_verb_schliesst_kein_issue
description: "GitHub schliesst Issues nur ueber englische Keywords — 'Schliesst #771' erzeugt nur eine Querreferenz"
metadata:
  node_type: memory
  type: feedback
  rule_class: B
---

GitHub wertet als Closing-Keyword ausschliesslich `close/closes/closed`, `fix/fixes/fixed`,
`resolve/resolves/resolved`. Deutsche PR-Texte sind Repo-Konvention — das **Closing-Verb**
muss davon ausgenommen bleiben. Realfall 2026-09-23: iilgmbh/risk-hub#772 („Schliesst #771")
wurde gemergt, #771 blieb OPEN; die Timeline zeigt nur `cross-referenced`, kein `closed`.

**How to apply:** Im PR-Text `Closes #<n>` schreiben (englisch), der erklaerende Satz bleibt
deutsch. Nach dem Merge einmal `gh issue view <n> --json state` — die Querreferenz sieht im
Issue genauso aus wie ein echter Schluss.
```

### adr_candidates

Keine. Die drei Gate-Kandidaten sind Hook-/Test-Aenderungen nach bestehendem Muster
(`adr-threshold.md`: reine Ergaenzung nach Muster = kein ADR).

## 7. Massnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Verlorene Korrektur nachziehen | platform | https://github.com/achimdehnert/platform/pull/3439 | 🔵 ready | mergen (du) |
| M2 | Regel-Verschattung + Anker-Bug | platform | https://github.com/achimdehnert/platform/issues/3405 | 🔵 offen | Fix-PR mit Overlap-Test (ich) |
| M3 | `paperless_zustellen` testen | platform | https://github.com/achimdehnert/platform/issues/3102 | 🔵 offen | Test mit gefaktem subprocess (ich) |
| M4 | Index vor Aufraeumschritt setzen | platform | https://github.com/achimdehnert/platform/issues/3102 | 🔵 offen | Reihenfolge drehen (ich) |
| M5 | risk-hub#771 schliessen | risk-hub | https://github.com/iilgmbh/risk-hub/issues/771 | 🔵 offen | schliessen + Ursache notieren (ich) |
| M6 | Gate ausweiten: `push-ohne-pr-zustand` | platform | https://github.com/achimdehnert/platform/issues/2234 | 🟢 offen | Owner-Wort zur Ausweitung |
| M7 | Sitzungs-ID in Branch-Namen | platform | https://github.com/achimdehnert/platform/issues/3405 | 🟢 offen | Entscheid: Schema aendern? |
| M8 | CHANGELOG-Pflicht klaeren | platform | https://github.com/achimdehnert/platform/issues/3405 | 🟢 offen | Gate oder Konvention streichen |
| M9 | Namen aus oeffentlichen Kommentaren entfernt | platform | https://github.com/achimdehnert/platform/issues/3405#issuecomment-5788463915 | ✅ done | erledigt 2026-09-23, Kontrollprobe 0 |
| M10 | Checkpoint an den Prod-Ausloeser binden | platform | https://github.com/achimdehnert/platform/issues/2234 | 🟢 offen | Owner-Wort: zweiter Ausloeser neben dem 3. Repo |

## 8. Nicht verifiziert (Restluecken)

**Getan:** `gate_wirkung.py` und `retro_kpis.py` gelaufen; drei Finder in frischem Kontext; ein Skeptiker auf die zwei Bewertungsbefunde; eine Widerlegungsbahn (Tier 4) gegen den Entwurf; Befund #1 unabhaengig per `git merge-base` nachgeprueft und noch waehrend der Retro per #3439 behoben; Befund #17 nachgeprueft (4 Namenstreffer) und redigiert, mit Kontrollprobe (0 Namen, 3 Platzhalter); der von der Widerlegungsbahn neu gemeldete USD-Vorfall gegen die Kommentar-Zeitstempel gepruefte und als Fremdsitzung verworfen; Dokumentzahl der Sitzung gegen die Prod-Datenbank gezaehlt (19 + 5 = 24, nicht 21 wie im Finder-Auftrag angegeben).

**Angenommen:** Dass die 16 ueberlebenden Befunde vollstaendig sind — drei Dimensionen plus eine Widerlegungsbahn decken nicht jede denkbare Achse ab. Dass die Zuordnung der sechs nicht zugerechneten platform-Issues des Tages zu Fremdsitzungen korrekt ist; Befund #13 beschreibt genau diese Luecke, und sie hat in dieser Retro zweimal zugeschlagen.

**Nicht verifizierbar:** Ob Paperless-ngx eine zweite Zustellung derselben Datei per Pruefsumme abweist — das entscheidet, wie schwer Befund #6 wiegt. Billigster Check: `PAPERLESS_CONSUMER_DELETE_DUPLICATES` und die Checksum-Logik im Consumer lesen. Ob der Finder-Befund zur Werkzeug-Oekonomie (293 Aufrufe) ueber die vier benannten Ketten hinaus weitere enthaelt — dafuer waere eine Volltranskript-Auswertung noetig, die Kennzahlen-Datei listet nur Fehllaeufe.

**Offen geblieben:** Der Prod-Dispatch fuer risk-hub (69 Dokumente warten), iil-assist-voice#130, die Portal-Abholung (#3426, 68 Positionen), und die Frage aus #3405, wohin die 34 verbliebenen Schleusen-Eintraege gehoeren.

## Widerlegung

Ein Subagent (Tier 4, frischer Kontext, ohne Sitzungs-Erzaehlung) hat den Entwurf gegen `origin/main` geprueft. Ergebnis: **3 gekippt, 1 neu** — zwei Urteile des Entwurfs (#12, #16) fielen, ein dritter Punkt war ein Fund des Pruefers, den ich selbst wieder kippen musste, und ein echter neuer Befund (#17) kam dazu.

Die Spalte heisst bewusst **Ergebnis der Widerlegung**, nicht „Verdikt": das binaere Verdikt SURVIVES/REFUTED steht ausschliesslich in Abschnitt 2. Hier gilt das 3b-Vokabular BESTAETIGT / GEKIPPT / NEU.

| Punkt | Ergebnis der Widerlegung | Konsequenz im Report |
|---|---|---|
| Befund #12 („Schwelle vor der Messung gesetzt") | **GEKIPPT** | #3405 nennt Messung, 10-%-Ziel und die „30" im selben Text — 291 × 10 % = 29,1. Die Zahl war abgeleitet, nicht geraten. Befund umgeschrieben auf den beweglichen Nenner |
| Befund #16 (Scope-Checkpoint) | **GEKIPPT** | Das Urteil „vollstaendig REFUTED" faellt. In Abschnitt 2 bleibt #16 binaer REFUTED fuer die Repo-Haelfte; die Prod-Haelfte ist dort ein eigener Befund #18 mit eigenem Verdikt SURVIVES |
| Befunde #1–#7, #13, #14 | **BESTAETIGT** | Je gegen `origin/main` nachgezogen, nicht gegen den Report-Text; #13 haelt „eher unterschaetzt" (28 platform-PRs des Tages aus mindestens sechs Sitzungen) |
| Befund #15 (Audit-Trail) | **BESTAETIGT** | risk-hub `documents_document` = 0, `PAPERLESS_*` im Container 0 von 54 — ein Import kann nicht stattgefunden haben |
| `pre_refuted` | **BESTAETIGT** | Ergebnis richtig, aber die Begruendung war unbelegt; ausgetauscht gegen die Fremdsitzungs-Erklaerung |
| NEU: Personendaten im oeffentlichen Repo | **NEU** | Nachgeprueft: 4 Namenstreffer. Als Befund #17 aufgenommen und noch waehrend der Retro redigiert |
| NEU: USD-Belege doppelt umgerechnet | **GEKIPPT** | Der Beleg ist ein #3102-Kommentar von 10:50:54 — er gehoert zu einem `/rechnungsstrecke`-Lauf einer **anderen** Sitzung. Diese Sitzung hat die Rechnungsstrecke nie aufgerufen; ihr letzter #3102-Kommentar ist 09:47:22. Nicht als Befund aufgenommen |

Der letzte Punkt ist der lehrreichste: die Widerlegungsbahn hat fremde Arbeit dieser Sitzung zugerechnet — genau wie zuvor schon der Finder „Soll-Ist & Scope". Damit hat **Befund #13 sich selbst zweimal bewiesen**: ohne Sitzungs-ID im Artefakt ist die Zurechnung bei parallelen Sitzungen nicht verlaesslich, und zwar auch dann nicht, wenn ein sorgfaeltiger Pruefer mit `gh`-Zugriff hinsieht.

## Self-Review

Ein Meta-Agent hat den Report gegen die Skill-Regeln geprueft (nicht die Sitzung). Er bestaetigte Buchhaltung (16 + 2 + 1 = 19), Soll-Ablauf-Invariante (16 Zeilen, Befunde 1–14, 17, 18, keine doppelt), eingefrorene Spalten, Abschnittsreihenfolge, Vierklang in §8, §5a-Konsequenz und Streichbahn-Belegart. Fuenf Formfehler hat er gefunden, alle behoben: sieben statt fuenf Summary-Bullets, zwei Scores ohne Befund-Anker, „HALBIERT" als drittes Verdikt in der Widerlegungs-Tabelle, fehlende Einordnung der `refuted_rate`, und fuenf Beleg-Zellen ohne Kommando oder Zeilennummer.

**`refuted_rate` = 0,16 — unterhalb des Bandes (<0,2 ⇒ „Falsifikation ist Theater").** Die Einordnung, die die Regel verlangt: die Zahl ist hier nicht Theater, sondern Folge der Klassen-Sortierung aus Phase 0.1. Von 19 Befunden waren 16 **kommandobelegt** (Regex-Repro, `git merge-base`, `grep`, `gh api`) — fuer die sieht die Skill ausdruecklich **keinen** Skeptiker vor, weil ein zweiter Lauf dieselbe Zahl liefert. Der Skeptiker lief auf die drei Bewertungsbefunde und verwarf davon **zwei**; die echte Falsifikations-Quote auf dem Material, das ueberhaupt falsifizierbar war, betraegt also 2 von 3. Zusaetzlich kippte die Widerlegungsbahn zwei weitere Urteile (#12, #16) und ich selbst einen ihrer eigenen Funde. Der niedrige Gesamtwert entsteht durch den grossen Anteil mechanisch pruefbarer Befunde, nicht durch milde Pruefung.

## Streichbahn

**Kandidat: `retro-phase-2.5-finder-konflikt-erkennung`** — Belegart **kein Effekt**.

Phase 2.5 verlangt einen eigenen Durchgang, der Finder-Outputs auf widersprechende Fakt-Behauptungen ueber dasselbe Artefakt scannt und jeden Widerspruch als zusaetzlichen Skeptiker-Task routet. In dieser Retro trat kein einziger Widerspruch zwischen den drei Findern auf — sie berichteten ueber disjunkte Artefaktmengen (Commits/Diffs · Issue-Zustaende · Transkript-Kennzahlen). Die beiden verworfenen Befunde fielen nicht durch einen Finder-Konflikt auf, sondern durch die regulaere Skeptiker-Runde in Phase 3, die ohnehin laeuft.

Das ist ein Kandidat, kein Beschluss: eine einzelne Retro ohne Konflikt belegt nicht, dass Konflikte nie auftreten. Nach der Ratschen-Regel wird der Kandidat hier notiert; taucht er in der naechsten Retro desselben Scopes erneut auf, ohne gestrichen zu sein, ist das selbst ein Befund.
