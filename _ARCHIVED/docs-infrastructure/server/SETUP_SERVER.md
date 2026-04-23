# Server Setup Guide

## Voraussetzungen

- Hetzner Server (oder ähnlich) mit Ubuntu 22.04+
- Root-Zugang
- Domain `bfagent.de` mit DNS-Zugriff

## 1. Verzeichnisse anlegen

```bash
sudo mkdir -p /var/www/docs/{releases,versions}
sudo mkdir -p /var/www/letsencrypt
sudo mkdir -p /opt/docs
```

## 2. Deploy-User erstellen

```bash
# User anlegen
sudo adduser --disabled-password --gecos "" deploy

# Docker-Gruppe hinzufügen
sudo usermod -aG docker deploy

# Docs-Verzeichnis Ownership
sudo chown -R deploy:deploy /var/www/docs

# SSH-Key für GitHub Actions
sudo mkdir -p /home/deploy/.ssh
sudo touch /home/deploy/.ssh/authorized_keys
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
sudo chown -R deploy:deploy /home/deploy/.ssh

# Public Key hinzufügen (von GitHub Secrets)
echo "ssh-rsa AAAA..." | sudo tee -a /home/deploy/.ssh/authorized_keys
```

## 3. Docker installieren (falls nicht vorhanden)

```bash
# Docker installieren
curl -fsSL https://get.docker.com | sudo sh

# Docker Compose Plugin
sudo apt install docker-compose-plugin

# User zur Docker-Gruppe
sudo usermod -aG docker deploy
```

## 4. Docs Container starten

```bash
# Konfiguration kopieren
sudo cp -r server/* /opt/docs/
cd /opt/docs

# Initialen "current" Symlink erstellen (Placeholder)
sudo mkdir -p /var/www/docs/releases/initial
echo "<html><body><h1>Docs coming soon...</h1></body></html>" | sudo tee /var/www/docs/releases/initial/index.html
sudo ln -sfn /var/www/docs/releases/initial /var/www/docs/current

# Container starten
sudo docker compose up -d

# Status prüfen
sudo docker compose ps
sudo docker compose logs
```

## 5. SSL-Zertifikat (Wildcard)

### Option A: Cloudflare DNS (empfohlen)

```bash
# Certbot + Cloudflare Plugin
sudo apt install certbot python3-certbot-dns-cloudflare

# Cloudflare Credentials
sudo mkdir -p /etc/letsencrypt
sudo nano /etc/letsencrypt/cloudflare.ini
```

Inhalt:
```ini
dns_cloudflare_api_token = YOUR_CLOUDFLARE_API_TOKEN
```

```bash
# Berechtigungen
sudo chmod 600 /etc/letsencrypt/cloudflare.ini

# Wildcard-Zertifikat
sudo certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
  -d "bfagent.de" \
  -d "*.bfagent.de" \
  --preferred-challenges dns-01
```

### Option B: Manuelles DNS

```bash
sudo certbot certonly \
  --manual \
  --preferred-challenges dns \
  -d "bfagent.de" \
  -d "*.bfagent.de"
```

## 6. Host Nginx konfigurieren

```bash
# Nginx installieren (falls nicht vorhanden)
sudo apt install nginx

# vHost kopieren
sudo cp /opt/docs/nginx/docs.bfagent.de.conf /etc/nginx/sites-available/

# Aktivieren
sudo ln -sf /etc/nginx/sites-available/docs.bfagent.de.conf /etc/nginx/sites-enabled/

# Testen
sudo nginx -t

# Neuladen
sudo systemctl reload nginx
```

## 7. Firewall

```bash
# UFW aktivieren
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP (für Let's Encrypt)
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# Interne Ports NICHT öffnen (8081 bleibt localhost)
```

## 8. Automatische Zertifikatserneuerung

```bash
# Certbot Timer prüfen
sudo systemctl status certbot.timer

# Manueller Test
sudo certbot renew --dry-run
```

## 9. Testen

```bash
# Lokal auf Server
curl -I http://localhost:8081/
curl -s http://localhost:8081/build-info.txt

# Extern
curl -I https://docs.bfagent.de/
curl -s https://docs.bfagent.de/build-info.txt
```

## 10. GitHub Secrets setzen

Im Repository → Settings → Secrets and variables → Actions:

| Secret | Wert |
|--------|------|
| `HETZNER_HOST` | `your-server-ip` oder `docs.bfagent.de` |
| `HETZNER_USER` | `deploy` |
| `HETZNER_SSH_KEY` | Private Key (inkl. `-----BEGIN...`) |
| `HETZNER_PORT` | `22` (optional) |

## Troubleshooting

### Container startet nicht

```bash
# Logs prüfen
sudo docker compose logs docs

# Symlink prüfen
ls -la /var/www/docs/current
```

### 502 Bad Gateway

```bash
# Container läuft?
sudo docker compose ps

# Port belegt?
sudo ss -tlnp | grep 8081
```

### SSL-Fehler

```bash
# Zertifikat prüfen
sudo certbot certificates

# Manuell erneuern
sudo certbot renew
```

### Deploy schlägt fehl

```bash
# SSH-Verbindung testen (als deploy user)
ssh -i ~/.ssh/id_rsa deploy@your-server "echo OK"

# Berechtigungen prüfen
ls -la /var/www/docs/
```
