# App Decommission Runbook

Counterpart to onboarding (`/onboard-repo`). Onboarding *creates* a deployment;
decommissioning *tears it down*. This runbook exists because **archiving a repo
does NOT remove its deployment** — the source and the runtime are separate
lifecycles, and skipping the teardown leaves **orphans** that crash-loop on prod
for weeks.

> **Lehre (2026-06-03):** Beim Prod-Audit fanden sich 2 solche Orphans —
> `mcp_hub_discord_bot` (stillgelegt, Token weg) und ein als „lebende App"
> getarnter Halb-Zustand bei `trading_hub`. Repo-archiviert ≠ Deployment-tot.

## Wann dieser Runbook gilt

- Ein Repo wird **archiviert** oder eine App **stillgelegt**.
- Ein Audit findet einen **crash-loopenden Container** ohne aktiven Owner.

## ⚠️ Gate 0 — Tot oder lebendig? (PFLICHT vor jedem `rm`)

Die teuerste Verwechslung ist „toter Orphan" vs. „lebende App mit Daten".
**Erst klassifizieren, dann handeln:**

```bash
ssh root@<host> '
  # Läuft mehr als nur der kaputte Container? (db/redis/worker gesund = LEBT)
  docker ps -a --format "{{.Names}}\t{{.Status}}" | grep "^<app>"
  # Gibt es Daten-Volumes? (pgdata o.ä. = NICHT blind löschen)
  docker volume ls --format "{{.Name}}" | grep -i "<app>"'
```

| Befund | Einordnung | Vorgehen |
|---|---|---|
| nur 1 Container, kein Daten-Volume, crash-loopt | **toter Orphan** | → Schritt 2–5 (löschen ok) |
| mehrere Container `healthy`, Daten-Volume vorhanden | **lebende App** | **STOPP** — keine Decommission ohne Geschäftsentscheidung + Daten-Backup |

## Schritte (nur nach Gate 0 = „toter Orphan", oder nach expliziter Freigabe inkl. Daten)

1. **Backup** (falls Daten-Volumes existieren und nicht nachweislich entbehrlich):
   `pg_dump` / `docker run --rm -v <vol>:/data … tar` → an sicheren Ort. **Vor** allem Weiteren.
2. **Crash-Loop sofort entlasten (reversibel, kein Datenverlust):**
   `docker update --restart=no <container> && docker stop <container>`
   (verhindert auch Wiederkehr beim Reboot; rückgängig via `--restart=always` + `start`).
3. **Container + Image entfernen:**
   `docker rm -f <container>` · `docker rmi <image>` (nur wenn kein anderer Container es nutzt).
4. **Compose-Stack abbauen** (sonst re-creiert der nächste `compose up`/Reboot den Orphan):
   `cd /opt/<app> && docker compose down` — und das `/opt/<app>`-Verzeichnis archivieren/entfernen.
5. **Volumes** — NUR nach bestätigtem Backup/Entbehrlichkeit: `docker volume rm <vol>`.
   Niemals blanket `docker compose down --volumes` ohne Schritt 1.
6. **Aus den Rändern entfernen:** Traefik/Nginx-Route, DNS-Eintrag, Uptime-Monitoring,
   Auto-Deploy-Hook, `repos.json`/`ports.yaml`-Eintrag.
7. **Dokumentieren:** Decommission im zugehörigen Issue vermerken; Issue schließen.

## Anti-Patterns

- ❌ `rm` ohne Gate 0 — eine lebende App + DB-Volume blind löschen = irreversibler Datenverlust.
- ❌ Nur den Container entfernen, den Compose-Stack stehen lassen → Orphan kehrt beim nächsten Deploy/Reboot zurück.
- ❌ `docker compose down --volumes` ohne Backup.
- ❌ Repo archivieren und das Deployment „später" abbauen — „später" wird Wochen-Crash-Loop.

## Beziehung zu den anderen Infra-Werkzeugen

| Concern | Werkzeug |
|---|---|
| Onboarding (Deployment aufbauen) | `/onboard-repo` |
| Disk-Reclaim (on-demand, tiered) | `/infra-cleanup` |
| Standing-Prävention (Timer) | `infra/host-maintenance/` (P3-Timer) |
| **Decommission (Deployment abbauen)** | **dieser Runbook** |

## Changelog
- 2026-06-03: Initial. Aus dem Prod-Orphan-Befund (discord-bot, trading_hub-Verwechslung).
  Schließt die Lifecycle-Drift-Lücke: „Repo archiviert" muss „Deployment abgebaut" auslösen.
