---
description: Read-only Single-Pane-Infra-Übersicht — Server, App×Umgebung-Ports, Drift (local/staging/prod)
mode: read-only
---

# /infra-overview — Single Pane of Glass

> **Wann:** schneller Gesamtblick „was läuft wo" über alle Umgebungen
> (dev/staging/prod) — Server-Inventar, App×Umgebung-Port-Matrix, Compose-Drift.
> **Wann NICHT:** Deep-Dive Container-Health/Logs eines Servers → `/infra-health`;
> Config↔Server-State-Audit → `/drift-check`; Compose-Compliance → `/compose-audit`.
> Dieses Skill **aggregiert** die SSoT, es ersetzt die Spezial-Audits nicht.

## Verwendung

```
/infra-overview            # offline, deterministisch (kein SSH)
/infra-overview --live     # + read-only TCP-Reachability je Server
```

## Step 0: Platform-Kontext (NICHT hardcoden)

Die SSoT (`infra/ports.yaml`) lebt im **platform**-Repo. Pfad über die
Umgebungs-Konvention, nie literal:

```bash
PLATFORM="${GITHUB_DIR:-$HOME/github}/platform"
```

## Step 1: Übersicht erzeugen (read-only)

```bash
python3 "$PLATFORM/infra/scripts/infra_overview.py"
```

Aggregiert aus `infra/ports.yaml`:
- **Server-Inventar** (dev/staging/prod + IP/Name, ADR-157)
- **App × Umgebung Port-Matrix** (alle Hubs, ein Web-Port pro Umgebung)
- **Compose-Drift** (Port in `ports.yaml` ≠ Compose-File → deploy-blocker)
- **Staging≠Prod-Skew** (ADR-164 will `staging=prod`; markiert bewusste Ausnahmen)

Exit-Code: `0` = keine Compose-Drift, `1` = Drift (CI-tauglich).

## Step 2: Live-Reachability (optional)

```bash
python3 "$PLATFORM/infra/scripts/infra_overview.py" --live
```

Hängt read-only TCP-Probe + Uptime je Server an (delegiert an
`server_probe.py --all`; umgeht ICMP-Blocking). **Kein Write, kein Deploy.**

## Output-Format

```
=== Infra-Overview (read-only) — Quelle: ports.yaml, 24 Apps ===

SERVER
  dev      88.99.38.75      Dev Desktop (Development)
  staging  178.104.184.168  Hetzner Staging (Dedicated)
  prod     88.198.191.108   Hetzner Dedicated (Production)

APP                            dev  staging   prod   drift
  risk-hub                    8090     8099   8090   compose+skew
  trading-hub                 8088     8088   8088   compose
  coach-hub                   8007     8007   8007   ok
  ...

COMPOSE-DRIFT (7/24 betroffen — deploy-blocker)
  ! trading-hub: docker-compose.yml uses 8000:8000 — must change to 8088:8000
  ...

STAGING≠PROD-SKEW (1 — ADR-164 will staging=prod; ggf. bewusste Ausnahme)
  ~ risk-hub: staging=8099 prod=8090

=== DRIFT (compose): 7 (0 = sauber) ===
```

## Anti-Patterns

- ❌ Server-IPs / Ports / Pfade im Skill hardcoden — alles kommt aus `ports.yaml`
  bzw. der `GITHUB_DIR`-Konvention.
- ❌ `--live` als „Health-Check" verkaufen: es ist nur TCP-Reachability, kein
  Container-/App-Health (dafür `/infra-health`).
- ❌ Drift hier „fixen": read-only. Fixes laufen über `/compose-audit` + Deploy.

## Changelog

- 2026-05-30: Initial. MVP-Aggregator (offline-Matrix + Drift; `--live`
  Passthrough an `server_probe.py`). Dogfood: 24 Apps, 7 Compose-Drift,
  1 Staging-Skew, exit 1.
