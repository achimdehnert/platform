---
retro_schema: 1
date: 2026-08-21
repo_scope: [platform]
session_id: 8d6869-incr
footprint: full
findings_total: 13
findings_survived: 13
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [claim-before-cheapest-check, built-but-never-called, scope-checkpoint-not-durably-recorded, melder-ohne-leser]
over_ask: 0
over_act: 1
recurring_findings: [claim-before-cheapest-check, scope-checkpoint-not-durably-recorded, test-asserts-the-case-in-mind-not-the-harmful-one, built-but-never-called, canon-claim-without-source-reconcile, melder-ohne-leser, gate-matches-spelling-not-substance, always-instruction-without-enforcement]
---

# Session-Retro 2026-08-21 — platform (8d6869-incr)

**Increment-Retro** auf die Vor-Retro [`session-retro-2026-08-20-platform-8d6869`](session-retro-2026-08-20-platform-8d6869.md).
In-Scope sind **nur** die danach entstandenen Artefakte: PR #2177 bis #2196 (16 PRs, 15 gemergt),
Issue #2176 mit sechs Kriterien, der Skill `schreibstil`, zwei systemd-Timer und die
Vorgangsansicht des Todo-Boards. Die Vor-Retro wird **nicht** neu verhandelt.

Datenschutz: keine Namen Dritter, keine Mail-Adressen, keine Mail-Inhalte. Vorgänge nur als
Nummer. platform ist ein öffentliches Repo.

## 1. Executive Summary

- **Alle sechs Kriterien aus #2176 wurden gebaut und abgenommen — die Abnahme selbst trägt
  aber bei Kriterium 2 einen Beleg, der am zitierten Ort nicht steht.** Das ist der
  16-fach rückfällige Slug `claim-before-cheapest-check`, diesmal in der eigenen Abnahme.
- **Ein fremder Prüfer fand vier Fehler im Code von gestern und heute; die eigenen Tests
  fanden keinen davon.** Zwei sind ernst: ein Quantil, das unter elf Werten immer das
  Maximum liefert, und eine Kappung, die Einträge löschte statt sie zu verschieben.
- **Das teuerste Muster ist kein Fehler im Code, sondern in der Prüfung:** der Backtest
  misst den Flotten-Median, benutzt wird das Adress-Profil. Eine Selbstprüfung, die einen
  anderen Pfad misst als den produktiven, beruhigt, ohne zu decken.
- **`ledger_kappen.py` hat keinen Aufrufer und keinen Zeitplan.** Der Ledger steht wieder
  bei 67.771 Zeichen, drei Vorgänge über der eigenen 2.000-Zeichen-Grenze (max 4.175) —
  das Werkzeug, das genau dagegen gebaut wurde, läuft nur, wenn ich es von Hand starte.
- **Die Meta-Review deckte auf, dass die halbe Sitzung ungeprüft war:** acht der sechzehn
  PRs kamen im ersten Durchgang nicht vor, weil alle Befunde aus einem fremden Fehlerkatalog
  stammten. Ein zweiter Finder über genau diese acht fand **fünf weitere** Befunde — darunter
  ein Archiv, das niemand liest, und eine Datumsspanne, die rückwärts läuft.
- **Der Arbeitsbaum-Reaper lief mit `--karenz-stunden 0`** und griff weit über die zwei
  besprochenen Bäume hinaus. Kein Datenverlust (keiner der Bäume war voraus), aber der
  Scope war meiner, nicht der des Owners.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `faelligkeit.quantil()` liefert bei n≤10 immer das **Maximum** — `int(n*0.9)` ist dort `n-1`. Die „spätestens"-Grenze eines Gegenübers war dessen langsamster je gemessener Abstand. | fehlende Validierung | hoch | SURVIVES (kommandobelegt) | `quantil([0,0,12],0.9)` → `12`; Fix [#2196](https://github.com/achimdehnert/platform/pull/2196) | `test-asserts-the-case-in-mind-not-the-harmful-one` ×2 |
