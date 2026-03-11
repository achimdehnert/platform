---
status: accepted (v2)
date: 2026-03-06
decision-makers: Achim Dehnert
consulted: Cascade
informed: –
implementation_status: implemented
implementation_evidence:
  - "Cloudflare DNS active for all *.iil.pet domains"
---

# ADR-102: Adopt Cloudflare for DNS, CDN, and DDoS Protection

## Metadaten

| Attribut        | Wert                                                    |
|-----------------|---------------------------------------------------------|
| **Status**      | Accepted (v2 — Tunnel + Security Hardening)             |
| **Scope**       | platform                                                |
| **Erstellt**    | 2026-03-06                                              |
| **Autor**       | Achim Dehnert, Cascade                                  |
| **Bezug**       | ADR-101 (MCP-Plattform-Konzept), E-12, G-11, G-12      |

---

## 1. Context and Problem Statement

Die BF-Plattform (13 Apps auf einem Hetzner-Server 88.198.191.108) hatte
folgende Infrastruktur-Schwachstellen:

- **DNS split**: 2 Provider (Hetzner DNS fuer `iil.pet`, IONOS fuer `kiohnerisiko.de`)
- **Kein CDN**: Static Assets werden direkt vom Server ausgeliefert
- **Kein DDoS-Schutz (Layer 7)**: Nur Hetzner Cloud-Firewall (Layer 3/4)
- **Kein WAF**: OWASP Top 10 ungeschuetzt
- **SSL manuell**: Let's Encrypt/certbot mit 90-Tage-Zertifikaten, Cron-basiertes Renewal
- **IP direkt exponiert**: Alle 13 Apps zeigen die Server-IP
- **IONOS hat keine API**: MCP/Cascade ist fuer `kiohnerisiko.de` DNS-blind

**v2-Erweiterung**: Nach der initialen Migration wurde ein Cloudflare Tunnel
eingerichtet, um die Server-IP komplett zu verstecken und alle 9 Domains mit
einheitlichen Security-Settings zu haerten.

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

### 5.1 Phase 1 — DNS-Migration (2026-03-06 vormittags)

| # | Task | Status |
|---|------|--------|
| 1 | Cloudflare Account erstellt (Free Plan) | ✅ |
| 2 | 9 Domains als Sites hinzugefuegt | ✅ |
| 3 | NS bei IONOS auf Cloudflare umgestellt (alle Domains) | ✅ |
| 4 | 7/9 Domains Active, 2 Pending (drifttales.de, prezimo.com) | ✅ |
| 5 | API Token "MCP Platform Read" (Read-Only) erstellt | ✅ |
| 6 | `cloudflare-api` MCP-Server als Tier-2 in `mcp_config.json` | ✅ |
| 7 | Nginx `cloudflare-realip.conf` installiert (CF-Connecting-IP) | ✅ |

### 5.2 Phase 2 — Cloudflare Tunnel (2026-03-06 mittags)

| # | Task | Status |
|---|------|--------|
| 8 | `cloudflared` auf Hetzner installiert (v2026.2.0) | ✅ |
| 9 | Tunnel `bf-platform` erstellt (ID: f758021c-...-1c14599a38e2) | ✅ |
| 10 | systemd-Service `cloudflared.service` (enabled, active) | ✅ |
| 11 | Tunnel-Config: catch-all → `https://localhost:443` (noTLSVerify) | ✅ |
| 12 | Alle A/AAAA-Records per API zu Tunnel-CNAME migriert | ✅ |
| 13 | Server-IP 88.198.191.108 in keiner DNS-Abfrage mehr sichtbar | ✅ |

### 5.3 Phase 3 — Security Hardening (2026-03-06 nachmittags)

