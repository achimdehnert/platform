# Restore-Feuerübung 2026-08-30 — Host-Konfiguration `prod` (Tag `config`)

> Ausführung: Kapitäns-Kanal (Claude Code), Host `prod`, ohne Rückstände (Wegwerf-Verzeichnis per `trap` entfernt).
> Anlass: KONZ-platform-054 §12, Punkte 125–127 (Owner-Go 2026-08-30). Bis zu diesem Tag sicherte kein
> Snapshot einen Pfad unter `/etc` oder `/opt` — Datenbanken und Volumes ja, der Host selbst nicht.

| | |
|---|---|
| Quell-Snapshot | `675a3af4` · Tag `config` · 2026-08-30T10:39:58Z (32 s alt beim Restore) |
| Quelle des Snapshots | erster Lauf des neuen `config`-Blocks aus `infra/host-maintenance/prod-offsite-daily.sh` (#2503): 130 Pfade, 391 Dateien, 26,6 MiB (10,6 MiB gespeichert) |
| Restore-Ziel | `/mnt/HC_Volume_105908261/restore-drill-config-20260830T104032Z` (Wegwerf, per `trap` gelöscht) |
| Restore-Umfang | 667 Dateien/Verzeichnisse, 26,6 MiB |
| RTO-Ist | **1 s** Restore · Soll für Konfiguration: nicht definiert (ADR-241 nennt nur risk-hub 4 h) |

## Vergleich gegen live (`diff -rq`)

| Pfad | Ergebnis |
|---|---|
| `/etc/nginx/sites-enabled` | identisch |
| `/etc/nginx/nginx.conf` | identisch |
| `/root/.cloudflared` (Tunnel-Credential) | identisch |
| `/etc/cron.d` | identisch |
| `/etc/fstab` | identisch |

Compose- und `.env`-Dateien je App im Restore: **119**. Stichprobe: `/opt/risk-hub/docker-compose.prod.yml` parst als YAML, das Tunnel-Credential parst als JSON.

## Was der Drill belegt — und was nicht

Belegt: Der Snapshot `config` ist vollständig, unverändert und in Sekunden rückspielbar. Ein neuer Host bekäme nginx-vhosts, Tunnel-Credential, Cron, systemd-Units, Compose und `.env` je App aus dem Backup.

Nicht belegt: ein **Wiederanlauf** — dafür fehlen der restic-Schlüssel außerhalb von prod (Escrow, platform#2504) und ein Lauf auf einem leeren Host. Der Drill beweist die Datei, nicht den Weg.

## Auffälligkeiten

- Der Snapshot enthält `/opt/actions-runner-*/.env` (28 Runner-Verzeichnisse, davon 8 verwaist — Rückbau-Liste KONZ-054 §12.6). Kein Schaden, aber Ballast.
- `/etc/offsite-backup.env` ist im Snapshot enthalten. Das Repo ist verschlüsselt; wer den restic-Schlüssel hat, hat damit auch diesen. Das ist die Begründung für das Escrow **getrennt** vom Backup.
