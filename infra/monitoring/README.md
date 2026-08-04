# Fleet-Monitoring — Anmeldung am vorhandenen odoo-Prometheus (ADR-292)

**Zweck:** prod und prod-b melden Host- und Container-Metriken an den einzigen
vorhandenen Monitoring-Stack der Flotte (odoo-Host, `odoo_prometheus` +
`odoo_grafana`). Kein neuer Stack — 0-€-Schritt; der 16-h-blinde OOM-Ausfall vom
2026-07-20 (platform#1303) wird damit sichtbar. Netcup-Monitoring (ADR-289 R2)
bleibt vertagt.

## Rollout (Reihenfolge)

1. **Firewall zuerst — ZWEI Ebenen, beide nötig.** Eingehend TCP 9100 + 9338
   NUR für die odoo-Host-IP `46.225.127.211` freigeben. Ohne diese Regeln
   bleiben die Exporter offen erreichbar — nicht deployen.
   1. **Hetzner-Cloud-Firewall** (Owner, Cloud-Console): Regeln in `prod-web`
      bzw. `prod-b-web`.
   2. **Lokale Host-Firewall**: `prod` fährt zusätzlich `ufw` mit Policy
      `INPUT DROP`. Die Cloud-Regel allein reicht dort NICHT — das Paket wird
      erst auf dem Host verworfen:
      `ufw allow from 46.225.127.211 to any port 9100 proto tcp`
      (dasselbe für 9338). `prod-b` hat kein aktives ufw und braucht Ebene 2
      nicht — deshalb ist der Unterschied zwischen beiden Hosts kein Fehler,
      sondern muss je Host geprüft werden: `ufw status`.
2. **Exporter je Host starten** (prod, prod-b):
   `docker compose -p mon -f infra/monitoring/docker-compose.exporters.yml up -d`
3. **Scrape-Config ergänzen** (odoo-Host): Jobs aus `prometheus-scrape-fleet.yml`
   in die prometheus.yml des `odoo_prometheus`-Containers übernehmen, Container
   mit `--force-recreate` neu erzeugen.
4. **Verifizieren:** In Prometheus (odoo-Host) unter Status→Targets müssen
   `fleet-node` und `fleet-cadvisor` je 2 Targets `UP` zeigen. Erst dann gilt
   die Anmeldung als erledigt (nicht nach Schritt 2).
5. **Alerts (Folgeschritt):** OOM/Swap>80 %/Container-down als Alertmanager-Regeln
   — separater PR, damit dieser hier klein bleibt.

## Betriebserfahrung Erst-Rollout (2026-08-02)

- Der `odoo_prometheus`-Container hängt im `internal: true`-Netz
  (`odoo_hub_internal`, kein Gateway) und erreicht die Exporter nicht.
  ⚠ **Der ursprünglich hier dokumentierte Laufzeit-Fix `docker network connect
  bridge odoo_prometheus` ist NICHT persistent** — er überlebt kein
  `--force-recreate`. Am 2026-08-04 standen deshalb wieder alle 4 Fleet-Targets
  auf `down` (`network is unreachable`), obwohl beide Exporter liefen.
  Persistenter Fix: in `/opt/odoo-hub/docker-compose.prod.yml` beim Service
  `prometheus` das vorhandene, nicht-interne Netz ergänzen —
  `networks: [internal, proxy]` — danach
  `docker compose -f docker-compose.prod.yml up -d --force-recreate prometheus`.
- Scrape-Timeout auf prod kam vom toten NFS-Mount (Collector-Hänger 10,5 s) —
  deshalb der `/mnt`-Ausschluss im Compose (auf beiden Hosts bereits aktiv).

## Diagnose-Reihenfolge, wenn Targets `down` sind

Von innen nach außen — jeder Schritt schließt eine Ursache aus:

1. **Exporter lebt?** Auf dem Ziel-Host: `curl -s -o /dev/null -w '%{http_code}'
   http://localhost:9100/metrics` → 200 erwartet.
2. **Von außen erreichbar?** Vom odoo-Host aus dieselbe URL gegen die Host-IP.
   Antwortet Schritt 1 mit 200 und Schritt 2 nicht, liegt es an einer der
   beiden Firewall-Ebenen (siehe Rollout 1) — bei `prod` zuerst `ufw status`.
3. **Prometheus-Container hat Ausgang?** `docker exec odoo_prometheus wget -qO-
   --timeout=5 http://1.1.1.1` — schlägt das fehl, während Schritt 2 klappt,
   fehlt dem Container das nicht-interne Netz (siehe Betriebserfahrung).

Die Fehlermeldung `network is unreachable` zeigt auf Schritt 3, ein Timeout
(`000`) auf Schritt 2 — die beiden nicht verwechseln.

## Bewusste Entscheidungen

- **Bind offen + Firewall-Allowlist** statt Tunnel/VPN: einfachster Standardweg,
  eine bestehende Komponente (Hetzner-FW `prod-b-web` existiert bereits), kein
  neuer Dienst. Schwäche: Schutz hängt an der FW-Regel — deshalb Schritt 1 zuerst.
- **Images gepinnt** (node-exporter v1.8.2, cadvisor v0.49.1).
- Der odoo-Host selbst hat node_exporter bereits (`odoo_node_exporter`).