| # | Task | Status |
|---|------|--------|
| 14 | API Token "MCP Platform Write" (DNS:Edit, Zone Settings:Edit, SSL:Edit) | ✅ |
| 15 | Nginx kiohnerisiko.de: Security Headers, CSP, Rate Limiting, Path Blocks | ✅ |
| 16 | SSL Full fuer alle 7 Active Domains per API gesetzt | ✅ |
| 17 | Min TLS 1.2 fuer alle Domains | ✅ |
| 18 | HSTS (12 Monate, preload, includeSubdomains) fuer alle Domains | ✅ |
| 19 | Always HTTPS + Auto HTTPS Rewrites fuer alle Domains | ✅ |
| 20 | Security Level High + Browser Check fuer alle Domains | ✅ |
| 21 | Email Obfuscation + Hotlink Protection fuer alle Domains | ✅ |
| 22 | HTTP/3, 0-RTT, Brotli, Early Hints fuer alle Domains | ✅ |
| 23 | IONOS prezimo.com NS korrigiert (cleo/paige statt anastasia/nero) | ✅ |

### 5.4 Ausstehend

| # | Task | Prio |
|---|------|------|
| 24 | drifttales.de + prezimo.com Aktivierung abwarten + Tunnel-Migration | P1 |
| 25 | Port 80/443 extern schliessen (Nginx-Allow-List fuer Cloudflare-IPs) | P2 |
| 26 | Cloudflare Zero Trust fuer /admin/ Endpoints evaluieren | P3 |
| 27 | Cloudflare Workers fuer Wartungsseite evaluieren | P3 |

### 5.5 Architektur

```
VORHER (v1):
Browser → Cloudflare CDN → HTTPS → Nginx (88.198.191.108:443) → Docker Apps
                                    ↑ IP exponiert

NACHHER (v2 — Tunnel):
Browser → Cloudflare CDN/WAF/DDoS → Tunnel (QUIC) → cloudflared → Nginx (localhost:443) → Docker Apps
          ↓                          ↓                              ↓
     CF-Connecting-IP          4 Connections (fra)           real_ip_header
     HSTS, Security Headers    Auto-Reconnect                (nginx realip)
     Bot Fight, TLS 1.2+       systemd managed

Server-IP 88.198.191.108 ist NICHT mehr oeffentlich erreichbar via DNS.
DNS zeigt nur Cloudflare Anycast-IPs (104.21.x.x, 172.67.x.x, 188.114.x.x).
```

### 5.6 DNS-Konfiguration (9 Domains)

```
ACTIVE (7) — alle via Tunnel (CNAME → f758021c-...-1c14599a38e2.cfargotunnel.com):

iil.pet              Zone: 94737a5dbcb949de48bbbbd9fcc9910f  NS: anastasia/nero
  Subdomains: bfagent, billing, control-center, dev, devhub, governance,
              illustration, trading, wedding, writing-hub, www, @

kiohnerisiko.de      Zone: e49309df1fe4eb06bcf0e4a0700b0bd4  NS: anastasia/nero
  Records: @, www (Tunnel) + MX (ionos) + SPF + DMARC

ai-trades.de         Zone: 8691acd1c0ec0d164e55ce97ff2b2c25  NS: anastasia/nero
nl2cad.de            Zone: cbf1fbd363f8cbc49038a632430dc6db  NS: anastasia/nero
prezimo.de           Zone: 9c467c0ea40205b0a6e9935cac919f40  NS: paige/cleo
weltenforger.com     Zone: c822b7ba91bb237224e5944792cc2c7b  NS: paige/cleo
weltenforger.de      Zone: e5fdb0f50f2976176f8871169177e9b6  NS: paige/cleo

PENDING (2) — NS-Propagation laeuft:

drifttales.de        Zone: ef063c57ac1068ac342c86def35b2beb  NS: anastasia/nero
prezimo.com          Zone: cdc88cef00ce10710615533e8e3e36b1  NS: cleo/paige
```

### 5.7 MCP-Integration

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
- **Token Read**: DNS Settings, Zone, Analytics, SSL (fuer MCP-Server)
- **Token Write**: DNS:Edit, Zone Settings:Edit, SSL:Edit (fuer Automation)

### 5.8 Tunnel-Konfiguration

