# ADR-008: Infrastructure Services & Self-Healing Deployment

**Status:** PROPOSED  
**Version:** 1.0  
**Datum:** 2026-02-01  
**Autoren:** Platform Architecture Team

---

## Executive Summary

Dieses ADR definiert die **Infrastructure-as-Code-Architektur** und das **Self-Healing-Deployment-System** für die BF Agent Platform. Es etabliert Standards für Service-Deployment, automatisierte Fehleranalyse und autonome Reparaturmechanismen.

| Prinzip | Umsetzung |
|---------|-----------|
| **GitOps** | Infrastruktur-Code in Git, deklarativ, versioniert |
| **Self-Healing** | Autonome Fehleranalyse und sichere Auto-Fixes |
| **Zero-Downtime** | Blue-Green/Rolling Deployments, Atomic Switches |
| **Observability** | Structured Logging, Metrics, Alerting |
| **Defense in Depth** | Multi-Layer Security, Least Privilege |

---

## Inhaltsverzeichnis

1. [Kontext & Problemstellung](#1-kontext--problemstellung)
2. [Ziele & Nicht-Ziele](#2-ziele--nicht-ziele)
3. [Service-Topologie](#3-service-topologie)
4. [Deployment-Architektur](#4-deployment-architektur)
5. [Self-Healing-System](#5-self-healing-system)
6. [CI/CD-Pipeline](#6-cicd-pipeline)
7. [Infrastructure as Code](#7-infrastructure-as-code)
8. [Monitoring & Observability](#8-monitoring--observability)
9. [Security](#9-security)
10. [Package Management](#10-package-management)
11. [Disaster Recovery](#11-disaster-recovery)
12. [Implementierung](#12-implementierung)
13. [Konsequenzen](#13-konsequenzen)

---

## 1. Kontext & Problemstellung

### Aktuelle Service-Landschaft

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BF AGENT ECOSYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Production Services                                                        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │    BF Agent     │    │   Travel Beat   │    │   Docs Portal   │         │
│  │ bfagent.iil.pet │    │travel-beat.iil  │    │ docs.bfagent.de │         │
│  │   (Django)      │    │    (Django)     │    │    (Sphinx)     │         │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘         │
│           │                      │                      │                   │
│           └──────────────────────┼──────────────────────┘                   │
│                                  │                                          │
│  ┌───────────────────────────────▼───────────────────────────────────┐     │
│  │                     Shared Platform Layer                          │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │     │
│  │  │  bfagent-   │  │  creative-  │  │   sphinx-   │  │    MCP    │ │     │
│  │  │    core     │  │  services   │  │   export    │  │    Hub    │ │     │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘ │     │
│  └───────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  Infrastructure (Hetzner Cloud)                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Terraform │ Docker Compose │ Nginx │ PostgreSQL │ Redis │ Traefik  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Problemstellung

1. **Manuelle Deployments** – Fehleranfällig, nicht reproduzierbar
2. **Keine automatische Fehlerbehebung** – Downtime bei bekannten Problemen
3. **Fehlende Standardisierung** – Jedes Projekt eigene Deployment-Logik
4. **Kein Rollback-Konzept** – Manuelle Intervention erforderlich
5. **Limitierte Observability** – Keine zentrale Fehleranalyse

---

## 2. Ziele & Nicht-Ziele

### Ziele

| ID | Anforderung | Priorität |
|----|-------------|-----------|
| I1 | GitOps: Alle Infra-Änderungen via Git | **Must** |
| I2 | Self-Healing für bekannte Fehlerklassen | **Must** |
| I3 | Zero-Downtime Deployments | **Must** |
| I4 | Automatisches Rollback bei Failures | **Must** |
| I5 | Zentrale Deployment-Pipeline für alle Services | **Should** |
| I6 | AI-gestützte Fehleranalyse (Claude) | **Should** |
| I7 | Multi-Environment Support (staging/prod) | **Must** |
| I8 | Secrets Management | **Must** |

### Nicht-Ziele

- Multi-Cloud-Support (aktuell nur Hetzner)
- Kubernetes-Migration (Phase >1)
- Auto-Scaling (Phase >1)

---

## 3. Service-Topologie

### 3.1 Service-Registry

```yaml
# services/registry.yaml
services:
  bfagent:
    type: django
    domain: bfagent.iil.pet
    repo: achimdehnert/bfagent
    tier: production
    resources:
      cpu: 2
      memory: 4GB
    dependencies:
      - postgresql
      - redis
      - creative-services
    health_endpoint: /health/
    
  travel-beat:
    type: django
    domain: travel-beat.iil.pet
    repo: achimdehnert/travel-beat
    tier: production
    resources:
      cpu: 2
      memory: 4GB
    dependencies:
      - postgresql
      - redis
      - creative-services
    health_endpoint: /health/
    
  docs:
    type: static
    domain: docs.bfagent.de
    repo: achimdehnert/platform
    tier: production
    resources:
      cpu: 1
      memory: 512MB
    health_endpoint: /build-info.txt
```

### 3.2 Package-Registry

```yaml
# packages/registry.yaml
packages:
  bfagent-core:
    path: packages/bfagent-core
    version: 0.1.0
    type: library
    consumers:
      - bfagent
      - travel-beat
      
  creative-services:
    path: packages/creative-services
    version: 0.2.0
    type: library
    extras:
      - openai
      - anthropic
    consumers:
      - bfagent
      - travel-beat
      
  sphinx-export:
    path: packages/sphinx-export
    version: 0.1.0
    type: tool
    consumers:
      - docs
```

### 3.3 Environment-Matrix

| Environment | Domain Suffix | Branch | Auto-Deploy | Self-Healing |
|-------------|--------------|--------|-------------|--------------|
| development | .dev.iil.pet | feature/* | ❌ | ❌ |
| staging | .staging.iil.pet | develop | ✅ | ✅ (all) |
| production | .iil.pet | main | ✅ (manual approve) | ✅ (safe only) |

---

## 4. Deployment-Architektur

### 4.1 Deployment-Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          DEPLOYMENT PIPELINE                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│   │  Code   │───▶│  Build  │───▶│  Test   │───▶│ Deploy  │───▶│ Verify  │  │
│   │  Push   │    │  Image  │    │  Suite  │    │ Release │    │ Health  │  │
│   └─────────┘    └─────────┘    └─────────┘    └─────────┘    └────┬────┘  │
│                                                                     │       │
│                                      ┌──────────────────────────────┘       │
│                                      │                                      │
│                                      ▼                                      │
│                              ┌───────────────┐                              │
│                              │  Health OK?   │                              │
│                              └───────┬───────┘                              │
│                                      │                                      │
│                        ┌─────────────┼─────────────┐                        │
│                        │ YES         │          NO │                        │
│                        ▼             │             ▼                        │
│                  ┌─────────┐         │      ┌─────────────┐                 │
│                  │ SUCCESS │         │      │ Self-Heal   │                 │
│                  └─────────┘         │      │   Agent     │                 │
│                                      │      └──────┬──────┘                 │
│                                      │             │                        │
│                                      │      ┌──────▼──────┐                 │
│                                      │      │ Analyzable? │                 │
│                                      │      └──────┬──────┘                 │
│                                      │             │                        │
│                                      │   ┌─────────┼─────────┐              │
│                                      │   │ YES     │      NO │              │
│                                      │   ▼         │         ▼              │
│                                      │ ┌───────┐   │   ┌──────────┐         │
│                                      │ │Auto-  │   │   │ Human    │         │
│                                      │ │ Fix   │   │   │ Review   │         │
│                                      │ └───┬───┘   │   └──────────┘         │
│                                      │     │       │                        │
│                                      │     ▼       │                        │
│                                      │  Retry ─────┘                        │
│                                      │  Deploy                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Release-Strategie

```yaml
# deployment/strategy.yaml
release:
  type: atomic-switch  # Symlink-basiert für Static, Rolling für Containers
  
  static_sites:
    method: symlink
    releases_dir: /var/www/{service}/releases
    current_link: /var/www/{service}/current
    keep_releases: 20
    
  containers:
    method: rolling
    replicas: 2
    max_unavailable: 0
    max_surge: 1
    health_check_interval: 10s
    health_check_timeout: 5s
    health_check_retries: 3

rollback:
  auto_trigger_on:
    - health_check_failure
    - error_rate_threshold: 5%  # 5% 5xx in 1 Minute
    - response_time_threshold: 5s  # P95 > 5s
  max_auto_rollbacks: 2
  human_review_after: 2
```

### 4.3 Server-Layout

```
/opt/
├── terraform/           # Infrastructure as Code
│   ├── main.tf
│   ├── variables.tf
│   └── .terraform/
│
├── apps/
│   ├── bfagent/
│   │   ├── docker-compose.yml
│   │   ├── .env
│   │   └── data/
│   │       ├── postgres/
│   │       └── redis/
│   │
│   └── travel-beat/
│       ├── docker-compose.yml
│       ├── .env
│       └── data/
│
├── shared/
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── sites-enabled/
│   └── traefik/
│       └── traefik.yml
│
└── scripts/
    ├── deploy.sh
    ├── rollback.sh
    └── health-check.sh

/var/www/
├── docs.bfagent.de/
│   ├── releases/
│   │   ├── abc123/
│   │   └── def456/
│   ├── versions/
│   │   ├── v1.0.0/
│   │   └── v1.1.0/
│   └── current -> releases/def456/
│
└── letsencrypt/
    └── live/
```

---

## 5. Self-Healing-System

### 5.1 Architektur

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         SELF-HEALING ARCHITECTURE                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐         ┌─────────────────┐         ┌───────────────┐  │
│  │  Error Source   │────────▶│  Error Analyzer │────────▶│ Decision      │  │
│  │                 │         │    (Claude)     │         │   Engine      │  │
│  │ • Deploy Log    │         │                 │         │               │  │
│  │ • Health Check  │         │ • Classify      │         │ • confidence  │  │
│  │ • Container Log │         │ • Root Cause    │         │ • risk_level  │  │
│  │ • Terraform     │         │ • Fix Suggest   │         │ • auto_fix?   │  │
│  └─────────────────┘         └─────────────────┘         └───────┬───────┘  │
│                                                                   │          │
│                                           ┌───────────────────────┼──────┐   │
│                                           │                       │      │   │
│                                           ▼                       ▼      │   │
│                                   ┌───────────────┐       ┌────────────┐ │   │
│                                   │   AUTO-FIX    │       │   HUMAN    │ │   │
│                                   │   Executor    │       │   REVIEW   │ │   │
│                                   │               │       │            │ │   │
│                                   │ • Run Fix     │       │ • Slack    │ │   │
│                                   │ • Validate    │       │ • PR       │ │   │
│                                   │ • Rollback    │       │ • PagerDuty│ │   │
│                                   └───────────────┘       └────────────┘ │   │
│                                                                          │   │
│  ┌────────────────────────────────────────────────────────────────────┐  │   │
│  │                          FIX REGISTRY                              │  │   │
│  │                                                                    │  │   │
│  │  ┌──────────────────┬──────────┬────────┬─────────────────────┐   │  │   │
│  │  │ Error Pattern    │ Category │ Risk   │ Fix                 │   │  │   │
│  │  ├──────────────────┼──────────┼────────┼─────────────────────┤   │  │   │
│  │  │ 429 Too Many Req │ INFRA    │ LOW    │ Retry with backoff  │   │  │   │
│  │  │ Image not found  │ BUILD    │ LOW    │ Fallback tag        │   │  │   │
│  │  │ OOMKilled        │ RUNTIME  │ MEDIUM │ Increase limits     │   │  │   │
│  │  │ Permission denied│ PERM     │ LOW    │ chmod 600           │   │  │   │
│  │  │ State lock       │ INFRA    │ LOW    │ force-unlock        │   │  │   │
│  │  │ No space left    │ RUNTIME  │ LOW    │ docker prune        │   │  │   │
│  │  │ DB Migration     │ DEPLOY   │ HIGH   │ HUMAN REVIEW        │   │  │   │
│  │  │ SSL/DNS change   │ NETWORK  │ HIGH   │ HUMAN REVIEW        │   │  │   │
│  │  └──────────────────┴──────────┴────────┴─────────────────────┘   │  │   │
│  └────────────────────────────────────────────────────────────────────┘  │   │
│                                                                          │   │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Error-Klassifizierung

```python
# concepts/hetzner_auto_healer.py

from enum import Enum
from dataclasses import dataclass

class Category(Enum):
    INFRASTRUCTURE = "INFRASTRUCTURE"  # Hetzner API, Provisioning
    BUILD = "BUILD"                    # Docker, Dependencies
    DEPLOY = "DEPLOY"                  # Container-Start, Migrations
    RUNTIME = "RUNTIME"                # Crashes, Memory, CPU
    NETWORK = "NETWORK"                # DNS, SSL, Firewall
    PERMISSION = "PERMISSION"          # SSH, Tokens, Files

class Severity(Enum):
    CRITICAL = "CRITICAL"  # Sofortige Aktion, Service down
    HIGH = "HIGH"          # Service degraded
    MEDIUM = "MEDIUM"      # Feature nicht verfügbar
    LOW = "LOW"            # Cosmetic, Logging

class RiskLevel(Enum):
    LOW = "LOW"       # Auto-Fix erlaubt
    MEDIUM = "MEDIUM" # Auto-Fix mit Approval
    HIGH = "HIGH"     # Human Review required

@dataclass
class ErrorAnalysis:
    category: Category
    severity: Severity
    confidence: int  # 0-100
    root_cause: str
    error_pattern: str
    
@dataclass
class ProposedFix:
    action: str  # AUTO-FIX | HUMAN_REVIEW
    risk: RiskLevel
    commands: list[str]
    rollback: list[str]
    validation: list[str]
    prevention: str
```

### 5.3 Auto-Fix-Regeln

```yaml
# concepts/auto_fix_rules.yaml
rules:
  # ═══════════════════════════════════════════════════════════════════════════
  # AUTO-FIX ERLAUBT (confidence >= 85%, risk = LOW)
  # ═══════════════════════════════════════════════════════════════════════════
  
  rate_limit:
    pattern: "429 Too Many Requests"
    category: INFRASTRUCTURE
    confidence: 95
    risk: LOW
    fix:
      commands:
        - "sleep $((2**${RETRY_COUNT:-1} * 30))"
        - "${ORIGINAL_COMMAND}"
      max_retries: 3
      
  image_not_found:
    pattern: "manifest.*unknown|image.*not found"
    category: BUILD
    confidence: 90
    risk: LOW
    fix:
      commands:
        - "FALLBACK_TAG=$(git rev-parse HEAD~1 | head -c 7)"
        - "docker pull ${REGISTRY}/${IMAGE}:${FALLBACK_TAG}"
        - "docker tag ${REGISTRY}/${IMAGE}:${FALLBACK_TAG} ${REGISTRY}/${IMAGE}:${TARGET_TAG}"
      validation:
        - "docker images | grep ${IMAGE}"
        
  ssh_permission:
    pattern: "Permission denied.*publickey|bad permissions"
    category: PERMISSION
    confidence: 95
    risk: LOW
    fix:
      commands:
        - "chmod 600 ~/.ssh/id_*"
        - "chmod 700 ~/.ssh"
      validation:
        - "ls -la ~/.ssh/"
        
  terraform_lock:
    pattern: "Error acquiring the state lock|Lock Info"
    category: INFRASTRUCTURE
    confidence: 85
    risk: LOW
    fix:
      precondition:
        - "LOCK_AGE=$(terraform state list 2>&1 | grep -oP 'Created:\\s*\\K.*')"
        - "test $(date -d \"$LOCK_AGE\" +%s) -lt $(date -d '10 minutes ago' +%s)"
      commands:
        - "LOCK_ID=$(terraform force-unlock -force 2>&1 | grep -oP 'ID:\\s*\\K[a-f0-9-]+')"
        - "terraform force-unlock -force ${LOCK_ID}"
      validation:
        - "terraform plan -detailed-exitcode"
        
  no_space:
    pattern: "no space left on device|disk full"
    category: RUNTIME
    confidence: 90
    risk: LOW
    fix:
      commands:
        - "docker system prune -af --volumes"
        - "journalctl --vacuum-time=7d"
      validation:
        - "df -h / | awk 'NR==2 {print $5}' | grep -v '9[0-9]%'"
        
  oom_killed:
    pattern: "OOMKilled|Out of memory|memory limit"
    category: RUNTIME
    confidence: 85
    risk: MEDIUM  # Needs approval
    fix:
      commands:
        - "CURRENT_LIMIT=$(docker inspect ${CONTAINER} | jq -r '.[0].HostConfig.Memory')"
        - "NEW_LIMIT=$((CURRENT_LIMIT * 2))"
        - "docker update --memory ${NEW_LIMIT} ${CONTAINER}"
      max_increase: 2x
      validation:
        - "docker stats --no-stream ${CONTAINER}"

  # ═══════════════════════════════════════════════════════════════════════════
  # HUMAN REVIEW REQUIRED (risk >= MEDIUM or confidence < 85%)
  # ═══════════════════════════════════════════════════════════════════════════
  
  database_migration:
    pattern: "migration|migrate|alembic|django.*migrate"
    category: DEPLOY
    confidence: 70
    risk: HIGH
    action: HUMAN_REVIEW
    notification:
      - slack: "#deployments"
      - pagerduty: "infrastructure"
      
  ssl_certificate:
    pattern: "SSL|TLS|certificate|cert.*expired"
    category: NETWORK
    confidence: 80
    risk: HIGH
    action: HUMAN_REVIEW
    
  dns_change:
    pattern: "DNS|CNAME|A record|nameserver"
    category: NETWORK
    confidence: 75
    risk: HIGH
    action: HUMAN_REVIEW
    
  secrets_credentials:
    pattern: "secret|credential|token|api.?key|password"
    category: PERMISSION
    confidence: 60
    risk: HIGH
    action: HUMAN_REVIEW
```

### 5.4 Claude Integration

```python
# concepts/hetzner_auto_healer.py

SYSTEM_PROMPT = """Du bist ein autonomer DevOps-Agent für Hetzner Cloud Deployments.

## ROLLE
Analysiere Deployment-Fehler und generiere konkrete, ausführbare Fixes.

## KATEGORIEN
- INFRASTRUCTURE: Hetzner API, Provisioning, Netzwerk
- BUILD: Docker, Dependencies, Compilation
- DEPLOY: Container-Start, Health, Migrations
- RUNTIME: Crashes, Memory, CPU
- NETWORK: DNS, SSL, Firewall
- PERMISSION: SSH, Tokens, Dateiberechtigungen

## ENTSCHEIDUNGSLOGIK

AUTO-FIX (confidence ≥85%, risk=LOW):
- Dependency Mismatches → Version anpassen
- Image Tag fehlt → Fallback auf vorheriges Tag
- Rate Limits → Retry mit Backoff
- SSH Permissions → chmod 600
- Terraform Lock → force-unlock nach 10min
- Fehlende Dirs → mkdir -p

HUMAN REVIEW (confidence <85% oder risk≥MEDIUM):
- DB Migrations, Secrets, Firewall, DNS, Rollbacks, Skalierung

## OUTPUT FORMAT (YAML)

```yaml
analysis:
  category: CATEGORY
  severity: CRITICAL|HIGH|MEDIUM|LOW
  confidence: 0-100
  root_cause: "Kurze Beschreibung"
  
fix:
  action: AUTO-FIX|HUMAN_REVIEW
  risk: LOW|MEDIUM|HIGH
  commands:
    - "cmd1"
    - "cmd2"
  rollback:
    - "rollback_cmd"
  validation:
    - "validation_cmd"
  
prevention: "Empfehlung"
```

## REGELN
1. NIEMALS Secrets in Output
2. IMMER Rollback-Option
3. Bei Unsicherheit → HUMAN_REVIEW
4. Konkrete, copy-paste-fähige Befehle"""


async def analyze_error(error_log: str, context: dict) -> dict:
    """Analysiert Fehler mit Claude."""
    import anthropic
    
    client = anthropic.Anthropic()
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""DEPLOYMENT_CONTEXT:
  project: {context.get('project', 'unknown')}
  environment: {context.get('environment', 'unknown')}
  service: {context.get('service', 'unknown')}
  timestamp: {context.get('timestamp', 'unknown')}

ERROR_LOG:
{error_log[-5000:]}  # Letzte 5000 Zeichen
"""
        }]
    )
    
    return parse_yaml_response(message.content[0].text)
```

---

## 6. CI/CD-Pipeline

### 6.1 GitHub Actions Workflow

```yaml
# .github/workflows/self-healing-deploy.yml
name: 🚀 Self-Healing Deploy

on:
  push:
    branches: [main, develop]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment Environment'
        required: true
        default: 'staging'
        type: choice
        options: [staging, production]
      auto_fix:
        description: 'Enable Auto-Fix'
        required: false
        default: true
        type: boolean

env:
  REGISTRY: ghcr.io/${{ github.repository }}

jobs:
  # ══════════════════════════════════════════════════════════════════════════
  # BUILD
  # ══════════════════════════════════════════════════════════════════════════
  build:
    name: 🔨 Build & Test
    runs-on: ubuntu-latest
    outputs:
      image_tag: ${{ steps.meta.outputs.tags }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Docker Meta
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}
          tags: |
            type=sha,prefix=
            type=ref,event=branch
      
      - name: Build & Push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Run Tests
        run: |
          docker run --rm ${{ env.REGISTRY }}:${{ github.sha }} pytest

  # ══════════════════════════════════════════════════════════════════════════
  # DEPLOY
  # ══════════════════════════════════════════════════════════════════════════
  deploy:
    name: 🚀 Deploy to ${{ inputs.environment || 'staging' }}
    needs: build
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment || 'staging' }}
    outputs:
      status: ${{ steps.deploy.outcome }}
      error_log: ${{ steps.capture_error.outputs.log }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.HETZNER_SSH_KEY }}" > ~/.ssh/id_ed25519
          chmod 600 ~/.ssh/id_ed25519
          ssh-keyscan -H ${{ secrets.HETZNER_HOST }} >> ~/.ssh/known_hosts
      
      - name: Deploy Application
        id: deploy
        continue-on-error: true
        env:
          IMAGE_TAG: ${{ needs.build.outputs.image_tag }}
        run: |
          {
            echo "=== DEPLOYMENT START: $(date -Iseconds) ==="
            
            # SSH Deploy
            ssh ${{ secrets.HETZNER_USER }}@${{ secrets.HETZNER_HOST }} << 'DEPLOY'
              cd /opt/apps/${{ github.event.repository.name }}
              docker-compose pull
              docker-compose up -d
            DEPLOY
            
            # Health Check
            for i in {1..30}; do
              if curl -sf "https://${{ vars.APP_DOMAIN }}/health/"; then
                echo "✅ Health check passed"
                exit 0
              fi
              echo "Waiting for health check... ($i/30)"
              sleep 10
            done
            
            echo "❌ Health check failed"
            exit 1
            
          } 2>&1 | tee deploy.log
      
      - name: Capture Error Log
        id: capture_error
        if: steps.deploy.outcome == 'failure'
        run: |
          ERROR_LOG=$(tail -200 deploy.log | base64 -w 0)
          echo "log=$ERROR_LOG" >> $GITHUB_OUTPUT
      
      - name: Upload Deploy Log
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: deploy-log-${{ github.run_id }}
          path: deploy.log

  # ══════════════════════════════════════════════════════════════════════════
  # SELF-HEALING
  # ══════════════════════════════════════════════════════════════════════════
  self-heal:
    name: 🔧 Error Analysis & Auto-Fix
    needs: deploy
    if: needs.deploy.outputs.status == 'failure' && inputs.auto_fix != false
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Download Deploy Log
        uses: actions/download-artifact@v4
        with:
          name: deploy-log-${{ github.run_id }}
      
      - name: Analyze Error with Claude
        id: analyze
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python concepts/hetzner_auto_healer.py \
            --log deploy.log \
            --context '{"project": "${{ github.repository }}", "environment": "${{ inputs.environment }}"}' \
            --output analysis.json
          
          echo "analysis=$(cat analysis.json | jq -c)" >> $GITHUB_OUTPUT
      
      - name: Execute Auto-Fix
        if: fromJson(steps.analyze.outputs.analysis).fix.action == 'AUTO-FIX'
        run: |
          COMMANDS=$(echo '${{ steps.analyze.outputs.analysis }}' | jq -r '.fix.commands[]')
          
          for cmd in $COMMANDS; do
            echo "Executing: $cmd"
            eval "$cmd"
          done
      
      - name: Validate Fix
        if: fromJson(steps.analyze.outputs.analysis).fix.action == 'AUTO-FIX'
        run: |
          VALIDATIONS=$(echo '${{ steps.analyze.outputs.analysis }}' | jq -r '.fix.validation[]')
          
          for check in $VALIDATIONS; do
            echo "Validating: $check"
            eval "$check"
          done
      
      - name: Create Review PR
        if: fromJson(steps.analyze.outputs.analysis).fix.action == 'HUMAN_REVIEW'
        uses: peter-evans/create-pull-request@v5
        with:
          title: "🔧 Fix: ${{ fromJson(steps.analyze.outputs.analysis).analysis.root_cause }}"
          body: |
            ## Error Analysis
            
            **Category:** ${{ fromJson(steps.analyze.outputs.analysis).analysis.category }}
            **Severity:** ${{ fromJson(steps.analyze.outputs.analysis).analysis.severity }}
            **Confidence:** ${{ fromJson(steps.analyze.outputs.analysis).analysis.confidence }}%
            
            ### Root Cause
            ${{ fromJson(steps.analyze.outputs.analysis).analysis.root_cause }}
            
            ### Suggested Fix
            ```bash
            ${{ join(fromJson(steps.analyze.outputs.analysis).fix.commands, '\n') }}
            ```
            
            ### Rollback
            ```bash
            ${{ join(fromJson(steps.analyze.outputs.analysis).fix.rollback, '\n') }}
            ```
          branch: fix/auto-${{ github.run_id }}
      
      - name: Notify Slack
        if: always()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Deployment ${{ needs.deploy.outputs.status }}: ${{ github.repository }}",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*${{ needs.deploy.outputs.status == 'failure' && '❌' || '✅' }} Deployment ${{ needs.deploy.outputs.status }}*\n*Repo:* ${{ github.repository }}\n*Branch:* ${{ github.ref_name }}\n*Environment:* ${{ inputs.environment || 'staging' }}"
                  }
                }
              ]
            }
```

### 6.2 Docs Deployment

```yaml
# .github/workflows/docs.yml
name: 📚 Deploy Docs

on:
  push:
    branches: [main]
    paths:
      - 'docs/**'
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install Dependencies
        run: pip install -r docs/requirements.txt
      
      - name: Build Docs
        run: sphinx-build -W -b html docs/source docs/_build/html
      
      - name: Deploy to Hetzner
        env:
          SSH_KEY: ${{ secrets.HETZNER_SSH_KEY }}
        run: |
          # Setup SSH
          mkdir -p ~/.ssh
          echo "$SSH_KEY" > ~/.ssh/id_ed25519
          chmod 600 ~/.ssh/id_ed25519
          
          RELEASE_DIR="/var/www/docs.bfagent.de/releases/${{ github.sha }}"
          
          # Upload
          rsync -avz --delete \
            docs/_build/html/ \
            ${{ secrets.HETZNER_USER }}@${{ secrets.HETZNER_HOST }}:${RELEASE_DIR}/
          
          # Atomic switch
          ssh ${{ secrets.HETZNER_USER }}@${{ secrets.HETZNER_HOST }} \
            "ln -sfn ${RELEASE_DIR} /var/www/docs.bfagent.de/current"
          
          # Cleanup old releases (keep 20)
          ssh ${{ secrets.HETZNER_USER }}@${{ secrets.HETZNER_HOST }} \
            "ls -1dt /var/www/docs.bfagent.de/releases/* | tail -n +21 | xargs rm -rf"
```

---

## 7. Infrastructure as Code

### 7.1 Terraform-Struktur

```hcl
# terraform/main.tf

terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.44"
    }
  }
  
  backend "s3" {
    bucket = "platform-terraform-state"
    key    = "hetzner/terraform.tfstate"
    region = "eu-central-1"
  }
}

provider "hcloud" {
  token = var.hcloud_token
}

# ══════════════════════════════════════════════════════════════════════════════
# NETWORK
# ══════════════════════════════════════════════════════════════════════════════

resource "hcloud_network" "platform" {
  name     = "platform-network"
  ip_range = "10.0.0.0/16"
}

resource "hcloud_network_subnet" "apps" {
  network_id   = hcloud_network.platform.id
  type         = "cloud"
  network_zone = "eu-central"
  ip_range     = "10.0.1.0/24"
}

# ══════════════════════════════════════════════════════════════════════════════
# SERVERS
# ══════════════════════════════════════════════════════════════════════════════

resource "hcloud_server" "app" {
  for_each = var.app_servers
  
  name        = each.key
  server_type = each.value.type
  image       = "ubuntu-24.04"
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.deploy.id]
  
  labels = {
    environment = each.value.environment
    service     = each.value.service
  }
  
  network {
    network_id = hcloud_network.platform.id
    ip         = each.value.private_ip
  }
  
  user_data = templatefile("${path.module}/cloud-init.yaml", {
    hostname     = each.key
    docker_tag   = var.docker_tag
    environment  = each.value.environment
  })
}

# ══════════════════════════════════════════════════════════════════════════════
# FIREWALL
# ══════════════════════════════════════════════════════════════════════════════

resource "hcloud_firewall" "app" {
  name = "app-firewall"
  
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "22"
    source_ips = var.admin_ips
  }
  
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}

# ══════════════════════════════════════════════════════════════════════════════
# DNS (via Cloudflare)
# ══════════════════════════════════════════════════════════════════════════════

resource "cloudflare_record" "app" {
  for_each = var.dns_records
  
  zone_id = var.cloudflare_zone_id
  name    = each.value.name
  type    = each.value.type
  value   = each.value.type == "A" ? hcloud_server.app[each.value.server].ipv4_address : each.value.value
  proxied = each.value.proxied
}
```

### 7.2 Variables

```hcl
# terraform/variables.tf

variable "hcloud_token" {
  description = "Hetzner Cloud API token"
  type        = string
  sensitive   = true
}

variable "location" {
  description = "Hetzner datacenter location"
  type        = string
  default     = "nbg1"  # Nürnberg
}

variable "app_servers" {
  description = "Application servers configuration"
  type = map(object({
    type        = string
    environment = string
    service     = string
    private_ip  = string
  }))
  default = {
    "bfagent-prod" = {
      type        = "cx32"
      environment = "production"
      service     = "bfagent"
      private_ip  = "10.0.1.10"
    }
    "travel-beat-prod" = {
      type        = "cx22"
      environment = "production"
      service     = "travel-beat"
      private_ip  = "10.0.1.11"
    }
  }
}

variable "admin_ips" {
  description = "IP addresses allowed for SSH"
  type        = list(string)
  default     = []
}
```

---

## 8. Monitoring & Observability

### 8.1 Stack-Übersicht

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        OBSERVABILITY STACK                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Metrics   │    │    Logs     │    │   Traces    │    │   Alerts    │  │
│  │ Prometheus  │    │    Loki     │    │   Jaeger    │    │ AlertManager│  │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘  │
│         │                  │                  │                  │          │
│         └──────────────────┼──────────────────┼──────────────────┘          │
│                            │                  │                             │
│                            ▼                  ▼                             │
│                    ┌───────────────────────────────┐                        │
│                    │           Grafana             │                        │
│                    │     Unified Dashboard         │                        │
│                    └───────────────────────────────┘                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Health-Check-Endpoints

```python
# health/views.py

from django.http import JsonResponse
from django.db import connection
from redis import Redis
import time

def health_check(request):
    """Comprehensive health check endpoint."""
    checks = {}
    overall = True
    
    # Database
    try:
        start = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = {
            "status": "healthy",
            "latency_ms": round((time.time() - start) * 1000, 2)
        }
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall = False
    
    # Redis
    try:
        start = time.time()
        redis = Redis.from_url(settings.REDIS_URL)
        redis.ping()
        checks["redis"] = {
            "status": "healthy",
            "latency_ms": round((time.time() - start) * 1000, 2)
        }
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}
        overall = False
    
    # Disk Space
    import shutil
    total, used, free = shutil.disk_usage("/")
    disk_percent = (used / total) * 100
    checks["disk"] = {
        "status": "healthy" if disk_percent < 90 else "warning",
        "percent_used": round(disk_percent, 1)
    }
    if disk_percent >= 95:
        overall = False
    
    response = {
        "status": "healthy" if overall else "unhealthy",
        "timestamp": time.time(),
        "version": settings.VERSION,
        "checks": checks
    }
    
    return JsonResponse(
        response,
        status=200 if overall else 503
    )
```

### 8.3 Deployment Metrics

```python
# metrics/deployment.py

from prometheus_client import Counter, Histogram, Gauge

deployment_total = Counter(
    'deployment_total',
    'Total deployments',
    ['service', 'environment', 'status']
)

deployment_duration = Histogram(
    'deployment_duration_seconds',
    'Deployment duration',
    ['service', 'environment'],
    buckets=[30, 60, 120, 300, 600, 1200]
)

self_healing_total = Counter(
    'self_healing_total',
    'Self-healing actions',
    ['service', 'category', 'action', 'success']
)

active_deployments = Gauge(
    'active_deployments',
    'Currently running deployments',
    ['service', 'environment']
)
```

---

## 9. Security

### 9.1 Secrets Management

```yaml
# secrets/structure.yaml
secrets:
  # GitHub Actions Secrets
  github:
    - HETZNER_HOST
    - HETZNER_USER
    - HETZNER_SSH_KEY
    - HCLOUD_TOKEN
    - ANTHROPIC_API_KEY
    - SLACK_WEBHOOK_URL
    
  # Server Environment
  server:
    - DATABASE_URL
    - REDIS_URL
    - SECRET_KEY
    - OPENAI_API_KEY
    - ANTHROPIC_API_KEY
    
  # Terraform Variables
  terraform:
    - TF_VAR_hcloud_token
    - TF_VAR_cloudflare_api_token
```

### 9.2 SSH Key Rotation

```yaml
# ops/runbooks/ssh-key-rotation.md
schedule: quarterly
steps:
  1. Generate new key pair
  2. Add new public key to servers
  3. Update GitHub Secret
  4. Test deployment with new key
  5. Remove old public key from servers
  6. Document rotation date
```

### 9.3 Network Security

```yaml
# security/network.yaml
firewall_rules:
  ingress:
    - port: 22
      source: admin_ips_only
      description: SSH access
    - port: 80
      source: cloudflare_ips
      description: HTTP (redirect to HTTPS)
    - port: 443
      source: cloudflare_ips
      description: HTTPS
      
  egress:
    - port: 443
      destination: api.anthropic.com
      description: Claude API
    - port: 443
      destination: api.openai.com
      description: OpenAI API
    - port: 443
      destination: ghcr.io
      description: Container Registry
```

---

## 10. Package Management

### 10.1 Monorepo-Struktur

```
platform/
├── packages/
│   ├── bfagent-core/           # Shared core (tenancy, context, audit)
│   │   ├── src/bfagent_core/
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   ├── creative-services/      # LLM client, generation services
│   │   ├── src/creative_services/
│   │   │   ├── core/           # LLMClient, Registry, Tracker
│   │   │   ├── adapters/       # Django, BFAgent
│   │   │   ├── character/
│   │   │   ├── scene/
│   │   │   ├── story/
│   │   │   └── world/
│   │   └── pyproject.toml
│   │
│   └── sphinx-export/          # Documentation tools
│       └── pyproject.toml
│
├── concepts/                   # Deployment concepts
│   ├── hetzner_auto_healer.py
│   ├── hetzner_deployment_prompt.md
│   └── github-workflow-self-healing.yml
│
└── docs/
    └── source/
```

### 10.2 Dependency Graph

```
bfagent (app)
├── bfagent-core
│   └── django
├── creative-services
│   ├── anthropic (optional)
│   ├── openai (optional)
│   └── pydantic
└── django

travel-beat (app)
├── bfagent-core
├── creative-services
└── django
```

### 10.3 Release-Strategie

```yaml
# packages/release.yaml
strategy:
  type: semantic-versioning
  
  triggers:
    patch: bug fixes, security updates
    minor: new features (backward compatible)
    major: breaking changes
    
  automation:
    - on_merge_to_main: bump patch, create tag
    - on_breaking_change_label: bump major
    - on_feature_label: bump minor
    
  consumers:
    - pin_to_minor: true  # "bfagent-core>=0.1,<0.2"
    - auto_update_staging: true
    - auto_update_production: false  # Manual approval
```

---

## 11. Disaster Recovery

### 11.1 Backup-Strategie

```yaml
# ops/backup.yaml
backups:
  database:
    schedule: "0 */6 * * *"  # Every 6 hours
    retention: 30 days
    storage: hetzner_storage_box
    encryption: aes-256-gcm
    
  volumes:
    schedule: "0 2 * * *"  # Daily at 2 AM
    retention: 7 days
    storage: hetzner_snapshot
    
  configs:
    method: git
    repo: platform-configs (private)
```

### 11.2 Recovery-Runbook

```markdown
# ops/runbooks/disaster-recovery.md

## Database Recovery

1. List available backups:
   ```bash
   restic -r s3:backup/postgres snapshots
   ```

2. Restore to point-in-time:
   ```bash
   restic -r s3:backup/postgres restore <snapshot-id> --target /tmp/restore
   pg_restore -d postgres /tmp/restore/dump.sql
   ```

## Full Server Recovery

1. Create new server via Terraform:
   ```bash
   terraform apply -var="server_name=bfagent-recovery"
   ```

2. Restore latest backup:
   ```bash
   ansible-playbook playbooks/restore.yml -e "server=bfagent-recovery"
   ```

3. Update DNS:
   ```bash
   terraform apply -var="dns_target=<new-server-ip>"
   ```

4. Verify health:
   ```bash
   curl -sf https://bfagent.iil.pet/health/
   ```
```

### 11.3 RTO/RPO-Ziele

| Metric | Target | Current |
|--------|--------|---------|
| RPO (Recovery Point Objective) | 6 hours | 6 hours |
| RTO (Recovery Time Objective) | 30 minutes | ~45 minutes |
| MTTR (Mean Time To Recovery) | 15 minutes | ~20 minutes |

---

## 12. Implementierung

### 12.1 Package-Struktur

```
concepts/
├── hetzner_auto_healer.py      # Self-Healing Agent
├── hetzner_prompt_compact.py   # Claude System Prompt
├── hetzner_deployment_prompt.md # Ausführliche Dokumentation
├── github-workflow-self-healing.yml
└── auto_fix_rules.yaml

terraform/
├── main.tf
├── variables.tf
├── outputs.tf
└── modules/
    ├── server/
    ├── network/
    └── dns/

ops/
├── runbooks/
│   ├── deployment.md
│   ├── rollback.md
│   ├── disaster-recovery.md
│   └── ssh-key-rotation.md
├── scripts/
│   ├── deploy.sh
│   ├── rollback.sh
│   └── health-check.sh
└── monitoring/
    ├── grafana/
    └── prometheus/
```

### 12.2 Aufwandschätzung

| Komponente | Aufwand |
|------------|---------|
| Self-Healing Agent (hetzner_auto_healer.py) | 2 Tage |
| GitHub Actions Workflow | 1 Tag |
| Terraform Modules | 2 Tage |
| Monitoring Setup | 1 Tag |
| Runbooks & Dokumentation | 1 Tag |
| Testing & Integration | 2 Tage |
| **Gesamt** | **9 Tage** |

---

## 13. Konsequenzen

### 13.1 Positive Konsequenzen

1. **Reduzierte Downtime** – Automatische Behebung bekannter Fehler
2. **Schnelleres Recovery** – Dokumentierte Runbooks, automatisierte Rollbacks
3. **Reproduzierbarkeit** – Infrastruktur als Code, versioniert
4. **Transparenz** – Alle Deployment-Aktionen geloggt und auditierbar
5. **Skalierbarkeit** – Terraform ermöglicht einfache Server-Erweiterung

### 13.2 Negative Konsequenzen

1. **Komplexität** – Mehr bewegliche Teile, höhere Lernkurve
2. **Kosten** – Claude API für Fehleranalyse
3. **False Positives** – Auto-Fix könnte falschen Fix anwenden

### 13.3 Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Auto-Fix verschlimmert Problem | Niedrig | Hoch | Rollback immer verfügbar, Validation-Checks |
| Claude API nicht erreichbar | Niedrig | Mittel | Fallback auf pattern-basierte Fixes |
| Terraform State Lock | Mittel | Mittel | Auto-Unlock nach Timeout |
| SSH Key Compromise | Niedrig | Kritisch | Key Rotation, IP-Whitelisting |

---

## Appendix A: MCP Deployment Server

```python
# mcp-hub/deployment_mcp/server.py

from mcp import Server, Tool

server = Server("deployment-mcp")

@server.tool()
async def trigger_workflow(
    repo: str,
    workflow: str,
    ref: str = "main",
    inputs: dict = None
) -> dict:
    """Trigger a GitHub Actions workflow."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/dispatches",
            headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"},
            json={"ref": ref, "inputs": inputs or {}}
        )
        return {"status": "triggered", "ref": ref}

@server.tool()
async def get_deployment_status(
    repo: str,
    environment: str
) -> dict:
    """Get deployment status for an environment."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{repo}/deployments",
            headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"},
            params={"environment": environment}
        )
        deployments = response.json()
        if deployments:
            latest = deployments[0]
            return {
                "environment": environment,
                "status": latest["statuses_url"],
                "created_at": latest["created_at"],
                "sha": latest["sha"]
            }
        return {"environment": environment, "status": "no deployments"}
```

---

## Appendix B: Settings

```python
# settings/infrastructure.py

# Self-Healing Configuration
SELF_HEALING_ENABLED = True
SELF_HEALING_AUTO_FIX_CONFIDENCE_THRESHOLD = 85
SELF_HEALING_MAX_RETRIES = 3
SELF_HEALING_CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Deployment Configuration
DEPLOYMENT_STRATEGY = "rolling"  # or "blue-green"
DEPLOYMENT_HEALTH_CHECK_INTERVAL = 10  # seconds
DEPLOYMENT_HEALTH_CHECK_TIMEOUT = 300  # seconds
DEPLOYMENT_ROLLBACK_ON_FAILURE = True
DEPLOYMENT_KEEP_RELEASES = 20

# Monitoring
PROMETHEUS_ENABLED = True
PROMETHEUS_PORT = 9090
GRAFANA_ENABLED = True
ALERTMANAGER_ENABLED = True
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# Terraform
TERRAFORM_STATE_BACKEND = "s3"
TERRAFORM_STATE_BUCKET = "platform-terraform-state"
HETZNER_LOCATION = "nbg1"
```

---

**Letzte Aktualisierung:** 2026-02-01  
**Nächste Review:** 2026-03-01  
**Referenzen:**
- `concepts/hetzner_auto_healer.py`
- `concepts/github-workflow-self-healing.yml`
- `docs-infrastructure/README.md`
