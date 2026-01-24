#!/bin/bash
#
# BF Agent Health Check Script
# =============================
# Quick health check for monitoring
#
# Usage:
#   ./scripts/health_check.sh
#
# Exit codes:
#   0 = Healthy
#   1 = Unhealthy

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

HEALTHY=true

echo "BF Agent Health Check"
echo "===================="
echo ""

# Check 1: Service Running
echo -n "Service Status: "
if systemctl is-active --quiet bfagent; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ Not Running${NC}"
    HEALTHY=false
fi

# Check 2: HTTP Response
echo -n "HTTP Check: "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health/ 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ OK (200)${NC}"
else
    echo -e "${RED}❌ Failed ($HTTP_CODE)${NC}"
    HEALTHY=false
fi

# Check 3: Database Connection
echo -n "Database: "
if docker exec bfagent_db pg_isready -U bfagent -d bfagent_prod &>/dev/null; then
    echo -e "${GREEN}✅ Connected${NC}"
else
    echo -e "${RED}❌ Not Connected${NC}"
    HEALTHY=false
fi

# Check 4: Redis Connection
echo -n "Redis: "
if docker exec bfagent_redis redis-cli ping &>/dev/null | grep -q "PONG"; then
    echo -e "${GREEN}✅ Connected${NC}"
else
    echo -e "${RED}❌ Not Connected${NC}"
    HEALTHY=false
fi

# Check 5: Disk Space
echo -n "Disk Space: "
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    echo -e "${GREEN}✅ ${DISK_USAGE}% used${NC}"
elif [ "$DISK_USAGE" -lt 90 ]; then
    echo -e "${YELLOW}⚠️  ${DISK_USAGE}% used${NC}"
else
    echo -e "${RED}❌ ${DISK_USAGE}% used (critical)${NC}"
    HEALTHY=false
fi

# Check 6: Memory Usage
echo -n "Memory: "
MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3*100/$2}')
if [ "$MEM_USAGE" -lt 80 ]; then
    echo -e "${GREEN}✅ ${MEM_USAGE}% used${NC}"
elif [ "$MEM_USAGE" -lt 90 ]; then
    echo -e "${YELLOW}⚠️  ${MEM_USAGE}% used${NC}"
else
    echo -e "${RED}❌ ${MEM_USAGE}% used (critical)${NC}"
fi

# Check 7: SSL Certificate
echo -n "SSL Certificate: "
CERT_DAYS=$(echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -checkend 0 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Valid${NC}"
else
    echo -e "${RED}❌ Expired or Invalid${NC}"
    HEALTHY=false
fi

echo ""
echo "===================="

if [ "$HEALTHY" = true ]; then
    echo -e "${GREEN}Status: HEALTHY ✅${NC}"
    exit 0
else
    echo -e "${RED}Status: UNHEALTHY ❌${NC}"
    exit 1
fi
