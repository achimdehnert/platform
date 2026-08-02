# Fleet-Monitoring — Anmeldung am vorhandenen odoo-Prometheus (ADR-292)

**Zweck:** prod und prod-b melden Host- und Container-Metriken an den einzigen
vorhandenen Monitoring-Stack der Flotte (odoo-Host, `odoo_prometheus` +
`odoo_grafana`). Kein neuer Stack — 0-€-Schritt; der 16-h-blinde OOM-Ausfall vom
2026-07-20 (platform#1303) wird damit sichtbar. Netcup-Monitoring (ADR-289 R2)
bleibt vertagt.

## Rollout (Reihenfolge)

1. **Firewall zuerst** (Owner, Hetzner-Cloud-Console): eingehend TCP 9100 + 9338
   auf prod und prod-b NUR für die odoo-Host-IP `46.225.127.211` freigeben.
   Ohne diese Regel bleiben die Exporter offen erreichbar — nicht deployen.
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

- Der `odoo_prometheus`-Container hängt im `internal: true`-Netz und erreicht die
  Exporter nicht — er braucht zusätzlich das Bridge-Netz:
  `docker network connect bridge odoo_prometheus && docker restart odoo_prometheus`.
- Scrape-Timeout auf prod kam vom toten NFS-Mount (Collector-Hänger 10,5 s) —
  deshalb der `/mnt`-Ausschluss im Compose (auf beiden Hosts bereits aktiv).

## Bewusste Entscheidungen

- **Bind offen + Firewall-Allowlist** statt Tunnel/VPN: einfachster Standardweg,
  eine bestehende Komponente (Hetzner-FW `prod-b-web` existiert bereits), kein
  neuer Dienst. Schwäche: Schutz hängt an der FW-Regel — deshalb Schritt 1 zuerst.
- **Images gepinnt** (node-exporter v1.8.2, cadvisor v0.49.1).
- Der odoo-Host selbst hat node_exporter bereits (`odoo_node_exporter`).
