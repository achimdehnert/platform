#!/bin/bash
# Travel Beat - Hetzner Server Setup Script
# Run this on the Hetzner server as root

set -e

echo "=== Travel Beat Server Setup ==="

# 1. Create directory
echo "Creating /opt/travel-beat..."
mkdir -p /opt/travel-beat
cd /opt/travel-beat

# 2. Copy docker-compose.prod.yml from repo
echo "Downloading docker-compose.prod.yml..."
curl -sL https://raw.githubusercontent.com/achimdehnert/travel-beat/main/docker/docker-compose.prod.yml -o docker-compose.prod.yml

# 3. Create .env.prod
echo "Creating .env.prod..."
cat > .env.prod << 'EOF'
# Django
SECRET_KEY=$(openssl rand -base64 32)
ALLOWED_HOSTS=travel-beat.iil.pet,localhost
CSRF_TRUSTED_ORIGINS=https://travel-beat.iil.pet

# Database
POSTGRES_DB=travel_beat
POSTGRES_USER=travelbeat
POSTGRES_PASSWORD=$(openssl rand -base64 16)

# Image Tag
TRAVELBEAT_IMAGE_TAG=latest

# API Keys (fill in manually)
ANTHROPIC_API_KEY=

# Stripe (fill in later)
STRIPE_PUBLIC_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
EOF

# Generate actual secrets
SECRET_KEY=$(openssl rand -base64 32)
POSTGRES_PASSWORD=$(openssl rand -base64 16)
sed -i "s|SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|" .env.prod
sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|" .env.prod

echo "Generated secrets in .env.prod"

# 4. Update BF Agent Caddyfile
echo ""
echo "=== MANUAL STEP REQUIRED ==="
echo "Add this to /opt/bfagent/Caddyfile:"
echo ""
cat << 'CADDY'
travel-beat.iil.pet {
    encode gzip
    reverse_proxy travel-beat-web:8000
}
CADDY
echo ""
echo "Then run: docker compose -f /opt/bfagent/docker-compose.prod.yml restart caddy"
echo ""

# 5. Start services
echo "Starting Travel Beat services..."
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "=== Setup Complete ==="
echo "Check status: docker compose -f docker-compose.prod.yml ps"
echo "View logs: docker compose -f docker-compose.prod.yml logs -f"
