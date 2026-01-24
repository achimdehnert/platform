# 🚀 BF Agent - Production Deployment Checklist

**Status:** Ready for Hetzner Deployment  
**Last Updated:** 2024-12-08  
**Target:** Stable Production Environment

---

## 📋 Pre-Deployment Checklist

### Phase 1: Server Setup (Day 1)

- [ ] **1.1 Server Provisioning**
  - [ ] Hetzner Server bestellt (min. CX21: 2 vCPU, 4GB RAM)
  - [ ] SSH Key hinterlegt
  - [ ] Firewall aktiviert
  - [ ] Domain DNS konfiguriert (A Record → Server IP)

- [ ] **1.2 Initial Server Configuration**
  ```bash
  # On Hetzner Server
  ssh root@your-server-ip
  
  # Update system
  apt update && apt upgrade -y
  
  # Install essentials
  apt install -y git vim curl wget htop ufw fail2ban
  
  # Install Docker
  curl -fsSL https://get.docker.com -o get-docker.sh
  sh get-docker.sh
  
  # Install Docker Compose
  apt install -y docker-compose
  
  # Install Python
  apt install -y python3.11 python3.11-venv python3-pip
  
  # Install Nginx
  apt install -y nginx certbot python3-certbot-nginx
  ```

- [ ] **1.3 User Setup**
  ```bash
  # Create bfagent user
  adduser bfagent
  usermod -aG docker bfagent
  usermod -aG sudo bfagent
  
  # Setup SSH for bfagent user
  mkdir -p /home/bfagent/.ssh
  cp /root/.ssh/authorized_keys /home/bfagent/.ssh/
  chown -R bfagent:bfagent /home/bfagent/.ssh
  chmod 700 /home/bfagent/.ssh
  chmod 600 /home/bfagent/.ssh/authorized_keys
  ```

- [ ] **1.4 Firewall Configuration**
  ```bash
  # Configure UFW
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow 22/tcp    # SSH
  ufw allow 80/tcp    # HTTP
  ufw allow 443/tcp   # HTTPS
  ufw enable
  
  # Verify
  ufw status
  ```

- [ ] **1.5 Fail2Ban Setup**
  ```bash
  # Configure fail2ban for SSH protection
  systemctl enable fail2ban
  systemctl start fail2ban
  ```

---

### Phase 2: Application Setup (Day 1-2)

- [ ] **2.1 Clone Repository**
  ```bash
  # Switch to bfagent user
  su - bfagent
  
  # Create directory structure
  mkdir -p /opt/bfagent
  cd /opt/bfagent
  
  # Clone repository
  git clone https://github.com/yourusername/bfagent.git .
  
  # Create required directories
  mkdir -p logs media staticfiles backups
  ```

