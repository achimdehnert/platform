# 🚀 BF Agent - Quick Start Guide

Schnellstart für Development und Production Setup.

---

## 📦 Development (5 Minuten)

### Windows

```powershell
# 1. PostgreSQL starten
docker-compose up -d

# 2. Dependencies installieren
pip install -r requirements-postgres.txt

# 3. Environment kopieren
copy .env.example .env

# 4. Migrationen
python manage.py migrate

# 5. Server starten
python manage.py runserver
```

✅ **Fertig!** → http://localhost:8000

---

## 🌐 Production (1 Stunde)

### Auf Hetzner Server

```bash
# 1. Server vorbereiten
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose nginx certbot python3-pip git

# 2. User erstellen
sudo adduser bfagent
sudo usermod -aG docker,sudo bfagent
su - bfagent

# 3. Repository clonen
mkdir -p /opt/bfagent-app
cd /opt/bfagent-app
git clone https://github.com/yourusername/bfagent.git .

# 4. Environment konfigurieren
cp .env.production.example .env.prod
nano .env.prod  # Domain, Passwords, API Keys eintragen

# 5. Services starten
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-postgres.txt

# 6. Django setup
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser

# 7. Systemd Service
sudo cp scripts/systemd/bfagent.service /etc/systemd/system/
sudo systemctl enable bfagent
sudo systemctl start bfagent

# 8. Nginx konfigurieren
sudo cp scripts/nginx/bfagent.conf /etc/nginx/sites-available/
# Domain in Datei anpassen!
sudo nano /etc/nginx/sites-available/bfagent.conf
sudo ln -s /etc/nginx/sites-available/bfagent.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 9. SSL Zertifikat
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 10. Backup einrichten
chmod +x scripts/backup.sh
crontab -e
# Eintragen: 0 3 * * * /opt/bfagent-app/scripts/backup.sh
```

✅ **Fertig!** → https://yourdomain.com

---

## ✅ Checkliste

### Development
- [ ] Docker läuft
- [ ] PostgreSQL erreichbar (Port 5432)
- [ ] Migrations durchgeführt
- [ ] Superuser erstellt
- [ ] `runserver` funktioniert

### Production
- [ ] Domain DNS konfiguriert
- [ ] `.env` mit Production-Werten
- [ ] SSL Zertifikat aktiv
- [ ] Health check: `curl https://yourdomain.com/health/`
- [ ] Backup läuft (Cron)
- [ ] Monitoring eingerichtet

---

## 🆘 Hilfe

### Development Probleme

**PostgreSQL verbindet nicht:**
```powershell
docker-compose down
docker-compose up -d
docker ps  # Prüfen ob Container läuft
```

**Port 8000 belegt:**
```powershell
python manage.py runserver 8001
```

### Production Probleme

**Service startet nicht:**
```bash
sudo journalctl -u bfagent -n 50
sudo systemctl status bfagent
```

**Nginx Fehler:**
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

**Datenbank Verbindung:**
```bash
docker exec -it bfagent_db psql -U bfagent bfagent_prod
```

---

## 📚 Nächste Schritte

1. **Development:**
   - [ ] Lies `SETUP_DEV_PROD.md` für Details
   - [ ] Konfiguriere IDE (VSCode/PyCharm)
   - [ ] Installiere Pre-commit Hooks

2. **Production:**
   - [ ] Lies `PRODUCTION_CHECKLIST.md` komplett durch
   - [ ] Richte Monitoring ein (UptimeRobot)
   - [ ] Teste Backup/Restore
   - [ ] Dokumentiere deine spezifischen Anpassungen

---

## 🔗 Links

- **Vollständige Anleitung:** `SETUP_DEV_PROD.md`
- **Production Checklist:** `PRODUCTION_CHECKLIST.md`
- **Scripts:** `../scripts/`
- **Docker Config:** `docker-compose.yml`
