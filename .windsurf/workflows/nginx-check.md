---
description: Audit Nginx configs on production server for IPv6, SSL, proxy_pass, security headers
---

# /nginx-check

Prüft alle Nginx-Konfigurationen auf dem Prod-Server gegen Platform-Standards.

## Schritte

1. **Nginx-Status prüfen**
// turbo
```
mcp0_system_manage(action="nginx_status", host="88.198.191.108")
```

2. **Alle Site-Configs listen**
// turbo
```
mcp0_ssh_manage(action="exec", host="88.198.191.108", command="ls -la /etc/nginx/sites-enabled/")
```

3. **Für jede Config prüfen** (via `mcp0_ssh_manage file_read`):
   - [ ] `listen 443 ssl http2` UND `listen [::]:443 ssl http2` (IPv6!)
   - [ ] `listen 80` UND `listen [::]:80` mit redirect zu HTTPS
   - [ ] `proxy_pass http://127.0.0.1:PORT` — Port stimmt mit ports.yaml überein
   - [ ] `server_name` enthält alle Domain-Aliases
   - [ ] SSL-Zertifikat Pfade vorhanden und gültig
   - [ ] Security Headers: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`
   - [ ] `proxy_set_header X-Forwarded-Proto $scheme`
   - [ ] Keine `proxy_pass` zu `0.0.0.0`

4. **SSL-Ablauf prüfen**
```
mcp0_network_manage(action="ssl_expiring", days=30, host="88.198.191.108")
```

5. **Report erstellen**
   Format:
   ```
   ✅ schutztat.de.conf — all checks passed
   ⚠️ trading-hub.iil.pet.conf — missing IPv6 listen directive
   ❌ prezimo.de.conf — wrong proxy_pass port (8093 vs expected 8020)
   ```

6. **Config-Test**
// turbo
```
mcp0_system_manage(action="nginx_reload", host="88.198.191.108")
```
   Nur Test, kein Force-Reload.

## Referenzen
- Lesson Learned (Nginx IPv6): `88e79861-a37f-43a7-9086-25335281176f`
- ports.yaml: `${GITHUB_DIR:-$HOME/github}/platform/infra/ports.yaml`
