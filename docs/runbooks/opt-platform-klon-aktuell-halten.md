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

> **Der Cron `adr-outline-sync` (Stand 2026-09-16, platform#2353):** `/etc/cron.d/adr-outline-sync`
> ruft täglich 04:00 `. /etc/adr-outline-sync.env && /opt/platform/scripts/sync_adrs_to_outline.sh`.
> Die Env-Datei (`root`, 0600) trägt `OUTLINE_URL`, `OUTLINE_API_TOKEN`, `OUTLINE_COLLECTION_ADR_MIRROR`
> als `export`-Zeilen — der Token steht **nur dort**, nie in der Cron-Zeile (so lag er bis 2026-08-27).
> Beide Dateien haben keine Quelle in `platform/infra`; dieser Absatz ist ihre Beschreibung.
> **Rotation:** Outline 1.6.0 erlaubt `apiKeys.create`/`delete` nicht per API-Key; der Weg ist eine
> Hash-Zeile in `apiKeys` (`sha256`, `last4`) und der Soft-Delete des alten Keys — Skriptmuster in
> #2353 (2026-09-16). Konsumenten des Tokens: diese Env-Datei und `~/.secrets/outline_api_token`
> (MCP `outline-knowledge`, `mcp-hub/scripts/start-outline-mcp.sh`).

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

## Ziehen — automatisch (Entscheid 2026-08-03)

Der Owner hat sich in [#1585](https://github.com/achimdehnert/platform/issues/1585)
für den **automatischen** Sync entschieden. Zuständig ist
`.github/workflows/opt-platform-sync.yml`:

| | |
|---|---|
| **Auslöser** | jeder Push auf `main` · täglich 01:15 UTC · `workflow_dispatch` |
| **Läuft auf** | `self-hosted` — derselbe Host wie der Klon, kein SSH nötig |
| **Aktion** | `git pull --ff-only origin main` in `/opt/platform` |

Bewusst **ohne** `paths`-Filter: der Klon soll `main` als Ganzes tracken. Ein
Filter stellte für jeden nicht gefilterten Pfad genau die Drift wieder her, die
der Workflow beseitigt. Der Zeitplan ist Redundanz, kein Ersatz — er fängt
verlorene Push-Läufe und Pushes während eines Runner-Ausfalls.

**Der Job scheitert laut** (DoD-Zeile 2 aus #1585), und zwar bei:

- fehlendem git-Klon unter `/opt/platform`
- lokalen Änderungen im Klon (werden **nicht** überschrieben — dort soll niemand editieren)
- `HEAD != origin/main` **nach** dem Pull

Der letzte Punkt ist der eigentliche Beweis: `git pull` kann mit Exit 0
zurückkehren und den Klon trotzdem hinter `origin/main` lassen, etwa wenn `main`
währenddessen weiterlief. Geprüft wird deshalb der **Zielzustand**, nicht der
Erfolg des Kommandos.

### Von Hand ziehen

Weiterhin möglich, etwa wenn der Runner steht:

```bash
platform/tools/opt-platform-drift.sh --sync
```

Das verändert den Werkzeugstand des nächtlichen Ingests — nie beiläufig, nie aus
dem Session-Runner heraus.

## Zwei unabhängige Signale

Der Workflow ist das Heilmittel, Phase 0.7.3 die unabhängige Gegenprobe: sie
misst den Klon von außen und würde auch dann anschlagen, wenn der Workflow selbst
ausfiele oder stillschweigend nichts täte. Ein Melder, der nur die eigene
Automatik befragt, prüft sich selbst.
