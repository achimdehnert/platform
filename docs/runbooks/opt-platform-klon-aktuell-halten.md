# Runbook: `/opt/platform` auf Prod aktuell halten

**Gilt für:** prod (`88.198.191.108`), Verzeichnis `/opt/platform`
**Zugehöriges Issue:** [platform#1585](https://github.com/achimdehnert/platform/issues/1585)

## Worum es geht

Der nächtliche Mail-Ingest liest seine Werkzeuge über einen read-only-Mount aus
einem git-Klon auf dem Prod-Host:

```
/opt/platform/tools/mail_agent  ->  /app/mail_tools   (rw=false)
```

**Diesen Klon zieht nichts automatisch.** Gemessen am 2026-08-03: kein `git pull`
in `/etc/cron.d/`, keiner in `/opt/scripts/`, keine systemd-Unit. Der einzige
Cron, der `/opt/platform` überhaupt anfasst (`adr-outline-sync`), liest nur.

Das Reflog zeigt ausschließlich Pulls zu unregelmäßigen Uhrzeiten (05:01, 09:47,
06:01, 07:02, 15:12 UTC) — das sind Handgriffe aus Sessions, kein Zeitplan.
Zwischen dem 2026-07-02 und dem 2026-07-29 lag eine Lücke von **27 Tagen**.

**Folge:** Ein Merge nach `main` wirkt hier nicht. Er sieht nur so aus. Genau
das führte bei PR #1584 zu einer falschen Behauptung im PR-Text („wirksam ohne
Deploy").

## Prüfen (read-only, jederzeit)

```bash
platform/tools/opt-platform-drift.sh
```

Der Check läuft außerdem in **jeder Session** als Phase `0.7.3` des
Session-Start-Runners. Er unterscheidet bewusst zwei Stufen:

| RESULT | Bedeutung | Handlungsbedarf |
|---|---|---|
| `OK` | Klon == `origin/main` | keiner |
| `HINTERHER` | Klon dahinter, **`tools/mail_agent` identisch** | Hygiene — kein Mail-Risiko |
| `DRIFT` | **`tools/mail_agent` weicht ab** | Prod-Befund: Ingest läuft auf altem Werkzeugstand |
| `UNGEPRUEFT` | Host nicht erreichbar | Drift **unbekannt** — nicht als grün lesen |

Die Trennung ist der Punkt: am 2026-08-03 war der Klon 28 Commits hinterher,
`tools/mail_agent/` aber identisch. Eine einzige Stufe hätte diesen harmlosen
Rückstand wie einen Mail-Ausfall aussehen lassen.

## Ziehen (bewusster Prod-Eingriff)

```bash
platform/tools/opt-platform-drift.sh --sync
```

Führt `git pull --ff-only` in `/opt/platform` aus. Das verändert den
Werkzeugstand, mit dem der nächtliche Ingest läuft — **nie beiläufig, nie aus
dem Session-Runner heraus.** Nach jedem Merge, der `tools/mail_agent/` berührt,
ist dieser Schritt fällig.

## Offene Entscheidung

Ob der Sync **automatisch** (Cron/Deploy-Schritt) oder **ausdrücklich manuell**
laufen soll, ist in [#1585](https://github.com/achimdehnert/platform/issues/1585)
noch nicht entschieden — beides ist vertretbar, stillschweigend driften nicht.
Dieses Runbook beschreibt den Ist-Zustand (manuell) und macht ihn prüfbar; es
nimmt die Entscheidung nicht vorweg.

Falls **automatisch** gewählt wird, gilt die zweite DoD-Zeile aus #1585: der Job
muss **laut scheitern**, wenn der Pull nicht durchgeht — ein stiller Fehlschlag
stellt genau den Zustand wieder her, den dieses Runbook beseitigen soll.
