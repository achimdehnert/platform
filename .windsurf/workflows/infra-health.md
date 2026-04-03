---
description: Check health of all deployed services and infrastructure
---

# /infra-health

Vollständiger Infrastruktur-Health-Check über alle Platform-Services.

## Schritte

0. **Connectivity-Gate (PFLICHT vor allen MCP-Calls)**

⚠️ **NIEMALS `ping` verwenden** — Hetzner-Server blockieren ICMP.
Stattdessen TCP-Probe auf SSH (22), HTTP (80), HTTPS (443):

// turbo
```bash
python3 ~/github/platform/infra/scripts/server_probe.py --host 88.198.191.108
```

→ Wenn Server **NICHT erreichbar**: STOPP. Kein MCP-Call wird funktionieren.
→ Fallback: `ssh -o ConnectTimeout=10 -o BatchMode=yes root@88.198.191.108 "uptime"`
→ Wenn auch SSH scheitert: Hetzner Cloud Console prüfen (https://console.hetzner.cloud)

1. **System-Überblick**
// turbo
```
mcp0_system_manage(action="info", host="88.198.191.108")
```

2. **Health-Dashboard aller Apps**
// turbo
```
mcp0_system_manage(action="health_dashboard", host="88.198.191.108")
```

3. **Container-Status**
// turbo
```
mcp0_docker_manage(action="container_list", host="88.198.191.108")
```

4. **Unhealthy Container identifizieren**
   - Filtere Container mit Status `unhealthy` oder `restarting`
   - Für jeden: Logs der letzten 50 Zeilen abrufen
   ```
   mcp0_docker_manage(action="container_logs", host="88.198.191.108", container_id="<id>", lines=50)
   ```

5. **Nginx prüfen**
// turbo
```
mcp0_system_manage(action="nginx_status", host="88.198.191.108")
```

6. **SSL-Zertifikate prüfen**
```
mcp0_network_manage(action="ssl_expiring", days=14, host="88.198.191.108")
```

7. **Disk & Memory prüfen**
   - Disk > 85%: WARNING
   - Disk > 95%: CRITICAL
   - Memory > 90%: WARNING

8. **Cloudflare Tunnel prüfen**
```
mcp0_cloudflare_manage(action="cf_tunnel_list")
```

9. **Report erstellen**
   ```
   === Infra Health Report ===
   Server: 88.198.191.108
   Disk: 45% (OK)
   Memory: 62% (OK)
   Containers: 38/40 healthy
   Nginx: OK (config test passed)
   SSL: 0 expiring within 14 days
   Tunnel: connected

   ⚠️ Issues:
   - pptx_hub_web: restarting (exit code 1)
   - illustration_hub_web: unhealthy (no /livez/ endpoint)
   ```

10. **Bei kritischen Issues** — Fixes vorschlagen, NICHT automatisch anwenden

## Referenzen
- ADR-021: Unified Deployment Pattern
- Deploy-Targets: `mcp2_deploy_check(action="targets")`
