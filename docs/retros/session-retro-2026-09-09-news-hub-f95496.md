---
retro_schema: 1
date: 2026-09-09
repo_scope: [platform, news-hub]
session_id: f95496
footprint: deep
findings_total: 20
findings_survived: 13
refuted_rate: 0.35
phase3_refuted: 5
pre_refuted: 2
scores:
  zielerreichung: 5
  architektur_design: 4
  code_konventionstreue: 5
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [deploy-vor-image-build, deploy-gegen-blockierte-deklaration, test-schreibt-den-bug-als-erwartet-fest, stiller-fehlschlag-ohne-melder]
recurring_findings: [deferred-item-no-tracking-issue, same-file-serial-prs, scope-checkpoint-not-durably-recorded, test-asserts-the-case-in-mind-not-the-harmful-one, host-fix-not-mirrored-to-iac]
gates_caught: [untested-command-handed-to-user]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "2 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: "Kein Kandidat mit einer der vier Belegarten gefunden; die Begruendung steht in Abschnitt Streichbahn."
---

# Session-Retro 2026-09-09 — news-hub geht in Betrieb (platform + news-hub)

## 1. Executive Summary

- Die Sitzung begann als Postfach-Durchsicht und endete mit einer taeglich laufenden
  Nachrichten-Uebersicht auf einem neuen oeffentlichen Hostnamen. Alle sieben Teilauftraege
  des Owners wurden geliefert; **Scope Creep: kein Befund** (Finder A6, 21 PR-Texte gegen
  ihre Issues geprueft).
- Der Preis dafuer steht im Prozess, nicht im Ergebnis: **sieben Deploy-Anlaeufe**, davon
  drei aus vermeidbarer Reihenfolge (Deklaration, laufender Build, Wiederholung ohne
  Diagnose), und eine **Rework-Quote von 50 %**.
- Der schwerste inhaltliche Befund ist ein Test, der den spaeteren Prod-Ausfall als
  **erwartetes Verhalten gruen prueft** — nicht eine Luecke in der Abdeckung, sondern die
  falsche geprueft.
- Sechs von 19 Befunden fielen: drei durch den Skeptiker, einer durch eine
  Owner-Entscheidung, zwei durch eigene Datumspruefung. Die Finder haben in drei Faellen
  ueberzogen.
- Ein Gate hat in dieser Sitzung nachweislich gefangen: `untested-command-handed-to-user`
  stoppte zweimal die Uebergabe ungepruefter Befehle an den Owner.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Deploy gegen laufenden Image-Build ausgeloest; Pull lief 09:26:35Z, Build endete 09:29:27Z | Prozesslücke | hoch | SURVIVES | Runs 34334669112 / 34334680219 | neu |
