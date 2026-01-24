# Story Engine - Deployment Guide

> **Focus**: Production Deployment, Infrastructure, Operations  
> **Status**: Production Planning  
> **Updated**: 2025-11-09

---

## 📋 Table of Contents

1. [Infrastructure Requirements](#infrastructure-requirements)
2. [Environment Setup](#environment-setup)
3. [Database Setup](#database-setup)
4. [Application Deployment](#application-deployment)
5. [Monitoring Setup](#monitoring-setup)
6. [Scaling Strategy](#scaling-strategy)

---

## 🏗️ Infrastructure Requirements

### Minimum Requirements

```yaml
Production Environment:
  App Server:
    CPU: 4 cores
    RAM: 16GB
    Storage: 100GB SSD
    
  Database (PostgreSQL):
    CPU: 4 cores
    RAM: 16GB
    Storage: 500GB SSD
    
  Redis:
    CPU: 2 cores
    RAM: 8GB
    
  Total Monthly Cost (AWS): ~$500-700
```

### Recommended Production Setup

```
┌─────────────────┐
│  Load Balancer  │  (AWS ALB / Nginx)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│ App 1 │ │ App 2 │  (Django + Gunicorn)
└───┬───┘ └──┬────┘
    │        │
    └───┬────┘
        │
   ┌────▼─────┐
   │PostgreSQL│  (Primary + Replica)
   └──────────┘
        │
   ┌────▼─────┐
   │  Redis   │  (Cache + Queue)
   └──────────┘
```

---

## 🔧 Environment Setup

### 1. Environment Variables

```bash
# .env.production
# Django
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql://user:pass@db-host:5432/storyengine
LANGGRAPH_DB_URI=postgresql://user:pass@db-host:5432/langgraph

# Redis
REDIS_URL=redis://redis-host:6379/0

# AI Models
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key

# Storage
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_STORAGE_BUCKET_NAME=storyengine-media
AWS_S3_REGION_NAME=us-east-1

# Monitoring
SENTRY_DSN=your-sentry-dsn
DATADOG_API_KEY=your-datadog-key

# Email
EMAIL_HOST=smtp.sendgrid.net
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-key
EMAIL_PORT=587
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

### 2. Django Settings

```python
# config/settings/production.py
from .base import *
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# Security
SECRET_KEY = env('SECRET_KEY')
DEBUG = False
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Database
DATABASES = {
    'default': env.db('DATABASE_URL'),
}
DATABASES['default']['CONN_MAX_AGE'] = 600
DATABASES['default']['OPTIONS'] = {
    'connect_timeout': 10,
    'options': '-c statement_timeout=30000'  # 30s
}

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50}
        }
    }
}

# Static Files (S3)
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME')
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/storyengine/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.story_engine': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Sentry Error Tracking
sentry_sdk.init(
    dsn=env('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    environment='production',
    traces_sample_rate=0.1,
    send_default_pii=False
)
```

---

## 💾 Database Setup

### PostgreSQL Configuration

```sql
-- Create databases
CREATE DATABASE storyengine;
CREATE DATABASE langgraph;

-- Create user
CREATE USER storyengine_user WITH PASSWORD 'secure-password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE storyengine TO storyengine_user;
GRANT ALL PRIVILEGES ON DATABASE langgraph TO storyengine_user;

-- Enable required extensions
\c storyengine
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For text search
CREATE EXTENSION IF NOT EXISTS btree_gin; -- For indexing

\c langgraph
CREATE EXTENSION IF NOT EXISTS btree_gin;
```

### Database Tuning (postgresql.conf)

```ini
# Connection
max_connections = 200
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 20MB
min_wal_size = 1GB
max_wal_size = 4GB

# Slow Query Logging
log_min_duration_statement = 1000  # Log queries > 1s
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
```

### Initial Migration

```bash
# Run on app server
python manage.py migrate
python manage.py migrate --database=langgraph

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --no-input
```

---

## 🚀 Application Deployment

### Docker Setup

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run gunicorn
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "gthread", \
     "--threads", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

### Docker Compose (Production)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    build: .
    image: storyengine:latest
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
    volumes:
      - static:/app/staticfiles
      - media:/app/mediafiles
    networks:
      - app-network
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 4G
  
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: storyengine
      POSTGRES_USER: storyengine_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - app-network
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 16G
  
  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    networks:
      - app-network
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - static:/var/www/static:ro
      - media:/var/www/media:ro
    depends_on:
      - app
    networks:
      - app-network

volumes:
  postgres-data:
  redis-data:
  static:
  media:

networks:
  app-network:
    driver: bridge
```

### Nginx Configuration

```nginx
# nginx/nginx.conf
upstream app_server {
    server app:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    client_max_body_size 100M;
    
    location /static/ {
        alias /var/www/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /var/www/media/;
        expires 1y;
        add_header Cache-Control "public";
    }
    
    location / {
        proxy_pass http://app_server;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
}
```

### Deployment Script

```bash
#!/bin/bash
# deploy.sh

set -e

echo "🚀 Starting deployment..."

# Pull latest code
git pull origin main

# Build new image
docker-compose -f docker-compose.prod.yml build

# Run migrations
docker-compose -f docker-compose.prod.yml run --rm app \
    python manage.py migrate --no-input

# Collect static files
docker-compose -f docker-compose.prod.yml run --rm app \
    python manage.py collectstatic --no-input

# Restart services (zero-downtime)
docker-compose -f docker-compose.prod.yml up -d --no-deps --scale app=4 app
sleep 10
docker-compose -f docker-compose.prod.yml up -d --no-deps --scale app=2 app

echo "✅ Deployment complete!"
```

---

## 📊 Monitoring Setup

### Application Monitoring (Sentry)

```python
# Already configured in settings/production.py
# View errors at: https://sentry.io/your-org/storyengine/
```

### Infrastructure Monitoring (Datadog)

```bash
# Install Datadog agent
DD_API_KEY=your-key DD_SITE="datadoghq.com" \
bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script.sh)"

# Configure
cat > /etc/datadog-agent/conf.d/postgres.d/conf.yaml <<EOF
init_config:
instances:
  - host: localhost
    port: 5432
    username: datadog
    password: ${DD_POSTGRES_PASSWORD}
    dbname: storyengine
EOF

# Restart
systemctl restart datadog-agent
```

### Custom Metrics

```python
# apps/story_engine/monitoring/metrics.py
from datadog import statsd

def track_chapter_generation(duration: float, success: bool):
    """Send metrics to Datadog"""
    
    statsd.increment(
        'storyengine.chapter.generated',
        tags=[f'success:{success}']
    )
    
    statsd.histogram(
        'storyengine.chapter.duration',
        duration,
        tags=[f'success:{success}']
    )

def track_agent_execution(agent: str, duration: float, tokens: int):
    """Track agent metrics"""
    
    statsd.histogram(
        'storyengine.agent.duration',
        duration,
        tags=[f'agent:{agent}']
    )
    
    statsd.histogram(
        'storyengine.agent.tokens',
        tokens,
        tags=[f'agent:{agent}']
    )
```

### Health Check Endpoint

```python
# apps/bfagent/views/health.py
from django.http import JsonResponse
from django.db import connection
from redis import Redis
import os

def health_check(request):
    """
    Health check for load balancer.
    
    Checks:
    - Database connectivity
    - Redis connectivity
    - Disk space
    """
    
    health = {
        'status': 'healthy',
        'checks': {}
    }
    
    # Database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health['checks']['database'] = 'ok'
    except Exception as e:
        health['checks']['database'] = f'error: {e}'
        health['status'] = 'unhealthy'
    
    # Redis
    try:
        r = Redis.from_url(os.environ['REDIS_URL'])
        r.ping()
        health['checks']['redis'] = 'ok'
    except Exception as e:
        health['checks']['redis'] = f'error: {e}'
        health['status'] = 'unhealthy'
    
    # Disk space
    stat = os.statvfs('/')
    free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
    health['checks']['disk_space_gb'] = round(free_gb, 2)
    
    if free_gb < 10:
        health['status'] = 'warning'
    
    status_code = 200 if health['status'] == 'healthy' else 503
    return JsonResponse(health, status=status_code)
```

---

## 📈 Scaling Strategy

### Horizontal Scaling (App Servers)

```bash
# Scale to 4 instances
docker-compose -f docker-compose.prod.yml up -d --scale app=4

# Or with Kubernetes
kubectl scale deployment storyengine-app --replicas=4
```

### Database Scaling

```yaml
# Read Replicas
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'storyengine',
        'USER': 'user',
        'PASSWORD': 'pass',
        'HOST': 'primary-db',
        'PORT': '5432',
    },
    'replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'storyengine',
        'USER': 'user',
        'PASSWORD': 'pass',
        'HOST': 'replica-db',
        'PORT': '5432',
    }
}

# Database Router
class PrimaryReplicaRouter:
    def db_for_read(self, model, **hints):
        return 'replica'
    
    def db_for_write(self, model, **hints):
        return 'default'
```

### Caching Strategy

```python
# View caching
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 15 minutes
def chapter_list_view(request):
    ...

# Query caching
from django.core.cache import cache

def get_story_bible(bible_id):
    cache_key = f'story_bible:{bible_id}'
    bible = cache.get(cache_key)
    
    if bible is None:
        bible = StoryBible.objects.get(id=bible_id)
        cache.set(cache_key, bible, timeout=3600)
    
    return bible
```

### Cost Optimization

```yaml
Strategies:
  1. Cache Aggressively:
     - Story bibles (rarely change)
     - Character profiles
     - Previous chapters
  
  2. Batch Operations:
     - Generate multiple chapters in parallel
     - Use cheaper models for drafts
  
  3. Use Spot Instances:
     - Non-critical workloads
     - Batch processing
  
  4. Monitor Token Usage:
     - Set budgets per story
     - Alert on anomalies
  
  5. Auto-scaling:
     - Scale down during low usage
     - Scale up during generation peaks
```

---

## 🔐 Security Checklist

```markdown
Pre-Launch Security:
- [ ] All secrets in environment variables
- [ ] HTTPS enforced
- [ ] HSTS enabled
- [ ] CSRF protection enabled
- [ ] SQL injection protected (ORM only)
- [ ] XSS protection enabled
- [ ] Rate limiting configured
- [ ] Database backups automated
- [ ] Firewall rules configured
- [ ] SSH keys only (no passwords)
- [ ] Monitoring alerts configured
- [ ] Sentry error tracking active
- [ ] Security headers configured
- [ ] Django admin secured
- [ ] API authentication required
```

---

## 📚 See Also

- [STORY_ENGINE_ARCHITECTURE.md](./STORY_ENGINE_ARCHITECTURE.md) - System architecture
- [MONITORING_LOGGING.md](./MONITORING_LOGGING.md) - Observability
- [PERFORMANCE_TUNING.md](./PERFORMANCE_TUNING.md) - Performance optimization

---

**Deployment Guide Version**: 1.0  
**Last Updated**: 2025-11-09  
**Status**: Production-Ready Guide