- [ ] **2.2 Environment Configuration**
  ```bash
  # Copy production environment
  cp .env.production.example .env
  
  # Edit with real values
  nano .env
  ```
  
  **Required values to set:**
  - [ ] `DJANGO_SECRET_KEY` (generate: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
  - [ ] `DJANGO_ALLOWED_HOSTS` (your domain)
  - [ ] `POSTGRES_PASSWORD` (strong password)
  - [ ] `OPENAI_API_KEY` (if using)
  - [ ] `EMAIL_*` settings

- [ ] **2.3 Python Environment**
  ```bash
  # Create virtual environment
  python3.11 -m venv .venv
  source .venv/bin/activate
  
  # Install dependencies
  pip install --upgrade pip
  pip install -r requirements.txt
  pip install -r requirements-postgres.txt
  ```

- [ ] **2.4 Database Setup**
  ```bash
  # Start PostgreSQL via Docker
  docker-compose up -d postgres redis
  
  # Wait for DB to be ready
  sleep 10
  
  # Run migrations
  python manage.py migrate
  
  # Create superuser
  python manage.py createsuperuser
  
  # Load initial data (if any)
  # python manage.py loaddata initial_data.json
  ```

- [ ] **2.5 Static Files**
  ```bash
  # Collect static files
  python manage.py collectstatic --noinput
  
  # Verify
  ls -la staticfiles/
  ```

---

### Phase 3: Service Configuration (Day 2)

- [ ] **3.1 Systemd Service**
  ```bash
  # Create service file (as root)
  sudo cp /opt/bfagent/scripts/systemd/bfagent.service /etc/systemd/system/
  
  # Reload systemd
  sudo systemctl daemon-reload
  
  # Enable service
  sudo systemctl enable bfagent
  
  # Start service
  sudo systemctl start bfagent
  
  # Check status
  sudo systemctl status bfagent
  
  # View logs
  sudo journalctl -u bfagent -f
  ```

- [ ] **3.2 Nginx Configuration**
  ```bash
  # Copy nginx config (as root)
  sudo cp /opt/bfagent/scripts/nginx/bfagent.conf /etc/nginx/sites-available/
  
  # Edit with your domain
  sudo nano /etc/nginx/sites-available/bfagent.conf
  
  # Enable site
  sudo ln -s /etc/nginx/sites-available/bfagent.conf /etc/nginx/sites-enabled/
  
  # Remove default site
  sudo rm /etc/nginx/sites-enabled/default
  
  # Test configuration
  sudo nginx -t
  
  # Restart nginx
  sudo systemctl restart nginx
  ```

- [ ] **3.3 SSL Certificate**
  ```bash
  # Get certificate
  sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
  
  # Test auto-renewal
  sudo certbot renew --dry-run
  
  # Verify HTTPS
  curl https://yourdomain.com/health/
  ```

- [ ] **3.4 Backup Setup**
  ```bash
  # Make backup script executable
  chmod +x /opt/bfagent-app/scripts/backup.sh
  
  # Test backup
  /opt/bfagent-app/scripts/backup.sh
  
  # Add to crontab
  crontab -e
  # Add: 0 3 * * * /opt/bfagent-app/scripts/backup.sh
  ```

---

### Phase 4: Monitoring & Security (Day 2-3)

- [ ] **4.1 Health Check**
  - [ ] Health endpoint funktioniert: `curl https://yourdomain.com/health/`
  - [ ] Database check: OK
  - [ ] Cache check: OK

- [ ] **4.2 Uptime Monitoring**
  - [ ] UptimeRobot Account erstellt
  - [ ] Monitor für `/health/` endpoint eingerichtet
  - [ ] Alert Email konfiguriert

- [ ] **4.3 Error Tracking**
  - [ ] Sentry Account erstellt (optional)
  - [ ] `SENTRY_DSN` in `.env` eingetragen
  - [ ] Test error gesendet

- [ ] **4.4 Log Rotation**
  ```bash
  # Install logrotate config
  sudo cp /opt/bfagent/scripts/logrotate/bfagent /etc/logrotate.d/
  
  # Test
  sudo logrotate -f /etc/logrotate.d/bfagent
  ```

- [ ] **4.5 Security Scan**
  ```bash
  # Django security check
  python manage.py check --deploy
  
  # Should show: System check identified no issues
  ```

---

### Phase 5: Testing (Day 3)

- [ ] **5.1 Functional Tests**
  - [ ] Homepage lädt: ✅
  - [ ] Login funktioniert: ✅
  - [ ] Admin Panel erreichbar: ✅
  - [ ] Static files laden: ✅
  - [ ] Media uploads funktionieren: ✅

- [ ] **5.2 Performance Tests**
  - [ ] Response time < 500ms
  - [ ] Static files cachen
  - [ ] GZIP compression aktiv

- [ ] **5.3 Security Tests**
  - [ ] HTTPS erzwungen
  - [ ] Security headers vorhanden
  - [ ] Admin Panel nur über HTTPS
  - [ ] CSRF funktioniert
  - [ ] SQL Injection geschützt

- [ ] **5.4 Backup Tests**
  - [ ] Backup erstellt: ✅
  - [ ] Backup restore getestet: ✅
  - [ ] Offsite backup funktioniert: ✅

---

## 🎯 Go-Live Checklist

### Vor dem Launch

- [ ] Alle Tests bestanden
- [ ] Backup funktioniert
- [ ] Monitoring eingerichtet
- [ ] SSL Zertifikat gültig
- [ ] Deployment script getestet
- [ ] Rollback-Plan dokumentiert

### Launch

- [ ] DNS auf Production umschalten
- [ ] Erste Requests monitoren
- [ ] Logs prüfen (30 min)
- [ ] Performance prüfen
- [ ] Error rate checken

### Nach dem Launch (erste 24h)

- [ ] Stündlich Logs checken
- [ ] Uptime Monitor prüfen
- [ ] Performance Metrics ansehen
- [ ] Backup verify
- [ ] User Feedback sammeln

---

## 🔥 Emergency Contacts & Procedures

### Rollback Procedure

```bash
# 1. Switch to previous version
cd /opt/bfagent-app
git log --oneline -10  # Find previous commit
git checkout <previous-commit>

# 2. Restore database (if needed)
/opt/bfagent-app/scripts/restore.sh <backup-file>
# Optional: include media/static restores
# /opt/bfagent-app/scripts/restore.sh <backup-file> --with-volumes

# 3. Restart services
docker compose -f /opt/bfagent-app/docker-compose.prod.yml --env-file /opt/bfagent-app/.env.prod up -d

# 4. Verify
curl https://yourdomain.com/health/
```

### Emergency Shutdown

```bash
# Stop application
sudo systemctl stop bfagent

# Stop database
docker-compose down

# Show maintenance page
sudo cp /opt/bfagent/maintenance.html /var/www/html/
```

### Key Contacts

- **Hosting:** Hetzner Support
- **Domain:** Your registrar
- **SSL:** Let's Encrypt
- **Email:** Your email provider
- **Monitoring:** UptimeRobot alerts

---

## 📊 Post-Launch Monitoring (First Week)

### Daily Checks
- [ ] Check uptime monitor
- [ ] Review error logs
- [ ] Check disk space: `df -h`
- [ ] Check memory: `free -h`
- [ ] Verify backups: `ls -lh /var/backups/bfagent/`

### Weekly Checks
- [ ] Update system: `apt update && apt upgrade`
- [ ] Review access logs
- [ ] Check certificate expiry: `certbot certificates`
- [ ] Test backup restore
- [ ] Performance review

---

## ✅ Sign-Off

**Deployment Lead:** _________________  
**Date:** _________________  
**Production URL:** _________________  
**Status:** _________________

**Notes:**
_____________________________________________________________________
_____________________________________________________________________
_____________________________________________________________________

---

## 📚 Quick Reference

### Useful Commands

```bash
# Service management
sudo systemctl status bfagent
sudo systemctl restart bfagent
sudo systemctl stop bfagent

# View logs
sudo journalctl -u bfagent -f
tail -f /var/log/bfagent/error.log

# Database
docker exec -it bfagent_db psql -U bfagent bfagent_prod

# Django management
cd /opt/bfagent && source .venv/bin/activate
python manage.py shell
python manage.py migrate
python manage.py createsuperuser

# Nginx
sudo nginx -t
sudo systemctl restart nginx
sudo tail -f /var/log/nginx/error.log

# SSL
sudo certbot renew
sudo certbot certificates
```

### Important Paths

- Application: `/opt/bfagent-app/`
- Logs: `/var/log/bfagent/`
- Backups: `/var/backups/bfagent/`
- Static files: Docker volume `bfagent_static_prod`
- Media files: Docker volume `bfagent_media_prod`
- Nginx config: `/etc/nginx/sites-available/bfagent.conf`
- Systemd service: `/etc/systemd/system/bfagent.service`
