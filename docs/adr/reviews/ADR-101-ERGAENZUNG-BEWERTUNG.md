# Bewertung: ADR-101 Ergänzung Hetzner/Cloudflare MCP

| Attribut | Wert |
|---|---|
| **Bezug** | ADR-101-ERGAENZUNG-hetzner-cloudflare-mcp.md |
| **Bewerter** | Cascade |
| **Datum** | 2026-03-06 |

---

## Executive Summary

Das Ergänzungsdokument identifiziert reale Infrastruktur-Lücken, basiert aber auf
**zwei falschen Prämissen**: (1) deployment-mcp hat keinen Hetzner Cloud API Zugriff,
(2) die Domains nutzen Cloudflare DNS. Beides ist faktisch falsch.

**Trotzdem ist die strategische Richtung korrekt**: Eine Cloudflare-Migration würde
die Plattform-Infrastruktur massiv verbessern — nicht wegen MCP, sondern wegen CDN,
DDoS-Schutz, WAF, SSL-Automatisierung und DNS-Vereinheitlichung.

---

## Punkt-für-Punkt Bewertung

### G-09: Hetzner Cloud Control Plane — ⚠️ FALSCHE PRÄMISSE

**Claim**: "deployment-mcp operiert ausschließlich auf dem Server via SSH"

**Fakt**: deployment-mcp hat BEREITS 16 Hetzner Cloud API Actions:

| Tool | Actions | API |
|------|---------|-----|
| `server_manage` | 9 (list, status, power, create, delete, rebuild, types, images, locations) | Hetzner Cloud API via custom `HetznerClient` (httpx → api.hetzner.cloud/v1) |
| `firewall_manage` | 7 (list, get, create, delete, set_rules, apply, remove) | Hetzner Cloud API |

**Architektur-Details**:
- Custom async `HetznerClient` in `deployment_mcp/clients/hetzner_client.py`
- Nutzt `httpx.AsyncClient` mit Bearer-Token Auth
- Token: `DEPLOYMENT_MCP_HETZNER_API_TOKEN` in Settings (bereits konfiguriert)
- **Kein `hcloud` Python-SDK nötig** — eigener Client ist besser (async, keine Extra-Dependency)

**Echte Restlücken** (deutlich kleiner als dargestellt):

| Lücke | Aufwand | Lösung |
|-------|---------|--------|
| Volumes (list, detail) | 30 min | 1 Action in `server_manage` + HetznerClient erweitern |
| Traffic-Stats | 30 min | 1 Action in `server_manage` (metrics Endpoint) |
| Firewall-Audit (Nginx ↔ Cloud-FW Cross-Check) | 1h | 1 Action in `firewall_manage` |

**Aufwand real: ~2h** (nicht 3.5h). Kein neues SDK, kein neues Tool.

### G-10: Cloudflare DNS — ❌ FALSCHE PRÄMISSE

**Claim**: "`*.iil.pet` und `kiohnerisiko.de` sind Cloudflare-verwaltet"

**Fakt** (DNS NS-Lookup verifiziert):
- `iil.pet` → `ns1.your-server.de` = **Hetzner DNS**
- `kiohnerisiko.de` → `ns1093.ui-dns.com` = **IONOS/1&1 DNS**

Keine der Domains nutzt Cloudflare. Der vorgeschlagene Cloudflare MCP Server
würde ins Leere laufen.

**Echte DNS-Lücke**: IONOS DNS für `kiohnerisiko.de` hat keine API →
Cascade ist für die Haupt-Domain tatsächlich blind.

### Marktübersicht Community MCP-Server — ✅ KORREKT

Die Bewertung der Community-Implementierungen (dkruyt, MahdadGhasemian, valerius21)
ist korrekt: Keine ist ADR-044-konform und Integration wäre unnötig, da deployment-mcp
bereits den besseren Custom-Client hat.

### Tool-Budget-Kalkulation — ⚠️ FEHLERHAFT

Das Dokument rechnet mit "health-mcp: 5 Tools" und "docs-search-mcp: 5 Tools" als
Tier-1 Always-On. ADR-101 v2 hat diese bereits korrigiert:
- Health ist Action in `system_manage` (0 neue Tools)
- docs-search ist Tier-2 (disabled)
- test-generator ist Tier-2 (disabled)

---

## Strategische Empfehlung: Cloudflare Migration

Obwohl die DNS-Prämisse falsch ist, wäre eine **aktive Migration zu Cloudflare**
die optimale Entscheidung für die Plattform:

### Ist-Zustand (Schwachstellen)

| Aspekt | Aktuell | Risiko |
|--------|---------|--------|
| IP-Exposure | Alle 13 Apps exponieren 88.198.191.108 direkt | DDoS auf eine IP = alle Apps down |
| SSL | Let's Encrypt/certbot, 90-Tage-Zertifikate, manuelles Renewal | Renewal-Fehler = Ausfall |
| DNS | 2 Provider (Hetzner DNS + IONOS) | Kein einheitliches Management |
| CDN | Keins — nginx serviert alles direkt vom Server | Jeder Request trifft den Single-Server |
| DDoS | Nur Hetzner Cloud-Firewall (Layer 3/4) | Kein Layer 7 HTTP-Schutz |
| WAF | Keins | OWASP Top 10 ungeschützt |

### Was Cloudflare bringt (Free Tier)

