---
description: Host-Ressourcen sicher zurückgewinnen (Disk/Docker/Runner-Caches) — dry-run-first, gestaffelt, gegated
mode: write
---

# /infra-cleanup — Host Resource Reclamation (gated, tiered, dry-run-first)

> **Zweck:** Plattenplatz auf einem (self-hosted Runner-/App-)Host zurückgewinnen —
> Docker-Images/Build-Cache, Runner-`_work`-Caches — **gestaffelt, gemessen, bis zu
> einer Ziel-Schwelle**, mit Dry-run als Default und hartem Confirm-Gate vor jeder
> destruktiven Aktion. Erkennt zusätzlich Präventions-Lücken und **empfiehlt** sie
> (wendet sie NICHT an).
>
> **Wann:** Host läuft voll (`df` nahe 100 %), CI-Jobs scheitern mit
> `No space left on device`, oder periodische Hygiene.
> **Wann NICHT:** reine Diagnose ohne Aufräumen → `/infra-health` (read-only).
>   Config-Prävention anwenden (daemon.json/Timer, Daemon-Restart) → bewusster
>   eigener Schritt/PR, NICHT dieser Skill (siehe „Prävention" unten).
> **Abgrenzung:** Geschwister der `infra-`-Familie: `/infra-health` (Status),
> `/infra-overview` (Ports/Drift). Dieser hier ist der einzige mit `mode: write`.

## Verwendung

```
/infra-cleanup <host>                 # Dry-run: zeigt reclaimable pro Tier, ändert NICHTS
/infra-cleanup <host> --apply         # führt gestaffelt aus, stoppt bei --target-free
/infra-cleanup <host> --target-free 30G   # Schwelle (default 20G)
/infra-cleanup <host> --tier 1        # nur bis Tier N (1 sicher … 3 _work)
/infra-cleanup <host> --incident      # aggressiverer Default (bei 0 MB)
```

`<host>` = SSH-Ziel (z. B. `root@88.198.191.108`). **NICHT hardcoden** — als Arg
übergeben oder aus Infra-Quelle lesen; self-hosted Runner liegen aktuell auf dem
Prod-Host (Stand verifizieren, nicht annehmen).

## Step 0: Kontext + Connectivity-Gate (PFLICHT)

1. Host bestimmen: `$ARGUMENTS` → `<host>`. Kein Default-Hardcode; bei Unklarheit
   Host aus `platform/infra` bzw. Runner-Inventar lesen, sonst beim User erfragen.
2. **Kein `ping`** (Hetzner blockt ICMP) — TCP-Probe:
   `python3 ${GITHUB_DIR:-$HOME/github}/platform/infra/scripts/server_probe.py --host <ip>`
3. **Prod-Gate (HART):** Ist `<host>` ein Prod-Host, ist `--apply` ein
   ausdrücklich zu bestätigender Prod-Eingriff. Generisches „mach autonom" zählt
   NICHT (House-Rule). Ohne `--apply` immer nur Dry-run.

## Step 1: Recon (read-only, immer)

```bash
ssh <host> 'df -h /; echo "--docker--"; docker system df;
  echo "--_work top--"; du -sh /opt/actions-runner-*/_work 2>/dev/null | sort -rh | head;
  echo "--busy runners--"; for p in $(pgrep -f Runner.Worker); do ls -l /proc/$p/cwd 2>/dev/null | grep -o "/opt/actions-runner-[^/]*"; done | sort -u'
```
→ Tabelle „reclaimable pro Kategorie" + Liste **aktiver** Runner (deren `_work` ist tabu).

## Step 2: Tiers (nur mit `--apply`; nach JEDEM Tier `df` messen, bei Ziel STOPP)

> Reihenfolge = Risiko aufsteigend. Stoppe, sobald `avail ≥ --target-free`.
> **Volumes werden NIE blanket gelöscht** (Datenverlust — gestoppte-Service-Daten).

**Tier 1 — sicher (kein Daten-/Service-Risiko):**
```bash
ssh <host> 'docker container prune -f; docker image prune -f; docker builder prune -f; df -h /'
```
(stopped Container, **dangling** Images, Build-Cache)

**Tier 2 — unused Images, altersgefiltert:**
```bash
ssh <host> 'docker image prune -a -f --filter until=720h; df -h /'   # >30 Tage; schützt frisch gestoppte Services
```
Reicht es nicht (reclaimable steckt in <30-Tage-Images), Filter bewusst senken:
`--filter until=168h` (>7 Tage). **Nie ganz ohne Filter im Routine-Modus.** Laufende
Container und ihre Images bleiben immer unberührt; Entferntes ist re-pullbar (außer
lokal gebaut + ungepusht → vorher prüfen).

**Tier 3 — Runner-`_work` (NUR idle Runner):**
```bash
ssh <host> 'pgrep -f Runner.Worker >/dev/null && { echo BUSY-ABORT; exit 1; } || \
  find /opt/actions-runner-*/_work -mindepth 1 -maxdepth 1 ! -name _tool ! -name _actions -exec rm -rf {} +; df -h /'
```
Entfernt Repo-Checkouts + `_temp`/`_diag`, **behält `_tool`** (Python-Cache, sonst Re-Download)
**und `_actions`**. Guard bricht ab, wenn ein Job läuft. `_tool` zusätzlich nur mit
explizitem Wort (`--include-tool`) — bringt mehr GB, kostet Re-Download.

## Step 3: Präventions-Befund (Advisory — NICHT anwenden)

Erkennen und im Report ausweisen (Fix bleibt bewusster Extra-Schritt):
- **P1 Log-Rotation:** `docker info -f '{{.LoggingDriver}}'` + `/etc/docker/daemon.json`
  ohne `log-opts max-size/max-file` → Container-Logs wachsen unbegrenzt.
- **P2 Builder-GC:** `daemon.json` ohne `builder.gc.defaultKeepStorage` → Cache uncapped.
- **P3 kein scheduled Cleanup:** kein systemd-Timer/Cron für periodisches Tier 1.
- **P4 Runner-`_work`-Auto-Clean** nicht aktiv.
> ⚠️ P1/P2 erfordern `systemctl restart docker` (bouncet alle Container) → **eigener
> gegateter PR/Routine**, nicht dieser Skill. Hier nur „erkannt → empfohlen".

## Output-Format

```
/infra-cleanup <host> — <datum>  (mode: dry-run|apply · target-free: <N>G)
BEFORE: df / = <used>/<size> (<avail> avail)
| Tier | Aktion | reclaimable | ausgeführt | frei danach |
|------|--------|-------------|------------|-------------|
| 1 | container/dangling/build-cache | … | ja/nein | … |
| 2 | image -a until=<h> | … | … | … |
| 3 | _work (idle, keep _tool) | … | … | … |
Volumes: <X>G reclaimable — NICHT angefasst (Datenverlust-Gate)
Prävention: P1 <ok/fehlt> · P2 <ok/fehlt> · P3 <ok/fehlt> · P4 <ok/fehlt>
Ergebnis: avail <vorher> → <nachher> (Ziel <N>G <erreicht/verfehlt>)
```

## Anti-Patterns

- ❌ `docker system prune --volumes` / blanket Volume-Löschung → Datenverlust.
- ❌ `image prune -a` **ohne** `until`-Filter im Routine-Modus (entfernt frisch gestoppte Services).
- ❌ `_work` eines Runners mit **aktivem Job** anfassen (Guard ist Pflicht).
- ❌ `_tool`/`_actions` löschen ohne explizites `--include-tool` (unnötiger Re-Download).
- ❌ `/etc/docker/daemon.json` ändern oder `docker restart` als Cleanup-Nebenwirkung — Prävention ist ein eigener bewusster Schritt.
- ❌ Host hardcoden statt als Arg/aus Infra-Quelle.
- ❌ `--apply` auf Prod ohne ausdrückliche Freigabe (generische Autonomie zählt nicht).
- ❌ Über die Schwelle hinaus prunen — bei `avail ≥ target-free` stoppen.

## Changelog

- 2026-06-03: Initial. Entstanden aus dem Prod-0-MB-Incident (88.198.191.108, `/` 100 %).
  Design adversarial reviewt (D1–D8): dry-run-first, gestaffelt+gemessen+self-terminating,
  Volume-Datenverlust-Gate, Job-Safety-Guard, host-agnostisch, Prävention nur Advisory
  (kein Daemon-Restart als Nebenwirkung). Split von der Prävention bestätigt.