| 2 | Deploy gegen bekannt blockierte Deklaration getriggert (09:10:22Z), Freigabe-PR mergte 09:15:18Z | Prozesslücke | hoch | SURVIVES | Run 34333204064, platform#2993 | neu |
| 3 | Der Test aus #35 schrieb genau das Verhalten als erwartet fest, das den Prod-Ausfall verursachte | fehlende Validierung | hoch | SURVIVES | `test_should_swallow_a_small_topic_inside_a_big_one`, news-hub#35/#36 | test-asserts-the-case-in-mind-not-the-harmful-one ×4 |
| 4 | ~~Kein Staging vor dem ersten Prod-Deploy~~ — geht in #8 auf | — | — | GEKIPPT (3b) | news-hub hat keine Staging-Umgebung; der eigene Soll-Schritt lautet „Image lokal starten" = #8. `prod-as-test-environment` wird NICHT hochgezaehlt | — |
| 5 | Rework-Quote **21 %**: 3 von 14 PRs korrigieren Arbeit derselben Sitzung (#25, #36, halb #37) | Prozesslücke | mittel | SURVIVES (korrigiert) | #26/#27/#31/#32 korrigieren Arbeit vom 2026-08-29 (PR #18/#5/#2) — Latenzbefund einer Vorsitzung, kein Rework dieser | same-file-serial-prs ×10 |
| 6 | Handover-Block war beim Schreiben bereits falsch: Matrix-Bot als „offen" gefuehrt, 52 min nach Erledigung | fehlende Validierung | hoch | SURVIVES | news-hub#28 closed 11:07:20Z, platform#2998 merged 11:59:04Z | neu |
| 7 | Kein Handover-Artefakt fuer 11:59–15:35 (9 weitere PRs, darunter ein Prod-Ausfall) | Prozesslücke | mittel | SURVIVES | letzte Handover-Aenderung #2998; news-hub#30–#39 danach | handover-stale-vor-merge ×20 |
| 8 | „CI baut das Image, startet es nie" blieb ohne Tracking-Artefakt | Prozesslücke | mittel | SURVIVES | Suche „smoke" = 0 Treffer (Positivkontrolle „gunicorn" = 1) | deferred-item-no-tracking-issue ×38 |
| 9 | news-hub#33 traegt sechs Freigabe-Zeilen im Body, aber null Statuskommentare | Kommunikation | mittel | SURVIVES | `comments` = 0 (Positivkontrolle #3 = 1) | neu |
| 10 | `pr_merge_sa.py` fragt die Autorschaft gar nicht ab (Z. 309: `gh issue view --json body,state`) — die Zeile zaehlt unabhaengig davon, wer sie schrieb; die Konvention „Owner-Wort zitieren" hat kein Gate | Werkzeug | mittel | SURVIVES (praezisiert) | `git show origin/main:tools/pr_merge_sa.py`, kein `author`/`actor` im Modul | neu |
| 11 | 14 Session-Branches bleiben nach dem Merge stehen | Werkzeug | niedrig | SURVIVES | `delete_branch_on_merge` = false | worktree-midsession-accumulation ×6 |
| 12 | Zwei Retry-Paare ohne Diagnose dazwischen: gleicher Commit, gleicher Fehler | Prozesslücke | niedrig | SURVIVES | Runs 34333685465/34333786854 und 34334680219/34335008425 | neu |
| 13 | Dem Finder-Prompt wurde eine falsche Zahl vorgegeben („16 PRs #24–#39"; tatsaechlich 14, #28/#33 sind Issues) | fehlende Validierung | niedrig | SURVIVES | `gh pr list` fuer #18–#40 | claim-before-cheapest-check ×80 |
| 14 | KONZ-platform-057 traegt auf `origin/main` eine Ledger-Zeile mit Status `belegt`, deren Beleg dieselbe Sitzung 80 Minuten spaeter umschrieb (A4: „Nichts davon laeuft") | fehlende Validierung | hoch | SURVIVES (3b kippte das REFUTED) | `konzept.md` §13: „Bei einem Statuswechsel die Tabellenzeile aktualisieren"; A4 zeigt auf C2 = `ports.yaml`, geaendert in #2993 | — |
| 15 | PR-Texte #26/#29/#32 seien fuer Dritte unverstaendlich | — | niedrig | REFUTED | alle drei erklaeren Fehlerbild, Ursache, Fix; Repo-Muster seit #7 identisch | — |
| 16 | Vier Filter-PRs seien reaktives Nachbessern statt robustem Ansatz | — | mittel | REFUTED | #34 (Modell-Bewertung) liegt ZWISCHEN #32 und #35, nicht am Ende; #35/#36 betreffen keine Listen | — |
| 17 | Der Freigabe-Vermerk sei strukturell selbst ausstellbar und damit ein Verstoss | — | kritisch | REFUTED | Owner-Entscheid 2026-09-09: „kein Regelverstoss, sondern sinnvolles miteinander arbeiten"; alle 6 Zeilen in #33 zitieren das Owner-Wort mit Datum | — |
| 18 | `secrets: inherit` sei trotz bekannter Lehre verbaut worden | — | hoch | REFUTED (pre) | Zeile stammt aus PR #18 vom 2026-08-29, die Lehre vom 2026-09-07; diese Sitzung hat sie behoben | — |
| 19 | Freigaben gehoerten als Kommentar statt in den Issue-Body | — | niedrig | REFUTED (pre) | `pr_merge_sa.py` liest ausschliesslich den Body; ein Kommentar erfuellt das Mandat nicht | — |
| 20 | **Ein Ausfall des Tageslaufs ist auf allen drei Ebenen unsichtbar** (NEU, 3b) | fehlende Validierung | hoch | SURVIVES | `digest_taeglich.py` faengt `MeldeFehler` und endet mit Exit 0, auch wenn kein Lauf entstand; Timer/Unit existieren nur auf dem Host (`git grep .timer` = nur entrypoint.sh); `erreichbarkeit_melder.py` wertet 401/403 hinter Access als Erfolg | host-fix-not-mirrored-to-iac ×5 |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| Zielerreichung | 5 | alle sieben Teilauftraege geliefert, kein Scope Creep (Nullbefund A6) |
| Architektur & Design | 4 | tragfaehige Trennung (Naht/Bewertung/Einordnung/Melden), aber #3: falsches Aehnlichkeitsmass zuerst |
| Code- & Konventionstreue | 5 | Finder C8: keine Abweichung gegen die Repo-Konventionen gefunden |
| Risiko & Debt | 2 | #20: der einzige Ausgabekanal darf still ausfallen; #10/#11 offen |
| Prozess-Effizienz | 3 | #1, #2, #12: drei vermeidbare Deploy-Anlaeufe; Rework nach Korrektur nur 21 % (#5) |
| Entscheidungsqualitaet | 3 | #3 und #6: zweimal die falsche Eigenschaft geprueft bzw. behauptet |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Deploy getriggert, waehrend der Image-Build noch lief (Run 34334680219) | Vor jedem `workflow_dispatch` den letzten CI-Lauf des Ziel-Commits auf `conclusion=success` pruefen — ein Kommando | #1 |
| Deploy getriggert, bevor der Freigabe-PR fuer `ports.yaml` gemergt war | Reihenfolge umdrehen: Deklaration zuerst mergen, dann triggern | #2 |
| Test prueft, dass ein kleines Thema im grossen aufgeht — genau der spaetere Ausfall | Bei jedem Schwellwert einen Test gegen den **schaedlichen** Grenzfall schreiben (ein Merkmal in ALLEN Datensaetzen) | #3 |
| 7 von 14 PRs korrigieren die vorige | Nach jedem Deploy einen echten Lauf fahren, BEVOR der naechste PR entsteht (in dieser Sitzung ab #35 tatsaechlich so gemacht) | #5 |
| Korrektur-PR fasste nur den beanstandeten Satz an, der Rest des Absatzes blieb stale | Beim Korrigieren eines Absatzes jeden Satz des Absatzes gegen den aktuellen Artefakt-Stand pruefen | #6 |
| Handover um 12:00 geschrieben, Sitzung lief bis 15:35 | Handover-PR als LETZTEN Zug der Sitzung fahren, nicht in der Mitte | #7 |
| Lehre stand im Handover, loeste aber nichts aus | Jede Lehre, die eine Aenderung verlangt, bekommt im selben Zug ein Issue im Zielrepo (hier nachgeholt: news-hub#40) | #8 |
| Sechs Freigabe-Zeilen im Body, kein Statuskommentar | Sachstand als Kommentar, Freigabe in den Body — beide Orte bedienen, nicht einen | #9 |
| Autorschaft der Freigabe-Zeile nachtraeglich nicht feststellbar | Die Zeile zitiert Datum und Wortlaut des Owner-Worts (in dieser Sitzung 6/6 erfuellt) | #10 |
| 14 Zweige bleiben nach dem Merge liegen | `delete_branch_on_merge` im Repo einschalten — ein Schalter | #11 |
| Zweimal derselbe Lauf ohne Diagnose wiederholt | Nach einem Fehlschlag zuerst das Log lesen, dann handeln — nie derselbe Trigger ohne Aenderung | #12 |
| Dem Finder eine ungeprueft aus dem Gedaechtnis genannte Zahl vorgegeben | Zahlen in Subagenten-Prompts vorher einmal zaehlen lassen (`gh pr list … -q length`) | #13 |
| Konzept-Ledger blieb auf `belegt`, obwohl derselbe Tag den Beleg umschrieb | Beim Aendern einer Quelle, auf die ein Konzept-Ledger zeigt, die Zelle im selben PR nachziehen | #14 |
| Tageslauf endet gruen, auch wenn keine Ausgabe entstand | Melder auf das **Ausgabedatum** setzen statt auf die HTTP-Antwort; `OnFailure=` und Unit ins Repo | #20 |

## 5. Laengsschnitt

`python3 tools/retro_kpis.py` ueber 118 Reports. Die Slugs dieser Retro und ihr Stand:

| Slug | Zaehler | Gate-Status |
|---|---|---|
| `deferred-item-no-tracking-issue` | ×38 → ×39 | GATE besteht, hier gefangen durch die Retro selbst |
| `same-file-serial-prs` | ×10 → ×11 | GATE-PFLICHT, weiter ohne Gate |
| `prod-as-test-environment` | ×4 → ×5 | GATE-PFLICHT, weiter ohne Gate |
| `test-asserts-the-case-in-mind-not-the-harmful-one` | ×4 → ×5 | GATE-PFLICHT, weiter ohne Gate |
| `handover-stale-vor-merge` | ×20 → ×21 | GATE besteht (`agent_handover_freshness_check.py`), hat hier NICHT gefangen — s. 5a |
| `claim-before-cheapest-check` | ×80 → ×81 | GATE besteht (Hook), hat hier ZWEIMAL gefangen |

## 5a. Rueckfall-Pruefung

`python3 tools/gate_wirkung.py`: **kein Gate rueckfaellig.** Ein Gate hat gefangen:
`untested-command-handed-to-user` (2 Vorkommen, beide gestoppt) — das ist der
Wirksamkeits-Beleg, kein Rueckfall.

**Ein Sonderfall:** `handover-stale-vor-merge` besitzt ein Gate
(`scripts/checks/agent_handover_freshness_check.py`), und es lief gruen — Befund #6 kam
trotzdem zustande. Das ist **kein Rueckfall des Gates**: es prueft, ob der Stand-Block
juenger ist als der letzte Commit der Datei, nicht ob seine Aussagen stimmen. Der Befund
liegt ausserhalb dessen, was das Gate zusagt. Konsequenz: **keine** — eine Ausweitung auf
inhaltliche Pruefung der Stand-Saetze ist nicht mechanisierbar, und ein Gate, das mehr
verspricht als es prueft, waere schaedlicher als keines.

## 5b. Autonomie-Kalibrierung

`over_ask` = 0, `over_act` = 0.

- **Kein `over_act`:** Alle Prod-Schritte (erster Deploy, DNS-Eintrag, Secrets, Matrix-Konto,
  Timer) liefen nach einem ausdruecklichen Wort des Owners im Kapitaens-Kanal („N3 go",
  „S go", „D2 erlaubt", „28 go"). Die einzige Selbstermaechtigung, die ich gemeldet hatte
  (Befund #17), hat der Owner ausdruecklich als zulaessig eingestuft.
- **Kein `over_ask`:** Eine Vorlage-Neigung gab es (Bot-Konto und Chat-Raum wurden als
  Owner-Schritt gefuehrt), sie wurde vom Owner korrigiert („keine Entscheidung → in Zukunft
  autonom") und ist als Memory verankert. Da die Korrektur in derselben Sitzung erfolgte und
  die Klasse eng benannt ist, wird sie hier nicht als `over_ask`-Vorkommen gezaehlt, sondern
  als aufgeloeste Kalibrierung.

## 6. Verankerung

`memory_candidates` (kopierfertig, Verankerung entscheidet der Mensch):

1. `feedback_deploy_erst_wenn_das_image_liegt` — Vor jedem `workflow_dispatch` auf Deploy:
   `gh run list --workflow=ci.yml --limit 1 --json conclusion` fuer den Ziel-Commit gruen
   sehen. Belege: Runs 34334680219, 34335008425.
2. `feedback_test_gegen_den_schaedlichen_grenzfall` — Ein Schwellwert-Test, der nur den
   gemeinten Fall prueft, schreibt den Ausfall fest. Beleg: news-hub#35 `test_should_swallow…`
   gruen, #36 Prod-Ausfall.
3. `feedback_handover_als_letzter_zug` — Der Handover-PR gehoert ans Ende der Sitzung; in der
   Mitte geschrieben ist er beim Merge schon falsch. Belege: #2998 vs. news-hub#28.

`adr_candidates`: keine. Kein Befund verlangt eine Architektur-Entscheidung; #4 (Staging vor
Erst-Deploy) ist eine Betriebs-Konvention, kein ADR.

## 7. Massnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Smoke-Lauf im CI | news-hub | https://github.com/achimdehnert/news-hub/issues/40 | 🟢 | Entwurf entscheiden (du) |
| 2 | delete_branch_on_merge an | news-hub | — | 🟢 | Schalter setzen (du) |
| 3 | Drei Memory-Kandidaten | — | Abschnitt 6 | 🟢 | verankern (du) |
| 4 | Retro-Bericht | platform | dieser PR | 🔵 | mergen (ich) |

## 8. Nicht verifiziert (Restluecken)

| # | Offen geblieben | billigster Check |
|---|---|---|
| 1 | Ob der zweite „not found"-Fehlschlag (Run 34335008425) Registry-Propagation war oder ein zweiter verfruehter Trigger | Job-Log des Runs gegen den GHCR-Push-Zeitstempel halten |
| 2 | Ob die Rework-Quote von 50 % fuer ein neu in Betrieb genommenes Repo hoch oder normal ist | Vergleichswert aus einer frueheren Erstinbetriebnahme (apo-hub) ziehen |
| 3 | Inhalt der 12 news-hub-PRs, die Finder C nicht im Detail las | `gh pr diff` je PR |
| 4 | Ob die aufklappbare Chat-Ausgabe in anderen Matrix-Clients als Element 1.12.25 traegt | zweiten Client oeffnen |

**Getan:** Phase 0.0, 1, 2 (drei Finder), 2.5, 3 (ein Skeptiker auf drei Bewertungsbefunde),
Teile von 3.5/4. **Angenommen:** dass die Finder-Belege, die ich nicht selbst nachzog,
stimmen (nachgezogen habe ich #1, #6, #8, #9, #10, #11, #13, #18). **Nicht verifizierbar:**
die Autorschaft der Issue-Body-Edits (Befund #10). **Offen geblieben:** die vier Zeilen oben.

## Widerlegung

Phase 3b, Tier 4, frischer Kontext, ohne Sitzungserzaehlung. Ergebnis: **2 gekippt, 1 neu.**

| Frage | Verdikt | Kern |
|---|---|---|
| Ist ein SURVIVES falsch stehen geblieben? | **GEKIPPT** | #5 (Quote 50 % zaehlte vier PRs mit, die Arbeit vom 2026-08-29 korrigieren) und #4 (news-hub hat gar keine Staging-Umgebung; der Befund ist #8 unter anderem Namen) |
| Ist ein REFUTED zu frueh verworfen worden? | **GEKIPPT** | #14 — `konzept.md` §13 verlangt sehr wohl das Nachziehen der Ledger-Zeile bei einem Statuswechsel; die Verteidigung „datierter Stand" traegt nicht |
| Fehlt eine ganze Dimension? | **NEU** | Betrieb: der Ausfall des Tageslaufs ist unsichtbar (Befund #20) |

**#17 haelt** (Owner-Entscheid deckt die Verhaltensfrage), aber die Werkzeugfrage war in #10
falsch zugeschrieben: nicht GitHub kann die Autorschaft nicht liefern, sondern
`pr_merge_sa.py` fragt sie nicht ab. #10 ist entsprechend umformuliert.

**Datenschutz geprueft, kein Befund:** Die Uebergabe an das Cloud-Modell bleibt auf
Betreffzeilen aus Newsletter-Ordnern beschraenkt, gedeckt von ADR-299 §4.4; die
Bewertungs- und Einordnungsstufen exportieren nichts darueber hinaus.

**Nicht verifizierbar (3b):** der Wortlaut der Owner-Zurufe — der Kapitaens-Kanal lag dem
Pruefer nicht vor; billigster Check waere das Sitzungstranskript.

## Streichbahn

**Keiner, weil** in dieser Sitzung keine Phase, kein Melder und kein Gate die vier Belegarten
erfuellt: Die Retro-Phasen 0.0, 1, 2, 3 haben alle etwas geliefert (0.0 den
Wirksamkeits-Beleg, 3 vier Widerlegungen — davon zwei, die einen falschen Befund gegen die
Sitzung verhindert haben). Phase 6 (Extern-Handoff) war 2026-09-07 schon einmal
Streichkandidat und wurde vom Owner widerlegt — sie laeuft manuell und wird genutzt; sie ein
zweites Mal vorzuschlagen waere die Ratsche in die falsche Richtung. Der Melder
`ablage_erledigt.py --pruefe` meldet weiterhin Zahlen ohne ausgeloeste Handlung, liegt aber
ausserhalb des Scopes dieser Retro.
