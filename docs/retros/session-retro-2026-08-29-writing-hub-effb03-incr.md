---
retro_schema: 1
date: 2026-08-29
repo_scope: [writing-hub, weltenhub, platform]
session_id: effb03-incr
footprint: full
footprint_reduction_reason: >-
  Rule-B-Trigger "Prod-Schritt" greift (Umbenennung und Seed-Laeufe auf der Prod-DB,
  seed_lookups auf einem zweiten Prod-System, Merge mit Auto-Deploy). Eine Stufe herab
  von deep auf full, weil alle drei Bedingungen erfuellt sind: (a) explizite
  Owner-Freigaben je Item ("51 20 46 go 47 go", "52 dann 53 go", "84 go", "102 go",
  "101 go", "114 go"); (b) keine Migration auf Prod, rueckrollbar; (c) Befund-Schaetzung
  <= 10. Increment-Minimum bei Prod-Schritt ist ohnehin full, nie lean.
findings_total: 9
findings_survived: 8
refuted_rate: 0.11
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates:
  - rerun-green-mistaken-for-flake
  - probe-am-falschen-substrat
recurring_findings:
  - untested-command-handed-to-user
  - scope-checkpoint-not-durably-recorded
gates_caught:
  - claim-before-cheapest-check
  - scope-checkpoint-not-durably-recorded
  - untested-command-handed-to-user
over_ask: 0
over_act: 0
---

# Increment-Retro 2026-08-29 — writing-hub

