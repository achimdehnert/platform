# BF Agent - Development & Production Setup

Complete guide for setting up separated Development and Production environments with PostgreSQL.

---

## Quick Start (5 Minuten)

```powershell
# 1. Install PostgreSQL driver
pip install -r requirements-postgres.txt

# 2. Start PostgreSQL via Docker
docker-compose up -d

# 3. Create .env file
copy .env.example .env

# 4. Run migrations
python manage.py migrate

# 5. Start server
python manage.py runserver
```

---

## Detailed Setup

### Step 1: Install Requirements

```powershell
pip install -r requirements-postgres.txt
```

This installs:
- `psycopg2-binary` - PostgreSQL adapter
- `python-dotenv` - Environment variables
- `redis` - Cache backend
- `gunicorn` - Production server
- `whitenoise` - Static files

### Step 2: Docker Setup

Start PostgreSQL and Redis:

```powershell
# Start services
docker-compose up -d

# Verify running
docker ps

# Expected output:
# CONTAINER ID   IMAGE                  STATUS         PORTS
# xxx            postgres:16-alpine     Up             0.0.0.0:5432->5432/tcp
# xxx            redis:7-alpine         Up             0.0.0.0:6379->6379/tcp
```

Optional: Start pgAdmin (Web UI):

```powershell
docker-compose --profile tools up -d

# Access: http://localhost:5050
# Email: admin@bfagent.local
# Password: admin
```

### Step 3: Environment Configuration

```powershell
# Copy example file
copy .env.example .env

# Edit .env with your values (optional for development)
notepad .env
```

Default development values work out of the box.

### Step 4: Update Settings

Copy the new settings files:

```
config/settings/
├── __init__.py      # Environment loader
├── base.py          # Your existing base settings
├── development.py   # Development settings (PostgreSQL)
└── production.py    # Production settings (Hetzner)
```

### Step 5: Migrate Database

**Option A: Fresh start (no existing data)**

```powershell
python manage.py migrate
python manage.py createsuperuser
```

**Option B: Migrate from SQLite**

```powershell
# Export from SQLite, import to PostgreSQL
python scripts/migrate_sqlite_to_postgres.py
```

### Step 6: Verify

```powershell
python manage.py runserver
```

You should see:

```
╔══════════════════════════════════════════════════════════════════╗
║  BF Agent - Development Environment                              ║
╠══════════════════════════════════════════════════════════════════╣
║  Database: PostgreSQL                                            ║
║  Host: localhost:5432                                            ║
║  Name: bfagent_dev                                               ║
║  Debug: True                                                     ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## File Structure

```
bfagent/
├── docker-compose.yml          # Docker services
├── .env                        # Local environment (git-ignored)
├── .env.example                # Example environment
├── .env.production.example     # Production example
├── requirements-postgres.txt   # PostgreSQL requirements
├── config/
│   └── settings/
│       ├── __init__.py        # Loads dev or prod
│       ├── base.py            # Shared settings
│       ├── development.py     # Dev settings
│       └── production.py      # Prod settings
├── docker/
│   └── postgres/
│       └── init/
│           └── 01_init.sql    # DB init script
└── scripts/
    └── migrate_sqlite_to_postgres.py
```

---

## Common Commands

### Docker

```powershell
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f postgres

# Connect to PostgreSQL
docker exec -it bfagent_db psql -U bfagent -d bfagent_dev

# Backup database
docker exec bfagent_db pg_dump -U bfagent bfagent_dev > backup.sql

# Restore database
docker exec -i bfagent_db psql -U bfagent bfagent_dev < backup.sql
```

### Django

```powershell
# Run with development settings (default)
python manage.py runserver

# Run with production settings
$env:DJANGO_ENV="production"
python manage.py runserver

# Check deployment readiness
python manage.py check --deploy
```

---

## Production Deployment (Hetzner)

### 1. Server Setup

```bash
# On Hetzner server
sudo apt update
sudo apt install docker.io docker-compose python3-pip nginx certbot

# Clone repository
git clone https://github.com/yourusername/bfagent.git
cd bfagent

# Create production environment
cp .env.production.example .env
nano .env  # Edit with production values
```

### 2. Environment Variables

Required production variables:

```bash
DJANGO_ENV=production
DJANGO_SECRET_KEY=your-very-long-random-secret-key
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

POSTGRES_DB=bfagent_prod
POSTGRES_USER=bfagent
POSTGRES_PASSWORD=super-secure-password
POSTGRES_HOST=localhost

REDIS_URL=redis://localhost:6379/0
```

### 3. Start Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-postgres.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start with Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### 4. Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location /static/ {
        alias /path/to/bfagent/staticfiles/;
    }
    
    location /media/ {
        alias /path/to/bfagent/media/;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. SSL with Let's Encrypt

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## Troubleshooting

### PostgreSQL connection refused

```powershell
# Check if Docker is running
docker ps

# Check PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Permission denied on Windows

```powershell
# Run Docker Desktop as Administrator
# Or add your user to docker-users group
```

### Migration conflicts

```powershell
# Reset migrations (development only!)
python manage.py migrate --fake-initial
```

### Redis connection error

```powershell
# Development works without Redis (uses memory cache)
# For production, ensure Redis is running:
docker-compose logs redis
```

---

## Security Checklist

- [ ] Change default database password in `.env`
- [ ] Generate strong `DJANGO_SECRET_KEY` for production
- [ ] Never commit `.env` files to git
- [ ] Enable HTTPS in production
- [ ] Set `DEBUG=False` in production
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Set up database backups
- [ ] Enable Sentry error tracking

---

## Support

For issues:
1. Check Docker logs: `docker-compose logs`
2. Check Django logs: `python manage.py runserver --verbosity 2`
3. Verify environment: `python -c "import os; print(os.environ.get('DJANGO_ENV'))"`