| Feature | Nutzen | Kosten |
|---------|--------|--------|
| Universal SSL | Auto-Renew, kein certbot, Origin-Cert 15 Jahre | Free |
| CDN (Anycast, 300+ PoPs) | Static Assets global gecacht | Free |
| DDoS (Layer 3-7) | Schützt Single-Server | Free |
| DNS (1.1.1.1) | Schnellster DNS, Near-Instant Propagation | Free |
| Basic WAF | Managed Rulesets | Free |
| Analytics | Traffic, Threats, Cache Hit Rates | Free |
| Cloudflare Tunnel | Server-IP komplett versteckt | Free |
| Offizieller MCP | 2 Tools, 2500+ Endpoints, Remote-hosted | Free |

### Budget-Impact

```
OHNE Cloudflare (aktuell):
  Hetzner DNS:   kostenlos (bei Hetzner Server)
  IONOS DNS:     im Hosting-Paket
  Let's Encrypt: kostenlos, aber Ops-Aufwand (certbot, cron, 7 MCP-Actions)
  CDN:           keins
  DDoS:          keins (Layer 7)
  WAF:           keins
  MCP:           0 Tools für DNS/CDN/WAF

MIT Cloudflare (Free Tier):
  Cloudflare:    $0/Monat (Free Plan für beide Domains)
  SSL:           automatisch (7 certbot-Actions werden optional)
  CDN:           inklusive
  DDoS:          inklusive
  WAF:           inklusive (Basis-Rules)
  Analytics:     inklusive
  MCP:           +2 Tool-Slots (search, execute) als Tier-2

  Pro (optional): $20/Monat pro Domain für erweiterte WAF + Image-Optimierung
```

### Tool-Budget nach Cloudflare

```
Tier 1 (Always-On):    42 Tools / 100  (unverändert)
  deployment-mcp:      12
  github:              26
  platform-context:     4

Tier 2 (disabled):     36 Tools (+2)
  cloudflare-api:       2  (NEU: search + execute)
  docs-search:          5
  registry:             5
  test-generator:       3
  code-quality:         1
  llm-mcp:              2
  orchestrator:         3

Tier 3 (disabled):     15 Tools
  bfagent:              5
  bfagent-db:           2
  bfagent-monitoring:   2
  cadhub:               3
  illustration:         3
                       ──
Max bei allen aktiv:   78 / 100 (22 Reserve)
```

---

## Implementierungsplan (4 Phasen)

### Phase 1: Cloudflare DNS Migration (2h, P0)

| # | Task | Aufwand |
|---|------|---------|
| 1.1 | Cloudflare Account erstellen (Free Plan) | 10 min |
| 1.2 | `iil.pet` zu Cloudflare DNS migrieren (NS-Records bei Hetzner umstellen) | 30 min |
| 1.3 | `kiohnerisiko.de` zu Cloudflare DNS migrieren (NS-Records bei IONOS umstellen) | 30 min |
| 1.4 | Alle 13 Subdomains als Proxied (orange cloud) konfigurieren | 30 min |
| 1.5 | SSL-Mode: Full (Strict) + Origin Certificate auf Hetzner installieren | 20 min |

**Ergebnis**: CDN + DDoS + WAF + SSL-Auto + DNS-Vereinheitlichung aktiv.
**Risiko**: DNS-Propagation dauert bis zu 48h. Downtime: 0 bei korrekter Migration.

### Phase 2: Cloudflare MCP + ADR Update (1h, P0)

| # | Task | Aufwand |
|---|------|---------|
| 2.1 | Cloudflare API MCP in `mcp_config.json` als Tier-2 eintragen | 10 min |
| 2.2 | OAuth-Flow einmalig durchlaufen | 5 min |
| 2.3 | ADR-101 v3: G-10 korrigieren (Cloudflare aktiv, nicht "Lücke") | 30 min |
| 2.4 | ADR-102 anlegen: "Adopt Cloudflare for CDN, DNS, and DDoS Protection" | 20 min |

### Phase 3: deployment-mcp Restlücken (2h, P1)

| # | Task | Aufwand |
|---|------|---------|
| 3.1 | `server_manage volumes` Action (HetznerClient + server_tool.py) | 30 min |
| 3.2 | `server_manage traffic` Action (Hetzner metrics API) | 30 min |
| 3.3 | `firewall_manage audit` Action (Cloud-FW ↔ Nginx Cross-Check) | 1h |

### Phase 4: Cloudflare Tunnel evaluieren (optional, P2)

| # | Task | Aufwand |
|---|------|---------|
| 4.1 | Cloudflare Tunnel installieren (cloudflared Daemon auf Hetzner) | 30 min |
| 4.2 | Nginx auf localhost-only umstellen (Port 80/443 schließen) | 30 min |
| 4.3 | Cloud-Firewall-Rules entschlacken (nur Tunnel + SSH) | 30 min |

**Ergebnis**: Server-IP komplett versteckt. Kein direkter Zugriff mehr möglich.
Alle Requests laufen über Cloudflare Tunnel → maximale Sicherheit.

---

## Zusammenfassung

| Aspekt | Dokument-Vorschlag | Optimaler Vorschlag |
|--------|-------------------|-------------------|
| **G-09** | hcloud SDK + neues Tool | 3 Actions in bestehende Tools (Client existiert) |
| **G-10** | Cloudflare MCP eintragen | **Cloudflare DNS Migration** + dann MCP |
| **Aufwand** | 4.5h | Phase 1-3: ~5h, aber 10× mehr Nutzen |
| **Kosten** | — | $0 (Cloudflare Free Tier) |
| **Tool-Budget** | +3 Tools | +2 Tools (Cloudflare) + 3 Actions (0 neue Tools) |
| **Infrastruktur-Gewinn** | Nur MCP-Sichtbarkeit | CDN + DDoS + WAF + SSL-Auto + DNS-Vereinheitlichung + MCP |
