---
id: ADR-250
title: "Registry-getriebene Edge-Config + Drift-Lint (nginx-vhost/DNS aus repo-registry.yaml)"
status: proposed
date: 2026-06-17
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh, meiki-lra, ttz-lif]
domains: [infra, edge, deploy, cross-repo, monitoring]
supersedes: []
amends: []
depends_on: [ADR-156, ADR-157]
related: [ADR-242, ADR-248]
tags: [nginx, cloudflared, dns, edge, registry, drift, monitoring, cross-repo]
scope:
  include_paths:
    - "docs/adr/ADR-250-*"
---

# ADR-250 — Registry-getriebene Edge-Config + Drift-Lint (nginx-vhost/DNS aus repo-registry.yaml)

## 1. Kontext

Am 2026-06-17 waren **drei Prod-Hubs für Kunden nicht erreichbar**, alle durch
**hand-gepflegte Edge-Config-Drift** — und alle **unentdeckt**, bis ein
neu gebauter externer Canary sie aufdeckte:

- **writing-hub.iil.pet** → 502: nginx `proxy_pass` zeigte auf `:8091` (Port des
  archivierten bfagent), Origin lief auf `:8097`. **Port-Drift.**
- **research.iil.pet** → 502: nginx `proxy_pass :8104`, echter Container-Port `:8098`;
  zusätzlich nutzt der Hub `/healthz/` statt der Konvention `/livez/`. **Port- + Health-Pfad-Drift.**
- **travel-beat.iil.pet** → 000: **kein DNS-Record** und **kein nginx-vhost** (nutzt ein
  eigenes caddy), obwohl der Origin lokal gesund war. **Fehlende Edge-Verdrahtung.**

Gemeinsamer Nenner: die Edge (cloudflared catch-all → nginx-vhost je Host → Container-Port)
wird **manuell** gepflegt, ohne Standard und ohne Abgleich gegen eine Quelle der Wahrheit.
`repo-registry.yaml` deklariert pro Hub bereits `prod_url`, `port`, `health` — aber **nichts
erzwingt**, dass die reale nginx/DNS-Config dazu passt. Das ist dieselbe Klasse wie die
2026-06-15-Outage (COMPOSE-Kollision, ADR-248) und der tote Runner-Label-Pin: **Infra-Drift,
die niemand sieht.**

## 2. Entscheidung

`repo-registry.yaml` wird die **Single Source of Truth** für die Prod-Edge jedes Hubs, und
die reale Edge wird daraus **generiert bzw. dagegen gelintet** — Prinzip **„Standard wo
möglich, individuell wo nötig"**.

**2.1 Standard-Edge (default für jeden deploybaren Hub)**
- cloudflared catch-all → **nginx-vhost aus einem Template**, `proxy_pass` auf den in der
  Registry deklarierten `port`.
- **DNS bei Deploy** via `cloudflared tunnel route dns <tunnel> <prod_url>` (idempotent) —
  kein manuelles Anlegen, das vergessen werden kann (travel-beat-Bug).
- **Health-Pfad-Konvention `/livez/`**; Abweichung nur, wenn in der Registry als
  `health: <pfad>` deklariert (research → `/healthz/`).

**2.2 Drift-Lint (CI-Gate, ubuntu-latest)**
Ein registry-getriebener Audit (Erweiterung von `hosts_audit.py`) prüft je Hub mit `prod_url`:
- nginx `proxy_pass`-Port **==** Registry-`port`,
- es existiert ein **aktiver** nginx-vhost (kein `.disabled`) für die `prod_url`,
- die `prod_url` hat einen **DNS-Record**,
- der `health`-Pfad ist konsistent.
Drift → CI rot, mit konkretem Fix-Hinweis. Fängt die **Ursache** (Config-Drift), während der
Prod-Uptime-Canary (P2) nur das **Symptom** (Outage) fängt.

