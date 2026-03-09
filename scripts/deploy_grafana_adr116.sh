#!/bin/bash
# deploy_grafana_adr116.sh
#
# Macht Grafana + ADR-116 Agent Coding Team produktiv.
#
# Voraussetzung: A-Record grafana.iil.pet -> 88.198.191.108 gesetzt (✅)
#
# Ausführen auf hetzner-prod als root oder deploy mit sudo:
#   bash /opt/mcp-hub/scripts/deploy_grafana_adr116.sh
#
set -euo pipefail

echo "=== ADR-116 + Grafana Produktiv-Deploy ==="
echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo ""

# ------------------------------------------------------------------ #
# SCHRITT 1: Nginx vhost für grafana.iil.pet                         #
# ------------------------------------------------------------------ #
echo "[1/6] Nginx vhost für grafana.iil.pet..."

cat > /etc/nginx/sites-available/grafana.iil.pet << 'NGINX'
server {
    listen 80;
    server_name grafana.iil.pet;

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name grafana.iil.pet;

    ssl_certificate     /etc/letsencrypt/live/grafana.iil.pet/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/grafana.iil.pet/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass         http://127.0.0.1:3000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/grafana.iil.pet \
       /etc/nginx/sites-enabled/grafana.iil.pet
echo "  -> Nginx vhost angelegt"

# ------------------------------------------------------------------ #
# SCHRITT 2: SSL-Zertifikat für grafana.iil.pet                      #
# ------------------------------------------------------------------ #
echo "[2/6] SSL-Zertifikat (Certbot)..."

# Nginx temporär auf HTTP-Only für certbot
nginx -t && systemctl reload nginx

certbot certonly \
    --nginx \
    --non-interactive \
    --agree-tos \
    --email admin@iil.pet \
    -d grafana.iil.pet

echo "  -> SSL-Zertifikat ausgestellt"

# ------------------------------------------------------------------ #
# SCHRITT 3: Grafana-Container mit neuer Domain neu starten          #
# ------------------------------------------------------------------ #
echo "[3/6] Grafana-Container neu starten (grafana.iil.pet)..."

docker stop mcp_hub_grafana 2>/dev/null || true
docker rm   mcp_hub_grafana 2>/dev/null || true

docker run -d \
    --name mcp_hub_grafana \
    --network mcp-hub_default \
    --restart unless-stopped \
    -p 127.0.0.1:3000:3000 \
    -e GF_SECURITY_ADMIN_USER=admin \
    -e GF_SECURITY_ADMIN_PASSWORD=mcp-grafana-2024 \
    -e GF_SECURITY_SECRET_KEY=mcp-grafana-secret-2024 \
    -e "GF_SERVER_ROOT_URL=https://grafana.iil.pet/" \
    -e GF_SERVER_SERVE_FROM_SUB_PATH=false \
    -e GF_SERVER_DOMAIN=grafana.iil.pet \
    -e GF_AUTH_ANONYMOUS_ENABLED=false \
    -e GF_UNIFIED_ALERTING_ENABLED=true \
    -e GF_LOG_MODE=console \
    -e GF_LOG_LEVEL=warn \
    -e GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/etc/grafana/provisioning/dashboards/agent_controlling.json \
    -v mcp-hub_mcp_hub_grafana_data:/var/lib/grafana \
    -v /opt/mcp-hub/grafana/provisioning:/etc/grafana/provisioning:ro \
    --memory 256m \
    --cpus 0.5 \
    grafana/grafana-oss:11.4.0

echo "  -> Grafana Container gestartet mit GF_SERVER_ROOT_URL=https://grafana.iil.pet/"

# ------------------------------------------------------------------ #
# SCHRITT 4: Nginx neu laden (jetzt mit SSL-Zertifikat)              #
# ------------------------------------------------------------------ #
echo "[4/6] Nginx reload mit SSL..."
nginx -t && systemctl reload nginx
echo "  -> Nginx reload OK"

# ------------------------------------------------------------------ #
# SCHRITT 5: Migration 0003 (ModelRouteConfig + routing_reason)      #
# ------------------------------------------------------------------ #
echo "[5/6] Django Migration 0003 (ADR-116 Route-Tabelle)..."

# mcp-hub web container finden
MCP_WEB_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E 'mcp.*web|orchestrator' | head -1)

if [ -z "$MCP_WEB_CONTAINER" ]; then
    echo "  WARNUNG: mcp-hub web container nicht gefunden — Migration manuell ausführen:"
    echo "  docker exec <container> python manage.py migrate orchestrator_mcp 0003_model_route_config"
else
    docker exec "$MCP_WEB_CONTAINER" \
        python manage.py migrate orchestrator_mcp 0003_model_route_config
    echo "  -> Migration 0003 abgeschlossen in Container: $MCP_WEB_CONTAINER"
fi

# ------------------------------------------------------------------ #
# SCHRITT 6: ENV sicherstellen (BUDGET_GUARD_ENABLED=false)          #
# ------------------------------------------------------------------ #
echo "[6/6] .env: BUDGET_GUARD_ENABLED=false prüfen..."

ENV_FILE="/opt/mcp-hub/.env"
if [ -f "$ENV_FILE" ]; then
    if grep -q "BUDGET_GUARD_ENABLED" "$ENV_FILE"; then
        sed -i 's/BUDGET_GUARD_ENABLED=.*/BUDGET_GUARD_ENABLED=false/' "$ENV_FILE"
        echo "  -> BUDGET_GUARD_ENABLED=false gesetzt (existierte bereits)"
    else
        echo "BUDGET_GUARD_ENABLED=false" >> "$ENV_FILE"
        echo "  -> BUDGET_GUARD_ENABLED=false hinzugefügt"
    fi
else
    echo "  WARNUNG: $ENV_FILE nicht gefunden — BUDGET_GUARD_ENABLED manuell setzen"
fi

# ------------------------------------------------------------------ #
# VERIFIKATION                                                        #
# ------------------------------------------------------------------ #
echo ""
echo "=== Verifikation ==="
echo ""

echo "Grafana Container Status:"
docker ps --filter name=mcp_hub_grafana --format "  {{.Names}}: {{.Status}}"

echo ""
echo "Grafana Health:"
sleep 3
curl -sf https://grafana.iil.pet/api/health | python3 -m json.tool 2>/dev/null \
    && echo "  -> ✅ grafana.iil.pet erreichbar" \
    || echo "  -> ⚠️  Grafana noch nicht erreichbar (ggf. kurz warten)"

echo ""
echo "Nginx Status:"
systemctl is-active nginx && echo "  -> ✅ Nginx läuft"

echo ""
echo "=== Deploy abgeschlossen ==="
echo ""
echo "URLs:"
echo "  Grafana:    https://grafana.iil.pet/  (admin / mcp-grafana-2024)"
echo "  Dashboard:  https://grafana.iil.pet/d/agent-controlling"
echo ""
echo "Nächste Schritte:"
echo "  1. Grafana Login testen: https://grafana.iil.pet/"
echo "  2. Nach 7 Tagen Monitoring: BUDGET_GUARD_ENABLED=true in .env setzen"
echo "  3. docker compose restart mcp_hub_web (damit .env-Änderung wirksam wird)"
