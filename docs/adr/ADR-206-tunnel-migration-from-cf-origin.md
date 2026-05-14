---
status: accepted-pilot
date: 2026-05-14
decision-makers: [Achim Dehnert]
implementation_status: partial (1/23 migriert)
related: [ADR-205]
---

# ADR-206: Migration `*.iil.pet` von Konfig A (nginx + CF Origin Cert public:443) nach Konfig C (cloudflared Tunnel + internal:8999)

## Status

**Accepted (Pilot)** — `docs.iil.pet` als erster Vhost erfolgreich migriert am 2026-05-14. Weitere Vhosts folgen nach Beobachtungsphase (≥7 Tage Pilot-Stabilität).

## Architektur — vor/nach

### Vor (Konfig A, status quo der 23 Vhosts)

```
Browser → CF Edge (TLS-Term mit CF Public-Cert)
        → bf-platform tunnel → localhost:443 (nginx, TLS mit CF Origin Cert)
        → 127.0.0.1:8102 (paperless container)

Parallel-Pfad (Schwachstelle):
Browser → 88.198.191.108:443 direkt → nginx → backend
(funktioniert, weil nginx 0.0.0.0:443 listent — Tunnel ist nur additiv)
```

Double-TLS am Origin: ungenutzt. Direct-Hit-Bypass: möglich.

### Nach (Konfig C, Pilot docs.iil.pet)

```
Browser → CF Edge (TLS-Term mit CF Public-Cert)
        → bf-platform tunnel → 127.0.0.1:8999 (nginx, plain HTTP)
        → 127.0.0.1:8102 (paperless container)

Direct-Hit auf 88.198.191.108:443 mit Host=docs.iil.pet
        → kein Vhost-Match auf 0.0.0.0:443 für docs
        → default_server fängt ab (invalid.localhost cert + 444 close)
        → de facto nicht erreichbar
```

Single TLS-Termination (am Edge), kein public:443 für docs.iil.pet, weniger Surface.

## Mechanik der Migration (pro Vhost)

### 1. Cloudflared ingress rule hinzufügen
`/etc/cloudflared/config.yml` — **VOR** dem catch-all `service: https://localhost:443`:

```yaml
- hostname: <vhost>.iil.pet
  service: http://127.0.0.1:8999
  originRequest:
    httpHostHeader: <vhost>.iil.pet
```

### 2. nginx Vhost umbauen
- `listen 443 ssl http2;` und `listen [::]:443 ssl http2;` **entfernen**
- `ssl_certificate` / `ssl_certificate_key` **entfernen** (nicht mehr nötig)
- Neuen `server { listen 127.0.0.1:8999; server_name <vhost>.iil.pet; ... }` Block mit gleichem Body (Rate-Limits, proxy_pass, etc.)
- **PFLICHT: WebSocket-Upgrade-Headers** — Pilot v1 hing im Browser ohne diese (curl -I sagte 302 OK, aber JS-Asset/WS-Handshake hing). Bei TLS-Origin:443 schleift CF Edge WS transparent durch; bei plain-HTTP-Origin:8999 muss nginx den Upgrade explizit forwarden:
  ```nginx
  # auf Datei-Top-Level (außerhalb server{}):
  map $http_upgrade $connection_upgrade {
      default upgrade;
      ''      close;
  }
  # innerhalb jeder location {}:
  proxy_http_version 1.1;
  proxy_set_header Upgrade    $http_upgrade;
  proxy_set_header Connection $connection_upgrade;
  ```
- `listen 80; ... return 301 https://...` (HTTP→HTTPS Redirect) **kann bleiben** als defensive Maßnahme

### 3. Reload + Verify
```bash
nginx -t && systemctl reload nginx
systemctl restart cloudflared  # SIGHUP/reload nicht supported in dieser Version
# 30s warten bis Tunnel-Reconnects up sind
curl -sI https://<vhost>.iil.pet/                                    # via CF: 200/302
curl -sIk --resolve <vhost>.iil.pet:443:88.198.191.108 https://<vhost>.iil.pet/  # direct: empty/444
```

### 4. Backup vor jedem Migration-Schritt
```
/etc/nginx/sites-enabled.bak-2026-05-14-tunnel-pilot/  ← bereits angelegt
```

## Pilot-Ergebnis docs.iil.pet (2026-05-14)

### Pilot v1 — gescheitert (~13:13 UTC)
- ✅ Server-seitig grün: curl-Tests + nginx + cloudflared alle OK
- ❌ **Browser**: Seite hängt beim Laden (User-Report ~30 min später)
- Rollback aus `/etc/nginx/sites-enabled.bak-2026-05-14-tunnel-pilot/`: <1 min
- **Lesson**: `curl -I` testet HTML-Hop, nicht WebSocket-Upgrade. Server-Tests sind notwendig aber nicht hinreichend.

