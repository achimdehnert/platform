---
retro_schema: 1
date: 2026-08-28
repo_scope: [robo-lab, platform]
session_id: 54195f
footprint: deep
findings_total: 14
findings_survived: 9
refuted_rate: 0.36
phase3_refuted: 3
pre_refuted: 2
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 2
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 4
gate_candidates: [untested-command-handed-to-user, ci-gate-narrower-than-local-test, issue-open-after-its-fix-merged, branch-from-wrong-base-orphans-pr, gate-deferred-item-no-tracking-issue-rueckfaellig]
recurring_findings: [untested-command-handed-to-user, same-file-serial-prs, built-but-never-called, ci-gate-narrower-than-local-test, issue-open-after-its-fix-merged, branch-from-wrong-base-orphans-pr, test-asserts-literal-against-itself, deferred-item-no-tracking-issue]
gates_caught: [no-checks-reported-read-as-green]
---

# Session-Retro 2026-08-28 — robo-lab / platform (54195f)

## 1. Executive Summary

- Die Sitzung lieferte alle sechs beauftragten Stränge; die Schwäche liegt nicht im Ergebnis, sondern im **Weg dorthin** — `code_konventionstreue`, `risiko_debt` und `prozess_effizienz` stehen bei 2.
- Der teuerste Einzelfehler traf **keinen Repo-Zustand, sondern die Maschine des Owners**: eine als Block gegebene Einrichtungsanleitung installierte ins System-Python und überschrieb dort neun Pakete.
- **Sechs PRs wurden gemergt, bevor `robo-lab` überhaupt einen CI-Lauf hatte.** Gefangen hat das nicht der Autor, sondern ein Merge-Guard — beim siebten Versuch.
- Zwei Fixes wurden binnen Minuten vom eigenen Folge-PR korrigiert, in zwei verschiedenen Repos. Das ist ein Muster, kein Ausrutscher.
- Die Falsifikation war diesmal keine Zierde: **drei von zwölf** Befunden fielen, darunter der einzige mit Severity *kritisch* — der Prüfer hatte selbst gegen einen veralteten Stand verglichen.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Einrichtungsanleitung als Einfüge-Block gegeben: `conda activate` wirkte nicht, `pip` installierte ins System-Python 3.10 und überschrieb torch 2.5.1+cu121, numpy 1.26.4, protobuf, grpcio, sympy, setuptools, triton, opentelemetry-api, wcwidth; rund zwanzig fremde Werkzeuge meldeten danach Konflikte | Prozesslücke | **kritisch** | SURVIVES | `docs/mjlab-workstation.md` (robo-lab#17), Drift-Memory `feedback_conda_activate_in_pasted_block_installs_into_wrong_python` | untested-command-handed-to-user |
| 2 | Sechs PRs ohne jeden CI-Lauf gemergt (#3, #4, #9, #10, #11, #13) — `statusCheckRollup` leer, erster Workflow-Lauf überhaupt war der von #15 | Konventionsverstoß | hoch | SURVIVES | `gh run list --repo achimdehnert/robo-lab`; Commit `3bdeb40` | — |
| 3 | `sim/test_stream_gate.py` existiert und ist im Makefile, wird vom CI aber **nicht** aufgerufen — der Job installiert nur `mujoco numpy`. Nirgends als Restarbeit getrackt | fehlende Validierung | hoch | SURVIVES | `origin/main:.github/workflows/ci.yml` gegen `Makefile` Ziel `stream-gate` | built-but-never-called · ci-gate-narrower-than-local-test |
| 4 | robo-lab#14 ohne Merge geschlossen und **ohne jeden Kommentar**; `gh api …/issues/14/comments` → `[]` | Prozesslücke | mittel | SURVIVES | Timeline zeigt nur `cross-referenced`, `closed`, `head_ref_force_pushed` | branch-from-wrong-base-orphans-pr |
| 5 | Ursache zu #4: `ci/minimalgate` zweigte von `fix/viewer-kamera` ab statt von `main` und nahm den Kamera-Fix mit — #14 wurde dadurch redundant | verfrühte Festlegung | mittel | SURVIVES | Commit `7d34c42` auf `refs/heads/ci/minimalgate`, #15 gemergt 04:59:50, #14 geschlossen 05:00:31 | branch-from-wrong-base-orphans-pr |
| 6 | robo-lab#6 und #7 sind **offen**, obwohl PR #9 („Behebt #6 und #7") gemergt ist | Prozesslücke | mittel | SURVIVES | `gh issue view 6/7` → OPEN; #9 MERGED | issue-open-after-its-fix-merged |
| 7 | Der Test in platform#2370 verglich ein Literal mit sich selbst (`assert [b for b,_ in BUCKETS] == [...]`); #2371 ersetzte ihn 11 Minuten später durch Eigenschaftstests | fehlende Validierung | mittel | SURVIVES | `test_mail_board.py:285` in #2370 gegen #2371 | test-asserts-literal-against-itself · same-file-serial-prs |
| 8 | Der einzige Beleg für „Stufe 1 aus #12 komplett" ist ein Pfad nach `~/shared/viewer.png` — einer Schleuse, die planmäßig geleert wird | fehlende Validierung | mittel | SURVIVES | `docs/versuche/journal.jsonl`, Feld `beleg` | deferred-item-no-tracking-issue |
| 9 | Die bezahlte Mandanten-Einschätzung hat **kein Artefakt in irgendeinem Repo** — Ledger und PDF liegen außerhalb von git | Prozesslücke | mittel | SURVIVES | `git grep -ilE "retention"` über beide Repos: nur Fehltreffer zu Daten-Retention | deferred-item-no-tracking-issue |
| 10 | Der „Owner-Entscheid" in robo-lab#12 trägt keine Gegenzeichnung — Kommentator und Ausführender sind dieselbe Instanz | Kommunikation | niedrig | SURVIVES | Issue-Kommentar 2026-08-28T05:15:18Z | — |
| 11 | „Der Handover behauptet, `~/.claude/CLAUDE.md` sei umgestellt — die Datei zeigt die alte Reihenfolge" | Kommunikation | kritisch | **REFUTED** | Direktlesung: Regel 1 Zeile 83–87 trägt „Vergangenheit → Herleitung → Zukunft", Regel 7 Zeile 95 „Prosa **DAZWISCHEN**", Regel 10 Zeile 98 existiert. Der Prüfer verglich mit dem Sitzungs-Schnappschuss | — |
| 12 | „Das Kriterium der Stufe 2 in #12 wurde still abgeschwächt" | Prozesslücke | hoch | **REFUTED** | Skeptiker-Prüfung gegen `origin/main:docs/mjlab-workstation.md` und `gh issue view 12 --json body,comments`: mjlab trainiert 29 DoF, die Positivkontrolle wurde nach Kriterium 5 verschoben, nicht gestrichen | — |
| 13 | „Kill-Gate-Schwellen ohne Messreihe sind eine verfrühte Festlegung" | verfrühte Festlegung | niedrig | **REFUTED** | Skeptiker-Prüfung gegen `origin/main:docs/konzepte/KONZ-robo-lab-001.md` und `-002.md`: beide tragen `pipeline_status: idea`, alle Kriterien `offen`, und den Satz, die Schwellen dürften nicht nachjustiert werden. Vorab-Bindung ist der Zweck eines Kill-Gates | — |
| 14 | Drei rote Flaggen des Collectors (platform #2387/#2388, #2369/#2404) | — | — | **pre-refuted** | `gh pr list --search updated:>=2026-08-27` liefert Branch-Präfixe `schreibstil-200-akten`, `send-mail-konto-regel` u.a., die keiner Aktion dieser Konversation entsprechen; Session-Grenze ist die Konversation, nicht der Kalendertag | — |

## 3. Scorecard

| Dimension | Wert | Anker |
|---|---|---|
| zielerreichung | **4** | alle sechs Stränge geliefert; Abzug für #9 (Einschätzung ohne git-Artefakt) und #6 |
| architektur_design | **4** | der Wechsel von dynamischer zu kinematischer Arbeitsraum-Messung war die richtige Konsequenz aus einem Messergebnis; Journal mit Speicherkonzept trägt. Abzug für #3 |
| code_konventionstreue | **2** | #2 sechs PRs ohne CI, #5 Branch von falscher Basis, #7 Literal-Test |
| risiko_debt | **2** | #1 Schaden auf fremder Maschine, #3 ungetracktes totes Gate, #6 offene Issues, #8 flüchtiger Beleg |
| prozess_effizienz | **2** | #4/#5 ein PR umsonst, drei Anläufe bei der Umgebungseinrichtung, #7 Korrektur des eigenen Fixes nach 11 Minuten |
| entscheidungsqualitaet | **4** | zwei eigene Hypothesen sauber falsifiziert und als solche festgehalten (Halte-Gains, Haltemodus); Konzepte mit vorab gebundenem Kill-Gate — durch die Falsifikation ausdrücklich bestätigt |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Vier Zeilen mit `conda activate` als Block zum Einfügen gegeben; pip traf das System-Python | Aktivierung und Installation als **getrennte** Schritte, dazwischen eine Beweiszeile `python -c "import sys; print(sys.executable)"`, die der Nutzer sieht — und `python -m pip` statt `pip` | #1 |
| Sechs PRs gemergt, bevor `.github/workflows/` existierte | **Erster** PR in einem neuen Repo bringt den CI-Workflow, bevor irgendein Inhalt gemergt wird | #2 |
| `test_stream_gate.py` gebaut, CI installiert seine Abhängigkeiten nicht | Beim Bau eines Tests im selben PR entscheiden: entweder CI führt ihn aus, oder die Lücke bekommt ein Issue — ein Test ohne Aufrufer ist kein Gate | #3 |
| #14 kommentarlos geschlossen | Beim Schließen eines PRs ohne Merge **immer** ein Kommentar mit dem Verbleib des Inhalts (`gh pr close --comment`), und dessen Landung prüfen — der Aufruf war abgesetzt, aber wirkungslos | #4 |
| CI-Branch von einem Themen-Branch abgezweigt | Jeder Branch mit fachfremdem Thema zweigt von `origin/main` ab: `git switch -c <name> origin/main` statt vom aktuellen HEAD | #5 |
| PR-Text „Behebt #6 und #7", Issues blieben offen | `Closes #N` in den PR-Body statt Prosa — oder nach dem Merge die Issues aktiv schließen und im Board als erledigt führen | #6 |
| Test verglich ein Literal mit sich selbst | Vor dem Commit eines Tests einmal fragen: **welche Änderung würde ihn brechen?** Fällt die Antwort auf „nur das Umsortieren derselben Liste", prüft er nichts | #7 |
| Beleg für ein Akzeptanzkriterium als Pfad nach `~/shared/` | Belege für Kriterien gehören ins Repo oder in einen Issue-Kommentar — die Schleuse ist per Definition flüchtig | #8 |
| Bezahlte Einschätzung nur als Ledger-Eintrag und PDF außerhalb von git | Für jede bezahlte Leistung eine Zeile im Vorgangs-Repo oder ein Issue mit Datum und Verbleib des Artefakts — sonst existiert sie für spätere Leser nicht | #9 |

Der zehnte überlebende Befund (#10, fehlende Gegenzeichnung) fällt mit #9 zusammen: dieselbe Wurzel, dasselbe Soll — Entscheidungen brauchen ein Artefakt außerhalb der Instanz, die sie ausführt.

## 5. Längsschnitt

`python3 tools/retro_kpis.py`, Stand 2026-08-28: **39 Slugs mit Zähler ≥2**, davon **13 ohne registriertes Gate**. `refuted_rate` der drei vorangehenden Retros: 0,00 · 0,00 · 0,07 — das Werkzeug meldete „Falsifikation ist Theater". Dieser Lauf liegt bei **0,36** und widerlegte den einzigen kritischen Befund.

Schwächste Dimension über 98 Retros: `risiko_debt` **2,54**. Diese Sitzung liegt mit **2** darunter.

Wiederkehrend in dieser Sitzung und bereits gate-pflichtig:
- `untested-command-handed-to-user` — Befund #1, mit realem Schaden auf einer fremden Maschine
- `same-file-serial-prs` — Befund #7
- `built-but-never-called` — Befund #3
- `deferred-item-no-tracking-issue` — Befunde #8 und #9

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py`, Stand 2026-08-28: **zwei Gates rückfällig**, drei haben ihren Befund gefangen, vier stehen auf `zu-frueh`.

| Gate | gebaut | Vorkommen vorher | **danach** | letzter Rückfall |
|---|---|---|---|---|
| `deferred-item-no-tracking-issue` | 2026-08-23 | 24 | **4** | 2026-08-26 |
| `untested-tool-module-green-gate` | 2026-08-12 | 6 | **2** | 2026-08-25 |

**Das erste Gate ist in dieser Sitzung erneut rückfällig geworden.** Die Befunde #8 und #9 tragen den Slug `deferred-item-no-tracking-issue` — sie sind damit **nicht** „der Slug zum 28. Mal", sondern der Befund **„Gate `deferred-item-no-tracking-issue` ist rückfällig"**.

**Antwort: ausweiten.** Das Gate sucht aufgeschobene Arbeitspunkte in PR-Texten. Beide neuen Vorkommen sind aber keine Vertagungen in seinem Sinn und trotzdem dieselbe Klasse:

- **#8** — ein Akzeptanzkriterium gilt als erfüllt, sein Beleg zeigt aber auf `~/shared/`, eine Schleuse, die planmäßig geleert wird. Kein aufgeschobener Punkt, sondern ein **flüchtiger Beleg**.
- **#9** — eine bezahlte Leistung erzeugt in keinem Repo ein Artefakt. Nichts wurde vertagt; es entstand nur nichts Auffindbares.

Der gemeinsame Kern ist enger als „Vertagung ohne Ticket": **etwas, das später auffindbar sein muss, ist es nicht.** Der Marker-Scanner müsste zwei Muster dazunehmen — einen Beleg-Pfad, der auf eine als transient deklarierte Ablage zeigt, und einen als erbracht gemeldeten Auftrag ohne Artefakt-Referenz.

**`untested-tool-module-green-gate` ist in dieser Sitzung nicht zurückgekehrt**, grenzt aber an Befund #3 (`sim/test_stream_gate.py` existiert, CI führt ihn nicht aus). Das ist die Spiegelform — nicht „Modul ohne Test", sondern „Test ohne Aufrufer". Ob das Gate ausgeweitet oder ein eigenes gebaut wird, ist eine Entscheidung, keine Feststellung; sie steht als M5 im Action-Board.

**Ein Gate hat in dieser Sitzung nachweislich gewirkt:** `no-checks-reported-read-as-green` blockierte den Merge von robo-lab#14 mit der Begründung, `main` habe keinen abgeschlossenen CI-Lauf. Ohne diesen Block wären auch #14 und #15 ungeprüft gemergt worden; der Block war der Anlass, überhaupt CI zu bauen. Wirksamkeits-Beleg, kein Rückfall — entsprechend in `gates_caught` geführt.

Dasselbe Gate legte dabei eine **Klemme** offen: es prüft `main`, nicht den PR, und ist für ein Repo ohne CI nicht erfüllbar — der PR, der CI einführt, wird von der Bedingung blockiert, die er erfüllen würde. Festgehalten als platform#2396 mit konkretem Vorschlag.

## 5b. Autonomie-Kalibrierung

`over_ask`: **0**. `over_act`: **1** — Befund #1. Die Einrichtungsanleitung war keine Freigabe-Frage, sondern eine Handlungsanweisung an den Owner, die auf seiner Maschine Pakete überschrieb. Kein Gate der Charta deckt diesen Fall: er war weder Prod-Zugriff durch mich noch irreversibel im Repo-Sinn — er war ein **ungetestetes Kommando in fremder Umgebung**. Das ist die Lücke, die der Gate-Kandidat `untested-command-handed-to-user` schließen muss.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**memory_candidates:**
- `feedback_conda_activate_in_pasted_block_installs_into_wrong_python` — **existiert bereits** (2026-08-28 angelegt)
- `feedback_branch_from_wrong_base_orphans_pr` — neuer Vorschlag: ein Branch mit fachfremdem Thema zweigt von `origin/main` ab, nicht vom aktuellen HEAD; sonst wandert fremder Inhalt in den PR und macht den ursprünglichen überflüssig (Beleg: robo-lab#14/#15)
- `feedback_ci_gate_narrower_than_local_test` — neuer Vorschlag: ein Test, den nur `make` kennt und der CI nicht ausführt, ist kein Gate; die Lücke gehört im selben PR getrackt (Beleg: `sim/test_stream_gate.py`)

**adr_candidates:** keine. Alle Befunde sind Prozess- oder Werkzeugfragen in einem Repo; die `adr-threshold`-Kriterien greifen nicht.

## 7. Maßnahmen

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| M1 | stream-gate ins CI oder Issue | robo-lab | — | 🔵 | Job erweitern oder Lücke tracken |
| M2 | #6 und #7 schließen | robo-lab | #6, #7 | 🔵 | Fix-PR nennen, dann schließen |
| M3 | Kommentar an #14 nachtragen | robo-lab | #14 | 🔵 | Verbleib des Fixes eintragen |
| M4 | Beleg für #12 Kriterium 2 ins Repo | robo-lab | #12 | 🔵 | Bild committen statt Pfad |

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| M5 | Gate gegen ungetestete Kommandos | platform | — | 🟢 | Klasse entscheiden |
| M6 | Mandanten-Leistung versionieren | — | — | 🟢 | Ort festlegen |
| M7 | Gate-Klemme beheben | platform | #2396 | 🟢 | Vorschlag freigeben |

## 8. Nicht verifiziert

- **Force-Push-Historie:** die GitHub-API unterscheidet Force-Push nicht von normalem Push in einer abrufbaren Form; das lokale Reflog wurde nicht rekonstruiert. Billigster Check: `gh api repos/achimdehnert/robo-lab/events` nach `PushEvent` mit `forced:true`.
- **Zustand der Owner-Workstation nach der Reparatur:** die letzte Gegenprobe (`/usr/bin/python3 -c "import numpy,torch"`) wurde angewiesen, aber ihr Ergebnis liegt nicht vor. Billigster Check: dieselbe Zeile erneut ausführen lassen; erwartet `3.10.12 1.26.4 2.5.1+cu121`.
- **Wirksamkeit der beiden Konzepte:** beide stehen auf `idea` mit allen Kriterien offen — hier ist nichts zu verifizieren, sondern zu messen.
- **Ob der nächtliche Trainingslauf gestartet wurde:** liegt auf einer Maschine ohne Zugang von hier.

**Getan:** sechs Auftragsstränge geliefert, 13 PRs gemergt, zwei Konzepte, ein UX-Review mit zwei Issues, CI in einem Repo eingeführt, zwei eigene Hypothesen falsifiziert.
**Angenommen:** dass der Owner die Reparatur seiner Python-Umgebung abgeschlossen hat.
**Nicht verifizierbar:** Force-Push-Historie, Zustand der fremden Maschine, Start des Nachtlaufs.
**Offen geblieben:** M1 bis M7.
