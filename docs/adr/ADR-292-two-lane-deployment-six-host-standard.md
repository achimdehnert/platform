---
status: proposed
decision_date: 2026-08-02
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: [ADR-157, ADR-289]
related: [ADR-164, ADR-248, ADR-257, ADR-241]
implementation_status: partial
last_reviewed: 2026-08-02
staleness_months: 6
tags: [infrastructure, deployment, hosts, standardisierung, two-lane, governance]
---

<!-- supersedes-waiver: Ergaenzt ADR-157/ADR-289 (siehe amends:), loest sie nicht ab — kein Sprawl-Beitrag nach KONZ-011/ADR-264. Frontmatter-Feld nicht moeglich: das ADR-Schema verbietet Zusatzfelder. -->

# ADR-292: Two-Lane-Deployment auf dem 6-Host-Bestand — Standard vor Speziallösung

> **Nummern-Hinweis:** 292 = nächste freie Nummer zum Draft-Zeitpunkt; final allokiert
> zur Merge-Zeit (ADR-228).

## Metadaten

| Attribut   | Wert |
|------------|------|
| **Status** | Proposed |
| **Scope**  | platform (Deployment-Standard aller Hubs) |
| **Erstellt** | 2026-08-02 |
| **Autor**  | Achim Dehnert (Beschluss), Claude Code (Ausarbeitung) |
| **Amends** | ADR-157 (3-Tier-Anspruch entfällt), ADR-289 (Right-Sizing auf R1) |

## Decision Drivers

Owner-Weisungen vom 2026-08-02 (Chat-Session, Infra-Review):
1. **Standardisierung vor Speziallösungen; Rückbau vor Zusatzfunktionen.**
2. **Nur risk-hub und meiki brauchen die aufwändige Lösung** (Preprod-Gate).
3. **Kein Server wird gekündigt** — Ziel ist ein optimales Deployment- und
   Prod-Szenario mit sauberen Standards auf dem Bestand.

Messbasis (2026-08-02, read-only SSH-Probe + Hetzner-API — Details im
Session-Board `infra-zielbild`):
- Nur 2 von 26 Apps hatten ein lebendes Staging; der De-facto-Deploy-Weg war
  bereits Merge→main→Prod. ADR-157s Drei-Stufen-Anspruch war Papierlage.
- Doppelläufe als Symptom fehlender Placement-SSoT: illustration-hub lief
  parallel auf `prod` UND `prod-b` (10 Tage, divergierende DBs möglich);
  risk-/dev-hub-Staging existierte doppelt (88.99.38.75 + 178.104.184.168).
- Kosten Hetzner-Projekt: 390,58 €/M brutto; ~55 GiB RAM lagen brach, während
  `prod` und der Dev-Desktop im Swap standen (Verteilungs-, kein Kapazitätsproblem).

## Entscheidung

### 1. Rollen — jeder Host genau EINE

| Host | Rolle |
|---|---|
| `prod` (88.198.191.108, nbg1) | Prod-Kern: risk-hub, meiki/frist (sobald deployt), Plattform-Identität (authentik, Outline, MCP) + Kern-Hubs. Gov-/Kundendaten NUR hier (DE) |
| `prod-b` (89.167.43.30, hel1) | Prod-Long-Tail: unkritische Hubs. ⛔ nie meiki/frist/Gov (Standort Helsinki, Owner-Auflage 2026-07-22) |
| `staging-dedicated` (178.104.184.168) | **Preprod NUR für Lane G** (risk-hub, meiki). Alles andere entfällt dort |
| Dev-Desktop (88.99.38.75) | NUR Dev + Desktop-Streaming (+ ci-nonprod-Runner bis auf Weiteres, ADR-257) |
| `netcup` (152.53.136.219) | NUR Offsite-Backup (ADR-289 R1, append-only). R2–R4 vertagt |
| `odoo` (46.225.127.211) | Odoo + Monitoring-Stack (einziger der Flotte); `prod`/`prod-b` melden sich dort per node_exporter an |

### 2. Zwei Deployment-Lanes — sonst nichts

