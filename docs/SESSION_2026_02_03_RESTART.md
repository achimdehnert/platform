# Session Restart Guide - Feb 4, 2026

## 🎯 Offene Tasks

### 1. BFAgent 502 Fix (Priorität 1)
Server: `88.198.191.108` | Pfad: `/opt/bfagent-app`

```bash
ssh root@88.198.191.108
cd /opt/bfagent-app

# Port-Mapping korrigieren
sed -i 's/"80:80"/"127.0.0.1:8088:80"/' docker-compose.prod.yml

# Caddy neu starten
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --force-recreate caddy

# Verifizieren
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8088/login/
# Erwartung: 200 oder 302
```

### 2. Travel-Beat Deployment (Priorität 2)
Server: `88.198.191.108` | Pfad: `/opt/travel-beat`

```bash
cd /opt/travel-beat

# .env.prod bereinigen
sed -i '/^"$/d' .env.prod
sed -i '/^""$/d' .env.prod

# Deployment
docker compose -f docker-compose.prod.yml --env-file .env.prod pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate

# Verifizieren
curl -s -o /dev/null -w '%{http_code}' https://drifttales.app/impressum/
# Erwartung: 200
```

## ✅ Bereits erledigt

| Task | Status | Details |
|------|--------|---------|
| Impressum Template | ✅ | `templates/legal/impressum.html` |
| Datenschutz Template | ✅ | `templates/legal/datenschutz.html` |
| Legal Views | ✅ | `apps/core/views/legal.py` |
| URL Routes | ✅ | `/impressum/`, `/datenschutz/` |
| Footer Update | ✅ | iil GmbH Branding |
| GitHub Push | ✅ | Commit `8a669f2` |
| Caddyfile Fix | ✅ | `:80` Suffix hinzugefügt |

## 🔧 Root Causes

### BFAgent 502
1. **Caddyfile** hatte kein `:80` → Caddy versuchte HTTPS (behoben)
2. **docker-compose.prod.yml** hat `"80:80"` statt `"127.0.0.1:8088:80"` (offen)

### Travel-Beat Deployment
- `.env.prod` hat Syntaxfehler (extra `"` Zeichen ab Zeile 28)

## 📡 Server-Architektur

```
Internet → Nginx (Port 80/443) → Caddy Container → Django Container
                                    ↓
                              bfagent: 8088
                              travel-beat: 8089
```

## 🚨 Bekannte Probleme

- SSH-Verbindungen instabil (Connection reset by peer)
- Lösung: Kurz warten, erneut verbinden