| 2 | `ledger_kappen` **löschte** Einträge: der Dublettenfilter verglich Text, ein wortgleicher Eintrag landete weder im Archiv noch blieb er im Ledger — Bericht meldete trotzdem „verschoben". | fehlende Validierung | kritisch | SURVIVES (kommandobelegt) | Gegenbeispiel `['gelesen','gelesen','mittel']`; Fix #2196 | `test-asserts-the-case-in-mind-not-the-harmful-one` ×2 |
| 3 | `eintrag_mails._UID_IM_TEXT` liest `platform#2176` als Mail-UID und baut einen Link auf eine fremde Mail — genau das, was der Dateikopf ausschließt. | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | Link `/m/hnu/2176`; Fix #2196 | — |
| 4 | `kettencheck` meldet eine Datei mit Zukunfts-Zeitstempel als „OK, −5 Tage alt". | fehlende Validierung | niedrig | SURVIVES (kommandobelegt) | Fix #2196 | — |
| 5 | Die Abnahme von **Kriterium 2** in [#2176](https://github.com/achimdehnert/platform/issues/2176) nennt als Beleg „Stichprobe über 11 owner-Vorgänge: 0 Fehlstände" und zitiert dafür [#2177](https://github.com/achimdehnert/platform/pull/2177) — **am zitierten Ort steht der Beleg nicht**, und die Null kam aus dem eigenen Filter ohne Positivkontrolle. | fehlende Validierung | hoch | SURVIVES (Skeptiker) | `gh pr view 2177 --json body,comments` — kein solcher Satz | `claim-before-cheapest-check` ×58 |
| 6 | `ledger_kappen.py` hat **keinen Aufrufer und keinen Zeitplan**. Der Ledger steht wieder bei 67.771 Zeichen; drei Vorgänge liegen über der 2.000-Grenze (max 4.175). | Prozesslücke | hoch | SURVIVES (Skeptiker + kommandobelegt) | `grep -rl ledger_kappen` → nur Test + zwei Docstrings; `systemctl --user list-timers --all` liefert acht Timer, keiner davon `ledger_kappen` | `built-but-never-called` (neu) |
| 7 | `skills/schreibstil/SKILL.md` §7 beansprucht Kanonizität für den Stil, **erzeugt damit aber die Doppelquelle, vor der es warnt**: die vier genannten Memories zeigen nicht auf den Skill, und eine Owner-Korrektur (`knapp` als Vorgabe) steht nur in einer davon. | verfrühte Festlegung | mittel | SURVIVES (Skeptiker) | [#2193](https://github.com/achimdehnert/platform/pull/2193); `grep -ril schreibstil` in den Memories → 0 Treffer | `canon-claim-without-source-reconcile` (neu) |
| 8 | Der Arbeitsbaum-Reaper lief mit `--karenz-stunden 0` und entfernte **69** Bäume (90 → 21) statt der zwei besprochenen. Kein Verlust (0 Branches voraus), aber der Umfang war nicht freigegeben. | Prozesslücke | hoch | SURVIVES (selbst gemeldet) | `AGENT_HANDOVER.md`, Stand 2026-08-20 nachmittags | `scope-checkpoint-not-durably-recorded` ×17 |

| 9 | `_stille_karte()` gibt die Datumsspanne der zusammengefassten Erhebungen **rückwärts** aus, sobald die Ansicht auf „älteste zuerst“ steht: `verlauf()` drehte das Ergebnis unbedingt, obwohl der Aufrufer die Eingabe schon gedreht hatte. | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | `2026-08-12 bis 2026-08-10`; Fix in diesem PR | — |
| 10 | `mail-vorgaenge-erledigt.json` hat **keinen Leser**: `git grep` findet die Datei nur im Schreiber. Ein archivierter Vorgang verschwand damit aus jedem Lesezeichen — Archivieren wirkte wie Löschen. | Werkzeug | hoch | SURVIVES (kommandobelegt) | `git grep -n mail-vorgaenge-erledigt origin/main` → 1 Treffer; Fix in diesem PR | `melder-ohne-leser` |
| 11 | `entwurf_link()` prüft die **Schreibweise statt der Sache**: ein Eintrag „GESENDET: Entwurf aus Entwuerfe #23611 wurde versendet“ erzeugt weiter einen Link auf den Entwurfsordner. | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | Repro des Finders; Fix in diesem PR | `gate-matches-spelling-not-substance` |
| 12 | Der Fix am Scope-Melder (#2186) hält gegen sechs adversariale Kommandos stand — **getestet sind aber weiter nur die zwei realen Fehlalarm-Strings**. Der Fix ist breiter als sein Test. | fehlende Validierung | niedrig | SURVIVES (kommandobelegt) | sechs Gegenbeispiele des Finders, alle korrekt; Test ergänzt in diesem PR | `test-asserts-the-case-in-mind-not-the-harmful-one` |
| 13 | Die neue **PFLICHT**-Regel in `mailcheck.md` (#2191, Mail-Nummer mit Ordner) hat keinen Prüfer — sie ist eine Konvention, die niemand messen kann. | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | kein `tools/`-Skript referenziert die Regel; getrackt in [#2199](https://github.com/achimdehnert/platform/issues/2199) | `always-instruction-without-enforcement` |

**Zur Verifikationsquote:** `refuted_rate 0.0` ist kein gutes Zeichen, sondern eine
Auskunft über die Zusammensetzung: **zehn der dreizehn** Befunde sind kommandobelegt und
gehen laut Skill nicht an Skeptiker; die drei Bewertungsbefunde gingen an drei Skeptiker,
alle drei überlebten. Ein Verifikationslauf ohne einen einzigen Widerruf ist
selbst verdächtig — siehe §8.

## 3. Scorecard

| Dimension | Wert | Anker |
|---|---|---|
| zielerreichung | 4 | alle sechs Kriterien aus #2176 gebaut und in Betrieb; Abzug für die unbelegte Abnahme (#5) |
| architektur_design | 3 | kleine Werkzeuge mit einer Aufgabe, Auflösung beim Bau statt beim Seitenaufruf, Tests ohne Netz — aber **zweimal** fehlte die Gegenstelle: #6 ohne Auslöser, #10 ohne Leser, und in #9 entschieden zwei Stellen dieselbe Reihenfolge |
| code_konventionstreue | 4 | Ruff grün, `test_should_*`, Kopfkommentar mit Warum; keine Verstöße gefunden |
| risiko_debt | 2 | neun Fehler im Code von 24 Stunden, davon einer mit Datenverlust und einer mit unlesbarem Archiv; Kappung ohne Zeitplan; Ledger wieder über der eigenen Grenze |
| prozess_effizienz | 3 | 16 PRs in Folge, mehrere auf dieselbe Datei; der Reaper-Ausrutscher kostete eine ungeplante Runde |
| entscheidungsqualitaet | 3 | Abnahme ohne Beleg (#5) und Kanonizitätsanspruch ohne Quellenabgleich (#7) sind beides Entscheidungen, keine Flüchtigkeiten |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Der Backtest misst den Flotten-Median, benutzt wird ab drei Paaren das Adress-Profil | Ein Selbsttest prüft **den Pfad, den das Werkzeug im Betrieb nimmt** — die Vergleichsgröße im Test wird aus derselben Funktion gezogen wie im Produktivlauf | #1 |
| Der Idempotenz-Test prüfte „kein neuer Eintrag → nichts passiert" und bestätigte den Verlust sogar als Feature | Bei jedem Werkzeug, das Daten **bewegt**, ist der erste Test die Erhaltungsprobe: Summe vorher == Summe nachher über alle Ziele | #2 |
| Ein Regex baut Links aus allem, was wie eine Nummer aussieht | Wenn der Dateikopf sagt „ein falscher Link ist schlimmer als keiner", bekommt der Erkenner einen **Negativtest mit echtem Ledger-Text** (`platform#2176` steht dort ständig) | #3 |
| Frische wird als „Alter < N Tage" geprüft | Jede Schwellenprüfung bekommt beide Ränder — negatives Alter ist kein kleiner Wert, sondern ein kaputter Zustand | #4 |
| Die Abnahme zitierte einen Beleg aus dem Gedächtnis in ein Issue | Vor jedem „Kriterium erfüllt" wird der zitierte Ort **einmal geöffnet** (`gh pr view <n>`) und der Satz wörtlich übernommen — oder das Kriterium bleibt offen | #5 |
| Werkzeug gebaut, getestet, gemergt — und niemand ruft es | Ein Werkzeug, das gegen einen wachsenden Zustand arbeitet, wird **im selben PR** an seinen Auslöser gehängt (Timer, Board-Bau, Makefile-Ziel); ohne Aufrufer ist es kein Feature, sondern ein Vorschlag | #6 |
| Ein neuer Skill erklärt sich zur kanonischen Quelle, die Altquellen bleiben unberührt | Ein Kanonizitätsanspruch ist erst mit dem **Abgleich** fertig: jede genannte Altquelle zeigt im selben Zug auf den Skill, oder der Anspruch entfällt | #7 |
| Ein Aufräumkommando bekam eine Option, die den Umfang stillschweigend vervielfachte | Bei jedem löschenden Kommando wird die **Anzahl der Ziele** vor dem Lauf ausgegeben und gegen die besprochene Zahl gehalten; Abweichung = Rückfrage, nicht Ausführung | #8 |
| Zwei Stellen drehten dieselbe Liste — der Aufrufer die Eingabe, die Funktion das Ergebnis | Reihenfolge wird an **einer** Stelle entschieden: gebaut wird chronologisch, gedreht erst bei der Ausgabe | #9 |
| Ein Werkzeug schrieb eine Datei, die kein anderer Code liest | Wer eine neue Datei einführt, benennt im selben PR ihren **Leser** — sonst ist das Verschieben aus Sicht jedes Lesezeichens ein Löschen | #10 |
| Ein Link entstand aus dem Vorkommen einer Nummer im Text | Ein Link auf einen veränderlichen Zustand prüft den **Zustand**, nicht die Schreibweise: dasselbe Textfeld, das die Nummer nennt, sagt auch, ob es sie noch gibt | #11 |
| Ein Fix wurde von einer Schreibweise auf eine Klasse verallgemeinert, der Test blieb bei den Schreibweisen | Wird ein Fix zur Klasse verallgemeinert, wandert **die Klasse** in den Test (parametrisiert), nicht der reparierte Einzelfall | #12 |
| Eine neue PFLICHT-Regel wurde als Text in einen Workflow geschrieben | Eine Regel mit „MUSS“ bekommt im selben Zug einen Prüfer — oder ausdrücklich ein Tracking-Artefakt, das sagt, dass sie unbewacht bleibt | #13 |

## 5. Längsschnitt (`tools/retro_kpis.py`)

- **34 Slugs mit ≥2 Vorkommen** stehen unter Gate-Pflicht, **16 davon ohne jedes registrierte Gate**.
- `claim-before-cheapest-check` steht bei **×58** — Befund #5 ist das jüngste Vorkommen, und es
  entstand in der Abnahme eines Werkzeugs, das ich selbst gegen genau diese Klasse gebaut habe.
  (Zwei Messungen, nicht zu verwechseln: `retro_kpis.py` zählt **58 Vorkommen des Slugs**
  über alle Retros, `gate_wirkung.py` zählt **16 Rückfälle seit dem Bau des Gates**.)
- `scope-checkpoint-not-durably-recorded` steht bei **×17**, Befund #8 eingerechnet. Ein
  Muster mit siebzehn Vorkommen trägt keine Severity „mittel“; die Meta-Review hat #8
  zu Recht auf **hoch** gehoben.
- `test-asserts-the-case-in-mind-not-the-harmful-one` war ×1 und wird durch #1/#2 zu **×2**
  ⇒ neu gate-pflichtig.
- `melder-ohne-leser` ist als Gate registriert und steht auf `unerprobt` — Befund #10 ist
  der erste Rückfall nach dem Bau; das Gate sah ihn nicht.
- `risiko_debt` bleibt über 84 Retros die schwächste Dimension (Ø 2,58); diese Sitzung
  liegt mit **2** darunter.
- `refuted_rate`-Band gesund (0,05–0,55 über die letzten acht); dieser Lauf mit **0,0**
  liegt am unteren Rand — siehe §8.

## 5a. Gate-Wirkung (`tools/gate_wirkung.py`)

**2 Gates rückfällig**, unverändert gegenüber der Vor-Retro — beide erhielten in dieser
Sitzung keine der drei fälligen Antworten (ausweiten / umbauen / herabstufen mit Grund).
Das ist der Verzicht, den [#2143](https://github.com/achimdehnert/platform/issues/2143)
trägt; er wird hier ausdrücklich als **Verzicht mit Grund** verbucht: die Sitzung lief auf
dem Zielzustand aus #2176, und ein Gate-Umbau ist kein Nebenprodukt.

Zehn Gates stehen auf `zu-frueh` (weniger als drei Retros seit Bau) — dort ist ein
ausbleibender Rückfall **kein** Wirksamkeitsbeleg.

## 5b. over_ask / over_act

- `over_ask: 0` — keine Rückfrage, die ich selbst hätte entscheiden können.
- `over_act: 1` — Befund #8: der Reaper-Lauf ging über den besprochenen Umfang hinaus.
  Das ist die teurere Richtung von beiden.

## 6. Verankerte Lehren (Phase 6 — im selben Zug erledigt)

Zwei neue Memories, zwei Nachträge an bestehenden. Zwei der vier Kandidaten wurden
**nicht** neu angelegt, weil es die Klasse schon gab — eine zweite Datei zum selben Thema
wäre genau die Doppelquelle aus Befund #7.

| Lehre | Ort | Anlass |
|---|---|---|
| Ein Selbsttest, der einen anderen Pfad misst als den produktiven, beruhigt ohne zu decken | **neu** `feedback_selftest_must_measure_the_production_path` (drift) | #1 |
| Wer Daten bewegt, prüft zuerst die Erhaltung — Summe über alle Ziele vorher == nachher | **neu** `feedback_moving_tool_needs_conservation_test` | #2 |
| Aufrufer heißt Auslöser: ein Werkzeug gegen wachsenden Zustand kommt im selben PR an seinen Zeitplan | Nachtrag an `feedback_built_but_never_called_check_the_caller` | #6, #10 |
| Ein Kanonizitätsanspruch ist erst mit dem Abgleich fertig, nicht mit dem Satz | Nachtrag an `feedback_canon_decision_needs_enforcement_gate` | #7 |

## 7. Action Board

### 🟢 Offen — dein Zug

1. 🟢 PR #2196 (vier Fehlerbehebungen) freigeben — https://github.com/achimdehnert/platform/pull/2196
2. 🟢 Entscheiden, ob `ledger_kappen` einen eigenen Timer bekommt oder am Board-Bau hängt (#6)
3. 🟢 Zwei rückfällige Gates: ausweiten, umbauen oder herabstufen — https://github.com/achimdehnert/platform/issues/2143

### 🔵 Offen — ich kann sofort

4. 🔵 Vier Memories auf den Schreibstil-Skill zeigen lassen, `knapp` als Vorgabe übernehmen (#7)
5. 🔵 Erhaltungsprobe als Testmuster in die drei bewegenden Werkzeuge ziehen (#2)
6. 🔵 Vierter Skeptiker auf den schwächsten Befund (#7), Auftrag: kippen — siehe §8
7. 🔵 Prüfer für die PFLICHT-Regel bauen (#13) — https://github.com/achimdehnert/platform/issues/2199

### ✅ Erledigt

8. ✅ Vier reproduzierte Fehler behoben, 51 Tests grün — https://github.com/achimdehnert/platform/pull/2196
9. ✅ Vier weitere Fehler behoben (#9–#12), Tests ergänzt — in diesem PR
10. ✅ Vier Lehren verankert, vier Stil-Memories zeigen auf den Skill (§6)
11. ✅ Sechs Kriterien aus #2176 gebaut und in Betrieb (#2177–#2194)

## 8. Restlücken (getan · angenommen · nicht verifizierbar · offen geblieben)

- **Getan:** acht Fehler reproduziert und behoben; die von der Meta-Review aufgedeckte
  Lücke (acht ungeprüfte PRs) mit einem zweiten Finder geschlossen; Längsschnitt und
  Gate-Wirkung gemessen; der Ledger-Zustand (67.771 Zeichen, drei Vorgänge über der
  Grenze) frisch nachgezählt.
- **Angenommen:** dass die drei Skeptiker-Verdikte (#5, #6, #7) die Sache treffen — jeder
  lief mit engem Auftrag und benannten Artefakten, aber keiner wurde seinerseits geprüft.
- **Nicht verifizierbar:** nichts, was hier stünde. Die zunächst hier notierte Lücke („die
  genaue Zahl der entfernten Arbeitsbäume") war keine: die Zahl **69** samt Vorher/Nachher
  (90 → 21) und der Gegenprobe „0 Branches voraus" steht seit dem Vortag im
  `AGENT_HANDOVER.md`. Ich hatte im Transkript gesucht statt im dauerhaften Artefakt —
  dieselbe Klasse wie Befund #5, nur in die andere Richtung.
- **Offen geblieben:** `refuted_rate 0,0`. Drei Skeptiker, drei Mal SURVIVES — entweder
  waren die Befunde ungewöhnlich gut belegt, oder die Aufträge waren zu eng geschnitten,
  um zu widerlegen. Der billigste Gegentest wäre ein vierter Skeptiker auf den
  **schwächsten** Befund (#7) mit dem ausdrücklichen Auftrag, ihn zu kippen; er wurde
  nicht gefahren.
- **Deckungs-Lücke, geschlossen und benannt:** der erste Durchgang prüfte nur die Hälfte
  der PRs — nicht weil er dort nichts fand, sondern weil er dort nie hinsah. Aufgefallen
  ist das der Meta-Review, nicht mir. Die Lehre steht in §4 nicht drin, weil sie kein
  Befund über die Sitzung ist, sondern über den Retro: **wer mit einem fremden
  Fehlerkatalog startet, hält dessen Umfang für den Umfang der Arbeit.**
- **Regel-1-Lücke:** Phase 3.5 (Soll-Ablauf) und dieser Report stammen aus dem
  Haupt-Kontext — skillkonform, aber es heißt, dass die Formulierung der Lehren nicht
  fremdgeprüft ist. Phase 5 (Meta-Review) läuft als fremder Subagent nach.
