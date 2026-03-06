---
status: accepted
date: 2026-03-06
decision-makers: Achim Dehnert
consulted: Cascade
informed: –
---

# ADR-102: Adopt Cloudflare for DNS, CDN, and DDoS Protection

## Metadaten

| Attribut        | Wert                                                    |
|-----------------|---------------------------------------------------------|
| **Status**      | Accepted                                                |
| **Scope**       | platform                                                |
| **Erstellt**    | 2026-03-06                                              |
| **Autor**       | Achim Dehnert, Cascade                                  |
| **Bezug**       | ADR-101 (MCP-Plattform-Konzept), E-12, G-11, G-12      |

---

## 1. Context and Problem Statement

Die BF-Plattform (13 Apps auf einem Hetzner-Server 88.198.191.108) hat
folgende Infrastruktur-Schwachstellen:

- **DNS split**: 2 Provider (Hetzner DNS fuer `iil.pet`, IONOS fuer `kiohnerisiko.de`)
- **Kein CDN**: Static Assets werden direkt vom Server ausgeliefert
- **Kein DDoS-Schutz (Layer 7)**: Nur Hetzner Cloud-Firewall (Layer 3/4)
- **Kein WAF**: OWASP Top 10 ungeschuetzt
- **SSL manuell**: Let's Encrypt/certbot mit 90-Tage-Zertifikaten, Cron-basiertes Renewal
- **IP direkt exponiert**: Alle 13 Apps zeigen die Server-IP
- **IONOS hat keine API**: MCP/Cascade ist fuer `kiohnerisiko.de` DNS-blind

---

## 2. Decision Drivers

- Einheitliche DNS-Verwaltung ueber eine API (MCP-faehig)
- CDN fuer bessere Performance (Static Assets)
- DDoS- und WAF-Schutz fuer Single-Server-Architektur
- SSL-Automatisierung (kein manuelles certbot)
- Kosteneffizienz ($0 im Free Tier)
- Offizieller MCP-Server verfuegbar

---

## 3. Considered Options

### Option A: Status Quo (Hetzner DNS + IONOS + kein CDN)

- **Pro**: Keine Aenderung noetig
- **Contra**: DNS-Split, kein CDN, kein DDoS, kein WAF, IONOS API-blind

### Option B: Cloudflare Free Tier fuer alle Domains

- **Pro**: CDN, DDoS, WAF, SSL-Auto, DNS-Vereinheitlichung, MCP-Server, $0
- **Contra**: DNS-Propagation bei Migration, Abhaengigkeit von Cloudflare

### Option C: Hetzner Load Balancer + eigenes CDN

- **Pro**: Alles bei Hetzner
- **Contra**: LB €5/Monat, kein WAF, kein CDN, kein MCP-Server, hoher Aufwand

---

## 4. Decision Outcome

**Gewaehlt: Option B — Cloudflare Free Tier**

Begruendung: Maximaler Infrastruktur-Gewinn bei $0 Kosten. Offizieller MCP-Server
als Tier-2 schliesst G-12 aus ADR-101.

---

## 5. Implementation

### 5.1 Durchgefuehrt (2026-03-06)

| # | Task | Status |
|---|------|--------|
| 1 | Cloudflare Account erstellt (Free Plan) | ✅ |
| 2 | `iil.pet` als Site hinzugefuegt (14 A-Records, Proxied) | ✅ |
| 3 | `kiohnerisiko.de` als Site hinzugefuegt (2 A-Records + MX + CNAME) | ✅ |
| 4 | NS fuer `iil.pet` bei Hetzner Robot auf Cloudflare umgestellt | ✅ |
| 5 | NS fuer `kiohnerisiko.de` bei IONOS auf Cloudflare umgestellt | ✅ |
| 6 | `iil.pet` Cloudflare-Aktivierung bestaetigt (status: active) | ✅ |
| 7 | Cloudflare API Token erstellt ("MCP Platform Read", Read-Only) | ✅ |
| 8 | Token gespeichert in `~/.secrets/cloudflare_api_token` | ✅ |
| 9 | `cloudflare-api` MCP-Server als Tier-2 in `mcp_config.json` | ✅ |
| 10 | Nginx `cloudflare-realip.conf` installiert (CF-Connecting-IP) | ✅ |

### 5.2 Ausstehend