### Pilot v2 — erfolgreich (~13:50 UTC)
Identisch zu v1 plus WebSocket-Upgrade-Headers (siehe oben, Mechanik §2).

| Test | Erwartung | Ergebnis |
|---|---|---|
| `curl https://docs.iil.pet/` (via CF) | 200/302 | ✅ HTTP 302 |
| `curl -H "Host: docs.iil.pet" http://127.0.0.1:8999/` (internal) | 200/302 | ✅ HTTP 302 |
| `curl --resolve docs.iil.pet:443:88.198.191.108` (direct origin) | nicht erreichbar | ✅ invalid.localhost cert + 444 close |
| `systemctl is-active cloudflared` | active | ✅ 4 connections (fra03/06/19/+1) |
| nginx -t | ok | ✅ |
| **Browser-Load** (User-verifiziert) | funktional | ✅ docs.iil.pet "geladen und ist verfügbar" |

## Migrationsplan (Bestand)

Die anderen 22 `*.iil.pet` Vhosts werden NICHT in dieser PR migriert. Reihenfolge nach Pilot-Stabilität (≥7 Tage):

### Phase 1 — Low-Risk Static / Internal (Wave 1)
`docs` (✅ pilot), `learn`, `old-dashboard`, `pptx-hub`, `staging-coaching`, `staging-wedding`, `staging-writing`

### Phase 2 — Medium-Risk Internal Tools
`bfagent`, `billing`, `control-center`, `dms`, `dsb`, `governance`, `grafana`, `hr`, `illustration` (bereits direct-tunnel, keine Migration nötig), `llm-mcp`, `research`

### Phase 3 — Active Internal Apps
`coach-hub`, `devhub`, `wedding-hub`, `weltenhub`, `writing-hub`, `writing`

Jede Phase: ein Vhost migrieren, 24h beobachten, dann weiter. Bei Issues: Rollback aus dem `.bak`-Verzeichnis.

## Endzustand-Definition

Migration als "implementation_status: implemented" gilt sobald:
- Alle 23 `*.iil.pet` Vhosts via Tunnel statt public:443 (außer wenn ein konkreter Vhost Direct-Access ausdrücklich braucht — siehe `id.iil.pet`/Authentik?)
- nginx auf 0.0.0.0:443 listent nur noch für Domains der Konfig B (externe Domains)
- ggf. Firewall-Rule: TCP/443 nur von Cloudflare IP-Ranges akzeptieren (defense-in-depth)
- CF Origin Cert (`/etc/nginx/ssl/cf-origin/iil-pet.{crt,key}`) wird dann nicht mehr genutzt, kann archiviert/gelöscht werden

## Open Questions / Trade-offs

- **`id.iil.pet` (Authentik)** — wenn das eine SSO-Quelle für externe Kunden ist und Direct-Access braucht, muss es Konfig B (LE) statt C werden.
- **Rate-Limits in nginx** bleiben in Konfig C erhalten (server-block move, nicht Verlust). Aber: CF Edge hat eigene Rate-Limits, die jetzt zusätzlich greifen — möglicherweise Konflikte oder Double-Limiting.
- **Origin IP-Whitelist**: Wenn alle iil.pet auf Konfig C, kann `iptables` 443 für externe IPs droppen. Externe Domains (Konfig B) müssen weiterhin direkt 443-erreichbar bleiben — geht über `server_name`-Filter UND CF-IP-Range-Check (`set_real_ip_from`-Patterns).

## cli.ini-Bug — gefunden während Pilot (Addendum zu ADR-205)

Versuch `dns_cloudflare_propagation_seconds = 120` global in `/etc/letsencrypt/cli.ini` zu persistieren scheiterte: certbot 2.x parst die Underscore-Form als Core-CLI-Arg statt sie an das Plugin zu mappen ("certbot: error: unrecognized arguments: --dns_cloudflare_propagation_seconds=120"). 

Workaround:
- Per-Cert in `/etc/letsencrypt/renewal/*.conf` setzen (funktioniert für bestehende, von certbot beim certonly-issue gesetzt)
- Bei `certbot certonly` für neue Domains **explizit** `--dns-cloudflare-propagation-seconds 120` auf der Kommandozeile angeben

**Permanente Fix-Optionen** (für künftige Sessions):
1. certbot auf 3.x upgraden — sollte das fixen
2. `--config` mit eigenem cli.ini-Path und custom Wrapper-Skript
3. Wrapper-Skript `/opt/scripts/certbot-issue.sh` der den Flag immer setzt
