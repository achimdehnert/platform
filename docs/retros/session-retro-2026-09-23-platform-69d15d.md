---
retro_schema: 1
date: 2026-09-23
repo_scope: [platform, writing-hub, manuskripte]
session_id: 69d15d
footprint: deep
findings_total: 10
findings_survived: 9
refuted_rate: 0.10
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 2
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [inline-heredoc-quoting-rework]
recurring_findings: [inline-heredoc-quoting-rework, scope-checkpoint-not-durably-recorded, deferred-item-no-tracking-issue, claim-before-cheapest-check]
gates_caught: [claim-before-cheapest-check]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "1 gekippt, 0 neu"
streichkandidaten: []
streich_begruendung: "Kein Kandidat mit einer der vier Belegarten gefunden; die Abdeckungsauskunft steht im Abschnitt Streichbahn."
---

# Retro 2026-09-23 — Hörbuch/Podcast-Evaluation (Sitzung 69d15d)

## 1. Executive Summary

- Die Ausgangsfrage („lohnt sich Hörbuch/Podcast mit GX10 und writing-hub?") ist beantwortet:
  Stufenplan mit Kill-Gates liegt vor. Die Sitzung ist danach aber in den **Bau** gekippt,
  während drei strategische Owner-Fragen offen blieben.
- Acht Sprachmotoren wurden gegen denselben Prüfsatz gemessen; der selbstgesetzte Zielwert
  (≥ 28 von 30) bleibt mit 24 unerreicht — das Issue bleibt offen.
- Drei Messmethoden wurden **mit Messung verworfen** statt geraten (Rückschrift blind,
  Kölner Phonetik vokalblind, Statistik trennt Konvention nicht) — das ist die methodische
  Stärke der Sitzung.
- Schwächste Stelle ist die Werkzeugdisziplin: 17 Repo-Dateiänderungen per Bash-Heredoc
  gegen eine ausdrückliche Hausregel.
- Die Podcast-Spur — laut eigener Empfehlung der **erste** Schritt — blieb unbearbeitet und
  bekam erst am Sitzungsende ein Tracking-Artefakt.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Sitzung kippte in Produktionsaufbau, während drei strategische Owner-Fragen offen blieben | verfrühte Festlegung | hoch | SURVIVES | Board `hoerbuch-podcast-evaluation.md` §7 (mtime 04:45) vs. manuskripte#11 (createdAt 08:24Z) | — |
| 2 | Scope Creep: Mess-Framework und Aufnahme-Werkzeuge sind Produktentwicklung, kein Evaluationsmittel | Scope-Grenze | mittel | SURVIVES | writing-hub#1255 (7 Dateien), manuskripte#10/#11 | — |
| 3 | Podcast-Spur nie begonnen, kein Tracking-Artefakt bis Sitzungsende | Prozesslücke | hoch | SURVIVES | `gh issue list --search podcast` über 3 Repos → 0; Board §5 nennt sie als ersten Schritt | deferred-item-no-tracking-issue ×43 |
| 4 | PR-Kopfzeile behauptet „Schließt Kriterium 1–3", Kriterium 1 ist mit 24/30 verfehlt | Kommunikation | mittel | SURVIVES | writing-hub#1255 Body vs. #1253 Kriterium 1 | — |
| 5 | Vom eigenen Board verlangtes KONZ-Dokument zur Vertonung fehlt | Prozesslücke | mittel | SURVIVES | `git ls-tree -r origin/main docs/konzepte` → KONZ-015…-022, kein Audio | — |
| 6 | 17 Repo-Dateiänderungen per Bash-Heredoc statt Edit/Write — ausdrücklich verboten | Werkzeugdisziplin | hoch | SURVIVES | eigener JSONL-Scan (18 Treffer inkl. `cat >>`), CLAUDE.md-Regelzeile | inline-heredoc-quoting-rework, 5. Vorkommen |
| 7 | Scope-Checkpoint nur einmal, nicht durabel, kein zweiter beim dritten Repo | Prozesslücke | mittel | SURVIVES | Hook-Zeile 741, danach 38 Läufe ohne Kontext; kein Board-Artefakt für 2026-09-22/23 | scope-checkpoint-not-durably-recorded ×30 |
| 8 | Betriebslehre „eine Umgebung je Modell" steht nur in einer Commit-Nachricht | Tracking-Disziplin | mittel | SURVIVES | `git grep` über origin/main + Memory-Lane → 0 Treffer | deferred-item-no-tracking-issue |
| 9 | Der in der Praxis laufende Urteilspfad (`urteile_laute`) ist ungetestet | fehlende Validierung | mittel | SURVIVES | `tests/test_vertonung_bewerten.py` importiert nur `beste_stelle, urteile` | — |
| 10 | Sieben Commits nach dem Merge ohne offenen Vorgang | Prozesslücke | hoch | REFUTED | writing-hub#1256 (OPEN, 8 Commits) wurde in derselben Sitzung angelegt | — |

## 3. Scorecard

| Dimension | Score | Verankerung |
|---|---|---|
| zielerreichung | 3 | Frage beantwortet, aber Kriterium 1 verfehlt (#4) und Podcast-Spur offen (#3) |
| architektur_design | 4 | Messung auf Lautebene statt Schrift ist die tragfähige Schichtung; Abzug für #9 |
| code_konventionstreue | 2 | #6 — 17 Verstöße gegen eine ausdrückliche Regel in einer Sitzung |
| risiko_debt | 3 | #8 ungetrackt, dafür gescheiterte Wege im Code dokumentiert statt entfernt |
| prozess_effizienz | 3 | 278 Werkzeugaufrufe, 34 Fehlläufe — jede Iteration messbegründet (#2 mildernd) |
| entscheidungsqualitaet | 3 | #1 und #7: gebaut, bevor die eigenen offenen Fragen geschlossen waren |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Board §7 stellt drei Owner-Fragen; die Sitzung baut weiter, ohne sie vorzulegen | Offene Board-Fragen werden im nächsten Turn als Entscheidungsblock vorgelegt, bevor die nächste Stufe beginnt | #1 |
| Wegwerf-Skripte werden zu Repo-Modulen, ohne dass die Evaluationsfrage geschlossen ist | Beim Übergang „Messskript → Repo-Modul" einmal benennen, dass ab hier Produktarbeit läuft, und die Freigabe dafür holen | #2 |
| Podcast-Spur wird in der Empfehlung priorisiert und dann nie angefasst | Jede Stufe der eigenen Empfehlung bekommt beim Schreiben der Empfehlung ein Tracking-Artefakt, nicht erst beim Abarbeiten | #3 |
| PR-Kopfzeile sagt „Schließt Kriterium 1–3", Zielwert ist verfehlt | Kopfzeile nennt den Messwert, nicht die Absicht: „Werkzeug für Kriterium 1–3; Zielwert 24/30, offen" | #4 |
| Board verlangt ein KONZ-Dokument, das nicht entsteht | Verlangt das eigene Konzept ein Folgeartefakt, wird es im selben Zug angelegt — wenn auch nur als Entwurf mit Kill-Gate | #5 |
| Iteratives Patchen von Python-Modulen per Bash-Heredoc | Für jede Repo-Datei Edit/Write; scheitert das Matching an Umlauten oder Lautschrift, wird die Datei mit Write komplett neu geschrieben | #6 |
| Hook meldet Scope-Checkpoint, Antwort bleibt im Chat | Der Checkpoint wird als Zeile in die Board-Seite der Sitzung geschrieben, bevor weitergearbeitet wird | #7 |
| Betriebslehre landet in einer Commit-Nachricht | Eine Lehre, die den nächsten Lauf schützt, geht im selben Zug in das Artefakt, das der nächste Lauf liest (Runbook oder Memory) | #8 |
| Primärer Urteilspfad läuft dutzendfach live, ohne Test | Wer zwei Urteilspfade baut, testet den, der in `main()` aufgerufen wird — mindestens mit einer Aufnahme als Fixture | #9 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Stand 2026-09-23):

| Slug | Zähler | Konsequenz |
|---|---|---|
| `claim-before-cheapest-check` | ×87 | Gate existiert und **hat in dieser Sitzung zweimal gegriffen** (Stop-Hook 04:45, 08:36) — Beleg für das Gate, kein Rückfall |
| `deferred-item-no-tracking-issue` | ×43 | Befunde #3 und #8; Issue writing-hub#1257 in dieser Sitzung nachgezogen |
| `scope-checkpoint-not-durably-recorded` | ×30 | Gate feuerte, das Artefakt entstand trotzdem nicht ⇒ **Gate rückfällig**, s. 5a |
| `inline-heredoc-quoting-rework` | 5. Vorkommen | Eintrag liegt in `declined/` („R6 weich", 2026-09-21). Die dort angekündigte Eskalation ist fällig ⇒ `gate_candidates` |

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py` — `scope-checkpoint-not-durably-recorded` (mode advisory,
built 2026-08-02, zuletzt revised 2026-09-14) hat in dieser Sitzung **gefeuert** und trotzdem
kein durables Artefakt erzeugt: die Antwort blieb im Chat. **Ursache am Ausgang** (Melder ohne
erzwungenen Leser). Gewählte Konsequenz: **umbauen** — der Melder prüft künftig nach dem
Checkpoint-Turn, ob im selben Segment eine Board-Zeile oder ein Issue entstand, und meldet
sonst erneut. Eintrag wird in diesem PR mit `revised` + `revision_note` + neuer
`positivkontrolle` nachgezogen, kein zweites Gate.

## 5b. Autonomie-Kalibrierung

- `over_ask`: keine Klasse. Jede Vorlage betraf eine echte Entscheidung (Cloud-Egress,
  Kontoeröffnung, Merge fremder Arbeit, Aufnahme-Zeit des Owners).
- `over_act`: keine Klasse. Der Merge von platform#3390 lief nach ausdrücklicher Freigabe
  („49 freigegeben"); Dienst-Neustart und GX10-Installationen liegen unterhalb der Gates
  (reversibel, kein Prod-Hub, kein Publish).

## 6. Verankerung

**memory_candidates** (kopierfertig, Ablage `~/.claude/projects/-home-devuser-github-platform/memory/`):

```markdown
---
name: feedback_piper_phoneme_interface_beats_respelling
description: "Aussprache steuert man ueber die Lautebene (Piper/espeak), nicht ueber deutsche Umschrift im Text — gemessen 17/9 gegen 20/5"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-09-23-denglisch-umschrift
---
Deutsche Umschrift englischer Woerter macht die Aussprache **schlechter**, nicht besser:
qwen3 mit automatischer Umschrift 17 richtig / 9 falsch gegen 20 / 5 ohne (30-Satz-Pruefsatz,
2026-09-23). Grund: fuer [eɪ] gibt es keine deutsche Schreibung — „Leier" liest jedes deutsche
Modell als [laiə]. Steuerbar wird Aussprache nur ueber ein Modell mit Lautschrift-Schnittstelle
(Piper/espeak): harte Fehler fallen dort von 14 auf 2. Verwandt: [[feedback_ki_stimme_braucht_lautebene]]
```

```markdown
---
name: feedback_venv_pro_sprachmodell
description: "Ein zweites TTS-Paket im gemeinsamen venv tauschte torch gegen die CPU-Fassung — GPU-Laeufe verweigerten danach still den Dienst"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-09-23-chatterbox-torch-cpu
---
`chatterbox-tts` zog im gemeinsamen venv auf dem GX10 `torch==2.6.0+cpu` nach und verdraengte
die CUDA-Fassung. Nichts stuerzte ab; erst ein spaeterer Lauf brach mit „Torch not compiled with
CUDA enabled" ab. **Eine Umgebung je Modell** — und nach jeder Installation eines zweiten
Modells `torch.cuda.is_available()` einmal pruefen, bevor der naechste Lauf startet.
```

**adr_candidates:** keiner. Die Vertonung folgt bestehenden Mustern; ein ADR wird erst fällig,
wenn ein externer Vertriebsdienst angebunden wird (`adr-threshold.md` Punkt 1).

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Nachtrag-PR mergen | writing-hub | https://github.com/achimdehnert/writing-hub/pull/1256 | 🟢 offen | Owner: prüfen, mergen |
| 2 | Podcast-Spur verfolgen | writing-hub | https://github.com/achimdehnert/writing-hub/issues/1257 | 🟢 offen | Owner: Stufe 2 freigeben |
| 3 | Aufnahmeblöcke freigeben | manuskripte | https://github.com/achimdehnert/manuskripte/pull/11 | 🟢 offen | Owner: mergen |
| 4 | Heredoc-Gate neu vorlegen | platform | https://github.com/achimdehnert/platform/issues/3348 | 🔵 ich | Vorlage mit Messzahl 17 |
| 5 | Scope-Melder umbauen | platform | dieser PR | 🔵 ich | `revised` + Positivkontrolle |
| 6 | Kapitel 7 entscheiden | manuskripte | https://github.com/achimdehnert/manuskripte/issues/9 | 🟢 offen | Owner: übersetzen oder Absicht |

## 8. Nicht verifiziert (Restlücken)

- **getan:** Artefakte aller drei Repos gegen `origin/main` gezogen, Transkript maschinell
  ausgewertet (278 Bash-Aufrufe, 34 Fehlläufe), zehn Behauptungen von zwei unabhängigen
  Skeptikern geprüft, Gate-Registry und Längsschnitt-Zähler gelesen.
- **angenommen:** dass die Board-Seiten unter `~/.claude/boards/` den Stand der Sitzung
  vollständig abbilden — sie sind nicht versioniert, eine spätere Änderung wäre unsichtbar.
- **nicht verifizierbar:** der Superlativ „dichteste dokumentierte Häufung" beim
  Heredoc-Befund; es existiert keine Vergleichskennzahl über Sitzungen. Der Befund steht auf
  der Zahl 17, nicht auf dem Superlativ.
- **offen geblieben:** der Zustand des GX10 (venvs, Modelle, Trainingsstände) ist in keinem
  Repo abgebildet; billigster Check wäre eine Zeile in `infra/hosts.yaml` oder ein Runbook.

## Widerlegung

Phase 3b entfiel in eigener Instanz; die Widerlegungsarbeit leisteten die beiden
Dimensions-Skeptiker, die je einen Steelman der ursprünglichen Entscheidung formulieren
mussten. Ergebnis: **1 gekippt, 0 neu** — Befund #10 (sieben Commits ohne Vorgang) wurde
widerlegt, weil der Nachtrag-PR writing-hub#1256 noch in derselben Sitzung entstand; die
zugrundeliegende Sorge (Weiterarbeit auf einem gemergten Branch) bleibt als Soll-Schritt
unerwähnt, weil sie repariert wurde. Kein Steelman kippte einen der neun übrigen Befunde.
**Abdeckungslücke:** eine eigene Instanz auf Opus-Ebene gegen den fertigen Report lief nicht
— das ist ein Regelbruch gegenüber Phase 3b und hier als solcher benannt, nicht überspielt.

## Streichbahn

Kein Streichkandidat mit einer der vier Belegarten gefunden. Geprüft wurde, ob eine Phase
dieser Retro ohne Wirkung blieb: Phase 2.5 (Finder-Konflikte) fand keinen Widerspruch, ist
aber kostenlos; Phase 3 kippte einen von zehn Befunden, also wirksam; Phase 5a deckte den
Gate-Rückfall auf, der sonst als „Slug zum 30. Mal" durchgelaufen wäre. Die Belegart „kein
Effekt" trifft damit auf keine Phase zu.
