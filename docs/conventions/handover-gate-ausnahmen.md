# Ausnahmen vom Frische-Gate `handover-stale-vor-merge`

> Gehört zu [#1945](https://github.com/achimdehnert/platform/issues/1945) Kriterium 2.
> Erhoben mit `python3 tools/handover_fleet_check.py --gate` am **2026-08-13** (54 aktive
> Registry-Repos). Zum Nachziehen: dasselbe Kommando erneut laufen lassen — zwei Läufe
> liefern identische Ergebnisse.

Kriterium 2 verlangt: das Gate läuft in jedem aktiven Repo — **oder** das Repo steht hier
mit Begründung, „so fein wie der Befund, keine Pauschal-Ausnahmen".

## Der Stand in einem Satz

Von 54 aktiven Repos tragen **23** ein `AGENT_HANDOVER.md`. Von diesen 23 haben nach dem
Rollout **alle** das Gate. Die übrigen **31** stehen unten — nicht weil das Gate dort
unerwünscht wäre, sondern weil es dort **nichts zu prüfen** gibt.

## Ausnahmegrund: kein Handover-Dokument vorhanden

Das Gate hängt an einem `paths`-Filter auf `AGENT_HANDOVER.md`. Existiert die Datei nicht,
läuft der Workflow nie an — ein Caller wäre eine Zeile Konfiguration, die nichts tut, und
genau solche Zeilen erzeugen später den Eindruck, ein Repo sei abgedeckt.

Der Grund ist **je Repo gemessen**, nicht pauschal nach Typ vergeben: er stammt aus der
Datei-Erhebung über die GitHub-API, nicht aus einer Regel wie „Bibliotheken brauchen keins".

| Repo | Owner | Befund am 2026-08-13 |
|---|---|---|
| 137-hub | achimdehnert | kein `AGENT_HANDOVER.md` |
| bahn-hub | achimdehnert | kein `AGENT_HANDOVER.md` |
| billing-hub | achimdehnert | kein `AGENT_HANDOVER.md` |
| cad-hub | achimdehnert | kein `AGENT_HANDOVER.md` |
| coach-hub | achimdehnert | kein `AGENT_HANDOVER.md` |
| dev-hub | achimdehnert | kein `AGENT_HANDOVER.md` |
| gaeb-toolkit | achimdehnert | kein `AGENT_HANDOVER.md` |
| ifc-mcp | achimdehnert | kein `AGENT_HANDOVER.md` |
| iil-codeguard | achimdehnert | kein `AGENT_HANDOVER.md` |
| iil-enrichment | achimdehnert | kein `AGENT_HANDOVER.md` |
| iil-fieldprefill | iilgmbh | kein `AGENT_HANDOVER.md` |
| iil-ingest | achimdehnert | kein `AGENT_HANDOVER.md` |
| iil-relaunch | iilgmbh | kein `AGENT_HANDOVER.md` |
| illustration-fw | iilgmbh | kein `AGENT_HANDOVER.md` |
| infra-deploy | achimdehnert | kein `AGENT_HANDOVER.md` |
| lastwar-bot | achimdehnert | kein `AGENT_HANDOVER.md` |
| learn-hub | achimdehnert | kein `AGENT_HANDOVER.md` |
| learnfw | achimdehnert | kein `AGENT_HANDOVER.md` |
| mcp-hub | achimdehnert | kein `AGENT_HANDOVER.md` |
| nl2cad | achimdehnert | kein `AGENT_HANDOVER.md` |
| nl2iot-hub | iilgmbh | kein `AGENT_HANDOVER.md` |
| odoo-hub | achimdehnert | kein `AGENT_HANDOVER.md` |
| onboarding-hub | achimdehnert | kein `AGENT_HANDOVER.md` |
| outlinefw | achimdehnert | kein `AGENT_HANDOVER.md` |
| pptx-hub | achimdehnert | kein `AGENT_HANDOVER.md` |
| recruiting-hub | achimdehnert | kein `AGENT_HANDOVER.md` |
| riskfw | achimdehnert | kein `AGENT_HANDOVER.md` |
| schutztat-reporting | achimdehnert | kein `AGENT_HANDOVER.md` |
| ttz-hub | ttz-lif | kein `AGENT_HANDOVER.md` |
| weltenfw | achimdehnert | kein `AGENT_HANDOVER.md` |
| weltenhub | achimdehnert | kein `AGENT_HANDOVER.md` |

## Was diese Liste NICHT beantwortet — offene Owner-Entscheidung

Diese Ausnahme ist mechanisch korrekt und inhaltlich unbefriedigend. Unter den 31 sind
produktive, aktiv beackerte Systeme: `dev-hub`, `mcp-hub`, `cad-hub`, `coach-hub`,
`learn-hub`, `recruiting-hub`, `weltenhub`, `137-hub`. Dass dort kein Frische-Gate läuft,
ist die Folge davon, dass es dort **gar keinen Handover-Stand** gibt — was der eigentliche
Befund ist, nicht die fehlende Gate-Zeile.

Der Zielzustand aus #1945 lautet: *„Jede Session in jedem aktiven Repo startet mit einem
vorhandenen, frischen und maschinell auf Veraltung geprüften Handover-Stand."* Für diese 31
Repos ist bereits das erste Wort — *vorhanden* — nicht erfüllt.

**Das ist eine Owner-Entscheidung, keine Mechanik-Frage**, und sie wird hier bewusst nicht
still beantwortet: ein automatisch erzeugtes Handover-Skelett in 31 Repos wäre 31 Dateien,
die ab Tag 2 veralten und dann ein grünes Gate tragen — schlimmer als keine Datei, weil das
Gate dann Frische *bescheinigt*, wo niemand etwas pflegt.

Denkbare Wege, absteigend nach Aufwand:

1. **Handover nur dort, wo Sessions laufen** — Kriterium: Repo hatte in den letzten 90 Tagen
   eine Session/PR. Messbar mit denselben Mitteln wie diese Liste.
2. **Handover in allen aktiven Repos**, Rollout gestaffelt, Gate erst nach dem ersten
   echten Stand-Block scharf.
3. **Bewusst dabei bleiben**: Handover ist ein platform-/hub-Werkzeug, Bibliotheken und
   Infra-Repos brauchen keins — dann gehört genau dieser Satz als Regel hierher, und die
   Liste schrumpft auf die Repos, die er nicht deckt.

Tracking: [#1945](https://github.com/achimdehnert/platform/issues/1945) (Kommentar zur
Erstmessung). Solange die Entscheidung offen ist, gilt Kriterium 2 als **im erreichbaren
Umfang erfüllt** — nicht als vollständig.