```yaml
# /root/.cloudflared/config.yml
tunnel: f758021c-a475-4ab7-9c02-1c14599a38e2
credentials-file: /root/.cloudflared/f758021c-...-1c14599a38e2.json
originRequest:
  noTLSVerify: true
ingress:
  - service: https://localhost:443   # Nginx handles all routing
```

- **Tunnel-Name**: bf-platform
- **Protokoll**: QUIC
- **Connections**: 4x Frankfurt (fra03, fra06, fra12)
- **systemd**: `cloudflared.service` (enabled, auto-restart)
- **Routing**: Catch-all → Nginx, Nginx routet per `server_name`

### 5.9 Security-Settings (alle 7 Active Domains)

| Setting | Wert |
|---------|------|
| SSL Mode | Full |
| Min TLS Version | 1.2 |
| Always Use HTTPS | On |
| Automatic HTTPS Rewrites | On |
| HSTS | 12 Monate, preload, includeSubdomains |
| Security Level | High |
| Browser Integrity Check | On |
| Email Obfuscation | On |
| Hotlink Protection | On |
| HTTP/3 (QUIC) | On |
| 0-RTT | On |
| Brotli Compression | On |
| Early Hints | On |
| Opportunistic Encryption | On |

---

## 6. Consequences

### 6.1 Good

- CDN fuer alle 9 Domains (Static Assets global gecacht)
- DDoS-Schutz Layer 3-7 (Cloudflare Anycast, 300+ PoPs)
- WAF (Managed Rulesets gegen OWASP Top 10)
- DNS vereinheitlicht: 9 Domains, 1 Provider, 1 API
- SSL automatisiert (Cloudflare Universal SSL, Edge Certificates)
- **Server-IP komplett versteckt** via Tunnel (nicht mehr in DNS)
- HSTS Preload + TLS 1.2+ + Security Level High auf allen Domains
- MCP-Sichtbarkeit: Cascade kann DNS, Analytics, SSL abfragen + aendern
- Vollautomatische DNS-Verwaltung per Write-Token
- Kosten: $0 (Free Tier)

### 6.2 Bad

- Abhaengigkeit von Cloudflare als Single Point of Failure fuer DNS + CDN + Tunnel
- DNS-Propagation bei Migration (bis 48h, real: Minuten)
- Nginx braucht `cloudflare-realip.conf` fuer korrekte Client-IPs
- Let's Encrypt certbot laeuft weiterhin parallel (Origin-Cert)
- Tunnel-Daemon (`cloudflared`) ist zusaetzlicher Service der laufen muss
- iptables Port-Closure funktioniert nicht zuverlaessig mit Docker-Networking

### 6.3 Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Cloudflare Outage | Niedrig | Hoch | NS zurueckstellen, A-Records auf Server-IP |
| Tunnel-Daemon Absturz | Niedrig | Hoch | systemd auto-restart, 4 Connections Redundanz |
| SSL-Mismatch (Flexible statt Full) | Niedrig | Hoch | Per API erzwungen, nicht manuell |
| certbot Renewal-Fehler | Niedrig | Mittel | Tunnel nutzt noTLSVerify, Cert-Ablauf unkritisch |
| Token-Leak (Write) | Niedrig | Hoch | Nur auf Server gespeichert, nicht im Repo |

---

## 7. Confirmation

1. `curl -sI https://bfagent.iil.pet/ | grep "server: cloudflare"` → ✅ cloudflare
2. `curl -sI https://kiohnerisiko.de/ | grep "strict-transport"` → ✅ HSTS preload
3. `dig @1.1.1.1 +short kiohnerisiko.de` → ✅ Cloudflare-IP (nicht 88.198.191.108)
4. `dig +short NS iil.pet` → ✅ anastasia/nero.ns.cloudflare.com
5. `systemctl is-active cloudflared` → ✅ active
6. `cloudflared tunnel list` → ✅ bf-platform, 4 Connections Frankfurt

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
| 2026-03-06 | Cascade + AD | v2: Tunnel bf-platform, 9 Domains, Security Hardening (14 Settings per API), Write-Token, Nginx Hardening |