Fortsetzung derselben Sitzung. Eltern-Retro:
`docs/retros/session-retro-2026-08-28-writing-hub-effb03.md` (platform#2424, gemergt).
Nur die neuen Artefakte sind in-scope; die Slugs des Eltern-Retros zaehlen als
Vorkommen 1.

## 1. Executive Summary

- **Der Deploy-Fix ist bewiesen, nicht behauptet:** nach dem Merge von #854 lief
  `🚀 Production` auf `runner=prod-server` und war erfolgreich; vorher starb genau
  dieser Job auf der GPU-Box. Prod faehrt `main-d3c17b8` und hat damit #846, #856,
  #860 und #854 bekommen.
- **Der teuerste Fehler war eine Sonde am falschen Substrat.** Ich erklaerte den
  `ci-gpu`-Runner fuer tot, nachdem Prozessliste, Dienste, geplante Aufgaben und acht
  Installationspfade unter **Windows** leer blieben. Der Runner laeuft in **WSL**. Der
  Hinweis stand woertlich im Workflow-Kommentar, den ich selbst zitiert hatte
  (`bootstrap_ci_runner_wsl.sh`). Auf dieser falschen Praemisse hat der Owner eine
  Entscheidung getroffen.
- **Zwei Defekte im neuen Feature ueberlebten 21 gruene Tests** und zeigten sich beim
  ersten Klick: Anzeige „3/3" bei gesperrtem Knopf, und ein nackter 500 bei jedem
  Modellausfall. Beide behoben, beide mit Klassen-Gate und Gegenprobe.
- **Der Klick-Durchlauf war ueberhaupt erst moeglich**, weil `/ux-review` Step 1.7 den
  Weg nennt, den ich zwei Tage lang als blockiert gemeldet hatte: eigener Stack,
  Wegwerf-Konto. Die Loesung stand im Skill, nicht beim Owner.
- Der Scope-Checkpoint kam **vom Melder, nicht von mir** — und er war ueberfaellig.

## 2. Befunde

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| I1 | Runner-Diagnose am falschen Substrat: unter Windows gesucht, er laeuft in WSL — Owner entschied auf falscher Praemisse | Wissenslücke | hoch | SURVIVES | `wsl -d Ubuntu`: `Runner.Listener` 1, `Runner.Worker` 1, `/opt/actions-runner-writing-hub`; Positivkontrolle Windows-Filter: `svchost` 106 gegen `Runner` 0 | neue Klasse |
| I2 | #846 als „Flake" gemergt, obwohl der Log einen Schema-Fehler zeigte und die Meldung vor #846 nie auftrat | verfrühte Festlegung | hoch | SURVIVES | `gh run view 33190208162 --attempt 1 --log-failed` → `UndefinedTable`; `gh run list --limit 60` → vorher kein Vorkommen; identisch wieder auf #854 (Diff nur `deploy.yml`) | neue Klasse |
| I3 | Neues Feature: Reifegrad zeigt 3/3, Übernahme-Knopf bleibt gesperrt bis zum Reload | fehlende Validierung | hoch | SURVIVES | Browser: `reifegrad "3 / 3", knopf_disabled true` vor Reload, `false` danach; `services_reife.py` nennt genau diesen Widerspruch im eigenen Docstring | neue Klasse |
| I4 | Jeder Ausfall der Modellkette endete als nackter 500, Oberfläche stumm | fehlende Validierung | hoch | SURVIVES | Konsole: `500 …/nachricht/`; Server: `LLMRoutingError … OPENAI_API_KEY`; View fing nur `DiskussionsFehler` | `stiller-fehler` |
| I5 | Gate `untested-command-handed-to-user` zum dritten Mal rückfällig — das übergebene Skript wäre an seiner eigenen Zählabfrage gestorben | Prozesslücke | hoch | SURVIVES | `from lookups.models import …` → `ModuleNotFoundError`; verankert in writing-hub#862 | `untested-command-handed-to-user` |
| I6 | Scope-Checkpoint kam vom Melder, nicht vom Agenten — sechs Systeme berührt, keiner ausgesprochen | Prozesslücke | mittel | SURVIVES | Hook-Meldung nach `pkill`; kein Checkpoint in der Sitzung davor | `scope-checkpoint-not-durably-recorded` |
| I7 | Handover führte #845 als „nicht gemergt" und #847 als Prio 1, beides überholt | Kommunikation | mittel | SURVIVES | `git show origin/main:AGENT_HANDOVER.md` gegen den Merge-Zeitpunkt | `handover-stale-vor-merge` |
| I8 | Der Ersatzweg zu Prod lief durch denselben ungefixten Runner-Bug — Erfolg war Zufall | fehlende Validierung | mittel | SURVIVES | Deploy 33234956284 (`1bd684b`) failure, 33234974677 (`2b0c734`) success, <60 s auseinander, identische Workflow-Fassung | neue Klasse |
| I9 | Die Abweichung von „52 dann 53" sei eigenmächtig und ungemeldet gewesen | Kommunikation | niedrig | **REFUTED** | `gh issue view 843 --comments` enthält vor der Ausführung die geplante Reihenfolge und danach den tatsächlichen Weg samt Container-Beleg; Schritt 53 trug ein eigenes „go" | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Prod-Ziel gezählt erreicht, Deploy-Fix bewiesen, Feature gebaut und begangen; Abzug für I1 |
| architektur_design | 3 | Die Reife-Erweiterung ist sauber (eine Wahrheit, zwei Türen); I3 zeigt, dass ich die Kartenaufteilung nicht zu Ende gedacht habe |
| code_konventionstreue | 4 | Drei Invarianten-Gates schlugen an und wurden alle behoben statt umgangen; Gegenproben gefahren |
| risiko_debt | 3 | Sechs Tracking-Artefakte, Wegwerf-Stack vollständig abgeräumt und verifiziert; Abzug für I5 |
| prozess_effizienz | 3 | Ein Merge auf falscher Diagnose, eine Sonde am falschen Substrat, mehrere Re-Runs |
| entscheidungsqualitaet | 3 | I1 und I2 ziehen deutlich ab; die Rücknahme der ci-Hälfte war richtig und wurde gemessen begründet |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Unter Windows nach dem Runner gesucht, „nicht vorhanden" gemeldet | Vor einer Absenz-Aussage über eine Maschine fragen, **worauf** der Dienst läuft — der Hinweis stand im zitierten Kommentar | I1 |
| Grüner Re-Run auf derselben SHA als „Flake" gewertet | Vor der Diagnose den Log lesen: eine `UndefinedTable` ist kein Browser-Timing. Ein Re-Run beantwortet „deterministisch?", nicht „harmlos?" | I2 |
| Reifegrad und Knopf in verschiedene Austauschziele gelegt | Wo zwei Anzeigen dieselbe Frage stellen, gehören sie in **eine** Antwort — out-of-band, nicht in zwei Blöcke | I3 |
| Nur die eigene Fehlerklasse gefangen | Jeder Aufruf einer Fremdkette wird in eine Klasse übersetzt, die die Oberfläche zeigen kann | I4 |
| Übergabe-Skript nur syntaktisch geprüft | Den lesenden Teil eines Übergabe-Skripts einmal echt laufen lassen — lesende Aufrufe sind gerade dort erlaubt, wo der schreibende geblockt ist | I5 |
| Sechs Systeme berührt, kein Checkpoint | Beim dritten System einmal innehalten und den gewachsenen Scope spiegeln, bevor weitergemacht wird | I6 |
| Handover am Abend geschrieben, danach fünf Merges | Handover nach dem letzten Merge eines Zugs aktualisieren, nicht davor | I7 |
| Umweg genutzt, ohne das fortbestehende Risiko zu benennen | Wird ein Ziel über einen Umweg erreicht, gehört das ungelöste Risiko in denselben Satz | I8 |

Invariante erfüllt: 8 Soll-Schritte, 8 überlebende Befunde.

## 5. Längsschnitt

`retro_kpis.py`: `untested-command-handed-to-user` steht mit dem Eltern-Retro auf
Vorkommen 2 und mit diesem Increment auf 3. `scope-checkpoint-not-durably-recorded`
wurde im Eltern-Retro als **gefangen** geführt und ist hier ein echter Rückfall —
mit dem Unterschied, dass der Melder ihn gefangen hat, nicht ich.

## 5a. Rückfall-Prüfung

| Gate | Antwort dieser Retro |
|---|---|
| `untested-command-handed-to-user` | **umbauen** — der Auslöser ist der Übergabe-Moment, nicht ein Wort im PR-Text. Verankert in writing-hub#862 mit dem konkreten Vorschlag: der lesende Teil muss einmal echt gelaufen sein, sonst gehört „ungeprüft" in das Skript selbst. |
| `scope-checkpoint-not-durably-recorded` | **wirksam, aber am falschen Ende** — der Hook fing ihn, der Agent nicht. Kein Umbau vorgeschlagen: ein Melder, der greift, ist besser als keiner. Der Befund gehört zum Agenten. |

**Gefangen (Wirksamkeits-Beleg):**

- `claim-before-cheapest-check` — feuerte in diesem Increment **viermal** und war jedes
  Mal berechtigt: zweimal auf CI-Status ohne Lauf, einmal auf eine Absenz-Behauptung
  über die GPU-Box, einmal auf eine universelle Aussage. Der dritte Fall entzog einer
  eigenen Aussage die Grundlage (die Dateisuche lief in einen Timeout) — ohne das Gate
  wäre sie stehengeblieben.
- `untested-command-scanner` — feuerte dreimal auf weitergereichte Befehle. Zweimal war
  es formal ein Fehlalarm (ich hatte den Befehl ausgeführt, nur anders geschrieben als
  gezeigt), einmal traf er hart: ein Befehl mit `<id>`-Platzhalter. Der Fix für alle drei
  war derselbe: Artefakt und Ausführung identisch machen, also Datei statt Textblock.
- `scope-checkpoint-not-durably-recorded` — siehe oben.

## 5b. Autonomie-Kalibrierung

`over_ask = 0`, `over_act = 0`. Jede Prod- und Merge-Aktion trägt eine wörtlich benannte
Freigabe. Der Wegwerf-Stack (eigene DB, eigener Port, eigenes Konto) fällt unter Step 1.7
des `/ux-review`-Skills und wurde vollständig abgeräumt — verifiziert: Server aus, DB
gelöscht, beide Arbeitsbäume mit 0 Einträgen.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

```markdown
---
name: drift-sonde-am-falschen-substrat
description: Prozess nicht gefunden heißt nicht abwesend — er kann in WSL, einem Container oder einer VM laufen
metadata:
  type: project
  drift: true
  drift_episode: 2026-08-29-ci-gpu-runner-in-wsl
---

Am 2026-08-29 erklaerte ich den `ci-gpu`-Runner auf DESKTOP-G1MN89S fuer tot: kein
Prozess auf `*Runner*`, kein Actions-Dienst, keine geplante Aufgabe, keine Installation
an acht ueblichen Pfaden auf C: und D:. Die Filter-Positivkontrolle bestand (`svchost`
106 gegen `Runner` 0) — die Sonde war also in Ordnung, sie sass nur auf dem falschen
Substrat. Der Runner laeuft in **WSL Ubuntu**: `/opt/actions-runner-writing-hub`,
`Runner.Listener` und `Runner.Worker` je ein Prozess.

Der Hinweis stand woertlich im Workflow-Kommentar, den ich in derselben Sitzung selbst
zitiert hatte: `platform bootstrap_ci_runner_wsl.sh`.

**Why:** Eine bestandene Positivkontrolle beweist, dass der Filter funktioniert — nicht,
dass er am richtigen Ort schaut. Auf einem Windows-Host mit WSL, Docker Desktop oder
Hyper-V gibt es mehrere Prozessraeume, und `tasklist` sieht nur einen davon.

**How to apply:** Vor „Prozess X laeuft nicht auf Maschine Y": erst fragen, **worin** er
laufen wuerde. `wsl -l -v`, `docker ps`, `systemctl` — je nach Host. Und: wenn ein
Kommentar im eigenen Repo den Installationsweg nennt, ist er die erste Quelle, nicht die
letzte. Verwandt: [[drift-messung-per-read-host-belegt-nichts]],
[[drift-pruefung-erkennt-eigenen-leerlauf-nicht]].
```

```markdown
---
name: drift-gruener-rerun-ist-kein-flake-beweis
description: Ein grüner Re-Run beantwortet „deterministisch?", nicht „harmlos?" — der Log sagt, welche Klasse vorliegt
metadata:
  type: project
  drift: true
  drift_episode: 2026-08-29-outlinetiefelauf-undefined-table
---

Am 2026-08-29 wurde PR #846 gemergt, weil ein Re-Run derselben SHA gruen war. Der Log des
roten Laufs zeigte aber keinen Playwright-Timing-Fehler, sondern
`psycopg2.errors.UndefinedTable: relation "outlines_outlinetiefelauf" does not exist` —
ein Schema-Fehler. Dieselbe Meldung war vor #846 in 60 Laeufen nie aufgetreten und trat
danach identisch auf PR #854 auf, dessen Diff nur `.github/workflows/deploy.yml` aendert.

**Why:** Ein Re-Run misst Determinismus, nicht Harmlosigkeit. Ein nichtdeterministischer
Fehler kann trotzdem ein echter Defekt sein.

**How to apply:** Bevor „Flake" faellt: den Log lesen und die Fehlerklasse benennen.
Timeout/Netz/Browser → Flake plausibel. Schema, Import, Migration, Datei fehlt → kein
Flake, sondern ein Defekt, der sich nur manchmal zeigt. Verfolgt in writing-hub#859.
```

### adr_candidates

Keine. Runner-Zuteilung, Job-Zuschnitt und ein Feature nach vorhandenem Muster sind
Konfiguration und Zubau in je einem Repo, kein Systemschnitt (`policies/adr-threshold.md`).

## 7. Maßnahmen

**✅ Im selben Zug erledigt**

| # | Item | Artefakt |
|---|---|---|
| I3, I4 | Beide Klick-Befunde behoben, je mit Klassen-Gate und Gegenprobe | writing-hub#864 |
| I5 | Rückfälliges Gate als Klasse verankert | writing-hub#862 |
| I2 | Fehlerbild samt Hypothese und billigstem Check | writing-hub#859 |
| I8 | Deploy-Fehlzuteilung behoben und **am Runner-Namen bewiesen** | writing-hub#854, gemergt |
| — | Klick-Durchlauf dokumentiert | writing-hub#869 |

**🔵 Offen — Agent**

| # | Item | Next Step |
|---|---|---|
| — | #864 mergen | Sobald CI grün |
| I7 | Handover | In dieser Sitzung nachgezogen |

**🟢 Offen — Owner**

| # | Item | Next Step |
|---|---|---|
| — | Ein CI-Runner ist ein Single Point of Failure | Eigenes Ticket, nicht in #854 gelöst |
| — | Station „Verdikt" blieb blind | Lauf mit gültigem Modell-Schlüssel |

## 8. Nicht verifiziert (Restlücken)

| Was | Billigster Check |
|---|---|
| Die Diskussion mit einer **echten** Modellantwort | Schlüssel in einen eigenen Stack, eine Runde senden |
| Station „Verdikt" im Browser | dito — Station 5 brach vorher ab |
| Ob eine Runner-**Installation** auf C:/D: an ungewöhnlichem Ort liegt | Die Dateisuche lief in einen Timeout; nach dem WSL-Fund ist die Frage gegenstandslos |
| Ursache der fehlenden Tabelle im `live_server` | In einem roten Lauf `\dt` auf der Worker-DB gegen die Basis-DB (#859) |

**Der Vierer:**
**getan** — Deploy-Fix gemergt und am Runner-Namen bewiesen, Prod auf `main-d3c17b8`,
`seed_lookups` auf WeltenHub-Prod, Prod-Umbenennung mit Gegenprobe, neues Feature samt
Klick-Durchlauf und zwei daraus behobenen Defekten, sechs Tracking-Artefakte, Wegwerf-Stack
verifiziert abgeräumt. **angenommen** — dass die Worker-DB-Hypothese in #859 die richtige
Spur ist. **nicht verifizierbar** — die Diskussion gegen ein echtes Modell, mangels
Schlüssel im eigenen Stack. **offen geblieben** — der Merge von #864, der Single Point of
Failure in der CI, Station „Verdikt".
