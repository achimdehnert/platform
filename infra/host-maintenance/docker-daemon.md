# Docker-Praevention dev-desktop (platform#2895 Item 98)

`/infra-cleanup dev-desktop` Trockenlauf 2026-09-07: Docker-Images 84 GB (74 GB
freigebbar), Build-Cache 8,3 GB, 8 dangling Images, 21 gestoppte Container
(davon 17 bewusst mit `restart=no` — die duerfen NIE weggeraeumt werden). Von
den drei Praeventions-Ebenen (P1 Log-Rotation, P2 Builder-GC, P3 Prune-Timer)
fehlte auf diesem Host **keine** — anders als bei prod (siehe `README.md`),
wo P3 die eigentliche Luecke war. Dieses Bundle liefert alle drei fuer
dev-desktop, IaC-only: **nichts davon ist auf dem Host angewendet**, Apply ist
ein bewusster Owner-Schritt (Refs #2895).

## Warum eigene Werte statt `daemon.json.recommended`

`daemon.json.recommended` in diesem Verzeichnis ist die generische Vorlage
(log-opts 20m/3, builder-GC 20GB) fuer neu bootstrappte Hosts
(`netcup-bootstrap.sh`). `docker-daemon.json` hier ist dev-desktop-spezifisch,
gegen den gemessenen Profil dieses Hosts kalibriert:

| Feld | Wert | Warum |
|---|---|---|
| `log-opts.max-size` | `50m` | dev-desktop faehrt 36 laufende Container inkl. Dauerdiensten (kd-server, ollama, robo-twin) — grosszuegiger als die generische Vorlage, damit Log-Rotation nicht selbst zur Betriebsstoerung wird |
| `log-opts.max-file` | `3` | wie generische Vorlage — 3 Rotationen reichen fuer Nachschau ohne Platzverbrauch |
| `builder.gc.enabled` | `true` | Build-Cache stand am 2026-09-07 bei 8,3 GB ungebremst |
| `builder.gc.defaultKeepStorage` | `"10GB"` | String mit Einheit (Docker-Doku-Syntax, keine Zahl) — deckt den gemessenen Cache mit Puffer, ohne die 339 GB freien Platz zu verschenken |

## Wirkung

- **P1 (Log-Rotation):** begrenzt `json-file`-Logs pro Container auf 150 MB
  (`50m` × `3`) statt unbegrenzt — verhindert den Leck-Typ aus dem
  prod-Incident 2026-06-03 (siehe `README.md`), falls hier je ein Container
  in eine Log-Schleife laeuft.
- **P2 (Builder-GC):** deckelt den Build-Cache bei 10 GB — greift aber NICHT
  gegen ungenutzte Images (siehe P3), das war exakt die prod-Luecke.
- **P3 (`docker-prune.timer`):** taeglich 05:30 (vor `flottenbild.timer` um
  06:10, damit das Flottenbild den aufgeraeumten Stand zeigt) `docker image
  prune -f` (nur dangling) + `docker builder prune -f --keep-storage 10GB`.
  **Bewusst NICHT** `container prune` (17 gestoppte Container mit
  `restart=no` sind Absicht, kein Leck), **NICHT** `volume prune`, **NICHT**
  `image prune -a` ohne Altersfilter (wuerde auch von den gestoppten
  Containern referenzierte Images ziehen).

## Rollback

```bash
rm /etc/docker/daemon.json && systemctl restart docker
```

Timer separat stoppen (unabhaengig von daemon.json):
```bash
systemctl disable --now docker-prune.timer
```

## Install (Owner-Schritte, sudo — bewusster Schritt, nicht Teil dieses PR)

> ⚠️ `systemctl restart docker` bouncet **alle** Container auf dem Host —
> auch laufende robo-lab-/ollama-Prozesse (siehe `infra/hosts.yaml` Rolle
> dev-desktop). Fenster waehlen, in dem kein Trainings-/Inferenzlauf aktiv ist.

```bash
# 0. Vorher-Zustand sichern (Diff-Basis)
ssh devuser@88.99.38.75 "docker info -f '{{json .LogConfig}}'"
ssh devuser@88.99.38.75 "df -h /"

# 1. Dateien auf den Host kopieren
scp infra/host-maintenance/docker-daemon.json root@88.99.38.75:/etc/docker/daemon.json.new
scp infra/host-maintenance/docker-prune.sh     root@88.99.38.75:/opt/infra/docker-prune.sh
scp infra/host-maintenance/docker-prune.{service,timer} root@88.99.38.75:/etc/systemd/system/

# 2. daemon.json einspielen (Backup des Alten, falls vorhanden — nie klobbern)
ssh root@88.99.38.75 '
  [ -f /etc/docker/daemon.json ] && cp /etc/docker/daemon.json /etc/docker/daemon.json.bak-$(date +%Y%m%d%H%M%S)
  mv /etc/docker/daemon.json.new /etc/docker/daemon.json
  chmod +x /opt/infra/docker-prune.sh
'

# 3. Docker-Daemon neu starten (bewusst — bouncet alle Container, siehe Warnung oben)
ssh root@88.99.38.75 'systemctl restart docker && docker info -f "{{json .LogConfig}}"'

# 4. Prune-Timer aktivieren
ssh root@88.99.38.75 '
  systemctl daemon-reload
  systemctl enable --now docker-prune.timer
  systemctl list-timers docker-prune.timer
'

# 5. Nachher-Messung
ssh devuser@88.99.38.75 "df -h /"
```

## Changelog
- 2026-09-07: Initial — Docker-Praevention dev-desktop (`/infra-cleanup`
  Trockenlauf, platform#2895 Item 98). IaC-only, Apply = Owner.