| # | Task | Prio |
|---|------|------|
| 11 | `kiohnerisiko.de` Propagation abwarten + Aktivierung bestaetigen | P0 |
| 12 | SSL-Mode "Full" in Cloudflare Dashboard setzen (beide Domains) | P0 |
| 13 | "Always Use HTTPS" aktivieren (beide Domains) | P0 |
| 14 | "Automatic HTTPS Rewrites" aktivieren (beide Domains) | P1 |
| 15 | Weitere Domains migrieren: schutztat.com, prezimo.com/de | P2 |
| 16 | Cloudflare Tunnel evaluieren (Server-IP verstecken) | P3 |

### 5.3 Architektur

```
Browser → Cloudflare CDN/WAF/DDoS → HTTPS → Nginx (88.198.191.108) → Docker Apps
              ↓                                      ↓
         CF-Connecting-IP Header              real_ip_header
         (echte Client-IP)                    (nginx realip module)
```

### 5.4 DNS-Konfiguration

```
iil.pet (Cloudflare Zone: 94737a5dbcb949de48bbbbd9fcc9910f)
  NS: anastasia.ns.cloudflare.com, nero.ns.cloudflare.com
  Subdomains (Proxied): bfagent, billing, trading, dev, illustration,
    wedding, control-center, devhub, governance, writing-hub, www, @

kiohnerisiko.de (Cloudflare Zone: pending activation)
  NS: anastasia.ns.cloudflare.com, nero.ns.cloudflare.com
  Records: @, www (A, Proxied) + MX (mx00/mx01.ionos.de) + SPF + DMARC
```

### 5.5 MCP-Integration

```json
{
  "cloudflare-api": {
    "command": "npx",
    "args": ["-y", "@cloudflare/mcp-server-cloudflare"],
    "disabled": true,
    "env": {
      "CLOUDFLARE_API_TOKEN": "<from ~/.secrets/cloudflare_api_token>"
    }
  }
}
```

- **Tier**: 2 (disabled by default, aktivierbar bei Bedarf)
- **Tools**: 2 (search, execute) — 2500+ Cloudflare API Endpoints
- **Token**: Read-Only (DNS, Zone, Analytics, SSL)

---

## 6. Consequences

### 6.1 Good

- CDN fuer alle `*.iil.pet` Apps (Static Assets global gecacht)
- DDoS-Schutz Layer 3-7 (Cloudflare Anycast, 300+ PoPs)
- WAF (Managed Rulesets gegen OWASP Top 10)
- DNS vereinheitlicht unter einem Provider mit API
- SSL automatisiert (Cloudflare Universal SSL, Edge Certificates)
- Server-IP hinter Cloudflare Proxy versteckt
- MCP-Sichtbarkeit: Cascade kann DNS, Analytics, SSL abfragen
- Kosten: $0 (Free Tier)

### 6.2 Bad

- Abhaengigkeit von Cloudflare als Single Point of Failure fuer DNS + CDN
- DNS-Propagation bei Migration (bis 48h, real: Minuten)
- Nginx braucht `cloudflare-realip.conf` fuer korrekte Client-IPs
- Let's Encrypt certbot laeuft weiterhin parallel (Origin-Cert)

### 6.3 Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Cloudflare Outage | Niedrig | Hoch | DNS-Fallback zu Hetzner (NS zurueckstellen) |
| SSL-Mismatch (Flexible statt Full) | Mittel | Hoch | Dashboard-Check, Monitoring |
| certbot Renewal-Fehler mit Cloudflare Proxy | Niedrig | Mittel | HTTP-01 Challenge funktioniert weiterhin |

---

## 7. Confirmation

1. `curl -sI https://bfagent.iil.pet/ | grep "server: cloudflare"` → muss "cloudflare" zeigen
2. `curl -sI https://kiohnerisiko.de/ | grep "cf-ray"` → muss CF-Ray Header haben (nach Propagation)
3. Cloudflare Dashboard → SSL/TLS → muss "Full" oder "Full (Strict)" zeigen
4. `dig +short NS iil.pet` → muss `*.ns.cloudflare.com` zeigen

---

## 8. More Information

- [Cloudflare Free Plan](https://www.cloudflare.com/plans/free/)
- [Cloudflare MCP Server](https://github.com/cloudflare/mcp-server-cloudflare)
- [Cloudflare Real-IP Config](https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/)
- ADR-101: MCP-Plattform-Konzept (E-12, G-11, G-12)

---

## 9. Changelog

| Datum | Autor | Aenderung |
|-------|-------|-----------|
| 2026-03-06 | Cascade + AD | Initial: Cloudflare Migration fuer iil.pet + kiohnerisiko.de |
