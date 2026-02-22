#!/bin/bash
# Test: Prüft ob build-deploy.sh für alle Apps funktionieren würde
# Verwendet die GLEICHE Detection-Logik wie das echte Script
echo "=== Build-Deploy Kompatibilitätstest ==="
echo ""

for dir in /opt/trading-hub /opt/travel-beat /opt/risk-hub /opt/weltenhub /opt/bfagent-app /opt/wedding-hub; do # noqa: hardcode
    app=$(basename "$dir")
    repo_name="$app"
    [ "$app" = "bfagent-app" ] && repo_name="bfagent"
    echo "--- $app (repo: $repo_name) ---"

    # Compose file? (same logic as build-deploy.sh)
    compose=""
    [ -f "$dir/docker-compose.prod.yml" ] && compose="$dir/docker-compose.prod.yml"
    [ -f "$dir/deploy/docker-compose.prod.yml" ] && compose="$dir/deploy/docker-compose.prod.yml"
    if [ -z "$compose" ]; then
        echo "  SKIP: Kein docker-compose.prod.yml"
        echo ""
        continue
    fi
    echo "  Compose: $compose"

    # Image from compose (same logic as build-deploy.sh)
    image=$(grep -oP 'ghcr\.io/achimdehnert/[^:"]+:latest' "$compose" | head -1)
    [ -z "$image" ] && image="ghcr.io/achimdehnert/${repo_name}:latest (fallback)"
    echo "  Image: $image"

    # Port detection (same logic as build-deploy.sh)
    port=$(grep -A2 'ports:' "$compose" | grep -oP '\b(8[0-9]{3}):\d+' | head -1 | cut -d: -f1) # noqa: hardcode
    if [ -z "$port" ]; then
        container="${app//-/_}_web"
        port=$(docker port "$container" 2>/dev/null | grep -oP '\d+$' | head -1) # noqa: hardcode
    fi
    [ -z "$port" ] && port="8088 (default)" # noqa: hardcode
    echo "  Port: $port"

    # Running container image (for comparison)
    container="${app//-/_}_web"
    running=$(docker inspect --format='{{.Config.Image}}' "$container" 2>/dev/null || echo "nicht laufend")
    echo "  Running: $running"

    # Health endpoint test
    port_num=$(echo "$port" | grep -oP '^\d+')
    if [ -n "$port_num" ]; then
        health_ok="FAIL"
        for path in /livez/ /health/ /healthz/; do
            code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://localhost:${port_num}${path}" 2>/dev/null) # noqa: hardcode
            if [ "$code" = "200" ]; then
                health_ok="OK ($path)"
                break
            fi
        done
        echo "  Health: $health_ok"
    fi

    echo ""
done

echo "=== Script ==="
ls -la /opt/build-deploy.sh 2>/dev/null && echo "OK" || echo "FEHLT" # noqa: hardcode
echo ""
echo "=== Usage ==="
echo 'nohup bash /opt/build-deploy.sh <app-name> > /dev/null 2>&1 &' # noqa: hardcode
echo 'cat /opt/<app-name>/build-deploy.status' # noqa: hardcode