- **Lane S (Standard, alle Hubs außer Lane G):** PR → shared-ci Required Checks →
  Merge auf main → Auto-Deploy auf den Host laut `prod_host` (ports.yaml) →
  Health-Check → bei Rot Rollback. Kein Staging. Bekannte Disziplin bleibt:
  Fixes vor push:main bündeln (kein Staging = Prod).
- **Lane G (Gated, NUR risk-hub + meiki/frist):** PR → CI → Preprod-Deploy auf
  `staging-dedicated` → Smoke-/Playwright-Check → manuelle Owner-Freigabe
  (No-Auto-Prod) → Prod-Deploy auf `prod`.
- Neue Ausnahmen (weitere Lane-G-Repos, stehendes Staging) nur per neuem
  Owner-Beschluss; Bedarfs-Umgebungen dann **ephemer** (Stunden-Server per API),
  nicht stehend.

### 3. Invarianten (prüfbar)

1. **Genau-ein-Ort:** Jede App läuft in Prod auf genau einem Host — genau ein
   Compose-Projekt (COMPOSE_PROJECT_NAME, ADR-248), ein Host-Port aus
   ports.yaml (ADR-164), ein Ingress (Tunnel ODER vhost).
2. **Placement-SSoT:** `infra/ports.yaml` Feld `prod_host` (Default `prod`).
   Deploy-Workflows lesen es; Handverteilung ist ein Regelverstoß.
3. **Register = Realität:** Freeze-/Rollen-Register (#1314, hosts.yaml) müssen
   dem `docker ps`-Ist entsprechen; Abweichung ist ein Befund.

## Konsequenzen

**Positiv:** Ein beschlossener statt behaupteter Standard; Doppelläufe werden
Regelverstöße mit SSoT-Prüfpfad; Preprod-Aufwand konzentriert sich auf die zwei
Repos mit echten Kunden-/Bürgerdaten; keine Kündigungen, keine Neubauten.

**Negativ / akzeptiert:** 24 Hubs deployen ohne Vorstufe direkt auf Prod
(Absicherung: CI-Gates, Offsite-Backup, Rollback); `prod` bleibt SPOF —
Monitoring-Anmeldung am odoo-Stack ist die 0-€-Minderung; Helsinki-Host trägt
dauerhaft Long-Tail (Standort-Auflage dokumentiert).

**Amendments:**
- **ADR-157:** Das universelle dev/staging/prod-Modell ist aufgehoben; Port-
  Governance (ports.yaml als SSoT) gilt unverändert fort.
- **ADR-289:** Right-sized auf R1 (Offsite-Backup). R2 (Monitoring), R3
  (CI-Runner), R4 (DR-Standby) sind vertagt und brauchen je einen neuen Beschluss.

## Umsetzung / Stand 2026-08-02

Bereits ausgeführt (Owner-Go im Chat):
- illustration-hub-Doppellauf aufgelöst: Traffic-Route per Marker-Request
  verifiziert (prod-b bedient `illustration.iil.pet`), prod-Kopie gestoppt
  (`--restart=no`, Volumes bleiben), `/health/` danach 200.
- Alt-Snapshot `risk-hub-pre-deploy-20260513` (68,9 GB, ~0,90 €/M) gelöscht.
- Compose-Drift-PRs für 6 Hubs angestoßen (ausschreibungs-, risk-, tax-,
  trading-, wedding-, writing-hub).

Offen (getrackt im Session-Board `infra-zielbild`, Übernahme in Issues beim
Merge dieses ADRs):
- Staging-Doppelung + Leichen-Container auf dem Dev-Desktop entfernen.
- Freeze-Abgleich #1314 (pptx-hub läuft trotz Freeze — stoppen oder Register ändern).
- Long-Tail-Umzugswelle prod→prod-b, danach Swap-Messung (Resize nur bei Bedarf).
- node_exporter-Anmeldung prod/prod-b am odoo-Prometheus.
- Lane-G-Verdrahtung für meiki/frist beim ersten Deployment (läuft heute nirgends).
