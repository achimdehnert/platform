#!/bin/bash
# CAD-Hub Production Deployment Script

set -e

echo "=== CAD-Hub Deployment ==="

# Check required environment variables
if [ -z "$DB_PASSWORD" ]; then
    echo "ERROR: DB_PASSWORD not set"
    exit 1
fi

# Build frontend
echo "Building frontend..."
cd ../frontend
npm install
npm run build
cd ../deploy

# Build and start services
echo "Starting services..."
docker compose -f docker-compose.prod.yml up -d --build

# Wait for health
echo "Waiting for API health..."
sleep 10
curl -sf http://localhost/health || echo "Warning: Health check failed"

echo "=== Deployment Complete ==="
echo "API: https://your-domain.com/api/docs"
echo "Frontend: https://your-domain.com"