**2.3 Individuell nur mit Begründung**
Sonder-Edge (z. B. travel-beats caddy, oder ein Hub mit eigener TLS-Terminierung) ist erlaubt,
muss aber in der Registry als `edge: custom` + `reason:` deklariert sein → der Lint überspringt
ihn bewusst statt blind.

## 3. Betrachtete Alternativen

- **Status quo (hand-gepflegt):** die belegte Drift-Quelle dreier Outages an einem Tag. Verworfen.
- **Voll-IaC für die Edge (Terraform/Ansible):** sauberste Reproduzierbarkeit, aber schwergewichtig
  für eine Single-Host-nginx-Topologie; höhere Einstiegshürde. Später möglich; jetzt YAGNI.
- **Nur Monitoring (Canary/Betterstack), keine Generierung:** fängt Outages, aber erst *nachdem*
  Kunden betroffen sind — adressiert die Ursache nicht. Ergänzend, nicht ersetzend.

## 4. Begründung im Detail

Der Hebel ist **Generierung + Lint aus einer SoT**: ist die nginx-Port-Angabe nicht mehr
hand-getippt, sondern aus `registry.port` erzeugt/geprüft, ist „Port-Drift wie bei writing-hub"
**strukturell unmöglich**. Das ist die Edge-Entsprechung zu ADR-248 (COMPOSE_PROJECT_NAME pinnen)
und zum Runner-Label-Gate — dieselbe Lehre (Infra-Transparenz als hartes Gate statt Notizzettel).

## 5. Implementation Plan

1. `repo-registry.yaml` als Edge-SoT bestätigen (`prod_url`/`port`/`health` je Hub; `edge: custom`
   + `archived: true` als Felder — letzteres bereits eingeführt für bfagent).
2. `hosts_audit.py` um `--check edge` erweitern: Registry ↔ nginx-`proxy_pass`-Port ↔ DNS ↔ vhost-aktiv.
3. Lint als CI-Job (ubuntu-latest) — analog zum Runner-Label-Check.
4. Optional Stufe 2: nginx-vhost + `cloudflared route dns` beim Deploy **generieren** statt nur linten.

## 6. Risiken

- Lint braucht Lesezugriff auf die reale nginx/DNS-Config (Prod-Host) — read-only SSH oder ein
  vom Host exportierter Snapshot; kein Schreibzugriff im Lint.
- Registry muss gepflegt werden — aber sie ist ohnehin schon SoT für Ports/Monitoring.

## 7. Konsequenzen

- (+) Port-/DNS-/Health-Drift als Outage-Klasse eliminiert; Canary fängt nur noch echte Ausfälle.
- (+) Neuer Hub: ein Registry-Eintrag → Edge generiert/geprüft, kein hand-getipptes vhost.
- (−) Ein Generierungs-/Lint-Schritt mehr im Deploy; Sonderfälle müssen deklariert werden.

## 8. Validation Criteria

- Ein bewusst falsch gesetzter nginx-Port (≠ Registry) lässt den Lint **rot** werden.
- Eine `prod_url` ohne DNS-Record lässt den Lint **rot** werden.
- Kein Prod-Hub mehr extern down bei gesundem Origin (writing/research/travel-Klasse).

## 9. Glossar

- **Edge:** cloudflared-Tunnel → nginx-vhost → Container-Port; der Weg von außen zum Origin.
- **Drift:** reale Config weicht von der deklarierten SoT ab, ohne dass es jemand bemerkt.

## 10. Referenzen

- Outage-Triage 2026-06-17 (writing-hub/research/travel-beat), Prod-Uptime-Canary (platform#586).
- ADR-242 (Branch-Protection-Rulesets), ADR-248 (COMPOSE_PROJECT_NAME), ADR-156/157 (Deploy/Staging).
- `platform/infra/scripts/hosts_audit.py`, `platform/infra/hosts.yaml`, `scripts/repo-registry.yaml`.

## 11. Changelog

- 2026-06-17: Initial (proposed) — aus dem Prod-Hub-Outage-Triage (3 Hubs, Edge-Drift) +
  der Standardisierungs-Frage „standard wo möglich, individuell wo nötig".
