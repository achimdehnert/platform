# Ausnahmen vom Frische-Gate `handover-stale-vor-merge`

> Gehört zu [#1945](https://github.com/achimdehnert/platform/issues/1945) Kriterium 2.
> Erhoben mit `python3 tools/handover_fleet_check.py --gate --aktiv` am **2026-08-13**
> (54 aktive Registry-Repos). Zum Nachziehen: dasselbe Kommando erneut laufen lassen.

Kriterium 2 verlangt: das Gate läuft in jedem aktiven Repo — **oder** das Repo steht hier
mit Begründung, „so fein wie der Befund, keine Pauschal-Ausnahmen".

## Der Stand in einem Satz

Von 54 aktiven Repos tragen **23** ein `AGENT_HANDOVER.md`, und alle 23 haben das Gate
(nachgemessen nach dem Merge der sechs Caller-PRs: „Frische-Gate nicht nachweisbar
verdrahtet: 0"). Für die übrigen 31 hat der Owner am 2026-08-13 **Weg 1** entschieden —
*Handover dort, wo Sitzungen laufen*: **26** bekommen eins, **5** bleiben Ausnahme.

## Die Owner-Entscheidung (2026-08-13): Weg 1

Die frühere Fassung dieser Liste ließ die Frage offen und führte alle 31 Repos ohne
Handover als Ausnahme. Entschieden ist jetzt: ein Repo bekommt ein `AGENT_HANDOVER.md`,
wenn dort in den letzten **90 Tagen mindestens eine Sitzung** lief.

**Gemessen wird die Sitzung, nicht die Aktivität** — und dieser Unterschied ist der Grund,
warum die Entscheidung überhaupt Wirkung hat. Nach der reinen PR-Zahl wären **29 von 31**
Repos „aktiv" gewesen; Weg 1 („nur wo Sitzungen laufen") und Weg 2 („in allen aktiven
Repos") wären praktisch dasselbe gewesen. Gezählt werden deshalb PRs aus
`session/`-Branches (ADR-233) — das Artefakt, das eine Sitzung hinterlässt. Damit trennt
das Kriterium: `infra-deploy` hat einen PR im Fenster, aber **null** Sitzungen; `dev-hub`
hat 127.

Rollout: 26 PRs, je einer pro Repo, angelegt am 2026-08-13. Der erzeugte Block sagt in
seiner ersten Zeile, dass er **kein Sitzungsstand** ist (Begründung unten).

## Die verbleibenden Ausnahmen (5)

Kein Handover-Dokument, keine Sitzung im 90-Tage-Fenster. Das Gate hängt an einem
`paths`-Filter auf `AGENT_HANDOVER.md` — ohne Datei läuft der Workflow nie an, ein Caller
wäre eine Zeile Konfiguration, die nichts tut. Genau solche Zeilen erzeugen später den
Eindruck, ein Repo sei abgedeckt.

| Repo | Owner | Sitzungen/90d | PRs/90d | letzter Push |
|---|---|---|---|---|
| bahn-hub | achimdehnert | 0 | 5 | 2026-07-04 |
| ifc-mcp | achimdehnert | 0 | 0 | 2026-02-07 |
| infra-deploy | achimdehnert | 0 | 1 | 2026-05-30 |
| nl2iot-hub | iilgmbh | 0 | 2 | 2026-07-04 |
| schutztat-reporting | achimdehnert | 0 | 0 | 2026-02-12 |

Der Grund ist **je Repo gemessen**, nicht pauschal nach Typ vergeben. `bahn-hub` ist der
lehrreiche Fall: fünf PRs im Fenster, aber keine einzige Sitzung — dort wurde etwas
geändert, ohne dass jemand mit einem Sitzungsstand gearbeitet hätte.

**Diese Liste ist nicht endgültig.** Läuft in einem der fünf Repos eine Sitzung, wandert es
beim nächsten Messlauf in die andere Gruppe. Der Lauf ist das Kriterium, nicht diese Tabelle.

## Warum der erzeugte Block sagt, dass er kein Stand ist

> **Korrektur 2026-08-13 (Owner-Rückfrage).** Eine frühere Fassung begründete die
> Zurückhaltung mit „31 Dateien, die ab Tag 2 veralten und dann ein grünes Gate tragen".
> Das ist **falsch**, nachlesbar in `agent_handover_freshness_check.py`: der Check
> vergleicht das Datum der Stand-Überschrift mit dem **letzten Commit, der die Datei
> berührt hat** — nicht mit heute. In einem ruhenden Repo bewegt sich keiner der beiden
> Werte, die Differenz bleibt null. Und der Workflow hängt an einem `paths`-Filter, läuft
> dort also ohnehin nie an. Ein Handover in einem ruhenden Repo veraltet nicht — er zeigt
> korrekt den letzten Stand.

Der Einwand, der trägt, betrifft **aktive** Repos: das Gate greift nur, wenn eine PR
`AGENT_HANDOVER.md` anfasst. Eine PR, die ein Issue schließt und den Handover unberührt
lässt, läuft daran vorbei (belegt: apo-hub#56 und #60, zweimal dasselbe Muster). Genau dort
wäre ein hohles Skelett schädlich — eine Datei, die eine Sitzung als Stand liest, während
sie den Tag ihrer Erzeugung beschreibt.

Deshalb trägt der ausgerollte Block einen datierten Kopf, den Hinweis auf seine Herkunft
(Flotten-Rollout, nicht Arbeit am Repo) und eine leere Schritte-Liste. Er behauptet nichts.
Die erste Sitzung im Repo ersetzt ihn.

Unabhängig davon bleibt die Lücke bestehen: eine PR, die den Handover nicht anfasst, sieht
das Gate nie. Dagegen wirkt der Melder aus Kriterium 3
(`handover-prio-zeigt-auf-erledigtes`, Runner-Phase 0.7.4) — er prüft am Sitzungsstart, ob
die Prio auf Erledigtes zeigt, unabhängig davon, ob je eine PR die Datei berührt hat.

## Offen

Die 26 Erstanlage-PRs sind angelegt, aber noch nicht gemergt. Bis dahin gilt Kriterium 2 für
diese Repos als **vorbereitet**, nicht erfüllt — die Dateien existieren dort noch nicht.
Ein Gate-Caller kommt erst, wenn ein echter Stand drinsteht; vorher prüfte er nur, dass das
Erstanlage-Datum mitgezogen wird.
